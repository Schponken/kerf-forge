"""Per-part manufacturability checks for FDM printing, done on the part in its print orientation."""
from __future__ import annotations

import numpy as np
from build123d import Location, Rot, Pos

from . import catalog, geom

PRINTERS = {  # usable build volume, mm
    "Bambu Lab A2L": (330, 320, 325),
    "Bambu Lab A1": (256, 256, 256),
    "Bambu Lab P1S": (256, 256, 256),
    "Monoprice Inventor II": (150, 140, 140),
}
FALLBACK_DENSITY = {"PLA": 1.24, "PETG": 1.27, "CF-PETG": 1.29, "PA6-CF": 1.17, "ABS": 1.04, "ASA": 1.07, "TPU": 1.21}

# Limits. A failed check blocks the project; a warning is reported but allowed.
MIN_WALL_FAIL = 0.8      # mm, 2nd-percentile local thickness
MIN_WALL_WARN = 1.2
OVERHANG_WARN = 0.03     # fraction of surface area needing support


def density(material: str) -> float:
    try:
        m = catalog.get(f"materials.{material}")
        return catalog.num(m, "density", "density_g_cm3")
    except Exception:
        if material not in FALLBACK_DENSITY:
            raise ValueError(f"unknown material '{material}' (use one of {sorted(FALLBACK_DENSITY)})")
        return FALLBACK_DENSITY[material]


def oriented(shape, rot) -> object:
    """Copy of the part rotated into print orientation and dropped onto the bed at the origin."""
    s = Rot(*rot) * shape.located(Location())
    bb = s.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * s


def part_checks(item, printer: str, supports: str = "allowed") -> dict:
    spec = item.spec
    shape = item.shape
    rot = spec.get("print_rot", [0, 0, 0])
    s = oriented(shape, rot)
    problems, warnings = [], []
    sol = geom.solids(s)
    if len(sol) != 1:
        problems.append(f"{item.id} is {len(sol)} separate solids; a printed part must be one piece")
    if not s.is_valid:
        problems.append(f"{item.id}: geometry is invalid (self-intersecting or broken faces)")
    bb = s.bounding_box()
    size = [bb.size.X, bb.size.Y, bb.size.Z]
    X, Y, Z = PRINTERS[printer]
    a, b = sorted(size[:2], reverse=True)
    c, d = sorted((X, Y), reverse=True)
    fits = a <= c and b <= d and size[2] <= Z
    if not fits:
        problems.append(f"{item.id} is {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm and does not fit the {printer} ({X} x {Y} x {Z} mm); split it or reorient")
    v, f = geom.mesh(s)
    ms = geom.mesh_stats(v, f)
    if not ms["watertight"]:
        problems.append(f"{item.id}: exported mesh is not watertight")
    oh_area, oh_frac, _ = geom.overhang(v, f, 45.0, bed_z=0.0)
    if supports == "avoid" and oh_frac > 0.005:
        problems.append(f"{item.id}: {oh_frac*100:.1f}% of the surface overhangs more than 45 degrees, but this project must print without supports")
    elif oh_frac > OVERHANG_WARN:
        warnings.append(f"{item.id}: {oh_frac*100:.1f}% of the surface needs support; consider chamfers or a different print orientation")
    th = geom.thickness_samples(v, f, n=1200)
    p02 = float(np.percentile(th, 2)) if len(th) else None
    if p02 is not None and p02 < MIN_WALL_FAIL:
        problems.append(f"{item.id}: walls as thin as {p02:.2f} mm (2nd percentile); minimum is {MIN_WALL_FAIL} mm, aim for {MIN_WALL_WARN}+")
    elif p02 is not None and p02 < MIN_WALL_WARN:
        warnings.append(f"{item.id}: some walls are {p02:.2f} mm thick; {MIN_WALL_WARN} mm or more prints more reliably")
    vol = geom.volume(s)
    mat = spec.get("material", "PETG")
    rho = density(mat)
    area = float(sum(fc.area for fc in s.faces()))
    shell = min(vol, area * 0.84)  # two 0.42 mm perimeters / top-bottom skins
    infill = float(spec.get("infill", 0.25))
    return {
        "ok": not problems, "problems": problems, "warnings": warnings,
        "material": mat, "print_rot": rot, "size_mm": [round(x, 2) for x in size], "fits": fits,
        "volume_mm3": round(vol, 1), "mass_solid_g": round(vol / 1000 * rho, 1),
        "mass_est_g": round((shell + infill * max(vol - shell, 0)) / 1000 * rho, 1), "infill": infill,
        "overhang_pct": round(oh_frac * 100, 2), "wall_p02_mm": None if p02 is None else round(p02, 2),
        "watertight": ms["watertight"], "solids": len(sol), "faces": len(s.faces()), "build_ms": item.build_ms,
    }


def item_mass_g(item) -> float:
    """Mass used for statics: printed parts from geometry, purchased parts from the catalog."""
    if item.role == "printed":
        vol = geom.volume(item.shape)
        rho = density(item.spec.get("material", "PETG"))
        infill = float(item.spec.get("infill", 0.25))
        area = float(sum(fc.area for fc in item.shape.faces()))
        shell = min(vol, area * 0.84)
        return (shell + infill * max(vol - shell, 0)) / 1000 * rho
    if item.role == "purchased":
        if "mass_g" in item.spec:
            return float(item.spec["mass_g"])
        try:
            return catalog.num(catalog.get(item.spec["catalog"]), "weight_g", "mass_g", "weight")
        except Exception:
            return 0.0
    return 0.0
