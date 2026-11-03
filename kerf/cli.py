"""kerf command line.

  kerf doctor                 environment self-test (must print ALL OK)
  kerf check  <project>       build + all checks, no files (fast loop while designing)
  kerf build  <project>       check + STEP/STL/3MF/plates/BOM + renders into projects/<p>/out/
  kerf verify [--fast]        the definition of done: tests, every project, every eval, every review
  kerf review-status <proj>   is the visual review current for this geometry?
  kerf new <name> "<title>"   scaffold a project
  kerf status                 one-screen overview: plan progress, every project, review and eval state
  kerf studio                 open Kerf Studio, the point-and-click app for everything above (local, in your browser)
  kerf print <project>        orient + plate + slice (Bambu Studio CLI) [--send N: start plate N over LAN] [--dry-run] [--open]
"""
from __future__ import annotations

import os
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _p(*a):
    print(*a, flush=True)


def doctor() -> int:
    bad = []
    try:
        import build123d, bd_warehouse, py_gearworks, trimesh, yaml  # noqa: F401
        _p(f"ok   python libs (build123d {build123d.__version__})")
    except Exception as e:
        bad.append(f"python libs: {e}")
    try:
        from . import catalog
        d = catalog.load()
        need = ["screws", "fdm_holes", "bearings", "servos", "servo_horns", "steppers", "drone", "motion", "boards", "materials", "rods"]
        need_drone = [k for k in ("motors", "props", "stacks", "batteries", "cameras") if k not in d.get("drone", {})]
        if need_drone:
            bad.append(f"catalog drone section missing {need_drone}")
        missing = [k for k in need if k not in d]
        unsourced = catalog.unsourced()
        if missing:
            bad.append(f"catalog missing categories {missing}")
        if unsourced:
            bad.append(f"catalog entries without a source: {unsourced[:8]}")
        if not missing and not unsourced:
            _p(f"ok   catalog ({sum(len(v) for k, v in d.items() if isinstance(v, dict) and not k.startswith('_'))} entries, all sourced)")
    except Exception as e:
        bad.append(f"catalog: {e}")
    try:
        from build123d import Box, export_gltf
        import tempfile
        from .pipeline import render_glb
        with tempfile.TemporaryDirectory() as t:
            g = Path(t) / "c.glb"
            export_gltf(Box(10, 20, 30), str(g), binary=True)
            info = render_glb(g, Path(t) / "c", views="iso", sheet=False)
            assert (Path(t) / "c_iso.png").stat().st_size > 5000
            _p(f"ok   headless renderer (box {info['size_mm']})")
    except Exception as e:
        bad.append(f"renderer: {e}")
    try:                                    # circuit check (kerf/circuit.py): SKiDL + KiCad symbols for every pin table
        from . import circuit
        skidl = circuit._skidl()             # (imported this way so SKiDL writes no .log/.erc files into the repo)
        n = sum(len(circuit.kicad_symbol(*e["symbol"].split(":"))) for e in circuit.load_pins().values() if e.get("symbol"))
        _p(f"ok   circuit check (SKiDL {skidl.__version__}, {n} KiCad symbols from {circuit.symbol_dir()})")
    except Exception as e:
        bad.append(f"circuit check: {e} (run ./setup.sh)")
    try:   # firmware check tools: missing ones are reported (firmware-check then says NOT RUN), not a doctor failure
        from . import fwcheck
        t = fwcheck.tools()
        if t["arduino_cli"] and t["core"] and t["avrsim"]:
            _p(f"ok   firmware check (arduino-cli {fwcheck.ARDUINO_CLI}, {fwcheck.CORE}, simavr harness)")
        else:
            _p("warn firmware check tools missing: " + "; ".join(
                w for w in ("" if t["arduino_cli"] and t["core"] else "arduino-cli/arduino:avr (run ./setup.sh)",
                            "" if t["avrsim"] else t["avrsim_why"]) if w) + " - `kerf firmware-check` reports NOT RUN")
    except Exception as e:  # noqa: BLE001
        _p(f"warn firmware check: {e}")
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "remote", "-v"], capture_output=True, text=True)
        _p(f"ok   git remote: {r.stdout.split()[1] if r.stdout.strip() else '(none — work will not be saved remotely!)'}")
    except Exception as e:
        bad.append(f"git: {e}")
    for b in bad:
        _p(f"FAIL {b}")
    _p("ALL OK" if not bad else f"{len(bad)} PROBLEM(S)")
    return 0 if not bad else 1


