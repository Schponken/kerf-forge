"""Pinned joints (printed hinges, dowels, screw pivots): prove the holes line up and the pin can do its job.

Every part a pin passes through cuts its hole with `iface.pin_hole(...)` under the same group name. With the assembly
solved at home, `check(asm)` proves for each group:
- all holes are coaxial (axes parallel within ANG_TOL, centres on one line within OFF_TOL), same pin, >= 2 parts;
- some part holds the pin (a `press`, `heatset` or `tap` hole); parts with only `free` holes turn on it;
- every moving joint that separates parts of the group turns ABOUT the pin axis (revolute) or slides ALONG it
  (linear), and the pin is fixed on one side of that joint only (fixed on both sides = the joint is locked);
- a stocked pin length (catalog `lengths`, or standard screw lengths for a screw pivot) fits inside the outer faces and,
  at some position, reaches every hole by at least min(hole length, 1.5 d); a screw pivot's head sits on a free hole and its thread
  reaches the insert/pilot by the screw's minimum engagement.
"""
from __future__ import annotations

import numpy as np

from . import geom
from .iface import pin_dims, screw_spec

ANG_TOL_DEG = 0.5
OFF_TOL = 0.05  # mm; a pin binds long before a fastener-style 0.15 mm offset
FIXED = ("press", "heatset", "tap")


def _collect(asm) -> dict:
    groups: dict[str, list] = {}
    for iid, it in asm.proj.items.items():
        if it.shape is None:
            continue
        for s in getattr(it.shape, "kerf_pins", []):
            w = it.shape.location * s.loc
            groups.setdefault(s.group, []).append((iid, s, geom.world_point(w, (0, 0, 0)), geom.world_dir(w, (0, 0, 1))))
    return groups


def _line_off(o_ref, u, p) -> float:
    v = p - o_ref
    return float(np.linalg.norm(v - np.dot(v, u) * u))


def _min_cover(s, d: float) -> float:
    if s.fit == "heatset":
        sp = screw_spec(s.pin)
        return min((sp.get("insert_len") or s.depth) * 0.7, 1.5 * d)
    if s.fit == "tap":
        return 1.5 * d
    return min(s.depth, 1.5 * d)


