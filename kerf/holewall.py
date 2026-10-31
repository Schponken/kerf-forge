"""Material around every fastener hole of a printed part (docs/ENGINEERING.md sections 5 and 7).

Each fastener site (iface.bolt_pattern / servo_mount / stack_mount / ...) records its hole axis and depth. Here a ring
of points around that axis is tested against the part's solid at several depths along the hole:
- wall ring at (hole radius + minimum wall): a heat-set insert needs the catalog `insert_wall` (fdm_holes
  heatset_min_wall), any other hole 0.8 mm (section 5: the check fails below 0.8 mm). Less than 95 % of that ring in
  material means the hole breaks out of the part or leaves a sliver: a PROBLEM (an insert there cannot be seated).
- edge ring at 1.5 x screw diameter from the hole centre (section 7 edge distance): less than 90 % in material is a
  WARNING naming how close the nearest free edge is.
Holes are judged where the screw actually works: a female hole over its engaged depth, a male hole over its grip;
levels with no material at all are past the far face of a through hole and are left out.
"""
from __future__ import annotations

import numpy as np

from . import geom

WALL_SOLID_MIN = 0.95
EDGE_SOLID_MIN = 0.90
N_THETA = 24
MIN_WALL_MM = 0.8


def _frame(loc):
    o = geom.world_point(loc, (0, 0, 0))
    return o, geom.world_dir(loc, (1, 0, 0)), geom.world_dir(loc, (0, 1, 0)), geom.world_dir(loc, (0, 0, 1))


def ring_points(loc, r: float, depths) -> np.ndarray:
    """Points on circles of radius r around the site axis, at each depth into the material (-Z of loc)."""
    o, ex, ey, ez = _frame(loc)
    th = np.linspace(0, 2 * np.pi, N_THETA, endpoint=False)
    pts = [o + r * np.cos(t) * ex + r * np.sin(t) * ey - z * ez for z in depths for t in th]
    return np.array(pts)


def _hole_r(site, sp) -> tuple[float, float]:
    """(hole radius, required wall) for a site."""
    if site.kind == "heatset":
        return sp["insert_hole"] / 2, float(sp.get("insert_wall") or MIN_WALL_MM)
    if site.kind == "tap":
        return sp["tap"] / 2, MIN_WALL_MM
    if site.kind == "nut_trap":
        return sp["nut_pocket_af"] / 2 / np.cos(np.pi / 6), MIN_WALL_MM
    return sp["clearance"] / 2, MIN_WALL_MM


def _depth(site) -> float:
    return float(site.engage if site.role == "female" else site.grip)


def check(item) -> tuple[list, list, list]:
    """(problems, warnings, per-site results) for one printed item, in its part frame."""
    from .iface import screw_spec
    import trimesh
    sites = list(getattr(item.shape, "kerf_sites", []) or [])
    if not sites:
        return [], [], []
    v, f = geom.mesh(item.shape)
    m = trimesh.Trimesh(v, f, process=True)
    mat = item.spec.get("material")
    problems, res = [], []
    near: dict = {}
    for s in sites:
        try:
            sp = screw_spec(s.screw, mat)
        except Exception:  # noqa: BLE001  (a screw size without fdm hole data: nothing to judge)
            continue
        depth = _depth(s)
        if depth <= 0.6:
            continue
        zs = np.linspace(0.3, depth - 0.3, 4)
        r_hole, wall = _hole_r(s, sp)
        wall_pts = ring_points(s.loc, r_hole + wall, zs)
        edge_pts = ring_points(s.loc, max(1.5 * sp["d"], r_hole + wall), zs)
        win = m.contains(wall_pts).reshape(len(zs), N_THETA)
        ein = m.contains(edge_pts).reshape(len(zs), N_THETA)
        keep = win.any(axis=1)              # a level with no material at all is past the far face (through hole)
        if not keep.any():
            continue
        w_frac = float(win[keep].mean())
        e_frac = float(ein[keep].mean())
        at = np.round(geom.world_point(s.loc, (0, 0, 0)), 1).tolist()
        r = {"group": s.group, "screw": s.screw, "kind": s.kind, "at": at, "wall_frac": round(w_frac, 2),
             "edge_frac": round(e_frac, 2)}
        res.append(r)
        if w_frac < WALL_SOLID_MIN:
            problems.append(f"{item.id}: {s.screw} {s.kind} hole (group '{s.group}') at {at} has less than {wall:.1f} mm "
                            f"of wall around it ({w_frac * 100:.0f} % of a ring at r {r_hole + wall:.1f} mm is material): it "
                            f"breaks out of the part or leaves a sliver; move it in from the edge or grow the material")
        elif e_frac < EDGE_SOLID_MIN:
            near.setdefault((s.group, s.screw, s.kind, 1.5 * sp["d"]), []).append((at, e_frac))
    warnings = [f"{item.id}: {len(v)} {scr} {kind} hole(s) of group '{g}' sit closer than 1.5 x d ({e:.1f} mm) to a free "
                f"edge (worst {min(x[1] for x in v) * 100:.0f} % of that ring is material, at {min(v, key=lambda x: x[1])[0]}); "
                f"ENGINEERING.md s7 edge distance: fine when the purchased part's hole pattern forces it, say so in DESIGN.md"
                for (g, scr, kind, e), v in near.items()]
    return problems, warnings, res
