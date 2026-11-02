"""Build → check → (export, render) one project and write out/report.json."""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from . import edges, partcache, progress, stressmap
from . import access, assembly as A, checks, electrical, export, heads, hole_axes, holewall, pins, project as P, requirements, shanks, ship, viewer, wiring_out

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "tools" / "render" / "render.mjs"


def req_line(r):
    """One requirement result; a failure whose rounded value equals its limit says so (it misses by less than the rounding)."""
    if not r['ok'] and r['value'] is None:     # the check could not be evaluated at all (e.g. a bad wiring run)
        return "BAD not evaluated - the reason is in the PROBLEM lines below"
    t = f"{'ok ' if r['ok'] else 'BAD'} {requirements.describe(r)}"
    # a range limit ([min, max]) never "equals" a value; plain floats so a numpy value can't broadcast against a list
    lim = r['limit']
    if not r['ok'] and not isinstance(lim, (list, tuple)) and isinstance(r['value'], (int, float)) \
            and float(r['value']) == lim:
        t += ' - misses the limit by less than the shown rounding; add margin'
    return t


def mass_split(proj, rep) -> dict:
    """Grams: printed parts, purchased items on the device, and items marked `off_board` (bench / desk: a power
    adapter, a controller beside it). The headline mass is printed + on-board; off-board is reported separately."""
    printed = sum(((rep["parts"].get(i) or {}).get("mass_est_g") or 0) * int(it.spec.get("qty", 1))
                  for i, it in proj.printed.items())
    on = off = 0.0
    for iid, p in rep["purchased"].items():
        m = (p.get("mass_g") or 0) * (p.get("qty") or 1)
        if p.get("off_board"):
            off += m
        else:
            on += m
    return {"printed_g": round(printed, 1), "on_board_g": round(on, 1), "device_g": round(printed + on, 1),
            "off_board_g": round(off, 1)}


_BALL = re.compile(r"^(M[\d.]+) screw in (\w+) \(group '(\w+)'\) at .*?a straight ([\d.]+) mm hex key hits")
_THIN_TAP = re.compile(r"^(\w+): (\d+) (M[\d.]+) tap hole\(s\) of group '(\w+)' sit closer than")


def maker_notes(warnings: list[str]) -> list[str]:
    """Warnings that change what the person building it must DO, rewritten as plain instructions (the originals stay
    in `warnings` for the designer). Only patterns known to be safe to translate; everything else stays designer-only."""
    notes, seen = [], set()
    for w in warnings:
        m = _BALL.match(w)
        if m and ("ball", m[3]) not in seen:
            seen.add(("ball", m[3]))
            notes.append(f"Use a ball-end {m[4]} mm hex key for the {m[1]} screws of `{m[3]}` ({m[2]}): a straight key can't reach "
                         "every one of them.")
        m = _THIN_TAP.match(w)
        if m and ("tap", m[4]) not in seen:
            seen.add(("tap", m[4]))
            notes.append(f"The {m[2]} {m[3]} screws of `{m[4]}` cut their own thread close to an edge of **{m[1]}**: turn them by "
                         "hand with a small driver and stop as soon as they are snug (a power driver or one more turn can split it).")
    return notes


def unattached(proj, fasteners, pins) -> list[str]:
    """A purchased item no screw or pin holds, and whose project.yaml doesn't say how it is held (`held_by`: press fit,
    strap, cable tie, glue...) or that it lives off the device (`off_board`), only *looks* mounted in the model: the
    assembly guide would tell the maker to fit it where nothing holds it."""
    held = set()
    for f in fasteners or []:
        held |= {f.get("male"), f.get("female")}
    for p in pins or []:
        held |= set(p.get("fixed_in") or []) | set(p.get("free_in") or [])
    out = []
    for iid, it in proj.items.items():
        if it.role != "purchased" or iid in held or it.spec.get("held_by") or it.spec.get("off_board"):
            continue
        out.append(f"{iid}: nothing holds it (no screw or pin, no `held_by`): give it a mount, or say in project.yaml how it "
                   "is held (`held_by: \"press fit in the bore\"`, strap, cable tie) or that it lives off the device "
                   "(`off_board: \"on the desk beside it\"`)")
    return out


