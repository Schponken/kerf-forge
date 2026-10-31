"""kerf command line.

  kerf doctor                 environment self-test (must print ALL OK)
  kerf check  <project>       build + all checks, no files (fast loop while designing)
  kerf build  <project>       check + STEP/STL/3MF/plates/BOM + renders into projects/<p>/out/
  kerf verify [--fast]        the definition of done: tests, every project, every eval, every review
  kerf review-status <proj>   is the visual review current for this geometry?
  kerf new <name> "<title>"   scaffold a project
  kerf status                 one-screen overview: plan progress, every project, review and eval state
  kerf print <project>        orient + plate + slice (Bambu Studio CLI) [--send N: start plate N over LAN] [--dry-run] [--open]
"""
from __future__ import annotations

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
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "remote", "-v"], capture_output=True, text=True)
        _p(f"ok   git remote: {r.stdout.split()[1] if r.stdout.strip() else '(none — work will not be saved remotely!)'}")
    except Exception as e:
        bad.append(f"git: {e}")
    for b in bad:
        _p(f"FAIL {b}")
    _p("ALL OK" if not bad else f"{len(bad)} PROBLEM(S)")
    return 0 if not bad else 1


def check(name, full=False, quick=False) -> int:
    from .pipeline import run, summary
    rep = run(name, sweeps=not quick, do_export=full, do_render=full)
    _p(summary(rep))
    if rep.get("traces"):
        for k, t in rep["traces"].items():
            _p(f"--- traceback {k}\n{t}")
    return 0 if rep["ok"] else 1


def projects() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / "projects").glob("*/project.yaml"))


def review_status(name) -> dict:
    from . import project as P
    proj = P.load(name)
    f = proj.dir / "review.json"
    fp = proj.fingerprint()
    if not f.exists():
        return {"ok": False, "why": f"no review.json (fingerprint {fp})", "fingerprint": fp}
    r = json.loads(f.read_text(encoding="utf-8"))
    if r.get("fingerprint") != fp:
        return {"ok": False, "why": f"review is for fingerprint {r.get('fingerprint')}, geometry is now {fp}; review again", "fingerprint": fp}
    if r.get("verdict") != "PASS":
        return {"ok": False, "why": f"review verdict {r.get('verdict')}: {r.get('summary', '')}", "fingerprint": fp}
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


def verify(fast=False) -> int:
    """The definition of done. Exit 0 only when everything passes."""
    t0 = time.time()
    results, fails = {}, []
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True)
    results["tests"] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
    if r.returncode != 0:
        fails.append(f"unit tests: {results['tests']}")
    from .pipeline import run
    for name in projects():
        rep = run(name, sweeps=True, do_export=not fast, do_render=not fast)
        results[name] = {"ok": rep["ok"], "problems": rep["problems"][:6]}
        if not rep["ok"]:
            fails.append(f"project {name}: {rep['problems'][:3]}")
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


def new(name, title) -> int:
    d = ROOT / "projects" / name
    if d.exists():
        _p(f"projects/{name} already exists")
        return 1
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(f"name: {title}\nprinter: Bambu Lab A2L\nparams: {{}}\nparts: {{}}\npurchased: {{}}\nassembly:\n  root: TODO\n  joints: []\nrequirements: []\n")
    _p(f"created projects/{name}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="kerf", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    c = sub.add_parser("check"); c.add_argument("project"); c.add_argument("--quick", action="store_true")
    b = sub.add_parser("build"); b.add_argument("project")
    v = sub.add_parser("verify"); v.add_argument("--fast", action="store_true")
    r = sub.add_parser("review-status"); r.add_argument("project")
    n = sub.add_parser("new"); n.add_argument("name"); n.add_argument("title")
    sub.add_parser("status")
    k = sub.add_parser("calibrate"); k.add_argument("--material", default="PETG"); k.add_argument("--printer", default=None)
    f = sub.add_parser("feedback"); f.add_argument("material"); f.add_argument("reports", nargs="+")
    f.add_argument("--printer", default=None)
    pr = sub.add_parser("print"); pr.add_argument("project"); pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--send", type=int, default=None, metavar="PLATE"); pr.add_argument("--open", action="store_true")
    fd = sub.add_parser("find"); fd.add_argument("query"); fd.add_argument("--project", default=None)
    fd.add_argument("--limit", type=int, default=8); fd.add_argument("--measure", type=int, default=4)
    for k in ("--add", "--title", "--license", "--dims", "--source"):
        fd.add_argument(k, default=None)
    g = sub.add_parser("gallery"); g.add_argument("projects", nargs="*")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    if a.cmd == "doctor":
        return doctor()
    if a.cmd == "check":
        return check(a.project, quick=a.quick)
    if a.cmd == "build":
        return check(a.project, full=True)
    if a.cmd == "verify":
        return verify(a.fast)
    if a.cmd == "review-status":
        s = review_status(a.project)
        _p(json.dumps(s))
        return 0 if s["ok"] else 1
    if a.cmd == "new":
        return new(a.name, a.title)
    if a.cmd == "status":
        return status()
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
    if a.cmd == "gallery":
        from . import gallery
        r = gallery.build(a.projects or None)
        _p(f"gallery: {r['index']} + {len(r['files'])} files (out/gallery/files.json) for "
           f"{len(r['projects'])} projects; publish index.html with those files as one Artifact")
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
