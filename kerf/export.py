"""Exports: STEP assembly, print-ready STL/3MF per part, A2L plates, GLB for viewing, BOM."""
from __future__ import annotations

import csv
import json
from collections import Counter

from build123d import Compound, Location, Mesher, Pos, export_gltf, export_step, export_stl, Color

from . import checks, geom

PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756", "#72B7B2", "#EECA3B", "#9D755D", "#FF9DA6", "#BAB0AC"]
PURCHASED_COLOR = "#3A3F44"


def _placed_copies(proj, include_keepouts=False, explode=0.0):
    shapes = []
    allb = [it.shape for it in proj.items.values() if it.shape is not None and it.role != "keepout"]
    if not allb:
        return shapes
    import numpy as np
    lo = np.min([geom.bbox(s)[0] for s in allb], axis=0)
    hi = np.max([geom.bbox(s)[1] for s in allb], axis=0)
    center = (lo + hi) / 2
    for k, (iid, it) in enumerate(proj.items.items()):
        if it.shape is None or (it.role == "keepout" and not include_keepouts):
            continue
        s = it.shape.moved(Location())
        if explode:
            c = (geom.bbox(it.shape)[0] + geom.bbox(it.shape)[1]) / 2
            d = c - center
            n = float(np.linalg.norm(d)) or 1.0
            s = Pos(*(d / n * explode * (1 + n / 100))) * s
        s.label = iid
        s.color = Color(PURCHASED_COLOR if it.role != "printed" else PALETTE[k % len(PALETTE)])
        if it.role == "keepout":
            s.color = Color(1, 0.4, 0.1, 0.25)
        shapes.append(s)
    return shapes


def step_assembly(proj, path):
    comp = Compound(children=_placed_copies(proj), label=proj.name)
    export_step(comp, str(path))


def glb(proj, path, explode=0.0, include_keepouts=False):
    geom.write_glb(_placed_copies(proj, include_keepouts, explode), path, 0.05, 0.2, label=proj.name)