def render_glb(glb: Path, prefix: Path, views="iso,front,right,top", sheet=True, labels=None, focus=None, title=None) -> dict:
    """tools/render/render.mjs: PNG per view (+ a 2x2 sheet). labels = node names to tag with a callout, focus = node
    names the camera frames (with context), title = a line printed on the sheet (e.g. the part's overall size)."""
    args = ["node", str(RENDER), str(glb), str(prefix), views] + (["--sheet"] if sheet else [])
    if labels:
        args.append("--labels=" + ",".join(labels))
    if focus:
        args.append("--focus=" + ",".join(focus))
    if title:
        args.append("--title=" + title)
    r = subprocess.run(args, capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(f"render failed: {r.stderr.strip()[-800:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def _layer_proofs(proj, rep):
    """A part whose declared load_axis runs across layers (checks.layer_direction warning) must be proven by a strength
    check that uses the across-layer strength: fea_static / cantilever_stress on that part with direction z or auto.
    With one, the warning is dropped (the check's own pass/fail stands); without one it becomes a problem
    (docs/ENGINEERING.md sections 3b and 4)."""
    proven = {r.get("part") for r in proj.data.get("requirements") or []
              if r.get("check") in ("fea_static", "cantilever_stress")
              and r.get("direction", "xy" if r.get("check") == "fea_static" else "auto") in ("z", "auto")}
    keep = []
    for w in rep["warnings"]:
        pid = w.split(":", 1)[0]
        if "runs" in w and "out of the layer plane" in w and pid in proj.items:
            if pid not in proven:
                rep["problems"].append(w.replace("; reorient so it lies along the bed, or prove it",
                                                 ": unproven; reorient so it lies along the bed, or prove it"))
            continue
        keep.append(w)
    rep["warnings"] = keep


def _fea_hygiene(proj) -> list:
    """Warnings on how strength checks are set up (audit ENG-8, ENG-11):
    - a part with fea_static / cantilever_stress but no `load_axis` (the layer-direction checks cannot judge it);
    - `direction: xy` while the part's load_axis runs > 30 deg out of the bed plane (judged on the strong direction);
    - a `cylinder` load (a bore or seat) given as `force_n`: a pin or bearing pushes on one side of a bore, use
      `bearing_n` (cosine-distributed);
    - a `fixed` box that holds none of the part's fastener sites (the clamp should be where the screws are)."""
    import numpy as np
    from . import geom
    from .checks import LAYER_WARN_NZ2
    from .requirements import _across_share, _region
    out = []
    for r in proj.data.get("requirements") or []:
        if r.get("check") not in ("fea_static", "cantilever_stress"):
            continue
        it = proj.items.get(r.get("part"))
        if it is None or it.shape is None:
            continue
        rid = r.get("id")
        if it.spec.get("load_axis") is None:
            out.append(f"requirement '{rid}': part {it.id} has no load_axis, so its print orientation is not judged "
                       f"against the load (ENGINEERING.md s4); add load_axis")
        elif r.get("check") == "fea_static" and r.get("direction", "xy") == "xy" and _across_share(it) > LAYER_WARN_NZ2:
            out.append(f"requirement '{rid}': direction xy but {it.id}'s load_axis runs across the layers in its print "
                       f"orientation; use direction z or auto")
        if r.get("check") != "fea_static":
            continue
        for ld in r.get("loads") or []:
            if "force_n" in ld and ("cylinder" in ld or any("cylinder" in a for a in (ld.get("any") or []))):
                out.append(f"requirement '{rid}': a cylinder (bore/seat) load given as force_n spreads it all round the "
                           f"bore; a pin or bearing pushes on one side: use bearing_n")
        fx = r.get("fixed") or {}
        boxes = [fx] if "box" in fx else [a for a in (fx.get("any") or []) if "box" in a]
        sites = [geom.world_point(st.loc, (0, 0, 0)) for st in getattr(it.shape, "kerf_sites", []) or []]
        if boxes and sites and len(boxes) == len(fx.get("any") or [fx]):
            pts = np.array(sites)
            held = False
            for b in boxes:
                pred = _region(it, {"box": b["box"]}, proj.params)
                lo = pred(pts[:, 0] - 0.0, pts[:, 1], pts[:, 2])
                held = held or bool(np.any(lo))
            if not held:
                out.append(f"requirement '{rid}': the fixed box(es) hold none of {it.id}'s fastener sites; clamp the part "
                           f"where its screws are (sites: radius) unless a face really rests on something")
    return out


def _print_checks(it, printer, supports) -> dict:
    """Every per-part check: a function of the built part alone (cached with it by kerf/partcache.py)."""
    iid = it.id
    r = checks.part_checks(it, printer, supports=supports)
    r["sharp_inside"], r["sharp_kept"] = edges.split_kept(edges.sharp_inside(it.shape, getattr(it.shape, "kerf_sites", [])),
                                                          getattr(it.shape, "kerf_sharp_ok", []))
    r["notes"] = list(getattr(it.shape, "kerf_notes", []))
    r["features"] = [dict(f) for f in getattr(it.shape, "kerf_features", [])]   # design-intent ledger (ctx.add / cut)
    r["warnings"] += [f"{iid}: {n}" for n in r["notes"]]
    hp, hw, hres = holewall.check(it)                  # wall around every fastener hole (ENGINEERING.md s5/s7)
    r["problems"] += hp
    r["warnings"] += hw
    r["hole_walls"] = hres
    tp, tw = hole_axes.check(it)                       # horizontal holes cut round (ENGINEERING.md s4)
    r["problems"] += tp
    r["warnings"] += tw
    return r


def first_look(proj, rep):
    """The 3D model first (Spencer, 2026-11-02): as soon as the parts are built and placed, write a preview
    viewer.html (no click-to-edit, no build steps, status "checks running") and say so; every check, file and render
    then runs on, and the full viewer replaces it at the end."""
    import time as _t
    from build123d import Location
    t0 = _t.time()
    home = {iid: Location(it.shape.location.wrapped) for iid, it in proj.items.items() if it.shape is not None}
    try:
        asm = A.plan(proj)
        A.solve(asm)
        out = proj.out()
        viewer.write(proj, asm, rep, out / "viewer.html", preview=True)
    except Exception as e:  # noqa: BLE001 - the full viewer at the end still comes; never fail a run here
        rep["warnings"].append(f"preview viewer could not be written: {type(e).__name__}: {e}")
        return
    finally:     # the print checks below judge each part where it was modelled, not where the assembly put it
        for iid, loc in home.items():
            proj.items[iid].shape.location = loc
    progress.emit("model", path="out/viewer.html", seconds=round(_t.time() - t0, 1))
    if not progress.on():
        print(f"3D model ready: {out / 'viewer.html'} (checks and files continue)", flush=True)


def run(name: str, *, sweeps=True, do_export=False, do_render=False, overrides=None, sweep_samples=9,
        mode: str | None = None, everything: bool = False) -> dict:
    """mode (kerf/modes.py: sketch | print | check | simulate | kit | ship) picks the stages; without it the old flags
    do (sweeps = the full check, do_export / do_render = kerf build). The requirements whose failure means a redesign
    run first (_redesign_first); if one fails the run stops before the detail checks unless `everything`."""
    t0 = time.time()
    from . import catalog, modes
    catalog.track()
    stg = modes.stages(mode) if mode else modes.legacy(sweeps, do_export, do_render)
    sweeps = "motion" in stg
    proj = P.load(name, overrides)
    from . import usestory
    planned = list(proj.data.get("requirements") or []) + usestory.requirements(proj) if "requirements" in stg else []
    core_planned = [r for r in planned if requirements.redesign_tier(r) is not None]
    planned = requirements.redesign_order(proj, core_planned) + [r for r in planned if requirements.redesign_tier(r) is None]
    progress.emit("start", project=proj.name, stages=[k for k, _ in progress.STAGES if (k != "motion" or sweeps)
                                                       and (k != "requirements" or "requirements" in stg)
                                                       and (k != "export" or stg & {"files", "docs", "viewer"})
                                                       and (k != "renders" or "renders" in stg)],
                  parts=list(proj.printed), reqs=[r.get("id", r.get("check")) for r in planned])
    progress.stage("build")
    P.build(proj)
    printer = proj.data.get("printer", "Bambu Lab A2L")
    supports = proj.data.get("supports", "allowed")
    rep = {"project": proj.name, "dir": proj.dir.name, "fingerprint": proj.fingerprint(), "printer": printer,
           "params": proj.params, "parts": {}, "purchased": {}, "assembly": {}, "requirements": [],
           "problems": [], "warnings": [], "mode": mode, "stages": sorted(stg),
           "cached_parts": [k for k, it in proj.printed.items() if it.cached]}   # kerf/partcache.py hits
    for iid, it in proj.items.items():
        if it.error:
            rep["problems"].append(f"{iid} failed to build: {it.error}")
            rep.setdefault("traces", {})[iid] = getattr(it, "trace", "")
            if it.diag is not None:
                rep.setdefault("diagnoses", {})[iid] = it.diag.as_dict()
    from . import find
    for q in find.pending_decisions(proj.dir):
        rep["warnings"].append(f"REFERENCES.md: `kerf find \"{q}\"` has no reuse decision yet (Decision: TODO)")
    if "viewer" in stg and not any(it.error for it in proj.items.values()):
        first_look(proj, rep)                 # the 3D model first; every check below runs on after it
    core = None
    if "requirements" in stg and not any(it.error for it in proj.items.values()):
        core = _redesign_first(proj, rep, quick="fea" not in stg and mode is not None)   # a chosen depth keeps its FEA choice
        if core and not everything and any(not r["ok"] for r in core):
            for r in core:
                r.pop("_viz", None)
                r.pop("_field", None)
            rep["requirements"] = core
            rep["problems"] += [f"requirement '{r['id']}' failed: {r['detail']} = {requirements.describe(r)}"
                                for r in core if not r["ok"]]
            rep["stopped_early"] = True
            rep["problems"].append("stopped before the detail checks (print, fit, fasteners, motion, wiring): the failed "
                                   "requirement(s) above change the design, so fix them first and the detail checks "
                                   "run on the design that stays (`--all` runs everything anyway)")
            return _finish(proj, rep, stg, t0, overrides)
    progress.stage("print")
    for iid, it in proj.printed.items():
        if it.shape is None:
            progress.emit("part", id=iid, ok=False)
            continue
        sup = it.spec.get("supports", supports)
        cache_as = f"print-{sup}" if it.cached and it.spec.get("source") != "meshy" else None
        r = partcache.lookup_extra(it.cache_key, cache_as) if cache_as else None   # unchanged part: same results
        if r is not None:
            r["build_ms"] = it.build_ms
        else:
            with partcache.recording() as deps:
                r = _print_checks(it, printer, sup)
            if it.cache_key and it.spec.get("source") != "meshy":
                partcache.store_extra(it.cache_key, f"print-{sup}", r, deps)
        progress.emit("part", id=iid, ok=not r.get("problems"), mass=r.get("mass_est_g"))
        if it.spec.get("airfoil"):          # a wing part names its airfoil: it must exist (catalog/airfoils or NACA)
            from . import aero
            r["airfoil"] = str(it.spec["airfoil"]).lower()
            try:
                aero.airfoil(r["airfoil"])
            except ValueError as e:
                r = {**r, "problems": [*r["problems"], f"{iid}: {e}"]}
        rep["parts"][iid] = r
        rep["problems"] += r["problems"]
        rep["warnings"] += r["warnings"]
    for iid, it in proj.items.items():
        if it.role == "purchased" and it.shape is not None and checks.item_mass_g(it) <= 0:
            rep["warnings"].append(f"{iid}: no mass (catalog {it.spec.get('catalog')} has no weight_g and the item no mass_g): "
                                   "mass, CG, tip-over and thrust/weight leave it out; add a sourced weight")
    for iid, it in proj.items.items():
        if it.role == "purchased" and it.shape is not None:
            rep["purchased"][iid] = {"catalog": it.spec.get("catalog"), "qty": it.spec.get("qty", 1),
                                     "mass_g": round(checks._purchased_mass_g(it), 1)}
            if it.spec.get("off_board"):
                rep["purchased"][iid]["off_board"] = str(it.spec["off_board"])
        elif it.role == "keepout" and it.spec.get("proxy") == "prop_disc" and it.spec.get("catalog"):
            # a bought prop, modelled by its swept disc; its mass rides on its motor (project.carry_props)
            rep["purchased"][iid] = {"catalog": it.spec.get("catalog"), "qty": it.spec.get("qty", 1),
                                     "mass_g": round(checks._purchased_mass_g(it), 1), "on": it.spec.get("owner")}
    rep["mass"] = mass_split(proj, rep)
    if not any(it.error for it in proj.items.values()):
        try:
            progress.stage("fit")
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
            asm.heads = heads.build(asm, fj)                         # screw heads join interference + sweeps
            asm.screws = shanks.build(asm, fj)                       # whole screws: wire routes stay off them
            for h in heads.interference(asm, None, A._allowed(asm)):
                rep["problems"].append(f"{h['a']} and {h['b']} overlap by {h['volume_mm3']} mm3 in the assembled position")
            pinj, pprob, pwarn = pins.check(asm)
            rep["assembly"]["pins"] = pinj
            rep["problems"] += pprob
            rep["warnings"] += pwarn
            keys, kprob, kwarn = access.hex_key_reach(asm)          # can every screw be driven?
            ins, iprob = access.insertion_paths(asm)                # can declared parts slide into their seats?
            hp, hprob = access.horn_paths(asm)                      # can each horn be pushed onto its spline?
            iprob += hprob
            rep["assembly"]["hex_keys"], rep["assembly"]["insertion"], rep["assembly"]["horns"] = keys, ins, hp
            rep["warnings"] += unattached(proj, fj, pinj)
            rep["problems"] += kprob + iprob
            rep["warnings"] += kwarn
            if sweeps:
                progress.stage("motion")
                sw = A.sweeps(asm, samples=sweep_samples)
                rep["assembly"]["sweeps"] = sw
                for s_ in sw:
                    progress.emit("sweep", joint=s_["joint"], clear=s_["clear"])
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
            emodel = cres = None
            powered = [i for i, it in proj.items.items() if it.role == "purchased"
                       and any(k in str(it.spec.get("catalog", "")) for k in ("servos.", "motors", "steppers", "boards."))]
            if powered and not proj.data.get("wiring") and "electrical" in stg:
                rep["warnings"].append(f"no electrical system: {', '.join(powered[:4])} need power and signal, but project.yaml "
                                       f"has no `electrical:` / `wiring:` (docs/ARCHITECTURE.md 'Electrical')")
            if (proj.data.get("wiring") or proj.data.get("electrical")) and "electrical" in stg:   # kerf/electrical.py
                try:
                    emodel = electrical.analyse(proj)
                    rep["electrical"] = emodel
                    rep["problems"] += electrical.length_problems(emodel)
                    if sweeps:      # routes over every joint extreme (slack, collisions): part of the full check
                        emodel["routes"], rprob = electrical.route_check(proj, asm, emodel)
                        rep["problems"] += rprob
                except electrical.ElectricalError as e:
                    rep["problems"].append(f"electrical: {e}")
                if emodel is not None:      # kerf/circuit.py: pin-level netlist + SKiDL ERC from the same wiring
                    try:
                        from . import circuit
                        cres = circuit.check(proj)
                        rep["circuit"] = {k: v for k, v in cres.items() if not k.startswith("_")}
                        rep["problems"] += cres["problems"]
                        rep["warnings"] += cres["warnings"]
                    except Exception as e:  # noqa: BLE001 - a crash in the circuit check is a failed check, not silent
                        rep["problems"].append(f"circuit check crashed: {type(e).__name__}: {e}")
            rq = []
            if "requirements" in stg:
                progress.stage("requirements")
                rest = (lambda r: requirements.redesign_tier(r) is None) if core is not None else None
                rq = (core or []) + requirements.run_all(proj, asm, quick="fea" not in stg, pick=rest)
                from . import usestory
                rep["problems"] += usestory.problems(proj)
                rep["use_story"] = usestory.summary(proj)
            fea_viz = {r["id"]: {**r.pop("_viz"), "part": (r.get("_field") or {}).get("part")}   # meshes stay out of report.json
                       for r in rq if "_viz" in r}
            fields: dict[str, list] = {}
            for r in rq:                                                   # stress fields too, summarised per part
                f = r.pop("_field", None)
                if f:
                    fields.setdefault(f["part"], []).append(f)
            for part, cases in fields.items():
                s = stressmap.summarize(cases)
                if s and part in rep["parts"]:
                    rep["parts"][part]["stress"] = s
                    msg = stressmap.advice(part, s)
                    if msg:
                        rep["warnings"].append(msg)
            for pid, pr in rep["parts"].items():                           # sharp inside corners: stressed ones fail
                st = pr.get("stress") or {}
                hz, cell = st.get("hot_zones", []), st.get("zone_mm", 0.0)
                prob = edges.hot_problem(pid, pr.get("sharp_inside") or [], hz, cell)
                if prob:
                    rep["problems"].append(prob)
                hzp = [z for z in hz if z.get("peak", 1.0) >= edges.HOT_PEAK]
                cool = [c for c in pr.get("sharp_inside") or [] if not edges._near_hot(c, hzp, cell)]
                for msg in (edges.advice(pid, cool, hz, cell), edges.kept_hot(pid, pr.get("sharp_kept") or [], hzp, cell)):
                    if msg:
                        rep["warnings"].append(msg)
            rep["requirements"] = rq
            if rq:
                from . import failure
                try:
                    rep["failure_modes"] = failure.table(proj, asm, rep)
                except Exception as e:  # noqa: BLE001 - a table gap must not stop the checks
                    rep["warnings"].append(f"failure table: {type(e).__name__}: {e}")
            _layer_proofs(proj, rep)
            rep["warnings"] += _fea_hygiene(proj)
            bp, bw = export.bom_extra_check(proj, rep.get("assembly", {}).get("fasteners"))
            rep["problems"] += bp
            rep["warnings"] += bw
            for r in rq:
                if not r["ok"]:
                    rep["problems"].append(f"requirement '{r['id']}' failed: {r['detail']} = {requirements.describe(r)}")
            A.solve(asm)
            if stg & {"files", "docs", "viewer", "renders"}:
                progress.stage("export")
                out = proj.out()
                export.glb(proj, out / "assembly.glb")
                rep["files"] = {}
            if stg & {"files", "renders"}:
                export.glb(proj, out / "exploded.glb", explode=25.0)
                export.glb(proj, out / "assembly_keepouts.glb", include_keepouts=True)
            if "files" in stg:
                export.step_assembly(proj, out / "assembly.step")
                rep["files"].update({"parts": export.part_files(proj, out / "parts"),
                                     "plates": export.plates(proj, out / "plates", printer)})
                try:                                    # per plate grams + time, per part slicer settings (kerf/printpkg.py)
                    from . import printpkg
                    rep["print"] = printpkg.write(proj, rep, rep["files"]["plates"], out / "plates")
                except Exception as e:  # noqa: BLE001
                    rep["problems"].append(f"print package could not be written: {type(e).__name__}: {e}")
                from . import drawings                  # out/drawings/<part>.pdf (cadgen eng_drawing)
                dr = drawings.write_all(proj, out / "drawings")
                rep["files"]["drawings"] = [f"drawings/{d['pdf']}" for d in dr.values() if d.get("pdf")]
                rep["problems"] += [f"drawing of {k} could not be made: {d['error']}" for k, d in dr.items() if d.get("error")]
                if asm.movable:                         # out/<project>.urdf + meshes for simulators (kerf/urdf.py)
                    from . import urdf
                    try:
                        masses = {**{k: v["mass_est_g"] for k, v in rep["parts"].items()},
                                  **{k: v["mass_g"] for k, v in rep["purchased"].items()}}
                        u = urdf.write(proj, out, asm, masses)
                        rep["files"]["urdf"] = [u["path"], u["zip"]]
                        rep["problems"] += [f"URDF {u['path']}: {m} ({c})" for sev, c, m in u["findings"] if sev == "error"]
                        rep["warnings"] += [f"URDF {u['path']}: {m} ({c})" for sev, c, m in u["findings"] if sev != "error"]
                    except Exception as e:  # noqa: BLE001
                        rep["problems"].append(f"URDF could not be written: {type(e).__name__}: {e}")
            if "docs" in stg:
                rep["bom"] = export.bom(proj, fj, rep["parts"], out, pins=pinj,
                                        extra=wiring_out.bom_rows(emodel) if emodel else None)
                if emodel:
                    (out / "WIRING.md").write_text(wiring_out.wiring_md(proj, emodel), encoding="utf-8")
                    (out / "wiring.svg").write_text(wiring_out.svg(proj, emodel), encoding="utf-8")
                    rep["files"]["wiring"] = ["WIRING.md", "wiring.svg"]
                if cres and cres.get("ran"):        # out/schematic.svg + .pdf, out/kicad/ (netlist, schematic, ERC)
                    from . import circuit
                    cw = circuit.write(proj, out, cres)
                    rep["files"]["circuit"] = cw["files"]
                    rep["problems"] += [f"circuit: {e}" for e in cw["errors"]]
                try:  # ship package (kerf/ship.py): priced BOM + ASSEMBLY.md with a render per step when rendering
                    rnd = (lambda g, pre, **kw: render_glb(g, pre, views="iso", sheet=False, **kw)) if "renders" in stg else None
                    rep["files"]["ship"] = ship.write(proj, asm, rep, out, render=rnd)
                    if emodel:      # solder / wiring steps after the mechanical ones
                        wiring_out.append_assembly(out / "ASSEMBLY.md", emodel, proj)
                except Exception as e:  # noqa: BLE001
                    rep["problems"].append(f"ship package (priced BOM / ASSEMBLY.md) could not be written: {type(e).__name__}: {e}")
                _firmware_check(proj, asm, rep, out)
            if "viewer" in stg:
                try:  # self-contained assembly viewer (kerf/viewer.py), after ASSEMBLY.md: its build-it-step-by-step mode
                    rep["files"]["viewer"] = "viewer.html"   # reads the step text; FEA fields colour the stress view
                    viewer.write(proj, asm, rep, out / "viewer.html", fea=fea_viz)
                except Exception as e:  # noqa: BLE001 - a failure here is a build problem, not silent
                    rep["problems"].append(f"viewer.html could not be written: {type(e).__name__}: {e}")
            if "renders" in stg:
                progress.stage("renders")
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
                for iid, it in proj.printed.items():
                    g = proj.out(f"part_{iid}.glb")
                    s = checks.oriented(it.shape, it.spec.get("print_rot", [0, 0, 0]))
                    s.label = iid
                    from . import geom
                    geom.write_glb([s], g, 0.03, 0.2, label=iid)       # mesh-aware (fused Meshy parts)
                    lo, hi = geom.bbox(s)
                    dx, dy, dz = (float(v) for v in (hi - lo))
                    render_glb(g, out / f"part_{iid}", sheet=True,
                               title=f"{iid}: {dx:.0f} x {dy:.0f} x {dz:.0f} mm overall, shown as printed (the gridded plate is the print bed, 10 mm squares)")
        except P.ProjectError as e:
            rep["problems"].append(f"assembly: {e}")
        except Exception as e:  # noqa: BLE001
            import traceback
            rep["problems"].append(f"assembly step crashed: {type(e).__name__}: {e}")
            rep.setdefault("traces", {})["assembly"] = traceback.format_exc(limit=8)
    return _finish(proj, rep, stg, t0, overrides)


def _redesign_first(proj, rep, quick=False):
    """Spencer, 2026-11-02: check first what would take the most work to redesign, so no effort goes into detail
    checks (and fixes) on a design about to change. Runs the requirements in requirements.REDESIGN_TIER (concept,
    then structure of the most connected parts; FEA included even in --quick) on the placed assembly, before the
    print, fit and motion checks. None if they could not run (then the normal stage runs every requirement)."""
    try:
        asm = A.plan(proj)
        A.solve(asm)
        return requirements.run_all(proj, asm, quick=quick, pick=lambda r: requirements.redesign_tier(r) is not None,
                                    by_redesign_cost=True)
    except Exception as e:  # noqa: BLE001 - the fit stage reports assembly problems properly
        rep["warnings"].append(f"redesign-level requirements could not run first ({type(e).__name__}: {e}); "
                               "they run with the others")
        return None


def _finish(proj, rep, stg, t0, overrides):
    if not overrides:           # record what this build read from the catalog, then the fingerprint that depends on it
        P.record_deps(proj)
        rep["fingerprint"] = proj.fingerprint()
    rep["maker_notes"] = maker_notes(rep["warnings"])
    _fold_stubs(proj, rep)
    rep["ok"] = not rep["problems"]
    rep["seconds"] = round(time.time() - t0, 1)
    progress.emit("done", ok=rep["ok"], problems=len(rep["problems"]), seconds=rep["seconds"])
    proj.out("report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    if "renders" in stg:                 # the design-reviewer's compact input (kerf/reviewpack.py)
        try:
            from . import reviewpack
            reviewpack.write(proj, rep, proj.out("report.json").parent)
        except Exception as e:  # noqa: BLE001 - the pack is a convenience: never fail a build over it
            print(f"review pack not written: {e}")
    return rep


def _firmware_check(proj, asm, rep, out):
    """Compile + simulate the bring-up program kerf/firmware.py just wrote (kerf/fwcheck.py) -> out/firmware/FIRMWARE_CHECK.json."""
    fw = ((rep.get("files") or {}).get("ship") or {}).get("firmware")
    if not fw or not fw.get("program"):          # no generated program (none, or flight-controller only)
        return
    from . import firmware, fwcheck
    try:
        res = fwcheck.check_dir(firmware.servos(proj, asm), out / "firmware")
    except Exception as e:  # noqa: BLE001 - a crash here is a build problem, never a silent pass
        res = {"status": "FAIL", "problems": [f"firmware check crashed: {type(e).__name__}: {e}"]}
    res["project"] = proj.name
    (out / "firmware" / "FIRMWARE_CHECK.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    rep["firmware_check"] = {"status": res["status"], "problems": res.get("problems", [])}
    rep.setdefault("files", {})["firmware_check"] = "firmware/FIRMWARE_CHECK.json"
    if res["status"] == "FAIL":
        rep["problems"] += [f"firmware: {p}" for p in res["problems"]]
    elif res["status"] in ("NOT_RUN", "COMPILED_ONLY"):
        rep["warnings"] += [f"firmware NOT verified ({res['status']}): {p}" for p in res["problems"]]


def _fold_stubs(proj, rep: dict):
    """Placeholder parts (ctx.stub / a STUB file) during design: every problem that names one is expected until it is
    modelled, so they move to rep['stub_problems'] and ONE problem says the design is in progress."""
    import re
    stubs = sorted(pid for pid, it in proj.printed.items() if getattr(it.shape, "kerf_stub", None))
    rep["stubs"] = stubs
    if not stubs:
        return
    pat = re.compile(r"\b(" + "|".join(map(re.escape, stubs)) + r")\b")
    keep, folded = [], []
    for p in rep["problems"]:
        (folded if pat.search(p) else keep).append(p)
    rep["stub_problems"] = folded
    n = len(proj.printed)
    keep.insert(0, f"design in progress: {len(stubs)} of {n} printed parts are still placeholders ({', '.join(stubs)}); "
                   f"{len(folded)} problem(s) involving them are expected until they are modelled (out/report.json "
                   f"stub_problems)")
    rep["problems"] = keep


def run_requirements(name: str, only=None, overrides=None) -> dict:
    """Just the named requirements (ids or check names; None = all), on the assembled project: parts from the build
    cache, placed by the joint tree, nothing else checked. The quick way to see one number after an edit, instead of
    a full check (interference, sweeps, print checks, every FEA). `kerf check` still decides PASS."""
    from . import assembly as A, usestory
    proj = P.load(name, overrides)
    reqs = list(proj.data.get("requirements") or []) + usestory.requirements(proj)
    known = {r.get("id", r["check"]) for r in reqs} | {r["check"] for r in reqs}
    unknown = sorted(set(only or ()) - known)
    if unknown:
        return {"ok": False, "results": [], "problems": [f"no requirement {', '.join(unknown)} in {name} "
                                                         f"(have: {', '.join(r.get('id', r['check']) for r in reqs)})"]}
    P.build(proj)                                 # every item: placement needs the whole joint tree
    bad = [f"{iid}: {it.error}" for iid, it in proj.items.items() if it.error]
    if bad:
        return {"ok": False, "results": [], "problems": bad}
    asm = A.plan(proj)
    A.solve(asm)
    res = requirements.run_all(proj, asm, only=set(only) if only else None)
    return {"ok": all(r["ok"] for r in res), "results": res, "problems": [],
            "cached_parts": [k for k, it in proj.printed.items() if it.cached]}


def summary(rep: dict) -> str:
    L = [f"{'PASS' if rep['ok'] else 'FAIL'}  {rep['project']}  ({rep['seconds']} s, fingerprint {rep['fingerprint']})"]
    if rep.get("cached_parts"):
        L.append(f"  {len(rep['cached_parts'])}/{len(rep['parts'])} parts unchanged, taken from the build cache")
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
        L.append(f"  req {r['id']:20s} " + ("skipped (--quick)" if r.get("skipped") else req_line(r)))
    for p in rep["problems"]:
        L.append(f"  PROBLEM: {p}")
    for w in rep["warnings"]:
        L.append(f"  warning: {w}")
    return "\n".join(L)
