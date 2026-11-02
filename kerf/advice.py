"""Specific advice for a failed requirement: what to change, by how much, and the alternatives, worked out from the
check's own numbers and settings (not one sentence for every miss).

advise(row, req, proj) -> list of plain sentences, best first. The sizing rules are the textbook first-order ones and
say so: bending stress in a rectangular section goes as 1/(b h^2) and its stiffness as b h^3 (beam theory), a beam's
natural frequency as sqrt(k / m), stall speed as sqrt(W / S), Lewis tooth stress as 1/(face width x module), a snap
hook's strain as t y / L^2 and a living hinge's as t theta / (2 L), a thin tube's bending stress as 1 / (d^2 t). They
give the size of the change to try first; the check then decides.
"""
from __future__ import annotations

import math

from . import catalog

STRESS = {"fea_static", "impact_fea", "stop_impact", "cantilever_stress", "creep_limit", "drop_impact"}


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _pct(f: float) -> str:
    return f"{(f - 1) * 100:.0f} %" if f >= 1 else f"{(1 - f) * 100:.0f} %"


def _materials() -> dict:
    try:
        return catalog.get("materials")
    except Exception:  # noqa: BLE001
        return {}


def _stronger_materials(current: str, need_mpa: float, direction: str, now_mpa: float) -> list[str]:
    from .requirements import _strength
    out = []
    for name in _materials():
        if name == current or name == "TPU":
            continue
        try:
            s = _strength(name, "z" if direction == "z" else "xy")
        except Exception:  # noqa: BLE001
            continue
        if s >= need_mpa:
            out.append((s, name))
    return [f"{n} ({s:g} MPa vs {now_mpa:g})" for s, n in sorted(out)[:3]]


