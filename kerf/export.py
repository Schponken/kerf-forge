"""Exports: STEP assembly, print-ready STL/3MF per part, A2L plates, GLB for viewing, BOM."""
from __future__ import annotations

import csv
import json
from collections import Counter

from build123d import Compound, Location, Mesher, Pos, export_gltf, export_step, export_stl, Color

from . import catalog, checks, geom
from .pins import lock_advice

PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756", "#72B7B2", "#EECA3B", "#9D755D", "#FF9DA6", "#BAB0AC"]
PURCHASED_COLOR = "#3A3F44"


def _hidden(it, for_render):
    """`render: false` on an item (e.g. a power supply modelled far from the device) keeps it out of the GLB views and
    renders so it doesn't shrink the device in them; it is still in every check, the STEP and the BOM."""
    return for_render and (getattr(it, "spec", None) or {}).get("render") is False


def _placed_copies(proj, include_keepouts=False, explode=0.0, for_render=False):
    shapes = []
    allb = [it.shape for it in proj.items.values() if it.shape is not None and it.role != "keepout" and not _hidden(it, for_render)]
    if not allb:
        return shapes
    import numpy as np
    lo = np.min([geom.bbox(s)[0] for s in allb], axis=0)
    hi = np.max([geom.bbox(s)[1] for s in allb], axis=0)
    center = (lo + hi) / 2
    for k, (iid, it) in enumerate(proj.items.items()):
        if it.shape is None or (it.role == "keepout" and not include_keepouts) or _hidden(it, for_render):
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
    geom.write_glb(_placed_copies(proj, include_keepouts, explode, for_render=True), path, 0.05, 0.2, label=proj.name)


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
        _write_part_settings(f, {f"{iid}_{n + 1}": proj.items[iid].spec for iid, n, _ in plate})
        out.append({"file": f.name, "parts": [f"{iid} #{n + 1}" for iid, n, _ in plate]})
    (outdir / "PRINT_SETTINGS.md").write_text(print_settings_md(proj), encoding="utf-8")
    return out


def part_print_settings(spec) -> dict:
    """Slicer settings a printed part's numbers assume (mass estimate, FEA): infill and perimeters."""
    return {"infill_pct": round(float(spec.get("infill", 0.25)) * 100), "walls": int(spec.get("walls", 2)),
            "material": spec.get("material", "PETG"), "print_rot": list(spec.get("print_rot", [0, 0, 0]))}


def print_settings_md(proj) -> str:
    L = ["# Print settings per part", "",
         "The mass estimate and the strength checks assume these. Set them per object in the slicer (Bambu Studio / "
         "OrcaSlicer: right-click the object, *Add settings*: Sparse infill density and Wall loops). The plate files carry "
         "them in `Metadata/model_settings.config` too.", "",
         "| Part | Material | Infill | Wall loops | Orientation (print_rot) |", "|---|---|---|---|---|"]
    for iid, it in proj.printed.items():
        ps = part_print_settings(it.spec)
        L.append(f"| {iid} | {ps['material']} | {ps['infill_pct']} % | {ps['walls']} | {ps['print_rot']} |")
    return "\n".join(L) + "\n"


def _write_part_settings(path, specs: dict):
    """Add per-object slicer settings (Bambu Studio / OrcaSlicer `Metadata/model_settings.config` form: one <object>
    per model object, keyed by the 3MF object id) to a plate 3MF written by the mesher."""
    import re
    import zipfile
    from xml.sax.saxutils import quoteattr
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    model = next((n for n in files if n.lower().endswith("3dmodel.model")), None)
    if model is None:
        return
    head = files[model].decode("utf-8", "ignore")             # whole model: object tags follow large meshes
    objs = []
    for tag in re.findall(r"<object\s[^>]*>", head):
        oid = re.search(r'\sid="(\d+)"', tag)
        pn = re.search(r'partnumber="([^"]+)"', tag) or re.search(r'\sname="([^"]+)"', tag)
        if oid and pn:
            objs.append((oid.group(1), pn.group(1)))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    for oid, pn in objs:
        sp = specs.get(pn)
        if sp is None:
            continue
        ps = part_print_settings(sp)
        lines += [f'  <object id="{oid}">', f'    <metadata key="name" value={quoteattr(pn)}/>',
                  f'    <metadata key="sparse_infill_density" value="{ps["infill_pct"]}%"/>',
                  f'    <metadata key="wall_loops" value="{ps["walls"]}"/>', "  </object>"]
    lines.append("</config>")
    files["Metadata/model_settings.config"] = "\n".join(lines).encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)


def horn_screw_rows(proj) -> list:
    """ENG-14: each servo horn's centre screw (catalog servo_horns.*.center_screw) is a part of the build too: one BOM
    row per size (it comes with the servo; access to it is checked in kerf/access.py)."""
    from collections import Counter
    n = Counter()
    for it in proj.items.values():
        cat = str(it.spec.get("catalog", ""))
        if it.role == "purchased" and cat.startswith("servo_horns."):
            cs = catalog.get(cat).get("center_screw")
            if cs:
                n[str(cs)] += int(it.spec.get("qty", 1))
    return [{"type": "fastener", "item": f"{cs} horn centre screw", "qty": q, "spec": "",
             "note": "comes with the servo; holds the horn on the spline (a drop of medium threadlocker: metal into metal)"}
            for cs, q in sorted(n.items())]


