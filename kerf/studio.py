"""Kerf Studio: a local web app to run and control Kerf Forge (`kerf studio`, opens http://127.0.0.1:8765).

Everything goes through the same engine and CLI as the terminal; the studio only starts jobs and shows results.
  - projects: status (build / review / eval), 3D viewer, requirements, problems, BOM, docs, downloadable files
  - parameters: sliders from project.yaml `params` (value/min/max/step/label). "Try" builds a scratch copy with the
    new values (the real project and its review are untouched); "Save" writes the values into project.yaml (that
    makes the review stale, which the page says); "Reset" goes back to the file.
  - actions: check, build, open plates in Bambu Studio, show the folder
  - new design: a description goes to Claude Code (`claude -p "/kerf ..."`) running in the repo; its progress streams
    into the page and the project appears in the list when its folder exists
  - change something: an edit request (from the 3D viewer's "Do it" or typed) goes to Claude Code as a scoped job on that
    project (KERF_STUDIO_JOB: the stop gate judges it on that project alone)
  - duplicate / remix: copy a project's design files under a new name, optionally with a change for Claude Code
  - materials: per printed part, tried and saved like parameters
  - compare: any build's geometry (kept per version) or the saved design next to a Try, as per-vertex distances
  - thumbnails: the viewer's own picture of the model, kept per geometry fingerprint
  - notifications: a desktop notification (macOS / notify-send) when a long job ends; the page also chimes
  - follow live: a project's 3D view updates part by part while cloud sessions push to it (kerf/live.py)
  - work: shared claims, Codex sessions and Studio jobs, with activity, progress and source freshness
Stdlib only (http.server + subprocess). Binds to 127.0.0.1: nothing is reachable from other machines.
"""
from __future__ import annotations

import json
import mimetypes
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from . import agent

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
TRIALS = ROOT / ".cache" / "studio"
ASSETS = Path(__file__).resolve().parent / "assets"
PY = sys.executable
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


# ---------------------------------------------------------------- jobs
class Job:
    def __init__(self, kind: str, project: str, cmd: list[str], label: str, parse=None, env=None):
        self.id = uuid.uuid4().hex[:10]
        self.kind, self.project, self.cmd, self.label, self.parse = kind, project, cmd, label, parse
        self.lines: list[str] = []
        self.events: list[dict] = []
        self.state = "running"
        self._stop_state: str | None = None
        self.started, self.ended = time.time(), None
        self.result: dict | None = None
        self.mode: str | None = None            # kerf run --mode (kerf/modes.py) when the job is a mode run
        self.session: str | None = None         # Claude Code session id (stream-json), so a cut-off run can resume
        self.usage: dict | None = None          # {text, until}: Claude usage ran out during this job
        self.resumed_by: str | None = None
        self.env = env
        self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     bufsize=1, env={**os.environ, **(env or {})}, start_new_session=True)
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for raw in self.proc.stdout:
            for ln in (self.parse(raw) if self.parse else [raw.rstrip("\n")]):
                if ln is None:
                    continue
                if ln.startswith("@@"):
                    try:
                        ev = json.loads(ln[2:])
                        if ev.get("k") == "session":
                            self.session = ev.get("id") or self.session
                            continue
                        if ev.get("k") == "usage":
                            self.usage = ev
                            USAGE.update(until=max(USAGE["until"], float(ev.get("until") or 0)), text=ev.get("text", ""))
                        self.events.append(ev)
                        if ev.get("k") == "hint":   # can't succeed: stop now, say why
                            with JOB_LOCK:
                                if self._stop_state is None:
                                    self._stop_state = "failed"
                                    try:
                                        os.killpg(self.proc.pid, 15)
                                    except Exception:  # noqa: BLE001
                                        self.proc.terminate()
                        continue
                    except Exception:  # noqa: BLE001
                        pass
                self.lines.append(ln)
        rc = self.proc.wait()
        with JOB_LOCK:
            self.ended = time.time()
            if rc and self._stop_state is None:
                self.lines.append(f"(stopped by signal {-rc}: out of memory or killed)" if rc < 0 else f"(exit code {rc})")
            self.state = self._stop_state or ("paused" if self.usage else "done" if rc == 0 else "failed")
            if self.state == "paused":
                self.lines.append(f"(paused: Claude usage ran out; it resumes around "
                                  f"{time.strftime('%-I:%M %p', time.localtime(float(self.usage.get('until') or time.time())))})")
        if self.state == "paused":
            schedule_resume(self)
        try:
            on_finished(self)
        except Exception:  # noqa: BLE001 - bookkeeping never breaks a job
            pass

    def stop(self):
        with JOB_LOCK:
            if self.state == "paused" and self._stop_state is None:
                self._stop_state, self.state = "stopped", "stopped"
                self.lines.append("Stopped; automatic resume cancelled.")
                successor = JOBS.get(self.resumed_by)
                if successor is not None and successor is not self:
                    successor.stop()  # A resume may have registered before this delayed Stop arrived.
            elif self.state == "running" and self._stop_state is None:
                # Keep project guards and UI polling active until the process has finished writing.
                self._stop_state = "stopped"
                self.lines.append("Stopping; waiting for the process to exit.")
                try:
                    os.killpg(self.proc.pid, 15)
                except Exception:  # noqa: BLE001
                    self.proc.terminate()

    def info(self, since: int = 0, esince: int = 0) -> dict:
        end = self.ended or time.time()
        return {"id": self.id, "kind": self.kind, "project": self.project, "label": self.label, "state": self.state,
                "usage": self.usage, "resumable": bool(self.state == "paused" and self.session and not self.resumed_by),
                "resumed_by": self.resumed_by, "agent": getattr(self, "agent", "claude"),
                "started": self.started, "seconds": round(end - self.started, 1), "lines": self.lines[since:],
                "n": len(self.lines), "events": self.events[esince:], "ne": len(self.events)}


JOBS: dict[str, Job] = {}
JOB_LOCK = threading.RLock()

# ---------------------------------------------------------------- run times + version history (.cache/studio)
TIMES = ROOT / ".cache" / "studio_times.json"
HISTORY = ROOT / ".cache" / "studio_history"


