"""Kerf Studio: a local web app to run and control Kerf Forge (`kerf studio`, opens http://127.0.0.1:8765).

Everything goes through the same engine and CLI as the terminal; the studio only starts jobs and shows results.
  - projects: status (build / review / eval), 3D viewer, requirements, problems, BOM, docs, downloadable files
  - parameters: sliders from project.yaml `params` (value/min/max/step/label). "Try" builds a scratch copy with the
    new values (the real project and its review are untouched); "Save" writes the values into project.yaml (that
    makes the review stale, which the page says); "Reset" goes back to the file.
  - actions: check, build, open plates in Bambu Studio, show the folder
  - new design: a description goes to Claude Code (`claude -p "/kerf ..."`) running in the repo; its progress streams
    into the page and the project appears in the list when its folder exists
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
        self.started, self.ended = time.time(), None
        self.result: dict | None = None
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
                        self.events.append(ev)
                        if ev.get("k") == "hint" and self.state == "running":   # can't succeed: stop now, say why
                            self.state = "failed"
                            try:
                                os.killpg(self.proc.pid, 15)
                            except Exception:  # noqa: BLE001
                                self.proc.terminate()
                        continue
                    except Exception:  # noqa: BLE001
                        pass
                self.lines.append(ln)
        rc = self.proc.wait()
        self.ended = time.time()
        if rc and self.state == "running":
            self.lines.append(f"(stopped by signal {-rc}: out of memory or killed)" if rc < 0 else f"(exit code {rc})")
        if self.state == "running":
            self.state = "done" if rc == 0 else "failed"
        try:
            on_finished(self)
        except Exception:  # noqa: BLE001 - bookkeeping never breaks a job
            pass

    def stop(self):
        if self.state == "running":
            self.state = "stopped"
            try:
                os.killpg(self.proc.pid, 15)
            except Exception:  # noqa: BLE001
                self.proc.terminate()

    def info(self, since: int = 0, esince: int = 0) -> dict:
        end = self.ended or time.time()
        return {"id": self.id, "kind": self.kind, "project": self.project, "label": self.label, "state": self.state,
                "started": self.started, "seconds": round(end - self.started, 1), "lines": self.lines[since:],
                "n": len(self.lines), "events": self.events[esince:], "ne": len(self.events)}


JOBS: dict[str, Job] = {}

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
    """Seconds a build / check of this project usually takes: median of its last runs from Studio, else the last
    report's own run time for a build."""
    runs = _times().get(project, {}).get(kind) or []
    if runs:
        return float(sorted(runs)[len(runs) // 2])
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
    if job.state != "done" or job.project in ("*", None) or job.kind not in ("build", "check"):
        return
    record_time(job.project, job.kind, (job.ended or time.time()) - job.started)
    if job.kind == "build":
        snapshot(job.project)


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
LIFE = {"last": time.time(), "bye": None, "seen": False}


def _alive():
    """A window talked to us. A request landing right after a goodbye is usually the closing page's own last poll,
    so it doesn't cancel the goodbye; a window that is really still open polls again within a few seconds."""
    now = time.time()
    LIFE.update(last=now, seen=True)
    if LIFE["bye"] and now - LIFE["bye"] > 2.0:
        LIFE["bye"] = None


def busy() -> bool:
    return any(j.state == "running" for j in JOBS.values())


def start_job(*a, **k) -> Job:
    j = Job(*a, **k)
    JOBS[j.id] = j
    return j


PROGRESS_ENV = {"KERF_PROGRESS": "1", "PYTHONUNBUFFERED": "1"}


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
    return {"name": name, "title": data.get("name", name), "description": (data.get("description") or "").strip(),
            "built": rep is not None, "ok": bool(rep and rep.get("ok")),
            "problems": len(rep.get("problems", [])) if rep else None,
            "stale": bool(rep and rv.get("fingerprint") and rep.get("fingerprint") != rv.get("fingerprint")),
            "review": rv, "thumb": _thumb(d), "running": running, "build_s": estimate(name, "build")}


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
                        "out/plates/PRINT_SETTINGS.md") if (d / f).exists()]
    renders = sorted(str(p.relative_to(d)) for p in (out / "renders").glob("*.png")) if (out / "renders").exists() else []
    trial = TRIALS / name
    trial_rep = _report(trial) if (trial / "out" / "viewer.html").exists() else None
    return {**summary(name), "params": params, "files": files, "docs": docs, "renders": renders[:40],
            "report": {k: rep.get(k) for k in ("ok", "problems", "warnings", "maker_notes", "mass", "requirements", "bom", "seconds", "fingerprint")} if rep else None,
            "viewer": "out/viewer.html" if (out / "viewer.html").exists() else None,
            "history": history(name),
            "estimate": {"build": estimate(name, "build"), "check": estimate(name, "check")},
            "summary_numbers": _numbers(rep),
            "trial": {"params": trial_rep.get("params") if trial_rep else None, "ok": trial_rep.get("ok") if trial_rep else None,
                      "problems": trial_rep.get("problems") if trial_rep else None,
                      "requirements": trial_rep.get("requirements") if trial_rep else None} if trial_rep else None}


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
        spec = known[k]
        if isinstance(spec, dict) and "min" in spec and "max" in spec and not (spec["min"] - 1e-9 <= v <= spec["max"] + 1e-9):
            raise ValueError(f"{k} = {v} is outside its allowed range {spec['min']}..{spec['max']}")
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


