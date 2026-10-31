"""Build → check → (export, render) one project and write out/report.json."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from . import access, assembly as A, checks, export, pins, project as P, requirements, shanks, viewer

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "tools" / "render" / "render.mjs"


def render_glb(glb: Path, prefix: Path, views="iso,front,right,top", sheet=True) -> dict:
    args = ["node", str(RENDER), str(glb), str(prefix), views] + (["--sheet"] if sheet else [])
    r = subprocess.run(args, capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(f"render failed: {r.stderr.strip()[-800:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def run(name: str, *, sweeps=True, do_export=False, do_render=False, overrides=None, sweep_samples=9) -> dict:
    t0 = time.time()
    proj = P.load(name, overrides)
    P.build(proj)
    printer = proj.data.get("printer", "Bambu Lab A2L")
    supports = proj.data.get("supports", "allowed")
    rep = {"project": proj.name, "dir": proj.dir.name, "fingerprint": proj.fingerprint(), "printer": printer,
           "params": proj.params, "parts": {}, "purchased": {}, "assembly": {}, "requirements": [],
           "problems": [], "warnings": []}
    for iid, it in proj.items.items():
        if it.error:
            rep["problems"].append(f"{iid} failed to build: {it.error}")
            rep.setdefault("traces", {})[iid] = getattr(it, "trace", "")
    for iid, it in proj.printed.items():
        if it.shape is None:
            continue
        r = checks.part_checks(it, printer, supports=it.spec.get("supports", supports))
        r["notes"] = list(getattr(it.shape, "kerf_notes", []))
        r["warnings"] += [f"{iid}: {n}" for n in r["notes"]]
        rep["parts"][iid] = r
        rep["problems"] += r["problems"]
        rep["warnings"] += r["warnings"]
    for iid, it in proj.items.items():
        if it.role == "purchased" and it.shape is not None:
            rep["purchased"][iid] = {"catalog": it.spec.get("catalog"), "qty": it.spec.get("qty", 1),
                                     "mass_g": round(checks.item_mass_g(it), 1)}
    if not any(it.error for it in proj.items.values()):
        try:
            asm = A.plan(proj)
            A.solve(asm)
            hits = A.interference(asm)
            rep["assembly"]["interference"] = hits
            for h in hits:
                rep["problems"].append(f"{h['a']} and {h['b']} overlap by {h['volume_mm3']} mm3 in the assembled position")
            fj, fprob = A.fasteners(asm)
            rep["assembly"]["fasteners"] = fj
            rep["problems"] += fprob
            rep["problems"] += shanks.check(asm, fj)
            pinj, pprob, pwarn = pins.check(asm)
            rep["assembly"]["pins"] = pinj
            rep["problems"] += pprob
            rep["warnings"] += pwarn
            keys, kprob, kwarn = access.hex_key_reach(asm)          # can every screw be driven?
            ins, iprob = access.insertion_paths(asm)                # can declared parts slide into their seats?
            rep["assembly"]["hex_keys"], rep["assembly"]["insertion"] = keys, ins
            rep["problems"] += kprob + iprob
            rep["warnings"] += kwarn
            if sweeps:
                sw = A.sweeps(asm, samples=sweep_samples)
                rep["assembly"]["sweeps"] = sw
                for s in sw:
                    if not s["clear"]:
                        c = s["collisions"][0]
                        rep["problems"].append(f"moving joint '{s['joint']}' collides: {c['a']} hits {c['b']} ({c['volume_mm3']} mm3) at {c.get('at', c.get('pose'))}")
            rep["assembly"]["joints"] = [{"name": e.name, "kind": e.kind, "parent": f"{e.parent}.{e.pjoint}",
                                          "child": f"{e.child}.{e.cjoint}", "range": list(e.range), "home": e.home}
                                         for e in asm.edges]
            A.solve(asm)
            rep["assembly"]["positions"] = {iid: [round(it.shape.location.position.X, 3), round(it.shape.location.position.Y, 3),
                                                   round(it.shape.location.position.Z, 3)]
                                            for iid, it in proj.items.items() if it.shape is not None}
            rep["assembly"]["joint_origins"] = {f"{iid}.{lab}": [round(j.location.position.X, 3), round(j.location.position.Y, 3),
                                                                 round(j.location.position.Z, 3)]
                                                for iid, it in proj.items.items() if it.shape is not None
                                                for lab, j in it.shape.joints.items()}
            rq = requirements.run_all(proj, asm, quick=not sweeps)
            fea_viz = {r["id"]: r.pop("_viz") for r in rq if "_viz" in r}   # meshes stay out of report.json
            rep["requirements"] = rq
            for r in rq:
                if not r["ok"]:
                    rep["problems"].append(f"requirement '{r['id']}' failed: {r['detail']} = {r['value']} (limit {r['limit']})")
            A.solve(asm)
            if do_export or do_render:
                out = proj.out()
                export.step_assembly(proj, out / "assembly.step")
                export.glb(proj, out / "assembly.glb")
                export.glb(proj, out / "exploded.glb", explode=25.0)
                export.glb(proj, out / "assembly_keepouts.glb", include_keepouts=True)
                rep["files"] = {"parts": export.part_files(proj, out / "parts"),
                                "plates": export.plates(proj, out / "plates", printer)}
                rep["bom"] = export.bom(proj, fj, rep["parts"], out, pins=pinj)
                try:  # self-contained assembly viewer (kerf/viewer.py); a failure here is a build problem, not silent
                    rep["files"]["viewer"] = "viewer.html"
                    viewer.write(proj, asm, rep, out / "viewer.html")
                except Exception as e:  # noqa: BLE001
                    rep["problems"].append(f"viewer.html could not be written: {type(e).__name__}: {e}")
            if do_render:
                out = proj.out("renders")
                out.mkdir(exist_ok=True)
                render_glb(proj.out("assembly.glb"), out / "assembly", sheet=True)
                render_glb(proj.out("exploded.glb"), out / "exploded", views="iso,iso2,front,top", sheet=True)
                render_glb(proj.out("assembly_keepouts.glb"), out / "keepouts", views="iso,top", sheet=False)
                from . import fea_render
                for rid, viz in fea_viz.items():
                    r = next(r for r in rq if r["id"] == rid)
                    r["render"] = f"renders/fea_{rid}.png"
                    fea_render.render(viz, out / f"fea_{rid}.png", viz.get("title", rid))
                for e in asm.movable:
                    for tag, v in (("min", e.range[0]), ("max", e.range[1])):
                        A.solve(asm, {e.name: v})
                        g = proj.out(f"pose_{e.name}_{tag}.glb")
                        export.glb(proj, g)
                        render_glb(g, out / f"pose_{e.name}_{tag}", views="iso", sheet=False)
                    A.solve(asm)
                from build123d import Compound
                for iid, it in proj.printed.items():
                    g = proj.out(f"part_{iid}.glb")
                    s = checks.oriented(it.shape, it.spec.get("print_rot", [0, 0, 0]))
                    s.label = iid
                    from build123d import export_gltf
                    export_gltf(Compound(children=[s]), str(g), binary=True, linear_deflection=0.03, angular_deflection=0.2)
                    render_glb(g, out / f"part_{iid}", sheet=True)
        except P.ProjectError as e:
            rep["problems"].append(f"assembly: {e}")
        except Exception as e:  # noqa: BLE001
            import traceback
            rep["problems"].append(f"assembly step crashed: {type(e).__name__}: {e}")
            rep.setdefault("traces", {})["assembly"] = traceback.format_exc(limit=8)
    rep["ok"] = not rep["problems"]
    rep["seconds"] = round(time.time() - t0, 1)
    proj.out("report.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep


def summary(rep: dict) -> str:
    L = [f"{'PASS' if rep['ok'] else 'FAIL'}  {rep['project']}  ({rep['seconds']} s, fingerprint {rep['fingerprint']})"]
    for iid, r in rep["parts"].items():
        L.append(f"  part {iid:18s} {'ok ' if r['ok'] else 'BAD'} {r['size_mm']} mm  {r['mass_est_g']} g  overhang {r['overhang_pct']}%  wall p2 {r['wall_p02_mm']} mm")
    a = rep.get("assembly", {})
    if "interference" in a:
        L.append(f"  interference: {len(a['interference'])} overlapping pairs")
    if "fasteners" in a:
        L.append(f"  fasteners: {len(a['fasteners'])} screws aligned")
    if a.get("pins"):
        L.append(f"  pins: {len(a['pins'])} pinned joints coaxial")
    for s in a.get("sweeps", []):
        L.append(f"  sweep {s['joint']:14s} {'clear' if s['clear'] else 'COLLIDES'} over {s.get('range', '')} ({s['samples']} samples)")
    for r in rep.get("requirements", []):
        L.append(f"  req {r['id']:20s} " + ("skipped (--quick)" if r.get("skipped") else f"{'ok ' if r['ok'] else 'BAD'} {r['value']} (limit {r['limit']})"))
    for p in rep["problems"]:
        L.append(f"  PROBLEM: {p}")
    for w in rep["warnings"]:
        L.append(f"  warning: {w}")
    return "\n".join(L)
