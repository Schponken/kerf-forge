"""Infill-aware strength: the FEA treats a printed part as solid plastic, but only its wall loops are solid; inside
them the slicer prints a lattice at the part's `infill` fraction.

A bending-dominated cellular solid fails at sigma = 0.3 * (relative density)^1.5 * the solid's strength (Ashby, "The
properties of foams and lattices", Phil. Trans. R. Soc. A 364 (2006) 15-30, eq. 3.5; the stretch-dominated bound
1/3 * rho is the upper limit, eq. 5.2). Infill under mixed loads is taken as bending-dominated (the lower, safer value).

The check: every FEA element whose centre is deeper than the wall shell (walls x 0.42 mm line, Bambu Studio's default
for a 0.4 nozzle) is held to the lattice strength / sf instead of the solid one. The solid-part FEA overstates the
inside's stress a little (soft infill sheds load to the walls), so a miss is a warning that names where to add a
100 %-infill modifier or more walls, not a failure. A modifier with a `box: [[x0, y0, z0], [x1, y1, z1]]` (part frame,
mm) and its own `infill` counts as that infill inside the box.
"""
from __future__ import annotations

import numpy as np

LINE_MM = 0.42          # Bambu Studio default line width, 0.4 mm nozzle (https://forum.bambulab.com/t/default-line-width-of-0-42/20400)
ASHBY_C = 0.3           # Ashby 2006 eq. 3.5, bending-dominated


def lattice_factor(infill: float) -> float:
    """Strength of the infill lattice as a fraction of solid plastic."""
    rho = min(max(float(infill), 0.0), 1.0)
    return 1.0 if rho >= 0.999 else ASHBY_C * rho ** 1.5


def depth_below_surface(shape, pts: np.ndarray, n: int = 30000) -> np.ndarray:
    """Distance (mm) from each point to the nearest point of the part's surface (dense surface samples)."""
    import trimesh
    from scipy.spatial import cKDTree
    from . import geom
    v, f = geom.mesh(shape, tol=0.1, ang=0.3)
    m = trimesh.Trimesh(np.asarray(v), np.asarray(f), process=False)
    samples, _ = trimesh.sample.sample_surface_even(m, n, seed=1) if len(f) else (np.zeros((1, 3)), None)
    samples = np.vstack([samples, np.asarray(v)])
    return cKDTree(samples).query(np.asarray(pts, float))[0]


def _local_infill(spec: dict, pts: np.ndarray) -> np.ndarray:
    infill = np.full(len(pts), float(spec.get("infill", 0.25)))
    for mod in spec.get("modifiers") or []:
        box = mod.get("box")
        if box and "infill" in mod:
            lo, hi = np.minimum(box[0], box[1]), np.maximum(box[0], box[1])
            inside = np.all((pts >= lo) & (pts <= hi), axis=1)
            infill[inside] = float(mod["infill"])
    return infill


def check(item, cases: list[dict]) -> dict | None:
    """{infill, shell_mm, use, share, at, warning} for one part from its FEA stress fields (cases: [{field, allow}]);
    use = worst interior stress / lattice allowable (99th percentile by volume); None when the part prints solid."""
    spec, shape = item.spec, item.shape
    if float(spec.get("infill", 0.25)) >= 0.999 or shape is None:
        return None
    shell = int(spec.get("walls", 2)) * LINE_MM
    from build123d import Location
    part = shape.located(Location())
    best = None
    for c in cases:
        f = c.get("field") or {}
        if not len(f.get("vm", [])):
            continue
        pts, vol, vm = np.asarray(f["c"], float), np.asarray(f["vol"], float), np.asarray(f["vm"], float)
        deep = depth_below_surface(part, pts) > shell
        if not deep.any():
            continue
        lf = np.array([lattice_factor(x) for x in _local_infill(spec, pts[deep])])
        use = vm[deep] / (float(c["allow"]) * lf)
        order = np.argsort(use)
        cw = np.cumsum(vol[deep][order]) / vol[deep].sum()
        u99 = float(use[order][min(int(np.searchsorted(cw, 0.99)), len(order) - 1)])
        over = float(vol[deep][use > 1.0].sum() / vol.sum())
        at = pts[deep][int(np.argmax(use))].round(1).tolist()
        if best is None or u99 > best["use"]:
            best = {"use": round(u99, 2), "share": round(over, 3), "at": at}
    if best is None:
        return None
    inf = float(spec.get("infill", 0.25))
    out = {"infill": inf, "shell_mm": round(shell, 2), "lattice_factor": round(lattice_factor(inf), 3), **best, "warning": ""}
    if best["use"] > 1.0:
        out["warning"] = (f"{item.id}: printed at {inf * 100:.0f} % infill, its inside is a lattice about "
                          f"{lattice_factor(inf) * 100:.0f} % as strong as solid plastic (Ashby 2006), but the stress there reaches "
                          f"{best['use']:.1f}x that ({best['share'] * 100:.0f} % of the part's volume, deeper than its "
                          f"{shell:.2f} mm walls, worst near {best['at']}): add a 100 % infill modifier with a box round that "
                          f"zone, more wall loops, or a higher infill")
    return out