def trial_copy(name: str, values: dict) -> Path:
    """Scratch copy of a project (sources only) with new param values; the real project is never touched."""
    src, dst = PROJECTS / name, TRIALS / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "review.json"))
    write_params(dst / "project.yaml", values)
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
            elif c.get("type") == "tool_use":
                inp = c.get("input", {})
                what = inp.get("description") or inp.get("command") or inp.get("file_path") or inp.get("prompt") or ""
                out.append(f"  > {c.get('name')}: {str(what).splitlines()[0][:140] if what else ''}")
            if c.get("type") == "tool_use":
                ph = _phase(c.get("name", ""), inp)
                out.append("@@" + json.dumps({"k": "tool", "name": c.get("name"), "what": str(what).splitlines()[0][:140] if what else "",
                                               "phase": ph}))
    elif t == "result":
        bad = ev.get("is_error") or ev.get("subtype") != "success"
        out.append(f"== {'stopped with an error' if bad else 'finished'} after {round(ev.get('duration_ms', 0) / 60000, 1)} min ==")
        if ev.get("result"):
            out.append(str(ev["result"]))
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
    signed in. Free: no model call."""
    exe = claude_bin()
    if not exe:
        return {"ok": False, "code": "missing", "why": "Claude Code isn't installed on this computer."}
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
                 "environment": "Environment", "printer": "Printer", "material": "Material", "notes": "Other constraints"}
QUOTES = ROOT / ".cache" / "studio" / "quotes"


def brief(description: str, intake: dict | None = None, option: dict | None = None) -> str:
    """The design brief Claude gets: the request, Spencer's answers to the intake questions, the parts he has on hand,
    and (after a quote) the option he picked."""
    from .ship import load_inventory
    L = [description.strip()]
    answers = [f"- {INTAKE_FIELDS[k]}: {str(v).strip()}" for k, v in (intake or {}).items() if k in INTAKE_FIELDS and str(v).strip()]
    if answers:
        L += ["", "Spencer's answers to the intake questions:", *answers]
    inv = load_inventory()
    if inv:
        L += ["", "Parts on hand (prefer these where they fit; the BOM counts them first): "
              + ", ".join(f"{k} x{v:g}" for k, v in sorted(inv.items()))]
    if option:
        L += ["", f"Spencer picked this option from the quote: {option.get('title', '')} - {option.get('summary', '')}"]
        if option.get("purchased"):
            L.append("Its purchased parts: " + ", ".join(f"{x.get('key')} x{x.get('qty', 1)}" for x in option["purchased"]))
    return "\n".join(L)


def _check_new(name: str, description: str):
    if not NAME_RE.match(name):
        raise ValueError("name: lowercase letters, digits and _ (2-41 chars), starting with a letter")
    if (PROJECTS / name).exists():
        raise ValueError(f"projects/{name} already exists")
    if not description.strip():
        raise ValueError("describe what to design")
    ready = claude_ready()
    if not ready["ok"]:
        raise ClaudeNotReady(ready)


def new_design(name: str, description: str, intake: dict | None = None, option: dict | None = None) -> Job:
    _check_new(name, description)
    exe = claude_bin()
    prompt = (f"/kerf {brief(description, intake, option)}\n\nProject folder name: projects/{name}. Spencer started this from "
              f"Kerf Studio and is not watching the terminal: work autonomously to a finished, built and reviewed project.")
    return start_job("design", name, [exe, "-p", prompt, "--output-format", "stream-json", "--verbose"],
                     f"New design: {description.strip()[:60]}", parse=_claude_lines)


def quote(name: str, description: str, intake: dict | None = None) -> Job:
    """Quote first: Claude researches and writes 2-3 candidate architectures with cost, print time and part count to
    .cache/studio/quotes/<name>.json (kerf skill, "Quote mode") and stops; nothing is designed until one is picked."""
    _check_new(name, description)
    QUOTES.mkdir(parents=True, exist_ok=True)
    out = QUOTES / f"{name}.json"
    out.unlink(missing_ok=True)
    prompt = (f"/kerf QUOTE ONLY. {brief(description, intake)}\n\nWrite the quote to {out} as the kerf skill's Quote mode "
              f"says and stop: do not create projects/{name} or any design files.")
    return start_job("quote", name, [claude_bin(), "-p", prompt, "--output-format", "stream-json", "--verbose"],
                     f"Options for: {description.strip()[:60]}", parse=_claude_lines)


def read_quote(name: str) -> dict:
    """The quote file, checked: 1-3 options, each with a title, summary, part count, cost and print hours."""
    f = QUOTES / f"{name}.json"
    if not NAME_RE.match(name) or not f.exists():
        raise ValueError("no quote yet")
    q = json.loads(f.read_text(encoding="utf-8"))
    opts = q.get("options") if isinstance(q, dict) else None
    if not isinstance(opts, list) or not 1 <= len(opts) <= 3:
        raise ValueError("the quote has no options (expected 1-3)")
    for o in opts:
        missing = [k for k in ("title", "summary", "parts_printed", "cost_usd", "print_hours") if o.get(k) in (None, "")]
        if missing:
            raise ValueError(f"quote option '{o.get('title', '?')}' is missing {', '.join(missing)}")
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
    INVENTORY.write_text(json.dumps({"_note": note or "Parts on hand: {key: quantity}.", "items": clean}, indent=2) + "\n",
                         encoding="utf-8")
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
            if parts == ["api", "projects"]:
                return self._json({"projects": [summary(n) for n in project_names()], "claude": bool(claude_bin()),
                                   "platform": platform.system()})
            if parts[:2] == ["api", "project"] and len(parts) == 3:
                if parts[2] not in project_names():
                    return self._err("no such project", 404)
                return self._json(detail(parts[2]))
            if parts == ["api", "claude"]:
                return self._json(claude_ready())
            if parts == ["api", "inventory"]:
                from .ship import load_inventory
                return self._json({"items": load_inventory(), "keys": inventory_keys()})
            if parts[:2] == ["api", "quote"] and len(parts) == 3:
                return self._json(read_quote(parts[2]))
            if parts == ["api", "jobs"]:
                return self._json({"jobs": [j.info(len(j.lines), len(j.events)) | {"tail": j.lines[-1:]} for j in
                                            sorted(JOBS.values(), key=lambda j: -j.started)]})
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
                        j = new_design(body.get("name", ""), body.get("description", ""), body.get("intake"), body.get("option"))
                except ClaudeNotReady as e:
                    return self._json({"error": str(e), "setup": e.ready["code"]}, 409)
                return self._json({"job": j.id})
            if u.path == "/api/inventory":
                return self._json({"items": save_inventory(body.get("items") or {})})
            if u.path == "/api/claude-setup":
                return self._json(claude_setup())
            if u.path == "/api/build-all":
                todo = [n for n in project_names() if body.get("all") or _report(PROJECTS / n) is None]
                if not todo:
                    return self._err("every project is already built")
                j = start_job("build", "*", [PY, "-m", "kerf.studio", "_buildall", *todo], f"Build {len(todo)} project(s)", env=PROGRESS_ENV)
                return self._json({"job": j.id})
            if u.path == "/api/stop":
                j = JOBS.get(body.get("job"))
                if not j:
                    return self._err("no such job", 404)
                j.stop()
                return self._json({"ok": True})
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
                elif action == "trial":
                    vals = {k: float(v) for k, v in (body.get("values") or {}).items()}
                    trial_copy(name, vals)
                    j = start_job("trial", name, [PY, "-m", "kerf.studio", "_trial", name], f"Try new values on {name}", env=PROGRESS_ENV)
                else:
                    return self._err(f"unknown action {action}")
                return self._json({"job": j.id})
            if u.path == "/api/save":
                changed = write_params(PROJECTS / name / "project.yaml", {k: float(v) for k, v in (body.get("values") or {}).items()})
                return self._json({"changed": changed})
            if u.path == "/api/open":
                return self._json(open_in_app(name, body.get("what")))
            if u.path == "/api/restore":
                return self._json({"changed": restore(name, str(body.get("stamp", "")))})
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
    for p in range(port, port + 20):
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
