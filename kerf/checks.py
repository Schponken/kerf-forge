"""Per-part manufacturability checks for FDM printing, done on the part in its print orientation."""
from __future__ import annotations

import json
import math

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
# A part no strength check loads may go down to one extrusion line: Bambu Studio's default line width for a 0.4 mm
# nozzle is 0.42 mm (https://forum.bambulab.com/t/default-line-width-of-0-42/20400). Load-carrying parts keep 0.8.
MIN_WALL_LINE = 0.42
OVERHANG_WARN = 0.03     # fraction of surface area needing support


def _finite_number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not a boolean")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be a finite number") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def print_parameters(spec) -> tuple[float, int]:
    """One interpretation for mass and slicer output; reject bad inputs rather than clamp or truncate them."""
    if not isinstance(spec, dict):
        raise ValueError("print settings must be a mapping")
    infill = _finite_number(spec.get("infill", 0.25), "infill")
    if not 0 <= infill <= 1:
        raise ValueError("infill must be a fraction from 0 to 1 inclusive")
    walls = _finite_number(spec.get("walls", 2), "walls")
    if walls < 0 or not walls.is_integer():
        raise ValueError("walls must be a nonnegative whole number of perimeter loops")
    return infill, int(walls)


def explicit_mass_g(spec) -> float | None:
    """An absent override stays absent; zero retains the existing unknown-mass warning behavior."""
    if not isinstance(spec, dict):
        raise ValueError("purchased item settings must be a mapping")
    if "mass_g" not in spec:
        return None
    mass = _finite_number(spec["mass_g"], "mass_g")
    if mass < 0:
        raise ValueError("mass_g must be nonnegative")
    return mass


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
    lo, hi = geom.bbox(s)                     # mesh-aware: a fused Meshy part sits on the bed by its shell
    return Pos(-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]) * s


BED_RATIO_WARN = 0.1   # bed contact under 10 % of the part's largest flat face: it stands on an edge or a point (ENG-9)


def bed_contact(pid, s) -> list:
    """First layer (docs/ENGINEERING.md s4, audit ENG-9): warn when the faces on the bed (planar, facing down, at the
    lowest z) add up to less than BED_RATIO_WARN of the part's largest planar face, i.e. the big flat face is lifted
    off the bed and the part starts on a narrow edge or on supports."""
    try:
        from build123d import GeomType
        faces = [f for f in s.faces() if f.geom_type == GeomType.PLANE]
        if not faces:
            return []
        zmin = s.bounding_box().min.Z
        big = max(f.area for f in faces)
        bed = sum(f.area for f in faces if f.normal_at().Z < -0.999 and abs(f.center().Z - zmin) < 0.05)
    except Exception:  # noqa: BLE001 - meshes / odd shapes: no verdict
        return []
    if big > 0 and bed < BED_RATIO_WARN * big:
        return [f"{pid}: only {bed:.0f} mm2 sits on the bed against a {big:.0f} mm2 flat face elsewhere: it starts on a "
                f"narrow edge or on supports; put the largest flat face down if the loads allow (ENGINEERING.md s4)"]
    return []


def part_checks(item, printer: str, supports: str = "allowed") -> dict:
    spec = item.spec
    infill, walls = print_parameters(spec)
    shape = item.shape
    rot = spec.get("print_rot", [0, 0, 0])
    s = oriented(shape, rot)
    problems, warnings = [], []
    sol = geom.solids(s)
    if geom.kmesh(s) is not None:                       # fused Meshy part: the printed body is the merged mesh
        sol = [None] * getattr(s, "kerf_mesh_info", {}).get("bodies", 1)
    if len(sol) != 1:
        problems.append(f"{item.id} is {len(sol)} separate solids; a printed part must be one piece")
    if not s.is_valid:
        problems.append(f"{item.id}: geometry is invalid (self-intersecting or broken faces)")
    lo_, hi_ = geom.bbox(s)
    size = [float(x) for x in hi_ - lo_]
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
    lp, lw = layer_direction(item)
    problems += lp
    warnings += lw
    bw = bed_contact(item.id, s)
    warnings += bw
    vol = geom.volume(s)
    mat = spec.get("material", "PETG")
    rho = density(mat)
    km = geom.kmesh(s)
    area = float(sum(fc.area for fc in s.faces())) if km is None else float(__import__("trimesh").Trimesh(*km, process=False).area)
    shell = min(vol, area * 0.84) if km is not None else shell_volume(s, spec, vol)
    return {
        "ok": not problems, "problems": problems, "warnings": warnings, "min_wall_p02": None if p02 is None else round(p02, 3),
        "material": mat, "print_rot": rot, "size_mm": [round(x, 2) for x in size], "fits": fits,
        "volume_mm3": round(vol, 1), "mass_solid_g": round(vol / 1000 * rho, 1),
        "mass_est_g": round((shell + infill * max(vol - shell, 0)) / 1000 * rho, 1), "infill": infill,
        "walls": walls,
        "overhang_pct": round(oh_frac * 100, 2), "wall_p02_mm": None if p02 is None else round(p02, 2),
        "watertight": ms["watertight"], "solids": len(sol), "faces": len(s.faces()), "build_ms": item.build_ms,
    }


LAYER_WARN_NZ2 = 0.25  # warn when more than 25% of the load direction runs across layers (> 30 deg out of the bed plane)


def _axis_vec(a) -> np.ndarray:
    if isinstance(a, str):
        sgn = -1.0 if a.startswith("-") else 1.0
        k = a.lstrip("+-").lower()
        if k not in ("x", "y", "z"):
            raise ValueError(f"load_axis '{a}' must be x, y, z (optionally signed) or [x, y, z]")
        v = np.zeros(3)
        v["xyz".index(k)] = sgn
        return v
    v = np.array(a, dtype=float)
    if v.shape != (3,) or not np.linalg.norm(v):
        raise ValueError(f"load_axis {a} must be a non-zero [x, y, z]")
    return v / np.linalg.norm(v)