def check(name, full=False, quick=False, everything=False) -> int:
    from .pipeline import run, summary
    rep = run(name, sweeps=not quick, do_export=full, do_render=full, everything=everything)
    _p(summary(rep))
    if rep.get("traces"):
        for k, t in rep["traces"].items():
            _p(f"--- traceback {k}\n{t}")
    return 0 if rep["ok"] else 1


def req(name, ids) -> int:
    """`kerf req <p> [id ...]`: just these requirements (pipeline.run_requirements)."""
    import time
    from .pipeline import req_line, run_requirements
    t = time.time()
    r = run_requirements(name, ids or None)
    for x in r["results"]:
        _p(f"  {x['id']}: {req_line(x)}")
        if x.get("value") is None and x.get("detail"):
            _p(f"      {x['detail']}")
        for t in x.get("advice") or []:
            _p(f"      -> {t}")
    for p in r["problems"]:
        _p(f"PROBLEM {p}")
    _p(f"{'ok' if r['ok'] else 'FAIL'}: {len(r['results'])} requirement(s) in {time.time() - t:.1f} s "
       f"({len(r.get('cached_parts', []))} parts from cache; `kerf check` decides PASS)")
    return 0 if r["ok"] else 1


def run_mode(name: str, mode: str, ship_confirmed: bool = False, runner=None) -> int:
    """kerf run <p> --mode <m> (kerf/modes.py). Ship it: refused without --ship; after the kit it needs a current
    design-review PASS, then hands plate 1 to the printer (kerf print --send 1)."""
    from . import modes
    from .pipeline import run, summary
    try:
        modes.confirm_ship(mode, ship_confirmed)
    except modes.ShipNotConfirmed as e:
        _p(f"FAIL {e}")
        return 2
    rep = (runner or run)(name, mode=mode)
    _p(f"mode {mode}: {modes.GIVES[mode]} (stages: {', '.join(rep.get('stages', []))})")
    _p(summary(rep))
    if not rep["ok"] or mode != "ship":
        return 0 if rep["ok"] else 1
    rs = review_status(name)
    if not rs["ok"]:
        _p(f"FAIL Ship it needs a current design review PASS before anything prints: {rs['why']}")
        return 1
    from . import bambu
    try:
        r = bambu.run(name, send_plate=1, say=_p)
    except (ValueError, RuntimeError) as e:
        _p(f"FAIL {e}")
        return 1
    if r["sent"] is None or not r["sent"]["started"]:
        _p(f"FAIL the printer did not report the job started: {(r['sent'] or {}).get('status')}")
        return 1
    _p("plate 1 is printing; send the next with `kerf print " + name + " --send 2` when it is off the bed")
    return 0


def projects() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / "projects").glob("*/project.yaml"))


INTENT = ("load_path", "feature_purpose", "print_intent", "finish")


def intent_scores(review: dict, printed: list[str]) -> str | None:
    """The reviewer scores every printed part on design intent (design-reviewer.md item 6); a PASS needs >= 3 on each."""
    sc = review.get("scores")
    if not sc:
        return "review has no design-intent scores (design-reviewer.md item 6); review again"
    missing = [p for p in printed if p not in sc]
    if missing:
        return f"review scores no design intent for {missing}; review again"
    low = [f"{p}.{k}={sc[p].get(k)}" for p in printed for k in INTENT if not isinstance(sc[p].get(k), (int, float)) or sc[p][k] < 3]
    return f"design-intent scores below 3: {', '.join(low)}" if low else None


def review_status(name) -> dict:
    from . import project as P
    try:
        proj = P.load(name)
        fp = proj.fingerprint()
    except (OSError, ValueError) as e:
        return {"ok": False, "why": str(e), "fingerprint": None}
    f = proj.dir / "review.json"
    if not f.exists():
        return {"ok": False, "why": f"no review.json (fingerprint {fp})", "fingerprint": fp}
    r = json.loads(f.read_text(encoding="utf-8"))
    if r.get("fingerprint") != fp:
        return {"ok": False, "why": f"review is for fingerprint {r.get('fingerprint')}, geometry is now {fp}; review again", "fingerprint": fp}
    if r.get("verdict") != "PASS":
        return {"ok": False, "why": f"review verdict {r.get('verdict')}: {r.get('summary', '')}", "fingerprint": fp}
    bad = intent_scores(r, list(proj.printed))
    if bad:
        return {"ok": False, "why": bad, "fingerprint": fp}
    out = _out_stale(proj, fp)
    return {"ok": True, "why": "current PASS review" + (f"; {out}" if out else ""), "fingerprint": fp, "out_stale": bool(out)}


