"""Custom stock parts: manufacturing handoff, separate from FDM print settings and material models."""
from __future__ import annotations

import json
import hashlib
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

from build123d import ExportDXF, GeomType, Location, Pos, export_step, extrude

from . import geom

PROCESSES = {"laser_cut": "laser cut", "cnc": "CNC machined"}


def validate(pid: str, spec: dict) -> dict:
    m = spec.get("manufacturing")
    if not isinstance(m, dict) or m.get("process") not in PROCESSES:
        raise ValueError(f"{pid}: manufacturing.process must be laser_cut or cnc")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", pid):
        raise ValueError(f"{pid}: manufactured part ids use letters, numbers, underscores and hyphens")
    for key in ("stock", "density_source"):
        if not isinstance(m.get(key), str) or not m[key].strip():
            raise ValueError(f"{pid}: manufacturing.{key} is required")
    if urlsplit(m["density_source"]).scheme not in ("https", "http") or not urlsplit(m["density_source"]).netloc:
        raise ValueError(f"{pid}: manufacturing.density_source must link to the stock density evidence")
    for key in ("density_g_cm3", "thickness_mm"):
        if key == "thickness_mm" and m["process"] != "laser_cut" and key not in m:
            continue
        val = m.get(key)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val <= 0:
            raise ValueError(f"{pid}: manufacturing.{key} must be a finite positive number")
    if m.get("price_key") is not None and (not isinstance(m["price_key"], str) or not m["price_key"].strip()):
        raise ValueError(f"{pid}: manufacturing.price_key must name one exact saved quote")
    qty = spec.get("qty", 1)
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise ValueError(f"{pid}: manufactured quantity must be a positive integer")
    fdm = set(spec) & {"material", "print_rot", "infill", "walls", "modifiers", "supports"}
    if fdm:
        raise ValueError(f"{pid}: FDM settings {sorted(fdm)} do not apply to manufactured stock; use manufacturing.stock")
    if spec.get("source") == "meshy" or Path(spec.get("import", "")).suffix.lower() in (".stl", ".3mf"):
        raise ValueError(f"{pid}: manufactured parts need exact CAD or STEP, not a triangle mesh")
    return m


def mass_g(it) -> float:
    return geom.volume(it.shape) / 1000 * it.spec["manufacturing"]["density_g_cm3"]


def quote_fingerprint(it) -> str:
    """Conservative quote identity: local geometry, stock, process, quantity. No self-referential quote fields."""
    import numpy as np
    m = it.spec["manufacturing"]
    v, f = geom.mesh(it.shape.located(Location()), tol=0.01, ang=0.1)
    h = hashlib.sha256(np.rint(v * 1e6).astype("<i8").tobytes() + f.astype("<i8").tobytes())
    h.update(json.dumps({"stock": m["stock"], "process": m["process"], "thickness_mm": m.get("thickness_mm"),
                         "qty": it.spec.get("qty", 1)}, sort_keys=True).encode())
    return h.hexdigest()


def guard_stock_models(proj, values):
    """Called by every registered strength check, including direct nested calls through REGISTRY."""
    ids = {iid for iid, it in proj.items.items() if it.role == "manufactured"}
    def mentions(v):
        if isinstance(v, str):
            return v.split(".", 1)[0] in ids
        if isinstance(v, dict):
            return any(mentions(x) for x in v.values())
        if isinstance(v, (list, tuple)):
            return any(mentions(x) for x in v)
        return False
    if mentions(values):
        raise ValueError("manufactured-part strength is not verified: this check uses FDM material models; "
                         "a stock-specific strength model is required")


def label(it) -> str:
    m = it.spec["manufacturing"]
    return f"{PROCESSES[m['process']]}, {m['stock']}"