def _times() -> dict:
    try:
        return json.loads(TIMES.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def record_time(project: str, kind: str, seconds: float):
    t = _times()
    runs = t.setdefault(project, {}).setdefault(kind, [])
    runs.append(round(float(seconds), 1))
    del runs[:-5]
    TIMES.parent.mkdir(parents=True, exist_ok=True)
    TIMES.write_text(json.dumps(t, indent=1), encoding="utf-8")


def estimate(project: str, kind: str) -> float | None:
    """Seconds a build / check / mode run (kind "mode_<m>") of this project usually takes: median of its last runs from
    Studio (a Build kit falls back to Build's, Check it to Check's), else the last report's own run time for a build."""
    t = _times().get(project, {})
    runs = t.get(kind) or t.get({"mode_kit": "build", "mode_ship": "build", "mode_check": "check"}.get(kind, ""), []) or []
    if runs:
        return float(sorted(runs)[len(runs) // 2])
    if kind in ("mode_kit", "mode_ship"):
        kind = "build"
    rep = _report(PROJECTS / project)
    return float(rep["seconds"]) if kind == "build" and rep and rep.get("seconds") else None


def _git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20)
    return r.stdout.strip() if r.returncode == 0 else ""


def snapshot(name: str) -> dict | None:
    """One version entry after a build: the values, results and picture of this build, and the commit it was built
    from (with a flag if the project had uncommitted edits), under .cache/studio_history/<project>/<stamp>/."""
    d = PROJECTS / name
    rep = _report(d)
    if not rep:
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = HISTORY / name / stamp
    dst.mkdir(parents=True, exist_ok=True)
    ship = (rep.get("files") or {}).get("ship") or {}
    entry = {"stamp": stamp, "time": time.time(), "commit": _git("rev-parse", "--short", "HEAD"),
             "dirty": bool(_git("status", "--porcelain", "--", f"projects/{name}")),
             "fingerprint": rep.get("fingerprint"), "ok": rep.get("ok"), "problems": len(rep.get("problems") or []),
             "params": rep.get("params") or {}, "mass": rep.get("mass"), "cost": (ship.get("bom") or {}).get("total_usd"),
             "requirements": {r["id"]: {"value": r.get("value"), "ok": r.get("ok"), "unit": r.get("unit")}
                              for r in rep.get("requirements") or [] if not r.get("skipped")}}
    th = _thumb(d)
    if th:
        shutil.copy2(d / th, dst / "thumb.png")
        entry["thumb"] = f"{stamp}/thumb.png"
    try:                                  # the geometry, so any later build can be compared with this one
        g = viewer_geom(d / "out" / "viewer.html")
        if g:
            import gzip
            (dst / "geom.json.gz").write_bytes(gzip.compress(json.dumps(g).encode()))
            entry["geom"] = True
    except Exception:  # noqa: BLE001 - a version without geometry still lists its values and results
        pass
    (dst / "version.json").write_text(json.dumps(entry, indent=1, default=str), encoding="utf-8")
    return entry


def history(name: str) -> list[dict]:
    out = []
    for f in sorted((HISTORY / name).glob("*/version.json"), reverse=True)[:30]:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return out


def on_finished(job) -> None:
    try:
        notify_job(job)
    except Exception:  # noqa: BLE001 - a notification never breaks a job
        pass
    try:
        auto_fix(job)
    except Exception:  # noqa: BLE001 - starting the fix is best effort; the Fix button stays
        pass
    if job.state != "done" or job.project in ("*", None):
        return
    if job.kind in ("edit", "fix") and (PROJECTS / job.project / "out" / "report.json").exists():
        snapshot(job.project)            # Claude Code rebuilt it: a version entry, so the change can be compared
        return
    if job.kind not in ("build", "check"):
        return
    record_time(job.project, f"mode_{job.mode}" if job.mode else job.kind, (job.ended or time.time()) - job.started)
    if job.kind == "build":
        snapshot(job.project)


AUTOFIXED: dict = {}     # project -> fingerprint already handed to an automatic fix (one try per design state)


def fixable(name: str) -> tuple[bool, str]:
    """Whether a fix job makes sense now: the last report failed, the design is not mid-way (placeholder parts), and
    no fix is already running for it."""
    rep = _report(PROJECTS / name)
    if not rep or rep.get("ok"):
        return False, "the last build passed" if rep else "not built yet"
    if rep.get("stubs"):
        return False, "it is still being designed (placeholder parts): the designing session finishes it"
    if any(j.kind == "fix" and j.project == name and j.state == "running" for j in JOBS.values()):
        return False, "a fix is already running"
    if _worked_on(name):
        return False, "another session has claimed this project (see Activity)"
    return True, ""


def slug(name: str) -> str:
    """What a typed project name becomes: 'Hawk Drone' -> 'hawk_drone' (lowercase, spaces and dashes to _)."""
    s = re.sub(r"[\s\-]+", "_", str(name).strip().lower())
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9_]", "", s)).strip("_")


class Claimed(ValueError):
    """Changing a project another session is editing: allowed only when the user confirms (override)."""


def guard_claimed(name: str, override: bool):
    if not override and _worked_on(name):
        raise Claimed("Another session has claimed this project (see Activity). Changing it here "
                      "can clash with its edits. Change it anyway?")


def fix_job(name: str) -> Job:
    """Claude Code fixes every problem of the last failed build: the mechanical ones with `kerf fixes --apply`, the
    rest at their cause, then check, build, review, commit (same rules as a change request)."""
    ok, why = fixable(name)
    if not ok:
        raise ValueError(f"nothing to fix: {why}")
    ready = claude_ready()
    if not ready["ok"]:
        raise ClaudeNotReady(ready)
    rep = _report(PROJECTS / name) or {}
    probs = rep.get("problems") or []
    listing = "\n".join(f"- {p}" for p in probs[:40]) + (f"\n- ... and {len(probs) - 40} more (out/report.json)" if len(probs) > 40 else "")
    prompt = (f"Kerf Studio: the last build of projects/{name} failed. Spencer clicked Build and wants it FIXED, not reported. "
              f"Problems:\n{listing}\n\nFollowing CLAUDE.md: first `.venv/bin/kerf fixes {name} --apply` for the mechanical "
              f"ones; fix every other problem at its cause in the part that owns it (never loosen a check, threshold, catalog "
              f"value or test); run `.venv/bin/kerf check {name}` until it passes, then `.venv/bin/kerf build {name}`, read the "
              f"renders, get a design-reviewer pass, append a dated STATUS.md entry, commit and push. Before editing, run "
              f"`.venv/bin/python tools/claims.py list`: if another session holds this project's claim and pushed in the last "
              f"90 minutes, stop and say so instead of editing its files. Do not start other PLAN work.")
    return agent_job("fix", name, prompt, f"Fix {name}: {len(probs)} problem(s)", env={"KERF_STUDIO_JOB": name})


def auto_fix(job) -> Job | None:
    """A Studio build / check that ends with problems starts a fix job by itself (setting `autofix`, on by default),
    once per design state, so a failed Build goes straight to fixing instead of a list to read."""
    if job.kind not in ("build", "check") or job.project in ("*", None) or not settings().get("autofix"):
        return None
    if budget_stop() or not pick_agent() or (pick_agent() == "claude" and usage_blocked()):
        return None                       # budget switch on, or no agent can run now (Claude out of usage, no Codex)
    rep = _report(PROJECTS / job.project)
    ok, _ = fixable(job.project)
    if not ok:
        return None
    fp = (rep or {}).get("fingerprint")
    if fp and AUTOFIXED.get(job.project) == fp:
        return None                       # this exact design already had its automatic try: the button is still there
    AUTOFIXED[job.project] = fp
    return fix_job(job.project)


def printer_info(live: bool = False) -> dict:
    """The Bambu printer Kerf sends plates to (~/.kerf/bambu.json; the access code is never sent to the page)."""
    from . import bambu
    p = (bambu.load_config() or {}).get("printer") or {}
    out = {"configured": bool(p.get("host") and p.get("serial") and p.get("access_code")), "host": p.get("host"),
           "serial": p.get("serial")}
    if live and out["configured"]:
        try:
            out["status"] = bambu.status()
        except Exception as e:  # noqa: BLE001
            out["error"] = str(e)
    return out


def printer_setup(host: str, code: str, serial=None) -> dict:
    """Connect to the printer on this Mac's network (LAN Only + Developer Mode), prove the login, save the config."""
    from . import bambu
    import ipaddress
    host, code = host.strip(), "".join(code.split())          # "1234 5678" pasted with a space is the same code
    try:
        ipaddress.ip_address(host)
    except ValueError:
        raise ValueError("printer IP: four numbers like 192.168.1.50 (printer screen: Settings > LAN Only)")
    if not code:
        raise ValueError("the access code from the printer's LAN Only screen")
    r = bambu.setup_printer(host, code, (str(serial).strip() or None) if serial else None, say=lambda s: None)
    return {"configured": True, "host": host, "serial": r["serial"], "status": r["status"]}


def restore(name: str, stamp: str) -> list[str]:
    """One-click revert of a version's parameter values (project.yaml params only; part code is never touched)."""
    f = HISTORY / name / stamp / "version.json"
    if not re.fullmatch(r"\d{8}-\d{6}", stamp) or not f.exists():
        raise ValueError("no such version")
    vals = json.loads(f.read_text(encoding="utf-8")).get("params") or {}
    known = {k for k, v in ((_read_yaml(name).get("params") or {}).items())
             if isinstance((v.get("value") if isinstance(v, dict) else v), (int, float))}
    return write_params(PROJECTS / name / "project.yaml", {k: v for k, v in vals.items() if k in known})


EXPORT_DIRS = ("plates", "parts", "drawings", "firmware", "assembly_steps")
EXPORT_FILES = ("assembly.step", "bom.csv", "bom.md", "ASSEMBLY.md", "WIRING.md", "wiring.svg", "viewer.html")


def export_zip(name: str) -> bytes:
    """Everything a maker needs in one zip: print plates and parts, STEP, BOM, guides, drawings, bring-up program,
    plus the design files (project.yaml, DESIGN.md, part sources)."""
    import io
    import zipfile
    d = PROJECTS / name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in EXPORT_DIRS:
            for f in sorted((d / "out" / rel).rglob("*")) if (d / "out" / rel).exists() else []:
                if f.is_file() and f.suffix != ".glb":
                    z.write(f, f"{name}/{f.relative_to(d / 'out')}")
        for rel in EXPORT_FILES:
            if (d / "out" / rel).exists():
                z.write(d / "out" / rel, f"{name}/{rel}")
        for f in ["project.yaml", "DESIGN.md", "REFERENCES.md", *[str(x.relative_to(d)) for x in sorted((d / "parts").glob("*.py"))]]:
            if (d / f).exists():
                z.write(d / f, f"{name}/design/{f}")
    return buf.getvalue()


UNIT_HINTS = (("deg", "°"), ("angle", "°"), ("teeth", "teeth"), ("count", ""))


def param_unit(key: str, spec: dict) -> tuple[str, bool]:
    """(unit, assumed). `unit:` in project.yaml wins; otherwise degrees/teeth when the label says so, else mm (every
    length in Kerf is mm) - flagged as assumed so the page can say so."""
    if spec.get("unit") is not None:
        return str(spec["unit"]), False
    words = f"{key} {spec.get('label', '')}".lower()
    for hint, unit in UNIT_HINTS:
        if hint in words:
            return unit, True
    return "mm", True


def param_effects(name: str) -> dict:
    """Which parts and requirement checks each parameter reaches: a part whose source (or the shared layout) names the
    parameter, and every requirement on those parts or whose own fields name it."""
    d = PROJECTS / name
    data = _read_yaml(name)
    params = list((data.get("params") or {}).keys())
    srcs = {f.stem: f.read_text(encoding="utf-8") for f in (d / "parts").glob("*.py")} if (d / "parts").exists() else {}
    layout = srcs.pop("layout", "")
    parts_of = {}
    for item, spec in (data.get("parts") or {}).items():
        src_name = (spec or {}).get("source", item) if isinstance(spec, dict) else item
        parts_of.setdefault(Path(str(src_name)).stem, []).append(item)
    derived = " ".join(str(v) for v in (data.get("derived") or {}).values())
    out = {}
    for k in params:
        word = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(k)}(?![A-Za-z0-9_])")
        via_layout = bool(word.search(layout) or word.search(derived))
        parts = sorted({it for src, txt in srcs.items() if word.search(txt) or via_layout for it in parts_of.get(src, [src])})
        checks = sorted({r.get("id") for r in data.get("requirements") or []
                         if r.get("part") in parts or word.search(json.dumps({x: y for x, y in r.items() if x not in ("id", "why")}))})
        out[k] = {"parts": parts, "checks": checks, "layout": via_layout}
    return out

# Lifetime: with an idle limit the server quits on its own once no window has talked to it for that long (pages poll
# every few seconds; a closing page says goodbye, which shortens the wait to a few seconds) and no job is running.
LIFE = {"last": time.time(), "bye": None, "seen": False, "native": 0.0}   # native: last poll from the Mac app's page


def _alive():
    """A window talked to us. A request landing right after a goodbye is usually the closing page's own last poll,
    so it doesn't cancel the goodbye; a window that is really still open polls again within a few seconds."""
    now = time.time()
    LIFE.update(last=now, seen=True)
    if LIFE["bye"] and now - LIFE["bye"] > 2.0:
        LIFE["bye"] = None


def busy() -> bool:
    return any(j.state == "running" for j in JOBS.values())


def require_idle(project: str):
    for current in JOBS.values():
        if current.state == "running" and (project == "*" or current.project in (project, "*")):
            raise ValueError(f"{current.label} is already running. Open Activity to follow it or stop it before changing this project.")


CLAUDE_KINDS = ("design", "edit", "fix", "quote")


def start_job(*a, **k) -> Job:
    prepare = k.pop("prepare", None)
    project = a[1] if len(a) > 1 else k["project"]
    kind = a[0] if a else k["kind"]
    cmd = a[2] if len(a) > 2 else k.get("cmd")
    if kind in CLAUDE_KINDS:
        who = agent.who_runs(cmd or [])
        why = usage_blocked() if who == "claude" else ""
        if why:
            raise ValueError(f"{why}. Kerf waits instead of starting work that would be cut off; try again then "
                             f"(a paused job resumes by itself), or install ChatGPT Codex so it takes over.")
        if cmd and who == "claude" and len(cmd) > 2 and cmd[1] == "-p" and CUTOFF_NOTE not in cmd[2]:
            cmd[2] = cmd[2] + CUTOFF_NOTE
        elif cmd and who == "codex" and CUTOFF_NOTE not in cmd[-1]:
            cmd[-1] = cmd[-1] + CUTOFF_NOTE
    with JOB_LOCK:
        require_idle(project)
        if prepare:
            prepare()
        if (k.get("env") or {}).get("KERF_STUDIO_JOB"):   # steering from "How Kerf decided" belongs to one job
            from . import steer
            steer.reset(project)
        j = Job(*a, **k)
        JOBS[j.id] = j
        return j


def resume_job(jid: str, auto: bool = False) -> Job:
    """Continue a job Claude's usage limit paused: the same Claude session, told to pick up where it stopped."""
    if auto:
        stop = budget_stop()
        if stop:
            raise ValueError(f"not resumed automatically: the budget switch is on ({stop})")
    with JOB_LOCK:
        if auto and not settings().get("autoresume", True):
            raise ValueError("automatic resume is off")
        old = JOBS.get(jid)
        if not old or old.state != "paused" or getattr(old, "_stop_state", None) or not old.session:
            raise ValueError("nothing to resume: that job isn't paused by a usage limit")
        if old.resumed_by:
            raise ValueError("it was resumed already")
        USAGE["until"] = 0.0                       # the person (or the reset timer) says usage is back: let it try
        msg = ("You were cut off by the Claude usage limit. Continue exactly where you left off: look at `git status`, the last "
               "commits and STATUS.md, finish the task you were given, then check, commit and push.")
        if getattr(old, "agent", "claude") == "claude" and usage_blocked() and agent.can_take_over():
            j = codex_takeover(old)              # Claude still out: Codex continues the same task from git
        else:
            j = agent_job(old.kind, old.project, msg, f"{old.label} (resumed)", env=old.env, resume=old.session,
                          who=getattr(old, "agent", "claude"))
        old.resumed_by = j.id
        return j


def agent_job(kind: str, name: str, prompt: str, label: str, resume: str | None = None, who: str | None = None,
              **k) -> Job:
    """Start an AI job with whichever agent can run now (kerf/agent.py: Claude Code, or ChatGPT Codex when Claude's
    usage is out or Spencer picked Codex). `resume` continues that agent's own session."""
    who = who or pick_agent()
    if not who:
        raise ValueError("No AI agent can run: install Claude Code or ChatGPT Codex (or wait for Claude's usage to reset).")
    j = start_job(kind, name, agent.command(who, prompt, resume, claude_exe=claude_bin()), label,
                  parse=agent.codex_lines if who == "codex" else _claude_lines, **k)
    try:
        j.agent = who
    except AttributeError:                   # a stand-in job (tests) without attributes
        pass
    return j


def pick_agent() -> str | None:
    """Claude Code or ChatGPT Codex for the next AI job (kerf/agent.py)."""
    return agent.pick(usage_blocked(), has_claude=bool(claude_bin()))


def codex_takeover(old) -> Job:
    """A Claude job the usage limit paused, continued by Codex (a new session: it picks up from git, not from Claude's
    conversation). Spencer, 2026-11-02: Codex takes over when Claude runs out."""
    with JOB_LOCK:
        if old.state != "paused" or getattr(old, "_stop_state", None) or old.resumed_by:
            raise ValueError("nothing to take over: that job isn't waiting on usage")
        msg = (f"Claude Code was working on this Kerf Studio task and ran out of usage: \"{old.label}\" (projects/{old.project}). "
               f"Take over and finish it. Look at `git status`, `git log --oneline -15`, the newest STATUS.md entries, "
               f"`.venv/bin/python tools/claims.py list` and the project's DESIGN.md first; keep Claude's work and continue from it.")
        request = getattr(old, "request", None)
        if request:
            msg += f"\nThe original request: {request}"
        j = agent_job(old.kind, old.project, msg, f"{old.label} (Codex took over)", env=old.env, who="codex")
        old.resumed_by = j.id
        return j