def _out_stale(proj, fp) -> str:
    """ENG-18: out/ (ASSEMBLY.md, BOM, renders the reviewer read) built from other inputs than the current geometry.
    The review itself still stands (verify rebuilds every project); this only says the shipped docs need `kerf build`."""
    rp = proj.dir / "out" / "report.json"
    if not rp.exists():
        return "out/ not built yet: run kerf build"
    try:
        ofp = json.loads(rp.read_text(encoding="utf-8")).get("fingerprint")
    except Exception:  # noqa: BLE001
        return "out/report.json unreadable: run kerf build"
    return "" if ofp == fp else f"out/ is from fingerprint {ofp}, not {fp}: run kerf build"


def _run_isolated(name, check_only=False, fast=False) -> dict:
    """Build one project in a child process so its OCC/mesh memory is returned to the OS before the next one
    (all projects in one process grew past 6 GB and was OOM-killed on a 7 GB machine, 2026-11-02)."""
    code = ("import json,sys; from kerf.pipeline import run; n,c,f=sys.argv[1],sys.argv[2]=='1',sys.argv[3]=='1'; "
            "r=run(n,mode='check') if c else run(n,sweeps=True,do_export=not f,do_render=not f); "
            "print('KERF_RESULT '+json.dumps({'ok':bool(r['ok']),'problems':[str(p) for p in r['problems']]}))")
    r = subprocess.run([sys.executable, "-c", code, name, "1" if check_only else "0", "1" if fast else "0"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
    for line in reversed(r.stdout.splitlines()):
        if line.startswith("KERF_RESULT "):
            return json.loads(line[len("KERF_RESULT "):])
    return {"ok": False, "problems": [f"build process exited {r.returncode}: {(r.stderr or r.stdout)[-300:]}"]}


class _Checkpoint:
    """Finished verify steps (pytest, each project) for the current commit, so a run cut off by a usage limit, a
    timeout or a kill resumes where it stopped instead of redoing an hour of work. Only used on a clean tree (tracked
    files): the results then belong to that exact commit. Local file, cleared when a run completes."""
    PATH = ROOT / ".claude" / "state" / "verify_checkpoint.json"

    def __init__(self, fast, all_failures):
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "-uno"], cwd=ROOT, capture_output=True,
                               text=True).stdout.strip()
        self.key = None if dirty or not head else f"{head} fast={fast} all={all_failures}"
        self.done = {}
        try:
            old = json.loads(self.PATH.read_text(encoding="utf-8"))
            if self.key and old.get("key") == self.key:
                self.done = old.get("done", {})
        except Exception:  # noqa: BLE001 - no checkpoint
            pass

    def save(self, step, result):
        self.done[step] = result
        if self.key:
            self.PATH.parent.mkdir(parents=True, exist_ok=True)
            self.PATH.write_text(json.dumps({"key": self.key, "done": self.done}, default=str), encoding="utf-8")

    def clear(self):
        self.PATH.unlink(missing_ok=True)


