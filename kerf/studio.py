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
                        self.events.append(json.loads(ln[2:]))
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
            "review": rv, "thumb": _thumb(d), "running": running}


def detail(name: str) -> dict:
    d = PROJECTS / name
    data = _read_yaml(name)
    rep = _report(d) or {}
    params = []
    for k, v in (data.get("params") or {}).items():
        spec = v if isinstance(v, dict) else {"value": v}
        val = spec.get("value")
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            continue
        lo = spec.get("min", round(val * 0.5, 3) if val else 0)
        hi = spec.get("max", round(val * 1.5, 3) if val else 10)
        params.append({"key": k, "value": val, "min": lo, "max": hi, "step": spec.get("step", 0.1 if isinstance(val, float) else 1),
                       "label": spec.get("label", k), "bounded": "min" in spec and "max" in spec})
    files = []
    out = d / "out"
    if out.exists():
        for rel in ("plates", "parts"):
            for f in sorted((out / rel).glob("*")) if (out / rel).exists() else []:
                if f.suffix in (".3mf", ".stl", ".md"):
                    files.append(str(f.relative_to(d)))
        for f in ("assembly.step", "bom.csv", "bom.md", "ASSEMBLY.md", "WIRING.md", "viewer.html"):
            if (out / f).exists():
                files.append(f"out/{f}")
    docs = [f for f in ("DESIGN.md", "REFERENCES.md", "out/ASSEMBLY.md", "out/WIRING.md", "out/bom.md",
                        "out/plates/PRINT_SETTINGS.md") if (d / f).exists()]
    renders = sorted(str(p.relative_to(d)) for p in (out / "renders").glob("*.png")) if (out / "renders").exists() else []
    trial = TRIALS / name
    trial_rep = _report(trial) if (trial / "out" / "viewer.html").exists() else None
    return {**summary(name), "params": params, "files": files, "docs": docs, "renders": renders[:40],
            "report": {k: rep.get(k) for k in ("ok", "problems", "warnings", "requirements", "bom", "seconds", "fingerprint")} if rep else None,
            "viewer": "out/viewer.html" if (out / "viewer.html").exists() else None,
            "trial": {"params": trial_rep.get("params") if trial_rep else None, "ok": trial_rep.get("ok") if trial_rep else None,
                      "problems": trial_rep.get("problems") if trial_rep else None,
                      "requirements": trial_rep.get("requirements") if trial_rep else None} if trial_rep else None}


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
        return [raw]
    out = []
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
        out.append(f"== finished: {ev.get('subtype', '')} in {round(ev.get('duration_ms', 0) / 60000, 1)} min ==")
        if ev.get("result"):
            out.append(str(ev["result"]))
    return out


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


def new_design(name: str, description: str) -> Job:
    if not NAME_RE.match(name):
        raise ValueError("name: lowercase letters, digits and _ (2-41 chars), starting with a letter")
    if (PROJECTS / name).exists():
        raise ValueError(f"projects/{name} already exists")
    if not description.strip():
        raise ValueError("describe what to design")
    exe = claude_bin()
    if not exe:
        raise ValueError("Claude Code (`claude`) is not installed on this computer: npm install -g @anthropic-ai/claude-code")
    prompt = (f"/kerf {description.strip()}\n\nProject folder name: projects/{name}. Spencer started this from Kerf Studio "
              f"and is not watching the terminal: work autonomously to a finished, built and reviewed project.")
    return start_job("design", name, [exe, "-p", prompt, "--output-format", "stream-json", "--verbose"],
                     f"New design: {description.strip()[:60]}", parse=_claude_lines)


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
            if parts == ["api", "jobs"]:
                return self._json({"jobs": [j.info(len(j.lines), len(j.events)) | {"tail": j.lines[-1:]} for j in
                                            sorted(JOBS.values(), key=lambda j: -j.started)]})
            if parts[:2] == ["api", "job"] and len(parts) == 3:
                j = JOBS.get(parts[2])
                return self._json(j.info(int(q.get("since", ["0"])[0]), int(q.get("esince", ["0"])[0]))) if j else self._err("no such job", 404)
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
            if u.path == "/api/new":
                j = new_design(body.get("name", ""), body.get("description", ""))
                return self._json({"job": j.id})
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
        p = subprocess.Popen(kerf_cmd("build", n), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             env={**os.environ, **PROGRESS_ENV})
        first = None
        for ln in p.stdout:
            if ln.startswith("@@"):
                print(ln.rstrip("\n"), flush=True)
            elif first is None and ln.strip() and ln.split()[0] in ("PASS", "FAIL"):
                first = ln.strip()
        bad += p.wait() != 0
        print(f"    {first or 'finished'}", flush=True)
    print(f"done: {len(names) - bad} passed, {bad} with problems", flush=True)
    return 1 if bad else 0


def _watchdog(srv, idle: float, grace: float, bye_wait: float = 6.0):
    t0 = time.time()
    while True:
        time.sleep(1.0)
        now = time.time()
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
