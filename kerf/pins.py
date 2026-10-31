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


def lock_advice(fixed_fit) -> str:
    """How to stop a screw pivot backing out (ENG-16): anaerobic threadlocker stress-cracks PETG/PLA/ABS, so it goes only
    on a screw tip that sits in a brass insert; a screw tapped into plastic gets a pre-applied nylon-patch locking screw."""
    if "heatset" in str(fixed_fit):
        return ("a small drop of medium threadlocker on the screw TIP only (it sits in the brass insert; keep it off the "
                "printed bores: anaerobic threadlocker stress-cracks printed plastic)")
    return ("no threadlocker on printed threads (it stress-cracks the plastic): use a nylon-patch (pre-applied locking) "
            "screw, or a heat-set insert")


PIN_SPAN_SLACK = 1.0  # mm; a dowel this much shorter than its span gets a warning (ENG-13)
SHOULDER_PLAY = 0.5  # mm; most axial play a shoulder-screw pivot may leave between the head and the moving part


def _min_cover(s, d: float) -> float:
    if s.fit == "heatset":
        sp = screw_spec(pin_dims(s.pin).get("thread", s.pin))
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
        if pd.get("shoulder"):
            length = _shoulder(g, pin, pd, iv, lo, hi, problems)
            if length is None:
                bad = True
        elif pd["screw"]:
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
                hp = sorted({x[2] for x in iv if abs((x[1] if head_end == "hi" else x[0]) - (hi if head_end == "hi" else lo)) < 1e-3})
                warnings.append(f"pin group '{g}': {pin} x {length:g} screw pivot - tightening the screw clamps the stack "
                                f"(head on {', '.join(hp)}) and stops the joint turning; back the screw off ~1/8 turn and lock it "
                                f"({lock_advice({x.fit for _, x, _, _ in sites if x.fit in FIXED})}), or use a shoulder screw")
        else:
            for L in sorted(pd["lengths"], reverse=True):
                if L > span + 1e-3:
                    continue
                if any(covers(a, a + L) for a in [*np.arange(lo, hi - L, 0.1), hi - L]):
                    length = L
                    break
            if length is not None and span - length > PIN_SPAN_SLACK:      # ENG-13: docs/ENGINEERING.md s8
                warnings.append(f"pin group '{g}': the {length:g} mm {pin} is {span - length:.1f} mm shorter than the "
                                f"{span:.1f} mm span it sits in (outer face to outer face): it can wander and an end "
                                f"hole is only partly filled; make the span equal a stocked length (ENGINEERING.md s8) "
                                f"or say in DESIGN.md what retains it")
        if length is None and not bad:
            need = ", ".join(f"{iid} {b - a:.1f} mm hole needs {_min_cover(st, d):.1f}" for a, b, iid, st in iv)
            rule = ("a screw pivot runs from its head end to the threaded hole, which must be the far end of the line; "
                    if pd["screw"] and not pd.get("shoulder") else "")
            problems.append(f"pin group '{g}': no stocked {pin} length fits inside the {span:.1f} mm span and reaches every "
                            f"hole by min(hole, 1.5 d) ({need}; stocked lengths {pd['lengths']}). {rule}"
                            f"Make the span (outer face to outer face along the pin) equal a stocked length")
        out.append({"group": g, "pin": pin, "d_mm": d, "length_mm": length, "span_mm": round(span, 2),
                    "fixed_in": fixed, "free_in": free, "screw_pivot": pd["screw"], "shoulder": bool(pd.get("shoulder")),
                    "fixed_fit": sorted({s.fit for _, s, _, _ in sites if s.fit in FIXED})})
    return out, problems, warnings


def _shoulder(g, pin, pd, iv, lo, hi, problems):
    """Shoulder-screw pivot: the head sits on the outer face of the free holes, the shoulder runs through them and
    bottoms on the face of the threaded (fixed) hole, the thread goes into that hole. Picks the shortest stocked
    shoulder length that does not clamp the moving parts (shoulder >= head face to fixed face) with at most
    SHOULDER_PLAY of axial play, and checks the thread fits and engages the fixed hole. Returns the length or None."""
    fx = [x for x in iv if x[3].fit in FIXED]
    fr = [x for x in iv if x[3].fit not in FIXED]
    if len(fx) != 1 or not fr:
        problems.append(f"pin group '{g}': a shoulder screw needs exactly one threaded hole and at least one free hole")
        return None
    a, b, iid, s = fx[0]
    if a <= min(x[0] for x in fr) - 1e-3:      # thread at the low end: head on the high end
        face, head, depth = b, max(x[1] for x in fr), b - a
    elif b >= max(x[1] for x in fr) + 1e-3:
        face, head, depth = a, min(x[0] for x in fr), b - a
    else:
        problems.append(f"pin group '{g}': the shoulder screw's threaded hole in {iid} must be at one end of the pin line")
        return None
    need = abs(head - face)
    fits = [L for L in sorted(pd["lengths"]) if need - 1e-3 <= L <= need + SHOULDER_PLAY]
    if not fits:
        problems.append(f"pin group '{g}': {pin} needs a shoulder of {need:.2f}-{need + SHOULDER_PLAY:.2f} mm (head face to "
                        f"the threaded part's face) but is stocked in {pd['lengths']}; change the knuckle widths")
        return None
    cover = _min_cover(s, pd["d"])
    if pd["thread_len"] > depth + 0.5 or min(pd["thread_len"], depth) < cover - 1e-3:
        problems.append(f"pin group '{g}': {pin} thread {pd['thread_len']:g} mm does not fit / engage the {depth:.1f} mm "
                        f"threaded hole in {iid} (needs >= {cover:.1f} mm)")
        return None
    return fits[0]