def schedule_resume(job, delay: float | None = None):
    """Resume a usage-paused job, or hand it to Codex, unless an explicit Stop won the job lock."""
    enabled = settings().get("autoresume", True)
    takeover = enabled and getattr(job, "agent", "claude") == "claude" and agent.can_take_over() and not budget_stop()
    with JOB_LOCK:
        if job.state != "paused" or getattr(job, "_stop_state", None) or job.resumed_by:
            return
        if takeover:
            try:
                codex_takeover(job)
                job.lines.append("(Codex took over: Claude's usage ran out)")
                return
            except Exception as e:  # noqa: BLE001 - fall back to waiting for Claude
                job.lines.append(f"(Codex couldn't take over: {e})")
        if not enabled or not job.session:
            return
        wait = delay if delay is not None else max(60.0, float((job.usage or {}).get("until") or 0) - time.time() + 120)
        def go():
            if job.state == "paused" and not job.resumed_by:
                try:
                    resume_job(job.id, auto=True)
                except Exception as e:  # noqa: BLE001 - say why on the paused job; the Resume button still works
                    job.lines.append(f"(not resumed automatically: {e})")
        t = threading.Timer(wait, go)
        t.daemon = True
        t.start()


PROGRESS_ENV = {"KERF_PROGRESS": "1", "PYTHONUNBUFFERED": "1"}
STEERABLE = ("design", "edit", "fix")      # Claude Code jobs that read steering (kerf/steer.py)


MODE_LABEL = {"sketch": "Sketch", "print": "Print it", "check": "Check it", "simulate": "Simulate it",
              "kit": "Build kit", "ship": "Ship it"}


def mode_menu(name: str, rep: dict | None) -> list[dict]:
    """The depths Kerf can run this project at (kerf/modes.py), each with what it gives, its usual time (past runs) and
    what it costs: every mode runs on this computer with no Claude usage; Ship it also prints (filament)."""
    from . import modes
    n = _numbers(rep) if rep else {}
    out = []
    for m in modes.ORDER:
        cost = "free: runs on this computer, no Claude usage"
        if m == "ship":
            g = n.get("filament_g")
            cost = ("prints on your printer" + (f": about {g:.0f} g of filament" if isinstance(g, (int, float)) else "")
                    + "; needs a current design review")
        out.append({"mode": m, "label": MODE_LABEL[m], "gives": modes.GIVES[m], "estimate": estimate(name, f"mode_{m}"),
                    "cost": cost, "confirm": m == "ship"})
    return out


def kerf_cmd(*args) -> list[str]:
    return [PY, "-m", "kerf.cli", *args]


# ---------------------------------------------------------------- projects
def project_names() -> list[str]:
    return sorted(p.parent.name for p in PROJECTS.glob("*/project.yaml"))


def _read_yaml(name: str) -> dict:
    return yaml.safe_load((PROJECTS / name / "project.yaml").read_text(encoding="utf-8")) or {}


def _report(d: Path) -> dict | None:
    f = d / "out" / "report.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    except Exception:  # noqa: BLE001
        return None


def _review(name: str) -> dict:
    sys.path.insert(0, str(ROOT))
    from .cli import review_status
    try:
        return review_status(name)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "why": f"{type(e).__name__}: {e}", "fingerprint": None}


def _thumb(d: Path) -> str | None:
    for rel in ("out/renders/assembly_iso.png", "out/renders/assembly.png", "out/renders/assembly_sheet.png"):
        if (d / rel).exists():
            return rel
    pngs = sorted((d / "out" / "renders").glob("assembly*.png")) if (d / "out" / "renders").exists() else []
    return str(pngs[0].relative_to(d)) if pngs else None


def summary(name: str) -> dict:
    d = PROJECTS / name
    data = _read_yaml(name)
    rep = _report(d)
    rv = _review(name)
    running = [j.info()["label"] for j in JOBS.values() if j.project == name and j.state == "running"]
    th = thumb_info(name)
    return {"name": name, "title": data.get("name", name), "description": (data.get("description") or "").strip(),
            "built": rep is not None, "ok": bool(rep and rep.get("ok")),
            "picture": th["url"], "picture_stale": bool(rep and rep.get("fingerprint") != th["fingerprint"]),
            "fingerprint": rep.get("fingerprint") if rep else None, "has_viewer": (d / "out" / "viewer.html").exists(),
            "cost_usd": (_numbers(rep) or {}).get("cost_usd"), "device_g": ((rep or {}).get("mass") or {}).get("device_g"),
            "built_at": (d / "out" / "report.json").stat().st_mtime if rep else None,
            "problems": len(rep.get("problems", [])) if rep else None,
            "stubs": len(rep.get("stubs") or []) if rep else 0,       # placeholder parts: the design is still in progress
            "stale": bool(rep and rv.get("fingerprint") and rep.get("fingerprint") != rv.get("fingerprint")),
            "review": rv, "thumb": _thumb(d), "running": running, "build_s": estimate(name, "build"),
            "worked_on": bool(rep and not rep.get("ok") and _worked_on(name))}


def _worked_on(name: str) -> bool:
    """A fresh shared claim names this project; ownership does not imply a running process."""
    from . import explain
    try:
        return explain.work_status(name, [], explain.claims(ROOT))["state"] == "claimed"
    except Exception:  # noqa: BLE001
        return False


def detail(name: str) -> dict:
    d = PROJECTS / name
    data = _read_yaml(name)
    rep = _report(d) or {}
    try:
        effects = param_effects(name)
    except Exception:  # noqa: BLE001 - a hint, never a failed page
        effects = {}
    params = []
    for k, v in (data.get("params") or {}).items():
        spec = v if isinstance(v, dict) else {"value": v}
        val = spec.get("value")
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            continue
        lo = spec.get("min", round(val * 0.5, 3) if val else 0)
        hi = spec.get("max", round(val * 1.5, 3) if val else 10)
        unit, assumed = param_unit(k, spec)
        params.append({"key": k, "value": val, "min": lo, "max": hi, "step": spec.get("step", 0.1 if isinstance(val, float) else 1),
                       "label": spec.get("label", k), "bounded": "min" in spec and "max" in spec, "unit": unit,
                       "unit_assumed": assumed, "affects": effects.get(k)})
    files = []
    out = d / "out"
    if out.exists():
        for rel in ("plates", "parts", "drawings"):
            for f in sorted((out / rel).glob("*")) if (out / rel).exists() else []:
                if f.suffix in (".3mf", ".stl", ".md", ".pdf"):
                    files.append(str(f.relative_to(d)))
        for f in ("assembly.step", "bom.csv", "bom.md", "ASSEMBLY.md", "WIRING.md", "viewer.html", f"{name}_urdf.zip"):
            if (out / f).exists():
                files.append(f"out/{f}")
        for f in sorted((out / "firmware").rglob("*")) if (out / "firmware").exists() else []:   # bring-up program + BRINGUP.md
            if f.suffix in (".ino", ".py", ".md"):
                files.append(str(f.relative_to(d)))
    docs = [f for f in ("DESIGN.md", "REFERENCES.md", "out/ASSEMBLY.md", "out/WIRING.md", "out/firmware/BRINGUP.md", "out/bom.md",
                        "out/plates/PRINT_SETTINGS.md", "out/OPTIMISE.md") if (d / f).exists()]
    renders = sorted(str(p.relative_to(d)) for p in (out / "renders").glob("*.png")) if (out / "renders").exists() else []
    trial = TRIALS / name
    trial_rep = _report(trial) if (trial / "out" / "viewer.html").exists() else None
    return {**summary(name), "params": params, "files": files, "docs": docs, "renders": renders[:40],
            "report": {k: rep.get(k) for k in ("ok", "problems", "warnings", "maker_notes", "mass", "requirements", "bom", "seconds", "fingerprint", "stubs")} if rep else None,
            "viewer": "out/viewer.html" if (out / "viewer.html").exists() else None,
            "history": history(name),
            "live_on": bool(LIVE["follow"].get(name, {}).get("on")),
            "estimate": {"build": estimate(name, "build"), "check": estimate(name, "check")},
            "modes": mode_menu(name, rep), "last_mode": (rep.get("mode") or ("kit" if rep.get("files") else None)) if rep else None,
            "summary_numbers": _numbers(rep),
            "issues": explained(name, rep, data),
            "use_story": (rep or {}).get("use_story"),
            "can_optimise": bool((_yaml(d) or {}).get("optimise")),
            "materials": materials(), "part_materials": part_materials(name),
            "trial": {"params": trial_rep.get("params") if trial_rep else None, "ok": trial_rep.get("ok") if trial_rep else None,
                      "materials": {k: v.get("material") for k, v in (trial_rep.get("parts") or {}).items()} if trial_rep else None,
                      "mass": trial_rep.get("mass") if trial_rep else None,
                      "problems": trial_rep.get("problems") if trial_rep else None,
                      "requirements": trial_rep.get("requirements") if trial_rep else None} if trial_rep else None}


def explained(name: str, rep: dict, data: dict) -> dict:
    """The Checks tab in plain words (kerf/explain.py): one card per problem, and whether anyone is working on them."""
    from . import explain
    jobs = [{"kind": j.kind, "label": j.label, "started": j.started} for j in JOBS.values() if j.project == name and j.state == "running"]
    parts = list((data.get("parts") or {}).keys()) + list((data.get("purchased") or {}).keys())
    try:
        cards = explain.cards(rep, parts) if rep else []
        work = explain.work_status(name, jobs, explain.claims(ROOT))
    except Exception as e:  # noqa: BLE001 - the plain-words layer never breaks the page
        return {"cards": [], "work": {"state": "idle", "text": ""}, "error": str(e)}
    if work.get("state") == "claimed":
        work["recent"] = recent_commits(name)
    return {"cards": cards, "work": work}


def recent_commits(name: str, n: int = 4) -> list[dict]:
    """The latest commits that touched projects/<name>/ ({subject, time}): what the session on it has done so far."""
    out = []
    for line in _git("log", f"-{n}", "--format=%ct%x09%s", "--", f"projects/{name}").splitlines():
        t, _, subj = line.partition("\t")
        subj = re.sub(rf"^{re.escape(name)}:\s*", "", subj)
        out.append({"time": float(t or 0), "subject": subj[:220]})
    return out


SESSIONS = {"at": 0.0, "list": []}


def sessions(max_age: float = 30) -> list[dict]:
    """Sessions with fresh shared claims naming a project, for Studio's Activity list.
    Cached for max_age s: /api/jobs is polled every few seconds."""
    LIVE["work_until"] = time.time() + 90  # Activity is polled on every page, so shared ownership keeps refreshing.
    _live_thread()
    if time.time() - SESSIONS["at"] < max_age:
        return SESSIONS["list"]
    from . import explain
    out = []
    try:
        cl = explain.claims(ROOT)
        for name in project_names():
            w = explain.work_status(name, [], cl)
            if w["state"] == "claimed":
                rep = _report(PROJECTS / name)
                last = recent_commits(name, 1)
                out.append({"project": name, "text": w["text"], "task": w.get("task", ""),
                            "problems": len((rep or {}).get("problems") or []) if rep else None,
                            "last": last[0] if last else None})
    except Exception:  # noqa: BLE001 - Activity never breaks over a claim file
        out = []
    SESSIONS.update(at=time.time(), list=out)
    return out


def _numbers(rep: dict) -> dict | None:
    """What it costs and weighs: priced BOM total, whole-pack cost, filament grams (printed mass)."""
    if not rep:
        return None
    b = ((rep.get("files") or {}).get("ship") or {}).get("bom") or {}
    m = rep.get("mass") or {}
    pl = (rep.get("print") or {}).get("plates") or []
    sliced = bool(pl) and all(x.get("sliced") for x in pl)
    secs = sum((x["sliced"]["seconds"] if sliced else x.get("min_seconds") or 0) for x in pl) if pl else None
    return {"print_s": secs, "print_sliced": sliced, "plates": len(pl) or None,
            "cost_usd": b.get("total_usd"), "packs_usd": b.get("packs_usd"), "unpriced": len(b.get("unpriced") or []),
            "filament_g": m.get("printed_g"), "device_g": m.get("device_g"),
            "print_parts": len(rep.get("parts") or {})}