def _stress(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or lim <= 0:
        return []
    ratio = v / lim
    part = req.get("part") or req.get("cheap") or "the part"
    tips = [f"The stress is {ratio:.2f}x what {part} may carry. Where it bends, make the section {_pct(math.sqrt(ratio))} "
            f"thicker in the bending direction (bending stress falls with thickness squared), or {_pct(ratio)} wider; where "
            f"it is pulled or sheared straight, {_pct(ratio)} more cross-section. Add it at the red zone in the Stress view."]
    if row.get("check") in ("fea_static", "impact_fea", "stop_impact", "creep_limit") and proj is not None and part in getattr(proj, "items", {}):
        it = proj.items[part]
        mat = it.spec.get("material", "PETG")
        direction = req.get("direction", "xy")
        try:
            from .requirements import _strength
            now = _strength(mat, "z" if direction == "z" else "xy")
            alts = _stronger_materials(mat, now * ratio, direction, now)
            if alts:
                tips.append(f"Or print it in a stronger material with the same shape: {', '.join(alts)}.")
        except Exception:  # noqa: BLE001
            pass
        if direction == "z":
            tips.append("The load runs across its layers, where prints are weakest: turning the part on the bed so the "
                        "layers run along the load often helps more than thickening.")
        if float(it.spec.get("infill", 0.25)) < 1 and ratio < 1.6:
            tips.append("A 100 % infill modifier around the stressed zone (with a `box`) also helps a little; the walls "
                        "still carry most of it.")
    if row.get("check") == "impact_fea":
        tips.append("For a crash load, a TPU bumper the hit goes through first lowers the peak force (impact_fea `bumper:`).")
    if row.get("check") == "creep_limit":
        tips.append("Under a constant load plastic slowly stretches: PETG and CF materials creep less than PLA.")
    return tips


def _natural_freq(row, req, proj) -> list[str]:
    fn, ex = row.get("value"), row.get("limit") or []
    sep = float(req.get("separation") or 0.2)
    if not _num(fn) or not ex:
        return []
    near = min(ex, key=lambda e: abs(e - fn))
    up, down = near * (1 + sep), near * (1 - sep)
    k_up = (up / fn) ** 2
    t_up = k_up ** (1 / 3)
    tips = [f"Its natural wobble ({fn:.0f} Hz) is too close to the {near:.0f} Hz shaking. To move it above {up:.0f} Hz it "
            f"needs {_pct(k_up)} more stiffness: about {_pct(t_up)} more depth in the direction it flexes (stiffness goes "
            f"with depth cubed), a shorter span, or a rib along it."]
    if down > 0 and fn > down:
        tips.append(f"Or move it below {down:.0f} Hz instead: {_pct((down / fn) ** 2)} less stiffness or "
                    f"{_pct((fn / down) ** 2)} more mass at the tip; usually the worse choice for a frame arm.")
    tips.append("Lighter things at the tip (motor, camera) raise the frequency too: frequency goes as sqrt(stiffness / mass).")
    return tips


def _servo(row, req, proj) -> list[str]:
    need = row.get("value")
    frac = float(req.get("max_fraction", 0.5))
    if not _num(need):
        return []
    stall = need / frac
    tips = [f"The joint needs {need:.2f} kg·cm; at the {frac * 100:.0f} % working limit that takes a servo with at least "
            f"{stall:.1f} kg·cm stall torque."]
    try:
        ok = sorted((v.get("stall_torque_kgcm", 0), k, v.get("weight_g")) for k, v in catalog.get("servos").items()
                    if v.get("stall_torque_kgcm", 0) >= stall)
        if ok:
            tips.append("Servos in the catalog that are strong enough: " + ", ".join(
                f"{k} ({s:g} kg·cm, {w:g} g)" for s, k, w in ok[:3]) + ".")
        else:
            tips.append("No catalog servo is that strong: add a gear reduction, or a second servo on the joint.")
    except Exception:  # noqa: BLE001
        pass
    tips.append("Or cut the torque itself: it is weight x distance, so a shorter or lighter arm beyond the joint, or a "
                "counterweight / spring on the other side, lowers it in proportion.")
    return tips


def _short_mm(row, req, proj, what: str) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)):
        return []
    d = lim - v
    who = " and ".join(str(x) for x in (req.get("a"), req.get("b")) if x)
    return [f"It is {d:.1f} mm short{(' between ' + who) if who else ''}: {what} by at least {d + 0.5:.1f} mm "
            f"(the shortfall plus 0.5 mm to spare)."]


def _mass(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)):
        return []
    tips = [f"It is {v - lim:.0f} g over ({_pct(v / lim)})."]
    try:
        from .checks import item_mass_g
        inc = set(req.get("include") or [])          # the requirement weighs only these items when it lists them
        rows = sorted(((item_mass_g(it), i, it.role) for i, it in proj.items.items()
                       if it.role in ("printed", "purchased") and (not inc or i in inc)), reverse=True)[:4]
        tips.append("Heaviest items: " + ", ".join(f"{i} {m:.0f} g" for m, i, _ in rows) + ".")
        printed = [(m, i) for m, i, r in rows if r == "printed"]
        if printed:
            tips.append(f"Printed parts get lighter with lower infill or pockets where the Stress view shows no load "
                        f"(the report's 'overbuilt' notes name them); bought parts only by choosing lighter ones.")
    except Exception:  # noqa: BLE001
        pass
    return tips