def part_files(proj, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    files = {}
    for iid, it in proj.printed.items():
        s = checks.oriented(it.shape, it.spec.get("print_rot", [0, 0, 0]))
        stl = outdir / f"{iid}.stl"
        if geom.kmesh(s) is not None:            # fused Meshy part: the printed body is the merged mesh
            import trimesh
            tm = trimesh.Trimesh(*geom.kmesh(s), process=False)
            tm.export(str(stl))
            (outdir / f"{iid}.3mf").write_bytes(trimesh.exchange.threemf.export_3MF(tm))
            files[iid] = [stl.name, f"{iid}.3mf"]
            continue
        export_stl(s, str(stl), tolerance=0.01, angular_tolerance=0.1)
        m = Mesher()
        m.add_shape(s, linear_deflection=0.01, angular_deflection=0.1, part_number=iid)
        m.write(str(outdir / f"{iid}.3mf"))
        files[iid] = [stl.name, f"{iid}.3mf"]
    return files


def plates(proj, outdir, printer="Bambu Lab A2L", gap=6.0):
    """Shelf-pack every printed copy onto as few plates as needed. Returns plate list."""
    outdir.mkdir(parents=True, exist_ok=True)
    X, Y, _ = checks.PRINTERS[printer]
    copies = []
    for iid, it in proj.printed.items():
        s = checks.oriented(it.shape, it.spec.get("print_rot", [0, 0, 0]))
        lo, hi = geom.bbox(s)
        for n in range(int(it.spec.get("qty", 1))):
            copies.append((iid, n, s, float(hi[0] - lo[0]), float(hi[1] - lo[1])))
    copies.sort(key=lambda c: -c[4])
    plates_, cur, x, y, row_h = [], [], gap, gap, 0.0
    for c in copies:
        iid, n, s, w, h = c
        if x + w + gap > X:
            x, y, row_h = gap, y + row_h + gap, 0.0
        if y + h + gap > Y:
            plates_.append(cur)
            cur, x, y, row_h = [], gap, gap, 0.0
        cur.append((iid, n, Pos(x + w / 2 - X / 2, y + h / 2 - Y / 2, 0) * s))
        x += w + gap
        row_h = max(row_h, h)
    if cur:
        plates_.append(cur)
    out = []
    for k, plate in enumerate(plates_, 1):
        f = outdir / f"plate_{k}.3mf"
        if any(geom.kmesh(s) is not None for _, _, s in plate):   # a Meshy part on the plate: write meshes
            import trimesh
            sc = trimesh.Scene()
            for iid, n, s in plate:
                sc.add_geometry(trimesh.Trimesh(*geom.mesh(s, tol=0.01, ang=0.1), process=True), geom_name=f"{iid}_{n + 1}")
            f.write_bytes(trimesh.exchange.threemf.export_3MF(sc))
        else:
            m = Mesher()
            for iid, n, s in plate:
                m.add_shape(s, linear_deflection=0.01, angular_deflection=0.1, part_number=f"{iid}_{n + 1}")
            m.write(str(f))
        out.append({"file": f.name, "parts": [f"{iid} #{n + 1}" for iid, n, _ in plate]})
    return out


def bom(proj, fastener_joints, part_reports, outdir, pins=None, extra=None):
    rows = []
    for iid, it in proj.printed.items():
        r = part_reports.get(iid, {})
        rows.append({"type": "printed", "item": iid, "qty": it.spec.get("qty", 1), "spec": it.spec.get("material", "PETG"),
                     "note": f"{r.get('mass_est_g', '?')} g each, {r.get('size_mm')}"})
    for iid, it in proj.items.items():
        if it.role == "purchased":
            from .wiring_out import link
            rows.append({"type": "purchased", "item": iid, "qty": it.spec.get("qty", 1), "spec": it.spec.get("catalog", ""),
                         "note": it.spec.get("note", ""), "link": link(it.spec.get("catalog", ""))})
    screws = Counter((j["screw"], j["length_mm"], {"countersink": "flat head"}.get(j["head"], "socket head")) for j in fastener_joints)
    for (size, length, head), n in sorted(screws.items(), key=lambda x: str(x)):
        rows.append({"type": "fastener", "item": f"{size} x {length} mm {head} screw", "qty": n, "spec": "ISO 4762 / 10642", "note": ""})
    recv = Counter((j["screw"], j["receiver"]) for j in fastener_joints if j["receiver"] in ("heatset", "nut_trap"))
    for (size, kind), n in sorted(recv.items()):
        rows.append({"type": "fastener", "item": f"{size} {'heat-set insert' if kind == 'heatset' else 'hex nut'}", "qty": n, "spec": "", "note": ""})
    for pj in pins or []:
        if pj["screw_pivot"]:
            rows.append({"type": "fastener", "item": f"{pj['pin']} x {pj['length_mm']:g} mm socket head screw (pivot)", "qty": 1,
                         "spec": "ISO 4762", "note": f"hinge '{pj['group']}'; medium threadlocker"})
            if "heatset" in pj["fixed_fit"]:
                rows.append({"type": "fastener", "item": f"{pj['pin']} heat-set insert", "qty": 1, "spec": "", "note": f"hinge '{pj['group']}'"})
        else:
            rows.append({"type": "pin", "item": f"{pj['d_mm']:g} x {pj['length_mm']:g} mm steel dowel pin", "qty": 1,
                         "spec": f"ISO 8734 ({pj['pin']})", "note": f"hinge '{pj['group']}', pressed into {', '.join(pj['fixed_in'])}"})
    rows += extra or []
    for x in proj.data.get("bom_extra") or []:
        rows.append({"type": x.get("type", "extra"), "item": x["item"], "qty": x.get("qty", 1), "spec": x.get("spec", ""),
                     "note": x.get("note", ""), "link": x.get("link", "")})
    for r in rows:
        r.setdefault("link", "")
    with open(outdir / "bom.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["type", "item", "qty", "spec", "note", "link"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    md = ["| Type | Item | Qty | Spec | Note | Buy / source |", "|---|---|---|---|---|---|"]
    md += [f"| {r['type']} | {r['item']} | {r['qty']} | {r['spec']} | {r['note']} | {r['link']} |" for r in rows]
    (outdir / "bom.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rows