# ---------------------------------------------------------------- params
def _fmt_num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else repr(round(float(v), 6))


def _yaml(d: Path) -> dict | None:
    try:
        return yaml.safe_load((d / "project.yaml").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def write_params(path: Path, values: dict) -> list[str]:
    """Set params.<k>.value (or params.<k>: v) in a project.yaml in place, keeping every comment and line."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    known = data.get("params") or {}
    changed = []
    for k, v in values.items():
        if k not in known:
            raise ValueError(f"unknown param {k}")
        v = float(v)
        import math
        if not math.isfinite(v):
            raise ValueError(f"{k}: enter a finite number")
        spec = known[k]
        if isinstance(spec, dict):
            if "min" in spec and v < spec["min"] - 1e-9:
                raise ValueError(f"{k} = {v} is outside its allowed range: enter {spec['min']} or more")
            if "max" in spec and v > spec["max"] + 1e-9:
                raise ValueError(f"{k} = {v} is outside its allowed range: enter {spec['max']} or less")
        pat_dict = re.compile(rf"^(\s+{re.escape(k)}:\s*\{{\s*value:\s*)([-+0-9.eE]+)", re.M)
        pat_plain = re.compile(rf"^(\s+{re.escape(k)}:\s*)([-+0-9.eE]+)(\s*(#.*)?)$", re.M)
        new, n = pat_dict.subn(lambda m: m.group(1) + _fmt_num(v), text, count=1)
        if not n:
            new, n = pat_plain.subn(lambda m: m.group(1) + _fmt_num(v) + (m.group(3) or ""), text, count=1)
        if not n:
            raise ValueError(f"could not find params.{k} in {path.name}")
        if new != text:
            changed.append(k)
        text = new
    check = yaml.safe_load(text)
    for k, v in values.items():
        got = check["params"][k]["value"] if isinstance(check["params"][k], dict) else check["params"][k]
        if abs(float(got) - float(v)) > 1e-9:
            raise ValueError(f"param write check failed for {k}")
    path.write_text(text, encoding="utf-8")
    return changed


def trial_copy(name: str, values: dict, mats: dict | None = None) -> Path:
    """Scratch copy of a project (sources only) with new param values and part materials; the real project is never touched."""
    src, dst = PROJECTS / name, TRIALS / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "review.json"))
    write_params(dst / "project.yaml", values)
    if mats:
        write_materials(dst / "project.yaml", mats)
    return dst


# ---------------------------------------------------------------- new design via Claude Code
def claude_bin() -> str | None:
    return shutil.which("claude")


def _claude_lines(raw: str):
    raw = raw.strip()
    if not raw:
        return []
    try:
        ev = json.loads(raw)
    except Exception:  # noqa: BLE001
        ev = {}
    out = [] if ev else [raw]
    t = ev.get("type")
    if t == "assistant":
        for c in ev.get("message", {}).get("content", []):
            if c.get("type") == "text" and c.get("text", "").strip():
                out.append(c["text"].strip())
                out.append("@@" + json.dumps({"k": "note", "text": c["text"].strip()[:400]}))   # for the thought web
            elif c.get("type") == "tool_use":
                inp = c.get("input", {})
                what = inp.get("description") or inp.get("command") or inp.get("file_path") or inp.get("prompt") or ""
                out.append(f"  > {c.get('name')}: {str(what).splitlines()[0][:140] if what else ''}")
            if c.get("type") == "tool_use":
                ph = _phase(c.get("name", ""), inp)
                out.append("@@" + json.dumps({"k": "tool", "name": c.get("name"), "what": str(what).splitlines()[0][:140] if what else "",
                                               "phase": ph, "query": str(inp.get("query") or "")[:160],
                                               "url": str(inp.get("url") or "")[:300], "path": str(inp.get("file_path") or "")[:300],
                                               "cmd": str(inp.get("command") or "").splitlines()[0][:200] if inp.get("command") else "",
                                               "agent": str(inp.get("subagent_type") or "")[:60]}))
    elif t == "system" and ev.get("session_id"):
        out.append("@@" + json.dumps({"k": "session", "id": str(ev["session_id"])}))
    elif t == "result":
        bad = ev.get("is_error") or ev.get("subtype") != "success"
        if ev.get("session_id"):
            out.append("@@" + json.dumps({"k": "session", "id": str(ev["session_id"])}))
        out.append(f"== {'stopped with an error' if bad else 'finished'} after {round(ev.get('duration_ms', 0) / 60000, 1)} min ==")
        if ev.get("result"):
            out.append(str(ev["result"]))
    for ln in list(out):
        if not ln.startswith("@@") and USAGE_RX.search(ln):
            out.append("@@" + json.dumps({"k": "usage", "text": ln[:300], "until": usage_reset(ln)}))
            break
    for ln in list(out):
        code = _claude_problem(ln)
        if code:
            out.append("@@" + json.dumps({"k": "hint", "code": code}))
            break
    return out


# Problems that stop a design before it starts, recognised in Claude Code's output. Each one is fixed once, by Spencer,
# in Terminal (Studio's "Set up Claude Code" button opens it); the design job is stopped at once instead of running on.
CLAUDE_PROBLEMS = [
    ("auth", re.compile(r"failed to authenticate|oauth session expired|not logged in|please run /login|invalid api key", re.I)),
    ("trust", re.compile(r"workspace has not been trusted|hasTrustDialogAccepted", re.I)),
]


# Claude usage running out mid-job (Spencer, 2026-11-02: "add in failsafes throughout for in case usage runs out").
# Claude Code ends the run with a message like "Claude AI usage limit reached|1762126800" or "You've hit your limit ·
# resets 7pm (America/New_York)". The job is then PAUSED, not failed: it keeps its Claude session id, shows when usage
# comes back, resumes by itself then (unless the budget switch is on) or now with Resume, and no new Claude job starts
# until then. Every Claude job is told to commit as it goes, so a cut-off loses nothing.
USAGE_RX = re.compile(r"usage limit (?:reached|exceeded)|hit your (?:usage )?limit|(?:5-hour|weekly|session) limit reached|"
                      r"out of (?:extra )?usage|credit balance is too low", re.I)
USAGE = {"until": 0.0, "text": ""}         # when Claude usage is expected back (epoch; 0 = unknown / not limited)
CUTOFF_NOTE = ("\n\nIf usage might run out: commit and push after every meaningful step (a work-in-progress commit is "
               "fine) and keep STATUS.md current, so a cut-off loses nothing and a resumed run can pick up from git.")


def usage_reset(text: str, now: float | None = None) -> float:
    """The reset time a usage-limit message gives (epoch), or now + 1 h when it gives none it can read."""
    now = time.time() if now is None else now
    m = re.search(r"\|(\d{10})\b", text)
    if m:
        return float(m.group(1))
    m = re.search(r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*([ap]m)", text, re.I)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)
        lt = time.localtime(now)
        t = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, int(m.group(2) or 0), 0, 0, 0, -1))
        return t if t > now else t + 86400
    return now + 3600


def usage_blocked(now: float | None = None) -> str:
    """Why a new Claude job must wait ('' when it may start): usage is out until its reset."""
    now = time.time() if now is None else now
    if USAGE["until"] > now:
        return f"Claude usage is used up until about {time.strftime('%-I:%M %p', time.localtime(USAGE['until']))}"
    return ""


def budget_stop() -> str:
    """Kerf's shared usage-budget switch (tools/budget.py): '' when work may start."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("kerf_budget", ROOT / "tools" / "budget.py")
        b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(b)
        return b.stopped()
    except Exception:  # noqa: BLE001 - no switch file: not stopped
        return ""


def _claude_problem(text: str) -> str | None:
    for code, rx in CLAUDE_PROBLEMS:
        if rx.search(text):
            return code
    return None


def _claude_config() -> Path:
    d = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(d) / ".claude.json" if d else Path.home() / ".claude.json"


def claude_ready() -> dict:
    """Check, before a design starts, everything that would make Claude Code fail or run without Kerf's settings:
    installed, this folder trusted (otherwise it ignores .claude/settings.json: permissions AND the quality hooks),
    signed in. Free: no model call. When Codex will run the job instead (kerf/agent.py), Codex being installed is enough."""
    if pick_agent() == "codex":
        return {"ok": True, "code": None, "why": "ready (ChatGPT Codex will run it)", "agent": "codex"}
    exe = claude_bin()
    if not exe:
        return {"ok": False, "code": "missing", "why": "Claude Code isn't installed on this computer."}
    if usage_blocked():
        return {"ok": False, "code": "usage", "why": usage_blocked() + ": new designs wait until then, and paused jobs "
                "resume by themselves.", "until": USAGE["until"]}
    try:
        cfg = json.loads(_claude_config().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cfg = {}
    projects = cfg.get("projects") or {}
    trusted = any((projects.get(str(p)) or {}).get("hasTrustDialogAccepted") for p in [ROOT, *ROOT.parents])
    if not trusted:
        return {"ok": False, "code": "trust", "why": f"Claude Code hasn't been told to trust {ROOT}, so it would ignore "
                                                      "Kerf's settings and quality checks."}
    try:
        r = subprocess.run([exe, "auth", "status", "--json"], capture_output=True, text=True, timeout=30)
        st = json.loads(r.stdout or "{}")
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "code": "auth", "why": f"couldn't read Claude Code's sign-in status ({type(e).__name__})."}
    if not st.get("loggedIn"):
        return {"ok": False, "code": "auth", "why": "Claude Code isn't signed in."}
    return {"ok": True, "code": None, "why": "ready"}


SETUP_SCRIPT = """#!/bin/bash
cd "{root}"
clear
echo "Kerf Studio: one-time Claude Code setup"
echo "  1. If asked, choose 'Yes, I trust this folder'."
echo "  2. If it says you're not signed in (or anything about login), type /login and follow it."
echo "  3. Type /exit when it's ready, close this window, and start your design again in Kerf Studio."
echo
claude
"""


def claude_setup() -> dict:
    """Open Terminal running Claude Code in the repo, where its trust and sign-in prompts appear (macOS)."""
    cmd = f'cd "{ROOT}" && claude'
    if platform.system() != "Darwin":
        return {"opened": False, "command": cmd}
    f = TRIALS.parent / "setup-claude.command"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(SETUP_SCRIPT.format(root=ROOT), encoding="utf-8")
    f.chmod(0o755)
    subprocess.run(["open", str(f)], check=False)
    return {"opened": True, "command": cmd}


DESIGN_PHASES = [("research", "Research"), ("plan", "Plan"), ("contract", "Contract"), ("parts", "Model parts"),
                 ("check", "Check + fix"), ("build", "Build"), ("review", "Review"), ("ship", "Save + push")]


def _phase(tool: str, inp: dict) -> str | None:
    """Which design phase a Claude Code tool call belongs to (for the studio timeline)."""
    path = str(inp.get("file_path") or "")
    cmd = str(inp.get("command") or "")
    agent = str(inp.get("subagent_type") or "") + " " + str(inp.get("description") or "")
    if tool in ("WebSearch", "WebFetch") or "researcher" in agent or "kerf find" in cmd:
        return "research"
    if "reviewer" in agent:
        return "review"
    if "part-designer" in agent or re.search(r"/parts/[^/]+\.py$", path):
        return "parts"
    if path.endswith(("DESIGN.md", "REFERENCES.md")):
        return "plan"
    if path.endswith("project.yaml"):
        return "contract"
    if "kerf build" in cmd:
        return "build"
    if "kerf check" in cmd or "kerf verify" in cmd:
        return "check"
    if "git push" in cmd or "git commit" in cmd:
        return "ship"
    return None


class ClaudeNotReady(ValueError):
    def __init__(self, ready: dict):
        super().__init__(ready["why"])
        self.ready = ready


INTAKE_FIELDS = {"budget": "Budget (USD, purchased parts + filament)", "power": "Power", "mounting": "Mounting",
                 "environment": "Environment", "printer": "Printer", "material": "Material", "notes": "Other constraints",
                 "who": "Use story - who uses it", "how_often": "Use story - how often",
                 "goes_wrong": "Use story - what goes wrong (drops, crashes, heat, rain, gloves)",
                 "request_kind": "Request kind", "success": "What a successful solution must do",
                 "priority": "What matters most", "effort": "Time and effort available"}
QUOTES = ROOT / ".cache" / "studio" / "quotes"


def _intake(intake: dict | None) -> dict:
    if intake is not None and not isinstance(intake, dict):
        raise ValueError("intake answers must be an object")
    return {k: str(v).strip() for k, v in (intake or {}).items() if k in INTAKE_FIELDS and str(v).strip()}


def brief(description: str, intake: dict | None = None, option: dict | None = None) -> str:
    """The design brief Claude gets: the request, Spencer's answers to the intake questions, the parts he has on hand,
    and (after a quote) the option he picked."""
    from .ship import load_inventory
    L = [description.strip()]
    intake = _intake(intake)
    answers = [f"- {INTAKE_FIELDS[k]}: {v}" for k, v in intake.items()]
    if answers:
        L += ["", "Spencer's answers to the intake questions:", *answers]
    if any(str((intake or {}).get(k, "")).strip() for k in ("who", "how_often", "goes_wrong")):
        L += ["", "Write the use story answers into project.yaml `use_story` (kerf/usestory.py); each hazard becomes checks."]
    inv = load_inventory()
    if inv:
        L += ["", "Parts on hand (prefer these where they fit; the BOM counts them first): "
              + ", ".join(f"{k} x{v:g}" for k, v in sorted(inv.items()))]
    if option:
        L += ["", f"Spencer picked this option from the quote: {option.get('title', '')} - {option.get('summary', '')}"]
        if option.get("purchased"):
            L.append("Its purchased parts: " + ", ".join(f"{x.get('key')} x{x.get('qty', 1)}" for x in option["purchased"]))
        if option.get("route"):
            L += ["", "Selected option, including its evidence and unresolved risks:", json.dumps(option, ensure_ascii=False),
                  "Keep these trade-offs and sources in DESIGN.md / REFERENCES.md; recheck estimates during design. "
                  "Do not buy anything or send anything to a printer."]
    return "\n".join(L)


def _check_new(name: str, description: str):
    name = slug(name)
    if not NAME_RE.match(name):
        raise ValueError("name: lowercase letters, digits and _ (2-41 chars), starting with a letter")
    if (PROJECTS / name).exists():
        raise ValueError(f"projects/{name} already exists")
    if not description.strip():
        raise ValueError("describe what to design")
    ready = claude_ready()
    if not ready["ok"]:
        raise ClaudeNotReady(ready)


def new_design(name: str, description: str, intake: dict | None = None, option: dict | None = None,
               option_index: int | None = None) -> Job:
    name = slug(name)
    intake = _intake(intake)
    if intake.get("request_kind") == "scenario" and option_index is None:
        raise ValueError("compare options first, then choose an adapt or build option")
    if option_index is not None:
        q = read_quote(name)
        if type(option_index) is not int or not 0 <= option_index < len(q["options"]):
            raise ValueError("choose one of the quoted options")
        context = q.get("context")
        if not (description or "").strip():      # "Design this" with an empty box: the options' own request is the brief
            description = (context or {}).get("description") or q.get("request") or ""
            if context:
                intake = _intake(context.get("intake"))
        if context and context != {"description": description.strip(), "intake": intake}:
            raise ValueError("your request changed; compare options again before designing")
        if q.get("questions"):
            raise ValueError("answer the open questions in your request, then compare options again")
        option = q["options"][option_index]
    if option and option.get("route") == "buy":
        raise ValueError("this is a buy-only option: follow its sources and next steps; no design is needed")
    _check_new(name, description)
    prompt = (f"/kerf {brief(description, intake, option)}\n\nProject folder name: projects/{name}. Spencer started this from "
              f"Kerf Studio and is not watching the terminal: work autonomously to a finished, built and reviewed project.")
    j = agent_job("design", name, prompt, f"New design: {description.strip()[:60]}", env={"KERF_STUDIO_JOB": name})
    if j is not None:
        j.request = description.strip()          # the whole request, for "How Kerf decided" (the label is cut at 60)
    return j


def quote(name: str, description: str, intake: dict | None = None) -> Job:
    """Quote first: Claude researches and writes 2-3 candidate architectures with cost, print time and part count to
    .cache/studio/quotes/<name>.json (kerf skill, "Quote mode") and stops; nothing is designed until one is picked."""
    name = slug(name)
    intake = _intake(intake)
    _check_new(name, description)
    out = QUOTES / f"{name}.json"
    prompt = (f"/kerf QUOTE ONLY. {brief(description, intake)}\n\nWrite the quote to {out} as the kerf skill's Quote mode "
              f"says and stop: do not create projects/{name} or any design files.")
    if intake.get("request_kind") == "scenario":
        prompt += ("\nSCENARIO OPTIONS: use the scenario quote contract in Quote mode. Compare buying a ready-made "
                   "solution with adapting an existing/free design or building one. Research first; cite the pages you "
                   "actually opened. Show fit to the success criteria, effort, risks and the reason for the recommendation. "
                   "Unknown prices/times stay null with an explanation, never zero. List unanswered questions; do not "
                   "pretend an unverified assumption meets the scenario. No purchases or printer actions.")
    def prepare():
        QUOTES.mkdir(parents=True, exist_ok=True)
        out.unlink(missing_ok=True)
        (QUOTES / f"{name}.request.json").write_text(
            json.dumps({"description": description.strip(), "intake": intake}), encoding="utf-8")
    return agent_job("quote", name, prompt, f"Options for: {description.strip()[:60]}", prepare=prepare)


def list_quotes() -> list[dict]:
    """Every saved set of options not yet turned into a project, newest first: {name, description, options, time}."""
    out = []
    for f in sorted(QUOTES.glob("*.json"), key=lambda f: -f.stat().st_mtime) if QUOTES.exists() else []:
        name = f.stem
        if name.endswith(".request") or not NAME_RE.match(name) or (PROJECTS / name).exists():
            continue
        try:
            q = json.loads(f.read_text(encoding="utf-8"))
            ctx_f = QUOTES / f"{name}.request.json"
            ctx = json.loads(ctx_f.read_text(encoding="utf-8")) if ctx_f.exists() else {}
            out.append({"name": name, "description": (ctx.get("description") or q.get("request") or "")[:160],
                        "options": len(q.get("options") or []), "time": f.stat().st_mtime})
        except Exception:  # noqa: BLE001 - a half-written quote is skipped, not fatal
            continue
    return out


def read_quote(name: str) -> dict:
    """The quote file, checked: 1-3 options, each with a title, summary, part count, cost and print hours."""
    f = QUOTES / f"{name}.json"
    if not NAME_RE.match(name) or not f.exists():
        raise ValueError("no quote yet")
    from .quotes import validate
    context_file = QUOTES / f"{name}.request.json"
    context = json.loads(context_file.read_text(encoding="utf-8")) if context_file.exists() else None
    scenario = bool(context and context.get("intake", {}).get("request_kind") == "scenario")
    q = validate(json.loads(f.read_text(encoding="utf-8")), scenario=scenario)
    q.pop("context", None)  # The request comes from Studio's saved input, never from generated quote content.
    if scenario:
        q["request_kind"] = "scenario"
    if context:
        q["context"] = context
    return q


# ---------------------------------------------------------------- open in apps
def open_in_app(name: str, what: str) -> dict:
    d = PROJECTS / name
    if what == "plates":
        files = sorted(str(p) for p in (d / "out" / "plates").glob("plate_*.3mf"))
        if not files:
            raise ValueError("no plates yet: build the project first")
        cmd = ["open", "-a", "Bambu Studio", *files] if platform.system() == "Darwin" else None
    elif what == "folder":
        target = d / "out" if (d / "out").exists() else d
        files = [str(target)]
        cmd = ["open", str(target)] if platform.system() == "Darwin" else (["xdg-open", str(target)] if shutil.which("xdg-open") else None)
    else:
        raise ValueError(f"unknown target {what}")
    if cmd is None:
        return {"opened": False, "paths": files}
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise ValueError((r.stderr or r.stdout or "open failed").strip()[:300])
    return {"opened": True, "paths": files}


# ---------------------------------------------------------------- settings + notifications
SETTINGS = ROOT / ".cache" / "studio_settings.json"
DEFAULT_SETTINGS = {"notify": True, "sound": True, "autofix": True, "autoresume": True}   # autofix: a failed build starts a fix job
NOTIFY_MIN_S = 20.0          # quick checks finish while you watch: no notification for those


def settings() -> dict:
    try:
        return {**DEFAULT_SETTINGS, **json.loads(SETTINGS.read_text(encoding="utf-8"))}
    except Exception:  # noqa: BLE001
        return dict(DEFAULT_SETTINGS)


def save_settings(new: dict) -> dict:
    s = settings()
    s.update({k: bool(v) for k, v in new.items() if k in DEFAULT_SETTINGS})
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s), encoding="utf-8")
    return s