def _twr(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or v <= 0:
        return []
    cut = 1 - v / lim
    return [f"Either cut the all-up weight by {cut * 100:.0f} %, or get {_pct(lim / v)} more thrust (bigger props, higher-KV "
            f"motors or one more battery cell; check the ESC and battery ratings after).",
            "Weight is usually cheaper: the battery is the biggest single item, and a smaller pack also shortens flight time."]


def _time(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or v <= 0:
        return []
    return [f"It runs {v:.1f} min of the {lim:g} wanted: about {_pct(lim / v)} more battery capacity (a bit more, since the "
            f"heavier pack draws more), or cut the average current: lighter build, efficient props, lower-draw electronics."]


def _tip(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or v <= 0 or lim >= 89:
        return []
    f = math.tan(math.radians(lim)) / math.tan(math.radians(v))
    return [f"It tips at {v:.0f}° instead of {lim:g}°: widen the footprint {_pct(f)} (distance from the balance point to the "
            f"tipping edge), or lower the balance point {_pct(1 / f)} (heavy parts low, e.g. the battery); tip angle = "
            f"atan(edge distance / height)."]


def _margin(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and isinstance(lim, (list, tuple)) and len(lim) == 2):
        return []
    lo, hi = lim
    if _num(lo) and v < lo:
        return [f"The balance point is too far back (static margin {v:.3f}, needs at least {lo:g}): move it forward by "
                f"{(lo - v + 0.01):.3f} x the wing's mean chord, usually by moving the battery forward or adding nose weight."]
    if _num(hi) and v > hi:
        return [f"The balance point is too far forward (static margin {v:.3f}, at most {hi:g}): move it back by "
                f"{(v - hi + 0.01):.3f} x the mean chord (battery back); too nose-heavy wastes elevator and raises landing speed."]
    return []


def _stall(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or lim <= 0:
        return []
    f = (v / lim) ** 2
    return [f"Stall speed goes as sqrt(weight / wing area): {_pct(f)} more wing area, or {_pct(1 / f)} less weight, brings it "
            f"from {v:.0f} to {lim:g} km/h. Flaps or a higher-lift airfoil also work."]


def _loading(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or lim <= 0:
        return []
    return [f"{_pct(v / lim)} more wing area or {_pct(lim / v)} less weight."]


def _spar(row, req, proj) -> list[str]:
    v = row.get("value")
    if not _num(v) or v <= 1:
        return []
    return [f"The spar is at {v:.2f}x its allowable: a tube {_pct(math.sqrt(v))} larger in diameter, or {_pct(v)} thicker "
            f"wall (a thin tube's bending stress goes as 1 / (diameter² x wall)), or a second spar sharing the load."]


def _gear(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or lim <= 0:
        return []
    r = v / lim
    return [f"Tooth stress is {r:.2f}x allowed: {_pct(r)} wider gear face, or a larger module (tooth size) by the same "
            f"factor (Lewis: stress goes as 1 / (face width x module)), or a stronger material such as PA6-CF."]


def _heat(row, req, proj) -> list[str]:
    max_c = req.get("max_c")
    if not _num(max_c):
        return []
    out = []
    for name, m in _materials().items():
        h = m.get("hdt_045_c")
        if _num(h) and h > max_c:
            out.append((h, name))
    tips = [f"Print the parts that soften in a material rated above {max_c} °C: " + ", ".join(f"{n} ({h:g} °C)" for h, n in sorted(out)[:4]) + "."] if out else []
    tips.append("Or keep it out of the heat (shade, vents) and lower max_c in the use story to what it really meets.")
    return tips


def _flex(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or lim <= 0:
        return []
    r = v / lim
    if req.get("kind") == "hinge":
        return [f"The hinge strains {r:.2f}x allowed: make it {_pct(r)} longer or {_pct(1 / r)} thinner (strain = thickness "
                f"x angle / (2 x length))."]
    return [f"The snap strains {r:.2f}x allowed: make the arm {_pct(math.sqrt(r))} longer, {_pct(1 / r)} thinner, or the "
            f"hook {_pct(1 / r)} shallower (strain goes as thickness x deflection / length²)."]


def _joint_speed(row, req, proj) -> list[str]:
    v, lim = row.get("value"), row.get("limit")
    if not (_num(v) and _num(lim)) or lim <= 0:
        return []
    return [f"The move takes {v:.2f} s of {lim:g}: a servo {_pct(v / lim)} faster (lower s/60°), less load on it, or a "
            f"shorter travel."]


TEXT = {
    "clearance_min": lambda r, q, p: _short_mm(r, q, p, "move them apart or trim the nearer one"),
    "prop_clearance": lambda r, q, p: _short_mm(r, q, p, "move the motors out, use a smaller prop, or trim what the disc hits"),
    "prop_ground": lambda r, q, p: _short_mm(r, q, p, "lengthen the legs / skids or raise the motors"),
    "channel_clear": lambda r, q, p: _short_mm(r, q, p, "widen the channel"),
    "access_opening": lambda r, q, p: ["Open up the space in front of it so a finger (about 32 mm wide with a glove) can "
                                       "reach, or move it to an edge."],
    "connector_access": lambda r, q, p: ["Leave a straight path the plug's size in front of the socket, or turn the board "
                                         "so the socket faces an opening."],
    "repair_access": lambda r, q, p: ["Make the blocked screws reachable from outside (a hole for the screwdriver) or "
                                      "change which part comes off first."],
    "rain_cover": lambda r, q, p: ["Put a lid or overhang over the items that must stay dry; rain is taken as falling "
                                   "straight down."],
    "screw_locking": lambda r, q, p: ["Give each listed screw group a locking method in `locking:` (nyloc nut, "
                                      "threadlocker, lock washer): on a vibrating machine plain screws back out."],
    "hard_stop": lambda r, q, p: ["Add a physical stop (a tab and a shoulder) that touches just past the joint's range, "
                                  "so the servo can't drive it further."],
    "weak_link": lambda r, q, p: ["Make the cheap, easy-to-reprint part the weakest: thin it at a planned break point or "
                                  "strengthen the expensive part, so a crash costs a spare, not the frame."],
    "story_covered": lambda r, q, p: ["Add the requirement(s) the use story names, or point covered_by at ones that exist."],
    "impact_case": lambda r, q, p: ["Add an `impact_fea` (or an fea_static with `case:` crash/drop) on the part that "
                                    "takes the hit, with the use story's speed or height."],
    "size_max": lambda r, q, p: ["Fold or split the largest dimension, or move parts closer together."],
    "power_budget": lambda r, q, p: ["Each listed element is asked for more than its rating: a bigger battery C rating, a "
                                     "higher-amp regulator or connector, or thicker wire for that run."],
    "grip_hold": lambda r, q, p: ["More squeeze (stronger servo or a longer finger lever ratio) or grippier pads (TPU) "
                                  "raise the friction force that holds it."],
}
TEXT.update({k: _stress for k in STRESS})
TEXT.update({
    "reservoir_capacity": lambda r, q, p: [f"Provide at least {r['needed_capacity_ml']:g} mL of internal reservoir "
                                           f"capacity with the declared usable fraction and reserve; the model has "
                                           f"{r['capacity_ml']:g} mL. Keep the demand tied to measured or sourced use."],
    "sensor_coverage": lambda r, q, p: [f"Move or aim the sensor so at least {r['limit']:g}% of the target region "
                                       f"is inside its sourced field of view (currently {r['value']:g}%). "
                                       "Check for obstructions and validate real detection separately."],
})
TEXT.update({"natural_freq": _natural_freq, "static_torque": _servo, "mass_max": _mass, "thrust_to_weight": _twr,
             "flight_time": _time, "run_time": _time, "tip_over": _tip, "static_margin": _margin, "static_margin_tail": _margin,
             "stall_speed": _stall, "wing_loading": _loading, "spar_bending": _spar, "gear_bending": _gear,
             "planetary_bending": _gear, "worm_drive": _gear, "heat_limit": _heat, "flex_strain": _flex,
             "joint_speed": _joint_speed})


def advise(row: dict, req: dict, proj=None) -> list[str]:
    """Advice for one failed requirement row (its spec `req` from project.yaml); [] when it passed or nothing specific
    can be said (the card then keeps its general line)."""
    if row.get("ok") or row.get("skipped"):
        return []
    if "check failed to run" in str(row.get("detail", "")):
        return ["The check itself could not run: fix its settings in project.yaml (see the details)."]
    fn = TEXT.get(row.get("check", ""))
    try:
        return [t for t in (fn(row, req or {}, proj) if fn else []) if t]
    except Exception:  # noqa: BLE001 - advice never breaks a check
        return []


def overlap(proj, a: str, b: str) -> str:
    """For two items that overlap at assembly: how deep, along which axis, and which one to change (a bought part's
    shape is fixed, so the printed part gets the pocket). '' when it can't be measured."""
    try:
        from . import geom
        ia, ib = proj.items[a], proj.items[b]
        common = ia.shape.intersect(ib.shape)
        if isinstance(common, list):                   # build123d returns a ShapeList for some shapes
            from build123d import Compound
            common = Compound(list(common))
        lo, hi = geom.bbox(common)
        size = [float(h - l) for l, h in zip(lo, hi)]
        ax = min(range(3), key=lambda i: size[i])
        mid = {i: (float(geom.bbox(it.shape)[0][ax]) + float(geom.bbox(it.shape)[1][ax])) / 2 for i, it in ((a, ia), (b, ib))}
        away = lambda p, o: "+" if mid[p] >= mid[o] else "-"  # noqa: E731  (direction that takes p off o)
        d = size[ax]
        at = [round(float((l + h) / 2), 1) for l, h in zip(lo, hi)]
        fixed = {i for i, it in ((a, ia), (b, ib)) if it.role != "printed"}
        printed = [i for i in (a, b) if i not in fixed]
        axis = "XYZ"[ax]
        if len(printed) == 1:
            p, other = printed[0], (b if printed[0] == a else a)
            return (f"{other} can't change shape, so cut a pocket {d + 0.3:.1f} mm deep into {p} at {at} (the "
                    f"{d:.1f} mm overlap along {axis} plus 0.3 mm clearance), or move {p} {d + 0.3:.1f} mm along "
                    f"{away(p, other)}{axis}")
        if not printed:
            return (f"two bought parts overlap {d:.1f} mm along {axis} at {at}: move one of them {d + 0.5:.1f} mm "
                    f"(change its joint position in project.yaml)")
        return (f"they overlap {d:.1f} mm along {axis} at {at}: move {b} {d + 0.3:.1f} mm along {away(b, a)}{axis}, or cut "
                f"that much out of whichever part has room there")
    except Exception:  # noqa: BLE001
        return ""


def sweep(s: dict, proj=None) -> str:
    """For a joint whose sweep collides: at which angles, and the two ways out (stop short, or make room)."""
    try:
        c0 = s["collisions"][0]
        a, b = c0["a"], c0["b"]
        angs = sorted(float(c["at"]) for c in s["collisions"] if c["a"] == a and c["b"] == b and "at" in c)
        lo, hi = s.get("range", [None, None])
        if not angs or lo is None:
            return ""
        unit = "mm" if s.get("kind") == "prismatic" else "°"
        step = (hi - lo) / max(s.get("samples", 9) - 1, 1)
        free = [x for x in (lo + i * step for i in range(s.get("samples", 9))) if x not in angs]
        tip = (f"{a} hits {b} from {angs[0]:g} to {angs[-1]:g}{unit} of the {lo:g}..{hi:g}{unit} range")
        if free:
            near_lo = angs[0] > lo
            stop = angs[0] - step / 2 if near_lo else angs[-1] + step / 2
            tip += (f": if it never needs those positions, end the range at about {stop:.0f}{unit} (a hard stop "
                    f"there too); otherwise make room in ")
        else:
            tip += ": they touch over the whole range, so make room in "
        roles = {i: proj.items[i].role for i in (a, b)} if proj is not None and a in proj.items and b in proj.items else {}
        printed = [i for i in (a, b) if roles.get(i) == "printed"]
        tip += (printed[0] if len(printed) == 1 else f"{a} or {b}") + " where the other passes (a relief cut or more spacing)"
        return tip
    except Exception:  # noqa: BLE001
        return ""
