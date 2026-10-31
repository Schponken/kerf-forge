"""Balance requirement checks: centre of gravity (and, later, tip-over). Registered into requirements.REGISTRY.

Masses come from checks.item_mass_g (printed: geometry x material x infill model; purchased: catalog/spec mass).
Each item's mass acts at its solid centroid. For a printed part with partial infill the true CG sits slightly toward
its thicker shell walls; for compact parts that error is well under a millimetre, so keep a margin on tight limits.
"""
from __future__ import annotations

import numpy as np

from . import assembly as A
from .checks import item_mass_g
from .requirements import _com, _joint_world, check


def wiring_masses(proj):
    """[(mass g, centroid xyz)] for every declared run that is not part of an item (`supplied`), at the CURRENT solved
    pose: the run's mass sits at the length-weighted centroid of its route polyline (from, route points, to)."""
    from .electrical import _point, wire_mass_g
    out = []
    for w in proj.data.get("wiring") or []:
        if w.get("supplied"):
            continue
        m = wire_mass_g(w)
        if m <= 0:
            continue
        pts = [_point(proj, w["from"], True)] + [_point(proj, r) for r in (w.get("route") or [])] + [_point(proj, w["to"], True)]
        segs = [(np.linalg.norm(b - a), (a + b) / 2) for a, b in zip(pts, pts[1:])]
        L = sum(l for l, _ in segs)
        c = sum(l * mid for l, mid in segs) / L if L > 0 else pts[0]
        out.append((m, np.asarray(c, dtype=float)))
    return out


def assembly_cg(proj, include=None, payload_g=0.0, payload_at=None):
    """(cg xyz in mm, total mass g) of the solved assembly: all non-keepout items plus every declared wiring run (the
    same all-up mass mass_max and thrust_to_weight use), or only `include`, plus a point payload at a joint origin."""
    ids = include or [i for i, it in proj.items.items() if it.role != "keepout" and it.shape is not None]
    ms, cs = [], []
    for i in ids:
        m = item_mass_g(proj.items[i])
        if m > 0:
            ms.append(m)
            cs.append(_com(proj.items[i]))
    if include is None:
        for m, c in wiring_masses(proj):
            ms.append(m)
            cs.append(c)
    if payload_g and payload_at:
        ms.append(float(payload_g))
        cs.append(_joint_world(proj, payload_at)[0])
    M = float(sum(ms))
    if M <= 0:
        raise ValueError("cg: no mass in the selected items")
    return np.sum(np.array(cs) * np.array(ms)[:, None], axis=0) / M, M


def _ref_frame(proj, ref=None, point=None, axis=None):
    if (ref is None) == (point is None):
        raise ValueError("cg: give exactly one of ref (item.joint) or point [x, y, z]")
    o = _joint_world(proj, ref)[0] if ref else np.array(point, dtype=float)
    u = np.array(axis if axis is not None else (0, 0, 1), dtype=float)
    return o, u / np.linalg.norm(u)


@check("cg")
def cg(proj, asm, ref=None, point=None, axis=None, max_lateral_mm=None, min_along_mm=None, max_along_mm=None,
       include=None, payload_g=0.0, payload_at=None, poses=None):
    """Assembled centre of gravity relative to a reference line: the line through `ref` (a joint origin, e.g.
    base.yaw) or `point`, along `axis` (world, default vertical [0, 0, 1]).
    lateral = distance of the CG from that line (e.g. how far a drone's CG sits from its thrust centre);
    along = signed height of the CG along the axis above the reference (e.g. a robot base's CG height).
    Evaluated at the home pose and every pose in `poses` (list of {joint: value}); the worst case is reported."""
    if max_lateral_mm is None and min_along_mm is None and max_along_mm is None:
        raise ValueError("cg: set max_lateral_mm and/or min_along_mm / max_along_mm")
    worst_lat, along_lo, along_hi, worst_pose, cg_home, mass = 0.0, np.inf, -np.inf, {}, None, 0.0
    for pose in [{}] + list(poses or []):
        A.solve(asm, pose)
        c, mass = assembly_cg(proj, include, payload_g, payload_at)
        o, u = _ref_frame(proj, ref, point, axis)
        v = c - o
        along = float(np.dot(v, u))
        lat = float(np.linalg.norm(v - along * u))
        if cg_home is None:
            cg_home = c
        if lat >= worst_lat:
            worst_lat, worst_pose = lat, pose
        along_lo, along_hi = min(along_lo, along), max(along_hi, along)
    A.solve(asm)
    ok = (max_lateral_mm is None or worst_lat <= max_lateral_mm + 1e-9) and \
         (min_along_mm is None or along_lo >= min_along_mm - 1e-9) and \
         (max_along_mm is None or along_hi <= max_along_mm + 1e-9)
    return {"ok": ok, "value": {"lateral_mm": round(worst_lat, 2), "along_mm": [round(along_lo, 2), round(along_hi, 2)]},
            "limit": {"max_lateral_mm": max_lateral_mm, "along_mm": [min_along_mm, max_along_mm]},
            "detail": f"CG of {mass:.0f} g vs line through {ref or point} along {list(axis or (0, 0, 1))}; home CG "
                      f"{np.round(cg_home, 2).tolist()} mm; worst lateral at {worst_pose or 'home'}"}