def layer_direction(item) -> tuple[list, list]:
    """Parts may declare `load_axis` in project.yaml: the direction (part frame) the main stress runs, e.g. the length
    of an arm in bending or the pull of a hook; a list of such directions is allowed. In the print orientation, layers
    lie in the bed plane, so stress along build Z pulls layers apart (ENGINEERING.md section 4). Warns when a load axis
    is more than 30 deg out of the bed plane and reports the blended strength (cos^2 rule, as cantilever_stress)."""
    la = item.spec.get("load_axis")
    if la is None:
        return [], []
    axes = [la] if isinstance(la, str) or (isinstance(la, (list, tuple)) and la and isinstance(la[0], (int, float))) else la
    rot = Rot(*item.spec.get("print_rot", [0, 0, 0]))
    problems, warnings = [], []
    mat = item.spec.get("material", "PETG")
    try:
        m = catalog.get(f"materials.{mat}")
        xy = catalog.num(m, "tensile_strength_xy_mpa", "tensile_strength_mpa", "tensile_strength_xy", "tensile_strength")
        z = catalog.num(m, "tensile_strength_z_mpa", "tensile_strength_z", default=xy * 0.5)
    except Exception:
        xy = z = None
    for a in axes:
        try:
            v = _axis_vec(a)
        except ValueError as e:
            problems.append(f"{item.id}: {e}")
            continue
        nz2 = float(geom.world_dir(rot, tuple(v))[2]) ** 2
        if nz2 > LAYER_WARN_NZ2:
            ang = float(np.degrees(np.arcsin(min(1.0, nz2 ** 0.5))))
            eff = "" if not xy else f"; {mat} strength along it ~{xy - (xy - z) * nz2:.0f} of {xy:.0f} MPa"
            warnings.append(f"{item.id}: main load axis {a} runs {ang:.0f} deg out of the layer plane in print orientation "
                            f"{list(item.spec.get('print_rot', [0, 0, 0]))} (across layers{eff}); reorient so it lies "
                            f"along the bed, or prove it with fea_static/cantilever_stress using direction z")
    return problems, warnings


LINE_W, SKIN_MM = 0.42, 0.84    # perimeter line width; top/bottom skin (~4 layers of 0.2 mm)


def shell_volume(s, spec, vol=None) -> float:
    """Solid-printed volume of a part in its PRINT orientation: faces that point up/down (within 45 deg of build Z) get
    the top/bottom skin, every other face `walls` perimeters of 0.42 mm. Capped at the part volume."""
    _, walls = print_parameters(spec)
    tb = side = 0.0
    for fc in s.faces():
        try:
            nz = abs(float(fc.normal_at().Z))
        except Exception:  # noqa: BLE001  (a face without a usable normal: count it as a side)
            nz = 0.0
        if nz > 0.7071:
            tb += fc.area
        else:
            side += fc.area
    vol = geom.volume(s) if vol is None else vol
    return min(vol, tb * SKIN_MM + side * walls * LINE_W)


def item_mass_g(item) -> float:
    """Mass used for statics: printed parts from geometry, purchased parts from the catalog."""
    if item.role == "printed":
        print_parameters(item.spec)       # even a cached answer must not hide invalid mutated inputs
        # every mass / CG / thrust / endurance requirement asks again; the answer depends on the geometry and the
        # spec only (not on where the part sits), so it is kept on the shape (copy-safe slot, geom._Memo)
        key = json.dumps(item.spec, sort_keys=True, default=str)
        hit = geom._memo_get(item.shape, "_kerf_mass")
        if hit is not None and hit[0] == key:
            return hit[1]
        g = _printed_mass_g(item)
        geom._memo_set(item.shape, "_kerf_mass", (key, g))
        return g
    if item.role == "purchased":
        return _purchased_mass_g(item) + float(getattr(item, "carried_g", 0.0) or 0.0)
    return 0.0


def _printed_mass_g(item) -> float:
    """Printed mass from geometry: perimeter shell at full density + the rest at the part's infill."""
    infill, _ = print_parameters(item.spec)
    vol = geom.volume(item.shape)
    rho = density(item.spec.get("material", "PETG"))
    if geom.kmesh(item.shape) is not None:
        area = float(sum(fc.area for fc in item.shape.faces()))
        shell = min(vol, area * 0.84)
    else:
        shell = shell_volume(oriented(item.shape, item.spec.get("print_rot", [0, 0, 0])), item.spec, vol)
    return (shell + infill * max(vol - shell, 0)) / 1000 * rho


def _purchased_mass_g(item) -> float:
    """Catalog (or yaml mass_g) mass of one purchased item."""
    override = explicit_mass_g(item.spec)
    if override is not None:
        return override
    try:
        e = catalog.get(item.spec["catalog"])
    except Exception:
        return 0.0
    try:
        return catalog.num(e, "weight_g", "mass_g", "weight")
    except Exception:
        pass
    # rods / tubes: catalog density (g/cm3) x cross-section x the item's length
    L = item.spec.get("length", e.get("length"))
    if isinstance(L, str) and e.get("density") and item.shape is not None:   # a param expression: the built tube
        return item.shape.volume / 1000 * float(e["density"])
    if e.get("density") and e.get("od") and L:
        od, i_d = float(e["od"]), float(e.get("id") or 0.0)
        return math.pi / 4 * (od ** 2 - i_d ** 2) * float(L) / 1000 * float(e["density"])
    return 0.0