BOM_EXTRA_KEYS = {"type", "item", "qty", "spec", "note", "link", "group", "price_key"}


def bom_extra_check(proj, fasteners) -> tuple[list, list]:
    """bom_extra rows (ENG-15): unknown keys and a missing item are problems (a YAML comma inside a row silently splits
    it into junk keys); a row naming a metric screw size the fastener check already buys is a warning (likely a
    duplicate of an automatic fastener row, e.g. 'M2 x 8' by hand next to the auto 'M2 x 5')."""
    import re
    problems, warnings = [], []
    auto = {}
    for j in fasteners or []:
        auto.setdefault(j["screw"], set()).add(j.get("length_mm"))
    for k, x in enumerate(proj.data.get("bom_extra") or []):
        if not isinstance(x, dict) or "item" not in x:
            problems.append(f"bom_extra row {k + 1}: needs an 'item' ({x!r})")
            continue
        bad = sorted(set(x) - BOM_EXTRA_KEYS)
        if bad:
            problems.append(f"bom_extra '{x['item']}': unknown key(s) {bad} (allowed {sorted(BOM_EXTRA_KEYS)}); a comma "
                            f"inside a value splits the row, quote it")
        m = re.search(r"\b(M\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\b", str(x["item"]))
        it = str(x["item"]).lower()
        screwish = "screw" in it and not any(k in it for k in ("set screw", "spacer", "standoff", "wood", "nut", "washer"))
        same_len = m and any(v is not None and abs(float(v) - float(m.group(2))) < 1e-6 for v in auto.get(m.group(1), ()))
        if m and screwish and same_len and str(x.get("type", "")) in ("fastener", "hardware", "extra", ""):
            warnings.append(f"bom_extra '{x['item']}': the fastener check already buys {m.group(1)} screws "
                            f"({', '.join(f'{L:g} mm' for L in sorted(v for v in auto[m.group(1)] if v))}); "
                            f"if this row is the same screws, drop it (duplicate)")
    return problems, warnings


def bom(proj, fastener_joints, part_reports, outdir, pins=None, extra=None):
    rows = []
    for iid, it in proj.printed.items():
        r = part_reports.get(iid, {})
        rows.append({"type": "printed", "item": iid, "qty": it.spec.get("qty", 1), "spec": it.spec.get("material", "PETG"),
                     "note": f"{r.get('mass_est_g', '?')} g each, {r.get('size_mm')}"})
    for iid, it in proj.printed.items():      # bits a part's features need (ctx.bom_item, e.g. the tripod nut)
        for b in getattr(it.shape, "kerf_bom", None) or []:
            rows.append({**b, "qty": b["qty"] * it.spec.get("qty", 1), "note": f"{iid}: {b['note']}".rstrip(": ")})
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
    def g(x):  # a pin with no valid stocked length is a check problem already; never crash the BOM on it
        return "? (no stocked length fits, see the pin problems)" if x is None else f"{x:g}"

    for pj in pins or []:
        if pj.get("shoulder"):
            from .iface import pin_dims
            pd = pin_dims(pj["pin"])
            rows.append({"type": "fastener", "item": f"{g(pj['d_mm'])} x {g(pj['length_mm'])} mm shoulder screw, {pd['thread']} thread (pivot)",
                         "qty": 1, "spec": pj["pin"], "link": catalog.get(pj["pin"]).get("buy", ""),
                         "note": f"hinge '{pj['group']}'; tighten gently until the shoulder bottoms"
                                 + (f"; {catalog.get(pj['pin'])['buy_note']}" if catalog.get(pj["pin"]).get("buy_note") else "")})
            if "heatset" in pj["fixed_fit"]:
                rows.append({"type": "fastener", "item": f"{pd['thread']} heat-set insert", "qty": 1, "spec": "", "note": f"hinge '{pj['group']}'"})
        elif pj["screw_pivot"]:
            rows.append({"type": "fastener", "item": f"{pj['pin']} x {g(pj['length_mm'])} mm socket head screw (pivot)", "qty": 1,
                         "spec": "ISO 4762", "note": f"hinge '{pj['group']}'; {lock_advice(pj['fixed_fit'])}"})
            if "heatset" in pj["fixed_fit"]:
                rows.append({"type": "fastener", "item": f"{pj['pin']} heat-set insert", "qty": 1, "spec": "", "note": f"hinge '{pj['group']}'"})
        else:
            rows.append({"type": "pin", "item": f"{g(pj['d_mm'])} x {g(pj['length_mm'])} mm steel dowel pin", "qty": 1,
                         "spec": f"ISO 8734 ({pj['pin']})", "note": f"hinge '{pj['group']}', pressed into {', '.join(pj['fixed_in'])}"})
    rows += extra or []
    rows += horn_screw_rows(proj)
    for x in proj.data.get("bom_extra") or []:
        rows.append({"type": x.get("type", "extra"), "item": x["item"], "qty": x.get("qty", 1), "spec": x.get("spec", ""),
                     "note": x.get("note", ""), "link": x.get("link", "")})
    for r in rows:
        r.setdefault("link", "")
    with open(outdir / "bom.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["type", "item", "qty", "spec", "note", "link"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    md = ["| Type | Item | Qty | Spec | Note | Buy / source |", "|---|---|---|---|---|---|"]
    md += [f"| {r['type']} | {r['item']} | {r['qty']} | {r['spec']} | {r['note']} | {r['link']} |" for r in rows]
    (outdir / "bom.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rows
