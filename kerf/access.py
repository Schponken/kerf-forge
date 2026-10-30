"""Assembly-access checks: can the screws be driven, and can parts be put in place?

(a) hex-key reach: from the head of every male screw site, a straight hex key (across-corners envelope, L-key long-arm
    reach from catalog tools.hex_key) along the screw axis must clear every item. If it doesn't but a ball-end key at up
    to 25 deg does, that's a warning (buy a ball-end driver); if neither, it's a problem.
(b) insertion paths: an item declared with `insert: {direction: [x, y, z], distance: mm}` (direction = the way it moves
    as it goes IN, in the item's own frame) is slid in from `distance` away and must not hit anything on the way
    (its own subtree moves with it; allow_overlap allowances still apply).
"""
from __future__ import annotations

import math

import numpy as np
from build123d import Plane, Pos, Solid, Vector

from . import assembly as A, catalog, geom
from .iface import screw_spec

HEAD_ON_SURFACE = {"clearance", "counterbore"}   # site origin = under the head; countersink heads sit flush


def key_spec(screw: str, kind: str) -> dict:
    hk = catalog.get("tools.hex_key")
    table = hk["socket_s_countersunk"] if kind == "countersink" and screw in hk["socket_s_countersunk"] else hk["socket_s_shcs"]
    if screw not in table:
        raise ValueError(f"no hex key size for {screw} in catalog tools.hex_key")
    s = float(table[screw])
    reach = float(hk["long_arm_mm"][f"{s:g}"])
    return {"s": s, "r": s / math.cos(math.radians(30)) / 2, "reach": reach, "ball_deg": float(hk["ball_end_max_deg"])}


def _rod(o, d, r, L):
    return Solid.make_cylinder(r, L, Plane(origin=Vector(*o), z_dir=Vector(*d)))


def _blocked(rod, shapes):
    return [i for i, s in shapes if geom.overlap(s, rod) > geom.OVERLAP_TOL_MM3]


def hex_key_reach(asm, n_azimuth: int = 12) -> tuple[list, list, list]:
    """Returns (per-screw results, problems, warnings) at the current pose."""
    items = asm.proj.items
    shapes = [(i, it.shape) for i, it in items.items() if it.shape is not None and it.role != "keepout"]
    results, problems, warnings = [], [], []
    for iid, it in items.items():
        if it.shape is None:
            continue
        for s in getattr(it.shape, "kerf_sites", []):
            if s.role != "male":
                continue
            w = it.shape.location * s.loc
            o = geom.world_point(w, (0, 0, 0))
            z = geom.world_dir(w, (0, 0, 1))
            k = key_spec(s.screw, s.kind)
            top = o + z * (screw_spec(s.screw)["head_h"] if s.kind in HEAD_ON_SURFACE else 0.0)
            start = top + z * 0.05           # the key tip sits in the socket; start just above the head
            hits = _blocked(_rod(start, z, k["r"], k["reach"]), shapes)
            res = {"item": iid, "group": s.group, "screw": s.screw, "key_mm": k["s"], "at": np.round(top, 2).tolist(),
                   "straight": not hits, "blocked_by": hits}
            if hits:
                a = math.radians(k["ball_deg"])
                ex = np.cross(z, [1.0, 0, 0] if abs(z[0]) < 0.9 else [0, 1.0, 0])
                ex /= np.linalg.norm(ex)
                ey = np.cross(z, ex)
                ok_dir = None
                for t in np.linspace(0, 2 * math.pi, n_azimuth, endpoint=False):
                    d = math.cos(a) * z + math.sin(a) * (math.cos(t) * ex + math.sin(t) * ey)
                    # the ball end sits in the socket, so the tilted shank starts one key radius up the axis
                    if not _blocked(_rod(start + z * k["r"], d, k["r"], k["reach"]), shapes):
                        ok_dir = d
                        break
                res["ball_end"] = ok_dir is not None
                where = f"{s.screw} screw in {iid} (group '{s.group}') at {res['at']}"
                if ok_dir is not None:
                    warnings.append(f"{where}: a straight {k['s']:g} mm hex key hits {hits}; it needs a ball-end key "
                                    f"(up to {k['ball_deg']:g} deg off axis)")
                else:
                    problems.append(f"{where}: no {k['s']:g} mm hex key can reach the head (straight hits {hits}, "
                                    f"ball-end at {k['ball_deg']:g} deg also blocked)")
            results.append(res)
    return results, problems, warnings


def insertion_paths(asm, step_mm: float = 1.0) -> tuple[list, list]:
    """Slide every item with an `insert:` spec into its seat; returns (results, problems)."""
    items = asm.proj.items
    allow = A._allowed(asm)
    results, problems = [], []
    for iid, it in items.items():
        spec = it.spec.get("insert")
        if not spec or it.shape is None:
            continue
        d_loc = np.asarray(spec["direction"], float)
        d_loc /= np.linalg.norm(d_loc)
        dist = float(spec["distance"])
        moving = sorted(asm.subtree(iid))
        homes = {m: items[m].shape.location for m in moving}
        d = geom.world_dir(items[iid].shape.location, d_loc)
        others = [i for i, o in items.items() if o.shape is not None and o.role != "keepout" and i not in moving]
        n = max(8, math.ceil(dist / step_mm))
        hits = []
        try:
            for back in np.linspace(dist, 0, n, endpoint=False):
                off = Pos(*(-d * back))
                for m in moving:
                    items[m].shape.location = off * homes[m]
                for m in moving:
                    if items[m].role == "keepout":
                        continue
                    for o in others:
                        lim = allow.get(frozenset((m, o)), (0.0, ""))[0]
                        v = geom.overlap(items[m].shape, items[o].shape)
                        if v > max(lim, geom.OVERLAP_TOL_MM3):
                            hits.append({"a": m, "b": o, "volume_mm3": round(v, 3), "mm_from_seat": round(float(back), 2)})
        finally:
            for m in moving:
                items[m].shape.location = homes[m]
        results.append({"item": iid, "direction": d.round(4).tolist(), "distance_mm": dist, "clear": not hits,
                        "collisions": hits[:12]})
        if hits:
            h = max(hits, key=lambda h: h["mm_from_seat"])
            problems.append(f"{iid} cannot be inserted along {np.round(d, 3).tolist()}: {h['a']} hits {h['b']} "
                            f"({h['volume_mm3']} mm3) {h['mm_from_seat']} mm before it is seated")
    return results, problems