def job_outcome(job) -> tuple[bool, str]:
    """(good, one line) for a finished job: the report's verdict for builds / checks / tries, else how it ended."""
    secs = (job.ended or time.time()) - job.started
    took = f"{int(secs // 60)}:{int(secs % 60):02d}"
    if job.state == "stopped":
        return False, f"stopped after {took}"
    if job.kind in ("build", "check", "trial") and job.project not in ("*", None):
        rep = _report((TRIALS if job.kind == "trial" else PROJECTS) / job.project)
        if rep is not None and job.state in ("done", "failed"):
            n = len(rep.get("problems") or [])
            return (not n), (f"every check passes ({took})" if not n else f"{n} problem{'s' if n > 1 else ''} to fix ({took})")
    if job.state == "done":
        return True, f"finished ({took})" + (": Claude Code is done" if job.kind in ("design", "edit", "fix") else "")
    return False, f"stopped with an error after {took}"


def _osa(text: str) -> str:
    """An AppleScript string literal."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(title: str, message: str, good: bool = True) -> bool:
    """A desktop notification: macOS (osascript, with a sound) or Linux (notify-send). False when there is no way."""
    try:
        if platform.system() == "Darwin":
            script = (f"display notification {_osa(message)} with title \"Kerf Studio\" subtitle {_osa(title)} "
                      f"sound name \"{'Glass' if good else 'Basso'}\"")
            return subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10).returncode == 0
        if shutil.which("notify-send"):
            return subprocess.run(["notify-send", "-a", "Kerf Studio", f"Kerf Studio: {title}", message],
                                  capture_output=True, timeout=10).returncode == 0
    except Exception:  # noqa: BLE001 - no notification is better than a broken job
        return False
    return False


def notify_job(job) -> bool:
    """Notify about a finished job that ran long enough to have been left alone, unless switched off or stopped by hand."""
    secs = (job.ended or time.time()) - job.started
    if not settings()["notify"] or job.state == "stopped" or (secs < NOTIFY_MIN_S and job.kind not in ("design", "edit", "fix")):
        return False
    if time.time() - LIFE.get("native", 0) < 20:
        return False                  # the Mac app is open: it posts its own notification, which opens the view when clicked
    good, line = job_outcome(job)
    return notify(job.label, line, good)


# ---------------------------------------------------------------- change something (Claude Code edit job)
def edit_job(name: str, request: str, title: str = "") -> Job:
    """A change to one project, done by Claude Code in the repo: make it, check, build, review, commit and push. The job
    is scoped: KERF_STUDIO_JOB tells the stop gate to judge it on this project, not on every open PLAN item."""
    if name not in project_names():
        raise ValueError("no such project")
    if not request.strip():
        raise ValueError("describe the change")
    ready = claude_ready()
    if not ready["ok"]:
        raise ClaudeNotReady(ready)
    prompt = (f"{request.strip()}\n\nThis change request comes from Kerf Studio for projects/{name}; Spencer is not watching "
              f"the terminal. Do exactly this change, following CLAUDE.md, for projects/{name} only: make it, run "
              f"`.venv/bin/kerf check {name}` until it passes, `.venv/bin/kerf build {name}`, read the renders, get a "
              f"design-reviewer pass, append a dated STATUS.md entry, commit and push. Do not start other PLAN work. "
              f"If the change can't be made without breaking a check, say why and leave the design as it was.")
    label = f"Change {name}: {(title or request).strip().splitlines()[0][:60]}"
    return agent_job("edit", name, prompt, label, env={"KERF_STUDIO_JOB": name})


# ---------------------------------------------------------------- duplicate / remix
COPY_SKIP = ("out", "__pycache__", "review.json", ".pytest_cache")


def duplicate(src: str, name: str, title: str = "") -> Path:
    """Copy a project's design files (project.yaml, parts, DESIGN.md, REFERENCES.md, ...) to projects/<name>; built
    files and the review stay behind (a copy is a new design: it is built and reviewed on its own)."""
    if src not in project_names():
        raise ValueError("no such project")
    name = slug(name)
    if not NAME_RE.match(name):
        raise ValueError("name: lowercase letters, digits and _ (2-41 chars), starting with a letter")
    dst = PROJECTS / name
    if dst.exists():
        raise ValueError(f"projects/{name} already exists")
    new_title = (title or "").strip() or f"{_read_yaml(src).get('name', src)} (copy)"
    shutil.copytree(PROJECTS / src, dst, ignore=shutil.ignore_patterns(*COPY_SKIP))
    y = dst / "project.yaml"
    text = y.read_text(encoding="utf-8")
    if re.search(r"^name:", text, re.M):
        new = re.sub(r"^name:[^\n#]*?(\s*#.*)?$", lambda m: f"name: {json.dumps(new_title)}" + (m.group(1) or ""), text, count=1, flags=re.M)
    else:
        new = f"name: {json.dumps(new_title)}\n" + text
    if (yaml.safe_load(new) or {}).get("name") != new_title:
        shutil.rmtree(dst)
        raise ValueError("could not set the copy's name in project.yaml")
    y.write_text(new, encoding="utf-8")
    return dst


# ---------------------------------------------------------------- materials per printed part
def materials() -> list[dict]:
    """Catalog materials with the numbers the checks use, plus the filament price when catalog/prices.json has one."""
    from . import catalog
    try:
        prices = json.loads((ROOT / "catalog" / "prices.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        prices = {}
    out = []
    for k, m in (catalog.load().get("materials") or {}).items():
        if not isinstance(m, dict) or k.startswith("_"):
            continue
        pr = prices.get(f"material:{k}") or {}
        usd = round(pr["pack_usd"] / pr["pack_qty"] * 1000, 2) if pr.get("pack_usd") and pr.get("pack_qty") else None
        out.append({"key": k, "density": m.get("density"), "xy_mpa": m.get("tensile_strength_xy_mpa"),
                    "z_mpa": m.get("tensile_strength_z_mpa"), "modulus_mpa": m.get("youngs_modulus_mpa"), "usd_per_kg": usd,
                    "source": m.get("source")})
    return out


def part_materials(name: str) -> dict:
    return {k: v.get("material", "PETG") for k, v in (_read_yaml(name).get("parts") or {}).items() if isinstance(v, dict)}


def write_materials(path: Path, values: dict) -> list[str]:
    """Set parts.<part>.material in a project.yaml in place (flow `{...}` or block style), keeping every comment."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    parts = data.get("parts") or {}
    known = {m["key"] for m in materials()}
    changed = []
    for part, mat in values.items():
        if part not in parts or not isinstance(parts[part], dict):
            raise ValueError(f"unknown printed part {part}")
        if mat not in known:
            raise ValueError(f"unknown material {mat}")
        if parts[part].get("material", "PETG") == mat:
            continue
        sec = re.search(r"^parts:[ \t]*(#.*)?$", text, re.M)
        m = re.compile(rf"^(?P<ind>[ \t]+){re.escape(part)}:[ \t]*(?P<rest>.*)$", re.M).search(text, sec.end() if sec else 0)
        if not m:
            raise ValueError(f"could not find parts.{part} in {path.name}")
        ind = len(m.group("ind"))
        nxt = re.compile(rf"^[ \t]{{0,{ind}}}\S", re.M).search(text, m.end())
        end = nxt.start() if nxt else len(text)
        seg = text[m.start():end]
        if re.search(r"\bmaterial:", seg):
            seg2 = re.sub(r"(\bmaterial:[ \t]*)([^,}\n#]+?)([ \t]*[,}\n#])", lambda x: x.group(1) + mat + x.group(3), seg, count=1)
        elif m.group("rest").lstrip().startswith("{"):
            seg2 = seg.replace("{", "{material: " + mat + ", ", 1)
        else:
            child = re.search(r"\n([ \t]+)\S", seg)
            pad = child.group(1) if child else " " * (ind + 2)
            nl = seg.index("\n") if "\n" in seg else len(seg)
            seg2 = seg[:nl] + f"\n{pad}material: {mat}" + seg[nl:]
        text = text[:m.start()] + seg2 + text[end:]
        changed.append(part)
    check = yaml.safe_load(text) or {}
    for part, mat in values.items():
        if ((check.get("parts") or {}).get(part) or {}).get("material", "PETG") != mat:
            raise ValueError(f"material write check failed for {part}")
    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