def verify(fast=False, all_failures=False) -> int:
    """The definition of done. Exit 0 only when everything passes."""
    t0 = time.time()
    results, fails = {}, []
    os.environ["KERF_NO_CACHE"] = "1"      # the definition of done builds every part from scratch (kerf/partcache.py)
    os.environ["KERF_NO_ATTRIBUTION"] = "1"   # viewer click-to-edit cannot change a verdict; minutes per project
    # tests read/write UTF-8 text without naming it; a C/POSIX locale (hooks, cron, nohup) would make that ASCII
    ck = _Checkpoint(fast, all_failures)
    if "tests" not in ck.done:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", *([] if all_failures else ["-x"]), "--no-header",
                            "-p", "no:cacheprovider"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        ck.save("tests", {"line": r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:],
                          "ok": r.returncode == 0})
    else:
        _p("tests: reusing this commit's finished result (an earlier run was cut off)")
    results["tests"] = ck.done["tests"]["line"]
    if not ck.done["tests"]["ok"]:
        fails.append(f"unit tests: {results['tests']}")
    from . import project as P
    for name in projects():
        check_only = bool(P.load(name).data.get("check_only"))   # a user's own design, checked, not designed by Kerf
        if name not in ck.done:
            ck.save(name, _run_isolated(name, check_only, fast))
        rep = ck.done[name]
        results[name] = {"ok": rep["ok"], "problems": rep["problems"][:6]}
        if not rep["ok"]:
            fails.append(f"project {name}: {rep['problems'][:3]}")
        if check_only:
            continue                     # the check report is the product: there is no Kerf design to review
        rs = review_status(name)
        results[name]["review"] = rs
        if not rs["ok"]:
            fails.append(f"project {name}: {rs['why']}")
    from evals import run_evals
    ev = run_evals.run_all()
    results["evals"] = ev
    for e in ev:
        if not e["ok"]:
            fails.append(f"eval {e['id']}: {e['failures'][:3]}")
    plan = (ROOT / "PLAN.md").read_text(encoding="utf-8")
    open_items = [l.strip() for l in plan.splitlines() if l.strip().startswith("- [ ]")]
    if open_items:
        fails.append(f"PLAN.md has {len(open_items)} unchecked items, first: {open_items[0]}")
    ck.clear()
    out = {"ok": not fails, "fails": fails, "results": results, "seconds": round(time.time() - t0, 1)}
    (ROOT / "VERIFY.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for f in fails:
        _p(f"FAIL {f}")
    _p(("VERIFY PASSED" if not fails else f"VERIFY FAILED ({len(fails)})") + f" in {out['seconds']} s")
    return 0 if not fails else 1


def status() -> int:
    plan = (ROOT / "PLAN.md").read_text(encoding="utf-8").splitlines()
    done = sum(l.strip().startswith("- [x]") for l in plan)
    todo = [l.strip()[6:] for l in plan if l.strip().startswith("- [ ]")]
    _p(f"PLAN: {done} done, {len(todo)} open" + (f"; next: {todo[0][:110]}" if todo else ""))
    from evals import run_evals
    ev = {e["id"]: e for e in run_evals.run_all()}
    for name in projects():
        rp = ROOT / "projects" / name / "out" / "report.json"
        rep = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else None
        rs = review_status(name)
        state = "no build yet" if rep is None else ("PASS" if rep["ok"] else f"FAIL ({len(rep['problems'])} problems)")
        fresh = "" if rep is None or rep.get("fingerprint") == rs["fingerprint"] else " (stale: geometry changed since)"
        e = ev.get(name)
        _p(f"  {name:16s} build {state}{fresh} | review {'PASS' if rs['ok'] else 'needed'}"
           + (f" | eval {'PASS' if e['ok'] else 'FAIL'}" if e else ""))
    for eid, e in ev.items():
        if eid not in projects():
            _p(f"  {eid:16s} not started (evals/{eid}/brief.md)")
    return 0


def new(name, title, module=None) -> int:
    import re
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name):
        _p("Choose a folder name with 2–41 lowercase letters, numbers or underscores, starting with a letter (for example desk_arm).")
        return 1
    d = ROOT / "projects" / name
    if d.exists():
        _p(f"projects/{name} already exists")
        return 1
    if module:
        from . import modules
        try:
            modules.instantiate(module, name, title, projects_dir=ROOT / "projects")
        except (OSError, ValueError) as e:
            _p(f"Could not create module instance: {e}")
            return 1
        _p(f"Created projects/{name} from {module}, with its source contract and checks. "
           f"Read MODULE.md; this new project is not checked or reviewed. Run `kerf check {name}` next.")
        return 0
    (d / "parts").mkdir(parents=True)
    import yaml
    title_yaml = yaml.safe_dump({"name": title}, allow_unicode=True, sort_keys=False).rstrip()
    text = (f"{title_yaml}\nprinter: Bambu Lab A2L\nparams: {{}}\nparts: {{}}\npurchased: {{}}\nassembly:\n  root: TODO\n"
            "  joints: []\nrequirements: []\nuse_story:              # who, where, how often, what goes wrong (kerf/usestory.py)\n"
            "  who: TODO\n  where: [indoor]\n  how_often: TODO\n  goes_wrong: []\n")
    (d / "project.yaml").write_text(text, encoding="utf-8")
    _p(f"Created starter files in projects/{name}. Add parts and an assembly before building; for an AI-generated design, use New design in Kerf Studio.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="kerf", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help='Check dependencies and headless rendering.', description='Check dependencies and headless rendering.')
    c = sub.add_parser("check", help='Check geometry, fit, motion and strength without making print files.', description='Check geometry, fit, motion and strength without making print files.'); c.add_argument("project"); c.add_argument("--quick", action="store_true")
    c.add_argument("--all", action="store_true", dest="everything",
                   help="run every check even when a redesign-level requirement fails (normally the run stops there)")
    b = sub.add_parser("build", help='Check a project and create print plates, guides and a 3D viewer.', description='Check a project and create print plates, guides and a 3D viewer.'); b.add_argument("project")
    b.add_argument("--all", action="store_true", dest="everything", help="as for check")
    rq = sub.add_parser("req", help="evaluate just these requirements (ids or check names; none = all) on the assembled "
                                    "project: seconds instead of a full check")
    rq.add_argument("project"); rq.add_argument("ids", nargs="*")
    v = sub.add_parser("verify", help='Run repository tests, project checks, reviews and evaluations.', description='Run repository tests, project checks, reviews and evaluations.'); v.add_argument("--fast", action="store_true")
    v.add_argument("--all-failures", action="store_true", help="don't stop pytest at the first failure (batched runs)")
    r = sub.add_parser("review-status", help='See whether an independent review covers the current design.', description='See whether an independent review covers the current design.'); r.add_argument("project")
    n = sub.add_parser("new", help='Create a project folder and starter files.', description='Create a project folder and starter files.'); n.add_argument("name"); n.add_argument("title")
    n.add_argument("--module", help="start from a reusable assembly with its contract and checks (see kerf modules)")
    md = sub.add_parser("modules", help="inspect reusable assemblies, interfaces, checks and source review status")
    md.add_argument("module", nargs="?"); md.add_argument("--json", action="store_true")
    sub.add_parser("status", help='List project names and their build and review status.', description='List project names and their build and review status.')
    k = sub.add_parser("calibrate", help='Make a fit-test coupon for your printer and material.', description='Make a fit-test coupon for your printer and material.'); k.add_argument("--material", default="PETG"); k.add_argument("--printer", default=None)
    f = sub.add_parser("feedback", help="fit measurements for a material (calibration), or a finding on a built project "
                                        "(--what / --note / --file), or --learn from every recorded finding")
    f.add_argument("material", nargs="?", help="a material (calibration reports follow) or a project name")
    f.add_argument("reports", nargs="*")
    f.add_argument("--part"); f.add_argument("--what"); f.add_argument("--note", default="")
    f.add_argument("--case"); f.add_argument("--at"); f.add_argument("--file", action="append", default=[])
    f.add_argument("--learn", action="store_true"); f.add_argument("--apply", action="store_true")
    f.add_argument("--printer", default=None)
    st = sub.add_parser("studio", help='Open the local point-and-click app.', description='Open the local point-and-click app.'); st.add_argument("--port", type=int, default=8765); st.add_argument("--no-open", action="store_true")
    st.add_argument("--idle-exit", type=float, default=None, metavar="SECONDS", help="quit when no window is open and nothing runs")
    ps = sub.add_parser("printer", help="connect Kerf to the Bambu printer on the LAN (setup) or read its state (status)")
    ps.add_argument("what", choices=["setup", "status"]); ps.add_argument("--host"); ps.add_argument("--code")
    ps.add_argument("--serial", default=None)
    pr = sub.add_parser("print", help='Slice existing plates, open them, or send a selected plate to the printer.', description='Slice existing plates, open them, or send a selected plate to the printer.'); pr.add_argument("project"); pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--send", type=int, default=None, metavar="PLATE"); pr.add_argument("--open", action="store_true")
    fd = sub.add_parser("find", help='Search for existing models before making a new design.', description='Search for existing models before making a new design.'); fd.add_argument("query"); fd.add_argument("--project", default=None)
    pc = sub.add_parser("price", help="price parts for a quote: kerf price servos.MG996R:2 screw:M3x8:socket:20 --grams 120")
    pc.add_argument("items", nargs="*"); pc.add_argument("--grams", type=float, default=0.0); pc.add_argument("--material", default="PETG")
    pc.add_argument("--json", action="store_true")
    rn = sub.add_parser("run", help="run a project at a chosen depth: sketch | print | check | simulate | kit | ship")
    rn.add_argument("project"); rn.add_argument("--mode", required=True, choices=["sketch", "print", "check", "simulate", "kit", "ship"])
    rn.add_argument("--ship", action="store_true", help="confirm Ship it: send plate 1 to your printer once the kit passes and a design review is current")
    op = sub.add_parser("optimise", help="search the project's `optimise:` params for a lighter / cheaper / stronger design that passes every check; writes out/OPTIMISE.md")
    op.add_argument("project")
    rp = sub.add_parser("review-pack", help="write out/review/ (PACK.md, catalog.json, contact sheets) from the last build")
    rp.add_argument("project")
    fx = sub.add_parser("fixes", help="turn the last check's common findings into edits (--apply writes the mechanical ones)")
    fx.add_argument("project"); fx.add_argument("--apply", action="store_true")
    fx.add_argument("--heatset", action="store_true", help="with --apply: also turn edge-near self-tapping holes into heat-set inserts")
    fd.add_argument("--limit", type=int, default=8); fd.add_argument("--measure", type=int, default=4)
    for k in ("--add", "--title", "--license", "--dims", "--source"):
        fd.add_argument(k, default=None)
    g = sub.add_parser("gallery", help='Create a gallery of built projects.', description='Create a gallery of built projects.'); g.add_argument("projects", nargs="*")
    sm = sub.add_parser("simulate", help="MuJoCo motion simulation of the URDF: servo limits, home hold, grip_hold / joint_speed / drop_impact")
    sm.add_argument("project")
    fw = sub.add_parser("firmware-check", help="compile + simulate the project's servo bring-up program (kerf/fwcheck.py)")
    fw.add_argument("project")
    for parser in sub.choices.values():
        if parser.description is None:
            parser.description = f"{parser.prog}: use the options below; project names are listed by `kerf status`."
        for action in parser._actions:
            if action.dest == "project" and not action.help:
                action.help = "project folder name (see kerf status), or a path containing project.yaml"
    a = ap.parse_args(argv)
    if a.cmd == "studio" and not 1 <= a.port <= 65535:
        ap.error("port must be from 1 to 65535")
    if getattr(a, "project", None):
        from . import project as P
        try:
            P.resolve_dir(a.project)
        except P.ProjectError:
            _p(f"Project '{a.project}' was not found. Run `kerf status` to see project names, or pass a folder containing project.yaml.")
            return 1
    sys.path.insert(0, str(ROOT))
    if a.cmd == "doctor":
        return doctor()
    if a.cmd == "check":
        return check(a.project, quick=a.quick, everything=a.everything)
    if a.cmd == "build":
        return check(a.project, full=True, everything=a.everything)
    if a.cmd == "req":
        return req(a.project, a.ids)
    if a.cmd == "verify":
        return verify(a.fast, a.all_failures)
    if a.cmd == "run":
        return run_mode(a.project, a.mode, ship_confirmed=a.ship)
    if a.cmd == "optimise":
        from . import optimise
        r = optimise.run(a.project)
        _p(Path(r["file"]).read_text(encoding="utf-8"))
        return 0 if r["best_report"].get("ok") else 1
    if a.cmd == "review-pack":
        from . import project as P, reviewpack
        proj = P.load(a.project)
        if not (proj.dir / "out" / "report.json").exists():
            _p(f"No build report yet. Run `kerf build {a.project}` first, then try review-pack again.")
            return 1
        rep = json.loads(proj.out("report.json").read_text(encoding="utf-8"))
        _p(str(reviewpack.write(proj, rep, proj.out("report.json").parent)))
        return 0
    if a.cmd == "review-status":
        s = review_status(a.project)
        _p(json.dumps(s))
        return 0 if s["ok"] else 1
    if a.cmd == "new":
        return new(a.name, a.title, a.module)
    if a.cmd == "modules":
        from . import modules
        try:
            rows = [modules.describe(k) for k in ([a.module] if a.module else modules.entries())]
        except (OSError, ValueError) as e:
            _p(f"Could not read module library: {e}")
            return 1
        if a.json:
            _p(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            for m in rows:
                _p(f"{m['id']} — {m['title']}\n  {m['description']}\n  Source review: {m['source_review']['why']}")
                if a.module:
                    _p("  Interfaces: " + "; ".join(f"{k}: {v}" for k, v in m["ports"].items()))
                    _p("  Parameters: " + ", ".join(m["params"]))
                    _p("  Inherited checks: " + ", ".join(r["id"] for r in m["requirements"]))
                    for limit in m["limits"]:
                        _p(f"  - {limit}")
                _p(f"  Start: kerf new my_joint \"My joint\" --module {m['id']}")
            _p("New instances need their own check, build and independent review. Inspect details with `kerf modules <module>`.")
        return 0
    if a.cmd == "status":
        return status()
    if a.cmd == "studio":
        from . import studio
        return studio.serve(a.port, open_browser=not a.no_open, idle_exit=a.idle_exit)
    if a.cmd == "printer":
        from . import bambu
        try:
            if a.what == "setup":
                if not (a.host and a.code):
                    _p("FAIL kerf printer setup --host <printer IP> --code <LAN access code> (printer screen: Settings > LAN Only)")
                    return 1
                bambu.setup_printer(a.host, a.code, a.serial, say=_p)
            else:
                _p(json.dumps(bambu.status(), indent=1))
        except Exception as e:  # noqa: BLE001 - say what failed, in words
            _p(f"FAIL {e}")
            return 1
        return 0
    if a.cmd == "print":
        from . import bambu
        try:
            r = bambu.run(a.project, dry_run=a.dry_run, send_plate=a.send, open_ui=a.open, say=_p)
        except (ValueError, RuntimeError) as e:
            _p(f"FAIL {e}")
            return 1
        if r["sent"] is not None and not r["sent"]["started"]:
            _p(f"FAIL the printer did not report the job started: {r['sent']['status']}")
            return 1
        return 0
    if a.cmd == "simulate":
        from . import sim
        return sim.simulate(a.project, say=_p)
    if a.cmd == "firmware-check":
        from . import fwcheck
        res = fwcheck.check_project(a.project)
        for ln in fwcheck.lines(res):
            _p(ln)
        return {"PASS": 0, "NONE": 0, "FAIL": 1}.get(res["status"], 2)     # NOT RUN / compiled only: not a pass
    if a.cmd == "gallery":
        from . import gallery
        r = gallery.build(a.projects or None)
        _p(f"gallery: {r['index']} + {len(r['files'])} files (out/gallery/files.json) for "
           f"{len(r['projects'])} projects; publish index.html with those files as one Artifact")
        return 0
    if a.cmd == "price":
        from . import ship, printpkg
        prices, inv = ship.load_prices(), ship.load_inventory()
        rows, missing, total, have = [], [], 0.0, []
        for it in a.items:
            # "key:qty"; a key that itself ends in a number (dowel:3) is taken whole when it is a known price key
            key, _, q = (it, "", "1") if it in prices or not it.rsplit(":", 1)[-1].replace(".", "", 1).isdigit() else it.rpartition(":")
            q = float(q or 1)
            e = prices.get(key)
            if e is None:
                missing.append(key)
                continue
            unit = float(e["pack_usd"]) / float(e["pack_qty"])
            own = min(q, inv.get(key, 0.0))
            rows.append({"key": key, "qty": q, "unit_usd": round(unit, 2), "total_usd": round(unit * (q - own), 2), "on_hand": own})
            total += unit * (q - own)
        fil = None
        if a.grams:
            e = prices.get(f"material:{a.material}")
            from . import catalog
            dens = float(catalog.get(f"materials.{a.material}")["density"])
            fil = {"grams": a.grams, "usd": round(float(e["pack_usd"]) / float(e["pack_qty"]) * a.grams, 2) if e else None,
                   "min_print_hours": round(a.grams / dens * 1000 / printpkg.profile(a.material)["max_flow"] / 3600, 2)}
            total += fil["usd"] or 0.0
        out = {"items": rows, "missing": missing, "filament": fil, "total_usd": round(total, 2)}
        if a.json:
            _p(json.dumps(out))
        else:
            for r in rows:
                _p(f"{r['key']:42s} {r['qty']:g} x ${r['unit_usd']:.2f} = ${r['total_usd']:.2f}" + (f" ({r['on_hand']:g} on hand)" if r["on_hand"] else ""))
            if fil:
                _p(f"filament {a.material} {a.grams:g} g = ${fil['usd']}; printing at least {fil['min_print_hours']} h (lower bound)")
            _p(f"total ${out['total_usd']:.2f}" + (f"; not in catalog/prices.json: {', '.join(missing)}" if missing else ""))
        return 0 if not missing else 1
    if a.cmd == "fixes":
        from . import autofix
        d = ROOT / "projects" / a.project if not Path(a.project).exists() else Path(a.project)
        if not (d / "out" / "report.json").exists():
            _p(f"FAIL no report for {a.project}: run `kerf check {a.project}` first")
            return 1
        fs = autofix.fixes(d, apply=a.apply, heatset=a.heatset)
        for f in fs:
            tag = "applied" if f.get("applied") else ("can apply" if f["kind"] in ("teardrop", "heatset") and f.get("edits") else "by hand")
            _p(f"[{tag}] {f['fix']}" + (f"  ({f['file']})" if f.get("file") else ""))
        _p(f"{len(fs)} finding(s); " + ("run `kerf check` now" if a.apply and any(f.get("applied") for f in fs) else
                                          "nothing to apply" if not any(f.get("edits") for f in fs) else "use --apply to write them"))
        return 0
    if a.cmd == "find":
        from . import find as F, project as P
        pdir = P.resolve_dir(a.project) if a.project else None
        if a.add:
            if pdir is None:
                _p("FAIL --add needs --project"); return 1
            F.add(pdir / "REFERENCES.md", a.query, {"source": a.source or "web", "title": a.title or a.add, "url": a.add,
                                                   "license": a.license or "", "dims": a.dims or "—"})
            _p(f"added to {pdir.name}/REFERENCES.md"); return 0
        r = F.find(a.query, pdir, a.limit, a.measure)
        _p(r["text"])
        if pdir is not None:
            _p(f"written to {pdir.name}/REFERENCES.md — fill in the Decision line")
        return 0
    if a.cmd == "feedback" and (a.learn or (a.material and (ROOT / "projects" / a.material / "project.yaml").exists())):
        from . import feedback as FB
        if a.learn:
            props = FB.learn(FB.findings())
            out = FB.write(props, ROOT / "LEARNED.md")
            _p(out.read_text(encoding="utf-8"))
            if a.apply:
                _p(f"{FB.apply_rules(props, ROOT / 'docs' / 'ENGINEERING.md')} rule(s) appended to docs/ENGINEERING.md")
            return 0
        if not a.what:
            _p("FAIL say what happened: --what " + " | ".join(FB.WHAT))
            return 1
        try:
            r = FB.record(a.material, a.part, a.what, a.note, a.case, a.at, a.file)
        except ValueError as e:
            _p(f"FAIL {e}")
            return 1
        pred = r.get("predicted") or {}
        _p(f"recorded finding #{r['n']} for {r['project']}" + (f" ({len(r['files'])} file(s) kept)" if r["files"] else "")
           + (f"; Kerf had predicted {r['part']} to fail in {pred.get('fails_in')} at {pred['use']:.0%} of its limit"
              if pred.get("use") is not None else ""))
        return 0
    if a.cmd == "feedback" and not (a.material and a.reports):
        _p("FAIL kerf feedback <material> <report>... (fit calibration), kerf feedback <project> --what ... --note ..., or kerf feedback --learn")
        return 1
    if a.cmd in ("calibrate", "feedback"):
        from . import calibrate as C
        printer = a.printer or C.DEFAULT_PRINTER
        if a.cmd == "calibrate":
            out = C.write_coupon(a.material, printer)
            _p(f"coupon for {printer} / {C.mat_key(a.material)}: {out}/coupon.3mf — print it, then follow {out}/CARD.md")
            return 0
        try:
            changed = C.feedback(a.material, C.parse_reports(a.reports), printer)
        except ValueError as e:
            _p(f"FAIL {e}")
            return 1
        for key, (was, now) in changed.items():   # not `new`: that would shadow new() for the whole of main()
            _p(f"{key}: {was} -> {now} mm")
        _p(f"saved {C.profile_path(printer).relative_to(ROOT)}" + ("" if changed else " (no change)")
           + "; rebuild projects to apply. Reprint the coupon to confirm anything that moved.")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