def check(asm) -> tuple[list, list, list]:
    """Returns (pins, problems, warnings). Call with the assembly solved at home."""
    out, problems, warnings = [], [], []
    for g, sites in sorted(_collect(asm).items()):
        names = sorted({s.pin for _, s, _, _ in sites})
        items = sorted({i for i, _, _, _ in sites})
        if len(names) > 1:
            problems.append(f"pin group '{g}': holes are cut for different pins {names}")
            continue
        if len(items) < 2:
            problems.append(f"pin group '{g}': only {items} has holes; a pin must join at least two parts")
            continue
        pin = names[0]
        pd = pin_dims(pin)
        d = pd["d"]
        _, _, o0, u = sites[0]
        bad = False
        for iid, s, o, z in sites:
            ang = np.degrees(np.arccos(np.clip(abs(np.dot(z, u)), -1, 1)))
            off = _line_off(o0, u, o)
            if ang > ANG_TOL_DEG or off > OFF_TOL:
                problems.append(f"pin group '{g}': hole in {iid} at {np.round(o, 2).tolist()} is off the pin axis "
                                f"({off:.2f} mm, {ang:.1f} deg); limit {OFF_TOL} mm / {ANG_TOL_DEG} deg")
                bad = True
        # a part holds the pin if any of its holes does (its other holes are just clearance in the same rigid part)
        fixed = sorted({i for i, s, _, _ in sites if s.fit in FIXED})
        free = sorted(set(items) - set(fixed))
        if not fixed:
            problems.append(f"pin group '{g}': the pin is free in every part ({items}); press it or thread it into one side")
            bad = True
        # moving joints that split the group
        for e in asm.movable:
            sub = asm.subtree(e.child)
            inside = {i for i in items if i in sub}
            if not inside or inside == set(items):
                continue
            pj = asm.proj.items[e.parent].shape.joints[e.pjoint]
            jo = geom.world_point(pj.location, (0, 0, 0))
            jd = geom.world_dir(pj.location, (0, 0, 1))
            ang = np.degrees(np.arccos(np.clip(abs(np.dot(jd, u)), -1, 1)))
            if e.kind == "revolute" and (ang > ANG_TOL_DEG or _line_off(o0, u, jo) > OFF_TOL):
                problems.append(f"pin group '{g}': joint '{e.name}' turns about an axis {_line_off(o0, u, jo):.2f} mm / "
                                f"{ang:.1f} deg away from the pin, so the pin would bind")
                bad = True
            if e.kind == "linear" and ang > ANG_TOL_DEG:
                problems.append(f"pin group '{g}': joint '{e.name}' slides across the pin ({ang:.1f} deg off its axis)")
                bad = True
            if any(i in inside for i in fixed) and any(i not in inside for i in fixed):
                problems.append(f"pin group '{g}': the pin is fixed in parts on both sides of moving joint '{e.name}' "
                                f"({fixed}), which locks the joint; make one side free")
                bad = True
        # pin length
        iv = []
        for iid, s, o, z in sites:
            t0 = float(np.dot(o - o0, u))
            t1 = t0 - s.depth * float(np.sign(np.dot(z, u)))
            iv.append((min(t0, t1), max(t0, t1), iid, s))
        lo, hi = min(a for a, _, _, _ in iv), max(b for _, b, _, _ in iv)
        span = hi - lo

        def covers(a0, a1):
            return all(min(b, a1) - max(a, a0) >= _min_cover(s, d) - 1e-3 for a, b, _, s in iv)

        length, head_end = None, None
        if pd["screw"]:
            fx = [x for x in iv if x[3].fit in FIXED]
            ends = []
            if fx and min(a for a, _, _, _ in fx) <= lo + 1e-3:
                ends.append(("hi", hi))  # thread at the low end, head on the high end
            if fx and max(b for _, b, _, _ in fx) >= hi - 1e-3:
                ends.append(("lo", lo))
            if fx and not ends:
                problems.append(f"pin group '{g}': the screw's threaded hole must be at one end of the pin line")
                bad = True
            for tag, end in ends:
                head = [x for x in iv if abs((x[1] if tag == "hi" else x[0]) - end) < 1e-3]
                if any(x[3].fit in FIXED for x in head):
                    continue
                for L in sorted(pd["lengths"], reverse=True):
                    a0, a1 = (end - L, end) if tag == "hi" else (end, end + L)
                    if L <= span + 1e-3 and covers(a0, a1):
                        length, head_end = L, tag
                        break
                if length:
                    break
            if length:
                warnings.append(f"pin group '{g}': {pin} x {length:g} screw pivot - the head clamps the moving part; "
                                f"use medium threadlocker and back the screw off ~1/8 turn, or use a shoulder screw")
        else:
            for L in sorted(pd["lengths"], reverse=True):
                if L > span + 1e-3:
                    continue
                if any(covers(a, a + L) for a in [*np.arange(lo, hi - L, 0.1), hi - L]):
                    length = L
                    break
        if length is None and not bad:
            problems.append(f"pin group '{g}': no stocked {pin} length fits inside the {span:.1f} mm span and reaches every "
                            f"hole by min(hole, 1.5 d) (lengths {pd['lengths']}); make the span equal a stocked length")
        out.append({"group": g, "pin": pin, "d_mm": d, "length_mm": length, "span_mm": round(span, 2),
                    "fixed_in": fixed, "free_in": free, "screw_pivot": pd["screw"],
                    "fixed_fit": sorted({s.fit for _, s, _, _ in sites if s.fit in FIXED})})
    return out, problems, warnings