# ---------------------------------------------------------------- geometry for compare + thumbnails
THUMBS = ROOT / ".cache" / "studio_thumbs"


def viewer_geom(path: Path) -> dict | None:
    """The solid items' meshes a viewer.html carries (world, home pose): {fingerprint, items: [{id, role, verts, tris}]}."""
    if not Path(path).exists():
        return None
    from .viewer import embedded
    d = embedded(path)
    if not d:
        return None
    return {"fingerprint": (d.get("report") or {}).get("fingerprint"),
            "items": [{k: it[k] for k in ("id", "role", "verts", "tris")} for it in d["items"] if it.get("role") != "keepout"]}


def _geom_of(name: str, which: str) -> tuple[dict | None, str]:
    """'saved' = the project's current build, 'trial' = the last Try, else a History stamp. (geometry, label)"""
    if which == "saved":
        return viewer_geom(PROJECTS / name / "out" / "viewer.html"), "the saved design"
    if which == "trial":
        return viewer_geom(TRIALS / name / "out" / "viewer.html"), "the tried values"
    if not re.fullmatch(r"\d{8}-\d{6}", which or ""):
        raise ValueError("no such version")
    f = HISTORY / name / which / "geom.json.gz"
    if not f.exists():
        raise ValueError("that version has no stored geometry (built before compare existed)")
    import gzip
    v = json.loads(gzip.decompress(f.read_bytes()))
    return v, time.strftime("the build of %b %d, %H:%M", time.strptime(which, "%Y%m%d-%H%M%S"))


def _mesh(it: dict):
    import base64
    import numpy as np
    import trimesh
    v = np.frombuffer(base64.b64decode(it["verts"]), np.float32).reshape(-1, 3).astype(float)
    t = np.frombuffer(base64.b64decode(it["tris"]), np.uint32).reshape(-1, 3)
    return trimesh.Trimesh(v, t, process=False), v


def _dist_b64(mesh, pts) -> tuple[str, float]:
    """Distance (mm) of each point to a mesh surface, stored as round(mm * 20) in one byte (0.05 mm steps, 12.75 max)."""
    import base64
    import numpy as np
    from trimesh.proximity import closest_point
    if len(pts) == 0 or len(mesh.faces) == 0:
        return base64.b64encode(np.full(len(pts), 255, np.uint8).tobytes()).decode(), float("inf") if len(pts) else 0.0
    _, d, _ = closest_point(mesh, pts)
    q = np.clip(np.round(d * 20), 0, 255).astype(np.uint8)
    return base64.b64encode(q.tobytes()).decode(), float(np.max(d))


def compare(name: str, source: str, target: str = "saved") -> dict:
    """What the viewer needs to draw `source` as a ghost over `target`: the ghost meshes, per-vertex distances both ways
    and a per-part summary (0.05 mm steps). A part on one side only is 'added' / 'removed'."""
    src, label = _geom_of(name, source)
    tgt, _ = _geom_of(name, target)
    if not src or not tgt:
        raise ValueError("build first: there is no 3D model to compare")
    S = {it["id"]: it for it in src["items"]}
    Tg = {it["id"]: it for it in tgt["items"]}
    dist, gdist, summary = {}, {}, []
    for iid, it in Tg.items():
        if iid not in S:
            summary.append({"id": iid, "status": "added", "max_mm": None})
            continue
        if it["verts"] == S[iid]["verts"] and it["tris"] == S[iid]["tris"]:
            summary.append({"id": iid, "status": "same", "max_mm": 0.0})
            continue
        m_s, v_s = _mesh(S[iid])
        m_t, v_t = _mesh(it)
        dist[iid], a = _dist_b64(m_s, v_t)
        gdist[iid], b = _dist_b64(m_t, v_s)
        mx = max(a, b)
        summary.append({"id": iid, "status": "changed" if mx > 0.05 else "same", "max_mm": round(mx, 2)})
    summary += [{"id": i, "status": "removed", "max_mm": None} for i in S if i not in Tg]
    moved = {x["id"] for x in summary if x["status"] in ("changed", "removed")}
    return {"label": label, "items": [S[i] for i in S if i in moved], "dist": dist, "gdist": gdist, "summary": summary,
            "fingerprints": [src.get("fingerprint"), tgt.get("fingerprint")]}


def save_thumb(name: str, data_url: str, fingerprint: str | None) -> dict:
    import base64
    if not data_url.startswith("data:image/png;base64,"):
        raise ValueError("expected a PNG data URL")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    if not raw.startswith(b"\x89PNG") or len(raw) > 4_000_000:
        raise ValueError("not a PNG (or too big)")
    THUMBS.mkdir(parents=True, exist_ok=True)
    (THUMBS / f"{name}.png").write_bytes(raw)
    (THUMBS / f"{name}.json").write_text(json.dumps({"fingerprint": fingerprint, "time": time.time()}), encoding="utf-8")
    return {"ok": True}