def flat_profile(it):
    """Prove an XY through-cut profile by reconstructing the exact solid from its bottom face."""
    s = it.shape.located(Location())
    lo, hi = geom.bbox(s)
    thickness = float(hi[2] - lo[2])
    declared = it.spec["manufacturing"]["thickness_mm"]
    if abs(thickness - declared) > 1e-5:
        raise ValueError(f"{it.id}: stock thickness {declared:g} mm does not match the model ({thickness:g} mm)")
    faces = [f for f in s.faces() if f.geom_type == GeomType.PLANE and f.normal_at().Z < -0.999999
             and abs(f.center().Z - lo[2]) < 1e-6]
    if len(faces) != 1:
        raise ValueError(f"{it.id}: DXF needs one flat XY through-cut profile; pockets, bevels and bent parts need CNC STEP")
    face = faces[0]
    stock = extrude(face, amount=thickness, dir=(0, 0, 1))
    tol = max(1e-6, abs(s.volume) * 1e-8)
    if abs((s - stock).volume) + abs((stock - s).volume) > tol:
        raise ValueError(f"{it.id}: model is not a constant-thickness through-cut plate; use CNC STEP for pockets or bevels")
    return Pos(0, 0, -lo[2]) * face


def part_check(it) -> dict:
    m = validate(it.id, it.spec)
    s = it.shape.located(Location())
    problems = []
    if not s.is_valid or len(geom.solids(s)) != 1:
        problems.append(f"{it.id}: a manufactured part must be one valid closed solid")
    if geom.kmesh(s) is not None:
        problems.append(f"{it.id}: manufacturing export requires exact CAD, not a mesh")
    if m["process"] == "laser_cut" or "thickness_mm" in m:
        try:
            flat_profile(it)
        except ValueError as e:
            problems.append(str(e))
    if it.spec.get("structural"):
        problems.append(f"{it.id}: manufactured-part strength is not verified; stock-specific strength models are not supported yet")
    lo, hi = geom.bbox(s)
    return {"ok": not problems, "problems": problems,
            "warnings": [f"{it.id}: manufacturing files do not prove stock strength or supplier tooling limits; confirm both before ordering"],
            "manufacturing": m, "size_mm": [round(float(x), 3) for x in hi - lo],
            "mass_est_g": mass_g(it), "volume_mm3": float(s.volume), "build_ms": it.build_ms}


def write(proj, outdir: Path) -> dict:
    """Write exact, local-frame CAD and an order manifest; no order is submitted."""
    if not proj.manufactured and not (outdir / "order.json").exists():
        return {}
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        previous = json.loads((outdir / "order.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    rows = {}
    for iid, it in proj.manufactured.items():
        report = part_check(it)
        if report["problems"]:
            raise ValueError("; ".join(report["problems"]))
        m = it.spec["manufacturing"]
        paths = [f"{iid}.step"]
        export_step(it.shape.located(Location()), str(outdir / paths[0]))
        if m["process"] == "laser_cut" or "thickness_mm" in m:
            dxf = ExportDXF()
            dxf.add_shape(flat_profile(it))
            paths.append(f"{iid}.dxf")
            dxf.write(outdir / paths[-1])
        rows[iid] = {**m, "qty": it.spec.get("qty", 1), "files": paths, "units": "mm", "mass_est_g": mass_g(it),
                     "size_mm": report["size_mm"], "current_quote_fingerprint": quote_fingerprint(it)}
    (outdir / "order.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    lines = ["# Parts to have made", "", "CAD is in millimetres at 1:1 in each part's own frame. STEP is the finished solid; "
             "DXF is the exact through-cut profile, including holes, with no kerf compensation. Confirm stock, tolerances, "
             "tool access, edge finish and strength with the supplier before ordering. No order has been placed.", "",
             "Saved quotes are dated prices for the exact part and quantity; missing quotes remain unpriced in bom.md. "
             "Request a new quote after changing dimensions, material, process or quantity.", ""]
    for iid, row in rows.items():
        lines += [f"## {iid}", "", f"- Quantity: {row['qty']}; {label(proj.items[iid])}.",
                  f"- Files: {', '.join(row['files'])}.",
                  f"- Estimated mass: {row['mass_est_g']:g} g each from {row['density_g_cm3']:g} g/cm³ stock density; "
                  f"evidence: {row['density_source']}.",
                  "- Inspect the received part and test its fit before final assembly.", ""]
    (outdir / "ORDER.md").write_text("\n".join(lines), encoding="utf-8")
    current = {f for row in rows.values() for f in row["files"]}
    if isinstance(previous, dict):
        for row in previous.values():
            for name in row.get("files", []) if isinstance(row, dict) else []:
                if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_-]+\.(step|dxf)", name) and name not in current:
                    (outdir / name).unlink(missing_ok=True)  # only files listed by our previous generated manifest
    return {"parts": rows, "guide": "manufacturing/ORDER.md", "manifest": "manufacturing/order.json"}