def thumb_info(name: str) -> dict:
    f = THUMBS / f"{name}.png"
    if not f.exists():
        return {"url": None, "fingerprint": None}
    try:
        meta = json.loads((THUMBS / f"{name}.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        meta = {}
    return {"url": f"/thumb/{name}.png?v={int(f.stat().st_mtime)}", "fingerprint": meta.get("fingerprint")}


# ---------------------------------------------------------------- follow live + Work tab (kerf/live.py)
# One background thread, one `git fetch` at most every live.FETCH_EVERY seconds, only while a project is followed or
# Activity is polled or the Work tab is open. Updates follow tools/mac/start.sh's rule (clean tree, fast-forward only) and wait while a Studio
# job runs, so they never pull under a build or a Claude Code change.
LIVE_DIR = ROOT / ".cache" / "studio_live"
LIVE: dict = {"follow": {}, "last_fetch": 0.0, "fetch_error": None, "work_until": 0.0, "work": None, "work_key": None,
              "thread": None}


def _live_state(name: str) -> dict:
    return LIVE["follow"].setdefault(name, {"on": False, "seq": 0, "data": None, "seeded": False, "changed": {},
                                            "removed": {}, "line": "", "error": None, "editing": {}, "designing": [],
                                            "building": False, "needs_full": False})


def live_data(name: str) -> dict:
    """The followed project's viewer data: the last build's viewer.html on this computer (or a blank model that the first
    live rebuild fills), then updated in place part by part."""
    from . import live
    st = _live_state(name)
    if st["data"] is None:
        from .viewer import embedded
        v = PROJECTS / name / "out" / "viewer.html"
        d = embedded(v) if v.exists() else None
        st["data"], st["seeded"] = (d or live.blank_data(name, f"projects/{name}")), d is not None
        st["needs_full"] = d is None
        rep = _report(PROJECTS / name) or {}
        st["designing"] = list(rep.get("stubs") or [])     # placeholders: shown as "being designed", as everywhere else
    return st["data"]


def follow(name: str, on: bool) -> dict:
    st = _live_state(name)
    st["on"], st["error"] = bool(on), None
    if on:
        live_data(name)
        _live_thread()
    return live_info(name, st["seq"])


def live_info(name: str, since: int = 0) -> dict:
    """What the page needs: state, the one-line latest commit, and the items whose mesh changed after `since`."""
    st = _live_state(name)
    d = st["data"]
    items = [it for it in (d or {}).get("items", []) if st["changed"].get(it["id"], 0) > since] if since < st["seq"] else []
    return {"on": st["on"], "seq": st["seq"], "line": st["line"], "error": st["error"], "editing": st["editing"],
            "designing": st["designing"], "building": st["building"], "ready": bool(d and d.get("items")),
            "fetched": LIVE["last_fetch"], "fetch_error": LIVE["fetch_error"], "items": items,
            "removed": [i for i, s in st["removed"].items() if s > since]}


def _live_rebuild(name: str, ids: list[str] | None, removed: list[str] | None = None, line: str | None = None) -> None:
    """Child process `python -m kerf.live`: geometry + meshes of those items only, merged into the live viewer data."""
    from . import live
    st = _live_state(name)
    data = live_data(name)
    st["building"] = True
    try:
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        out = LIVE_DIR / f"{name}.json"
        out.unlink(missing_ok=True)
        r = subprocess.run([PY, "-m", "kerf.live", name, str(out), *(ids if ids is not None else ["ALL"])], cwd=ROOT,
                           capture_output=True, text=True, timeout=1800, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        if r.returncode != 0 or not out.exists():
            tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [f"exit {r.returncode}"]
            st["editing"].update({i: f"live rebuild stopped: {tail[0][:160]}" for i in (ids or [])})
            return
        res = json.loads(out.read_text(encoding="utf-8"))
        m = live.merge(data, res, removed)
        st["seq"] += 1
        for i in m["changed"]:
            st["changed"][i] = st["seq"]
        for i in m["removed"]:
            st["removed"][i] = st["seq"]
        st["editing"] = {**{k: v for k, v in st["editing"].items() if k not in res["items"] and k not in (removed or [])},
                         **m["editing"]}
        st["designing"] = sorted((set(st["designing"]) - set(res["items"])) | set(m["designing"]))
        if line is not None:
            st["line"] = line
    finally:
        st["building"] = False


def live_tick(now: float | None = None) -> None:
    """One step of the background loop (also called directly by tests)."""
    from . import live
    now = time.time() if now is None else now
    followed = [n for n, s in LIVE["follow"].items() if s["on"] and n in project_names()]
    for n in followed:
        if _live_state(n)["needs_full"]:
            _live_state(n)["needs_full"] = False        # one try; a failure shows as "being edited"
            _live_rebuild(n, None)                      # never built here: first whole-model geometry
    if not (followed or now < LIVE["work_until"]) or now - LIVE["last_fetch"] < live.FETCH_EVERY:
        return
    LIVE["last_fetch"] = now
    LIVE["fetch_error"] = live.fetch(ROOT)
    LIVE["work"] = None
    SESSIONS["at"] = 0.0
    if LIVE["fetch_error"] or not followed:
        return
    up, head = live.upstream(ROOT), _git("rev-parse", "HEAD")
    if not up or up == head:
        return
    changes = {n: live.changed_parts(ROOT, head, up, n) for n in followed}
    relevant = {n: c for n, c in changes.items() if c["items"] or c["removed"]}
    if not relevant:
        return
    if busy():                                          # a Studio build / Claude Code job is working in this folder
        for n in relevant:
            _live_state(n)["line"] = "update waiting: a Studio job is running"
        return
    ok, why = live.fast_forward(ROOT)
    if not ok:
        for n in followed:
            st = _live_state(n)
            st["error"], st["on"] = why, False          # stop following; the page says why
        return
    for n, c in relevant.items():
        s = live.last_subject(ROOT, head, up, n)
        line = f"{time.strftime('%H:%M', time.localtime(s['time']))} {s['subject']}" if s else None
        _live_rebuild(n, None if c["all"] else c["items"], c["removed"], line)


def _live_loop():
    while True:
        time.sleep(2.0)
        try:
            live_tick()
        except Exception as e:  # noqa: BLE001 - the loop never dies; the page shows the reason
            LIVE["fetch_error"] = f"{type(e).__name__}: {e}"[:200]


def _live_thread():
    if LIVE["thread"] is None or not LIVE["thread"].is_alive():
        LIVE["thread"] = threading.Thread(target=_live_loop, daemon=True)
        LIVE["thread"].start()


def _work_picture(name: str) -> str | None:
    if name not in project_names():
        return None
    rel = _thumb(PROJECTS / name)
    return f"/files/{name}/{rel}" if rel else thumb_info(name)["url"]


def work() -> dict:
    """Cache shared git work separately from live jobs and bounded Codex session observations."""
    from . import codex_work, live, work as work_overview
    LIVE["work_until"] = time.time() + 90              # the tab is open: keep the shared fetch going
    _live_thread()
    # Claims are shared on main even when Studio itself runs from a feature branch.
    revision = live.shared_revision(ROOT)
    key = (revision, int(time.time() // 60))
    git_work = LIVE["work"]
    if git_work is None or LIVE["work_key"] != key:
        git_work = live.work_data(ROOT, revision, picture=_work_picture)
        LIVE["work"] = git_work
        LIVE["work_key"] = key
    codex = codex_work.snapshot(ROOT)
    now = time.time()
    timings = _times()
    auto_resume = settings().get("autoresume", True)
    retry_blocked = bool(budget_stop())
    jobs = []
    with JOB_LOCK:
        for j in list(JOBS.values()):
            if j.state != "running" and now - (j.ended or j.started) >= 86400:
                continue
            kind = f"mode_{j.mode}" if j.mode else j.kind
            runs = timings.get(j.project, {})
            comparable = runs.get(kind) or runs.get({"mode_kit": "build", "mode_check": "check"}.get(kind, ""))
            # A last report may be a quick check, so only recorded comparable runs support a countdown.
            jobs.append({"id": j.id, "kind": j.kind, "project": j.project, "label": j.label,
                         "state": j.state, "started": j.started, "mode": j.mode, "events": list(j.events),
                         "ended": j.ended, "agent": getattr(j, "agent", "claude"),
                         "session": getattr(j, "session", None),
                         "usage": getattr(j, "usage", None), "resumed_by": getattr(j, "resumed_by", None),
                         "resumable": bool(j.state == "paused" and getattr(j, "session", None)
                                           and not getattr(j, "resumed_by", None)),
                         "auto_resume": auto_resume, "retry_blocked": retry_blocked,
                         "estimate_seconds": estimate(j.project, kind) if comparable else None})
    sources = [{"name": "Shared claims", "state": "partial" if LIVE["fetch_error"] or not LIVE["last_fetch"] else "ok",
                "detail": "Last fetched repository state; claim updates show ownership, not live execution.",
                "updated_at": LIVE["last_fetch"] or None}, codex["source"],
               {"name": "Studio jobs", "state": "ok", "detail": "Jobs running on this computer and results from the last 24 hours.", "updated_at": now}]
    return {**work_overview.overview(git_work, sessions=codex["sessions"], jobs=jobs, sources=sources, now=now),
            "fetched": LIVE["last_fetch"], "fetch_error": LIVE["fetch_error"], "every": live.FETCH_EVERY}


# ---------------------------------------------------------------- http
def inventory_keys() -> list[dict]:
    """Everything that can go in "My parts": every priced key (catalog parts and fastener / wire packs)."""
    from .ship import load_prices
    from .export import human_name
    out = []
    for k in sorted(load_prices()):
        name = human_name(k, k) if "." in k and ":" not in k else k
        out.append({"key": k, "name": name})
    return out


def save_inventory(items: dict) -> dict:
    from .ship import INVENTORY, load_prices
    known = set(load_prices())
    clean = {}
    for k, v in items.items():
        if k not in known:
            raise ValueError(f"unknown part key {k} (pick one from the list)")
        q = float(v)
        if q < 0:
            raise ValueError(f"{k}: quantity must be 0 or more")
        if q > 0:
            clean[k] = int(q) if q.is_integer() else q
    try:
        note = json.loads(INVENTORY.read_text(encoding="utf-8")).get("_note")
    except Exception:  # noqa: BLE001
        note = None
    body = json.dumps({"_note": note or "Parts on hand: {key: quantity}.", "items": clean}, indent=2) + "\n"
    INVENTORY.write_text(body, encoding="utf-8")
    return clean


def _safe(base: Path, rel: str) -> Path | None:
    p = (base / unquote(rel)).resolve()
    return p if p.is_file() and (p == base.resolve() or base.resolve() in p.parents) else None


class Handler(BaseHTTPRequestHandler):
    server_version = "KerfStudio/1"

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):   # the window closed mid-request: nothing to answer
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=str).encode(), "application/json")

    def _err(self, msg, code=400):
        self._json({"error": str(msg)}, code)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            _alive()
        parts = [p for p in u.path.split("/") if p]
        q = parse_qs(u.query)
        try:
            if not parts:
                return self._send(200, (ASSETS / "studio.html").read_bytes(), "text/html; charset=utf-8")
            if len(parts) == 2 and parts[0] == "ui" and re.fullmatch(r"[\w-]+\.(js|css)", parts[1]) and (ASSETS / parts[1]).exists():
                return self._send(200, (ASSETS / parts[1]).read_bytes(),
                                  "text/javascript; charset=utf-8" if parts[1].endswith(".js") else "text/css; charset=utf-8")
            if parts == ["api", "projects"]:
                return self._json({"projects": [summary(n) for n in project_names()], "claude": bool(claude_bin()), "codex": bool(agent.codex_bin()),
                                   "agent": agent.mode(),
                                   "platform": platform.system()})
            if parts[:2] == ["api", "project"] and len(parts) == 3:
                if parts[2] not in project_names():
                    return self._err("no such project", 404)
                return self._json(detail(parts[2]))
            if parts == ["api", "claude"]:
                return self._json(claude_ready())
            if parts == ["api", "agent"]:
                return self._json({"mode": agent.mode(), "claude": bool(claude_bin()), "codex": bool(agent.codex_bin()),
                                   "next": pick_agent(), "claude_blocked": usage_blocked()})
            if parts == ["api", "inventory"]:
                from .ship import load_inventory
                return self._json({"items": load_inventory(), "keys": inventory_keys()})
            if parts == ["api", "quotes"]:
                return self._json({"quotes": list_quotes()})
            if parts[:2] == ["api", "quote"] and len(parts) == 3:
                return self._json(read_quote(parts[2]))
            if parts == ["api", "settings"]:
                return self._json(settings())
            if parts == ["api", "glossary"]:
                from . import glossary
                return self._json(glossary.as_json())
            if parts == ["api", "thoughtweb"]:
                from . import thoughtweb
                jid, nm = q.get("job", [""])[0], q.get("project", [""])[0]
                if jid in JOBS:
                    j = JOBS[jid]
                    from . import steer
                    live = j.state == "running"
                    return self._json({**thoughtweb.from_events(j.events, getattr(j, "request", "") or j.label), "live": live, "state": j.state, "label": j.label,
                                       "steerable": live and j.kind in STEERABLE, "steer": steer.read(j.project) if j.kind in STEERABLE else []})
                if nm in project_names():
                    return self._json({**thoughtweb.from_project(PROJECTS / nm), "live": False, "label": nm})
                return self._err("no such job or project", 404)
            if parts == ["api", "printer"]:
                return self._json(printer_info(live=q.get("live", ["0"])[0] == "1"))
            if parts == ["api", "work"]:
                return self._json(work())
            if parts[:2] == ["api", "live"] and len(parts) == 3:
                if parts[2] not in project_names():
                    return self._err("no such project", 404)
                return self._json(live_info(parts[2], int(q.get("since", ["0"])[0])))
            if parts[0] == "live" and len(parts) == 3 and parts[2] == "viewer.html":
                if parts[1] not in project_names():
                    return self._err("no such project", 404)
                from .viewer import html as viewer_html
                d = live_data(parts[1])
                return self._send(200, viewer_html({**d, "live_seq": _live_state(parts[1])["seq"]}).encode(), "text/html; charset=utf-8")
            if parts == ["api", "compare"]:
                nm = q.get("project", [""])[0]
                if nm not in project_names():
                    return self._err("no such project", 404)
                try:
                    return self._json(compare(nm, q.get("source", ["saved"])[0], q.get("target", ["saved"])[0]))
                except ValueError as e:
                    return self._err(e)
            if parts[0] == "thumb" and len(parts) == 2 and parts[1].endswith(".png"):
                f = _safe(THUMBS, parts[1])
                return self._send(200, f.read_bytes(), "image/png") if f else self._err("not found", 404)
            if parts == ["api", "jobs"]:
                if q.get("native"):
                    LIFE["native"] = time.time()
                return self._json({"jobs": [j.info(len(j.lines), len(j.events)) | {"tail": j.lines[-1:]} for j in
                                            sorted(JOBS.values(), key=lambda j: -j.started)], "sessions": sessions()})
            if parts[:2] == ["api", "job"] and len(parts) == 3:
                j = JOBS.get(parts[2])
                return self._json(j.info(int(q.get("since", ["0"])[0]), int(q.get("esince", ["0"])[0]))) if j else self._err("no such job", 404)
            if parts[0] == "export" and len(parts) == 2 and parts[1].endswith(".zip"):
                nm = parts[1][:-4]
                if nm not in project_names():
                    return self._err("no such project", 404)
                body = export_zip(nm)
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Disposition", f'attachment; filename="{nm}.zip"')
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            if parts[0] == "history" and len(parts) == 4 and parts[3] == "thumb.png":
                f = _safe(HISTORY / parts[1], f"{parts[2]}/thumb.png")
                return self._send(200, f.read_bytes(), "image/png") if f else self._err("not found", 404)
            if parts[0] in ("files", "trial") and len(parts) >= 3:
                base = (PROJECTS if parts[0] == "files" else TRIALS) / parts[1]
                f = _safe(base, "/".join(parts[2:]))
                if f is None:
                    return self._err("not found", 404)
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                if f.suffix == ".md":
                    ctype = "text/plain; charset=utf-8"
                if f.name == "viewer.html":
                    from .viewer import current_html
                    page = current_html(f)
                    if page is not None:
                        return self._send(200, page.encode("utf-8"), ctype)
                return self._send(200, f.read_bytes(), ctype)
            return self._err("not found", 404)
        except Exception as e:  # noqa: BLE001
            return self._err(f"{type(e).__name__}: {e}", 500)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/bye":                       # a window is closing (sendBeacon); others keep it alive
            LIFE["bye"] = time.time()
            return self._json({"ok": True})
        _alive()
        if u.path == "/api/quit":
            running = [j.label for j in JOBS.values() if j.state == "running"]
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            if running and not body.get("force"):
                return self._json({"running": running}, 409)
            for j in JOBS.values():
                j.stop()
            self._json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:  # noqa: BLE001
            return self._err("bad json")
        try:
            name = body.get("project")
            if u.path in ("/api/new", "/api/quote"):
                try:
                    if u.path == "/api/quote":
                        j = quote(body.get("name", ""), body.get("description", ""), body.get("intake"))
                    else:
                        j = new_design(body.get("name", ""), body.get("description", ""), body.get("intake"),
                                       body.get("option"), body.get("option_index"))
                except ClaudeNotReady as e:
                    return self._json({"error": str(e), "setup": e.ready["code"]}, 409)
                return self._json({"job": j.id})
            if u.path == "/api/inventory":
                return self._json({"items": save_inventory(body.get("items") or {})})
            if u.path == "/api/claude-setup":
                return self._json(claude_setup())
            if u.path == "/api/settings":
                return self._json(save_settings(body))
            if u.path == "/api/agent":                 # which AI runs jobs: auto / claude / codex (kerf/agent.py)
                return self._json({"mode": agent.set_mode(str(body.get("mode", "")))})
            if u.path == "/api/printer":
                try:
                    return self._json(printer_setup(str(body.get("host", "")), str(body.get("code", "")), body.get("serial")))
                except Exception as e:  # noqa: BLE001 - say what failed (wrong code, printer off, other network)
                    return self._err(str(e))
            if u.path == "/api/notify-test":
                return self._json({"shown": notify("Notifications are on", "You'll get one like this when a long job finishes.")})
            if u.path == "/api/build-all":
                todo = [n for n in project_names() if body.get("all") or _report(PROJECTS / n) is None]
                if not todo:
                    return self._err("every project is already built")
                j = start_job("build", "*", [PY, "-m", "kerf.studio", "_buildall", *todo], f"Build {len(todo)} project(s)", env=PROGRESS_ENV)
                return self._json({"job": j.id})
            if u.path == "/api/steer":                 # "How Kerf decided": focus / skip a question, or a short note
                j = JOBS.get(body.get("job"))
                if not j:
                    return self._err("no such job", 404)
                if j.state != "running" or j.kind not in STEERABLE:
                    return self._err("this job has finished; steering only reaches a design that is still running")
                from . import steer
                return self._json(steer.add(j.project, body.get("action", ""), body.get("label", ""), body.get("text", ""),
                                            body.get("node", "")))
            if u.path == "/api/stop":
                j = JOBS.get(body.get("job"))
                if not j:
                    return self._err("no such job", 404)
                j.stop()
                return self._json({"ok": True})
            if u.path == "/api/resume":
                try:
                    return self._json({"job": resume_job(str(body.get("job", ""))).id})
                except ValueError as e:
                    return self._err(str(e))
            if name not in project_names():
                return self._err("no such project", 404)
            if u.path == "/api/run":
                action = body.get("action")
                if action == "check":
                    j = start_job("check", name, kerf_cmd("check", name), f"Check {name}", env=PROGRESS_ENV)
                elif action == "quick":
                    j = start_job("check", name, kerf_cmd("check", name, "--quick"), f"Quick check {name}", env=PROGRESS_ENV)
                elif action == "build":
                    j = start_job("build", name, kerf_cmd("build", name), f"Build {name}", env=PROGRESS_ENV)
                elif action == "mode":
                    from . import modes
                    m = body.get("mode")
                    if m not in modes.MODES:
                        return self._err(f"unknown mode {m}")
                    if m == "ship" and body.get("confirm_ship") is not True:
                        return self._err("Ship it sends plates to your printer: it needs its own confirmation")
                    j = start_job("build" if m in ("kit", "ship") else "check", name,
                                  kerf_cmd("run", name, "--mode", m, *(["--ship"] if m == "ship" else [])),
                                  f"{MODE_LABEL[m]}: {name}", env=PROGRESS_ENV)
                    j.mode = m
                elif action == "fix":
                    try:
                        j = fix_job(name)
                    except ClaudeNotReady as e:
                        return self._json({"error": str(e), "setup": e.ready["code"]}, 409)
                    except ValueError as e:
                        return self._err(str(e))
                elif action == "optimise":
                    j = start_job("check", name, kerf_cmd("optimise", name), f"Optimise {name}", env=PROGRESS_ENV)
                elif action == "trial":
                    vals = {k: float(v) for k, v in (body.get("values") or {}).items()}
                    j = start_job("trial", name, [PY, "-m", "kerf.studio", "_trial", name], f"Try new values on {name}", env=PROGRESS_ENV,
                                  prepare=lambda: trial_copy(name, vals, {str(k): str(v) for k, v in (body.get("materials") or {}).items()}))
                else:
                    return self._err(f"unknown action {action}")
                return self._json({"job": j.id})
            if u.path in ("/api/save", "/api/restore", "/api/edit", "/api/save-materials"):
                try:
                    guard_claimed(name, body.get("override") is True)
                except Claimed as e:
                    return self._json({"error": str(e), "claimed": True}, 409)
            if u.path == "/api/save":
                with JOB_LOCK:
                    require_idle(name)
                    changed = write_params(PROJECTS / name / "project.yaml", {k: float(v) for k, v in (body.get("values") or {}).items()})
                return self._json({"changed": changed})
            if u.path == "/api/open":
                return self._json(open_in_app(name, body.get("what")))
            if u.path == "/api/restore":
                with JOB_LOCK:
                    require_idle(name)
                    return self._json({"changed": restore(name, str(body.get("stamp", "")))})
            if u.path == "/api/edit":
                try:
                    j = edit_job(name, str(body.get("request", "")), str(body.get("title", "")))
                except ClaudeNotReady as e:
                    return self._json({"error": str(e), "setup": e.ready["code"]}, 409)
                return self._json({"job": j.id})
            if u.path == "/api/duplicate":
                dst = duplicate(name, str(body.get("name", "")), str(body.get("title", "")))
                out = {"name": dst.name}
                if str(body.get("change", "")).strip():
                    try:
                        out["job"] = edit_job(dst.name, str(body["change"]), str(body.get("change", ""))[:60]).id
                    except ClaudeNotReady as e:
                        out["setup"] = e.ready["code"]
                        out["error"] = f"copied, but the change didn't start: {e}"
                return self._json(out)
            if u.path == "/api/save-materials":
                with JOB_LOCK:
                    require_idle(name)
                    return self._json({"changed": write_materials(PROJECTS / name / "project.yaml", {str(k): str(v) for k, v in (body.get("materials") or {}).items()})})
            if u.path == "/api/thumb":
                return self._json(save_thumb(name, str(body.get("png", "")), body.get("fingerprint")))
            if u.path == "/api/live/follow":
                return self._json(follow(name, bool(body.get("on"))))
            return self._err("not found", 404)
        except ValueError as e:
            return self._err(e)
        except Exception as e:  # noqa: BLE001
            return self._err(f"{type(e).__name__}: {e}", 500)


def _trial(name: str) -> int:
    """Child process: full check + exports (no renders) of the scratch copy, so the page can show its 3D model."""
    from .pipeline import run, summary as summ
    rep = run(str(TRIALS / name), sweeps=True, do_export=True, do_render=False)
    print(summ(rep), flush=True)
    return 0 if rep["ok"] else 1


def _buildall(names: list[str]) -> int:
    bad = 0
    for i, n in enumerate(names, 1):
        print(f"[{i}/{len(names)}] building {n} ...", flush=True)
        print("@@" + json.dumps({"k": "project", "name": n, "i": i, "n": len(names)}), flush=True)
        t0 = time.time()
        p = subprocess.Popen(kerf_cmd("build", n), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             env={**os.environ, **PROGRESS_ENV})
        first = None
        for ln in p.stdout:
            if ln.startswith("@@"):
                print(ln.rstrip("\n"), flush=True)
            elif first is None and ln.strip() and ln.split()[0] in ("PASS", "FAIL"):
                first = ln.strip()
        rc = p.wait()
        bad += rc != 0
        if rc == 0:                       # same bookkeeping as a single Studio build: run time + a version entry
            try:
                record_time(n, "build", time.time() - t0)
                snapshot(n)
            except Exception:  # noqa: BLE001
                pass
        print(f"    {first or 'finished'}", flush=True)
    print(f"done: {len(names) - bad} passed, {bad} with problems", flush=True)
    return 1 if bad else 0


def _watchdog(srv, idle: float, grace: float, bye_wait: float = 6.0):
    t0 = prev = time.time()
    while True:
        time.sleep(1.0)
        now = time.time()
        if now - prev > 30:                          # the computer slept: give open windows time to check in again
            LIFE["last"] = now
        prev = now
        if busy():
            continue
        quiet = now - LIFE["last"]
        if LIFE["bye"] and now - LIFE["bye"] >= bye_wait:
            break                                   # the last window said goodbye and nobody came back
        if LIFE["seen"] and quiet >= idle:
            break                                   # every window is gone (closed, crashed or the Mac slept)
        if not LIFE["seen"] and now - t0 >= grace:
            break                                   # started but never opened
    print("Kerf Studio: no window open and nothing running; closing.", flush=True)
    srv.shutdown()


def serve(port: int = 8765, open_browser: bool = True, idle_exit: float | None = None) -> int:
    srv = None
    for p in range(port, min(port + 20, 65536)):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            port = p
            break
        except OSError:
            continue
    if srv is None:
        print("no free port near", port)
        return 1
    url = f"http://127.0.0.1:{port}/"
    print(f"Kerf Studio running at {url}  (Ctrl+C to stop)", flush=True)
    if idle_exit:
        grace = float(os.environ.get("KERF_STUDIO_GRACE", max(90.0, 3 * idle_exit)))
        threading.Thread(target=_watchdog, args=(srv, float(idle_exit), grace), daemon=True).start()
    if open_browser:
        import webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    if len(sys.argv) >= 3 and sys.argv[1] == "_trial":
        sys.exit(_trial(sys.argv[2]))
    if len(sys.argv) >= 3 and sys.argv[1] == "_buildall":
        sys.exit(_buildall(sys.argv[2:]))
