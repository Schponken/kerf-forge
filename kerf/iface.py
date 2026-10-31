"""Mating-feature generators. Both sides of every connection come from here so they agree by construction.

Conventions
- `loc` is a Location on the part surface. Its +Z points OUT of the material: toward the screw head for a male
  (pass-through) side, toward the mating part for a female (threaded) side. Cutters go into the material along -Z.
- Every function returns a cutter solid (subtract it from your part) and registers fastener sites on `ctx` under
  `group`, which must match the group used on the other part (or in the purchased item's `groups:` in project.yaml).
- All hardware sizes come from the catalog via the normalisers at the top of this file.
"""
from __future__ import annotations

import math

from build123d import Align, Box, Cylinder, Location, Part, Pos, RegularPolygon, Rot, extrude, Plane

from . import calibrate, catalog
from .ctx import PinSite, Site

EXTRA = 1.0  # cutters overshoot the surface by this much so faces never coincide


# ---------------------------------------------------------------- catalog normalisers
def _first(entry, *keys, default=None):
    return catalog.num(entry, *keys, default=default)


def screw_spec(size: str, material: str | None = None) -> dict:
    """Everything needed to cut and size holes for a metric screw, from catalog screws + fdm_holes.
    material picks a material-specific printed pilot size when the catalog has one (e.g. self_tap_pilot_petg)."""
    s = catalog.get(f"screws.{size}")
    d = float(size.lstrip("M"))
    try:
        f = catalog.get(f"fdm_holes.{size}")
    except catalog.CatalogError:
        f = {}
    out = {
        "d": d,
        "clearance": _first(f, "clearance_hole", "screw_clearance", "clearance", default=_first(s, "clearance_hole", "clearance_hole_normal", "clearance")) if f else _first(s, "clearance_hole", "clearance_hole_normal", "clearance"),
        "tap": _first(f, "self_tap_pilot", "pilot", "self_tapping_pilot", default=_first(s, "tap_drill", default=d * 0.8)) if f else _first(s, "tap_drill", default=d * 0.8),
        "head_d": _first(s, "shcs_head_d", "socket_head_d", "head_d"),
        "head_h": _first(s, "shcs_head_h", "socket_head_h", "head_h"),
        "csk_d": _first(s, "countersunk_head_d", "csk_head_d", "countersink_head_d"),
        "nut_af": _first(s, "nut_across_flats", "hex_nut_af", "across_flats"),
        "nut_h": _first(s, "nut_thickness", "hex_nut_thickness", "nut_h"),
        "min_engage": 1.5 * d,
    }
    if f and material:
        m = material.lower().replace("-", "_")
        for key in (f"self_tap_pilot_{m}", "self_tap_pilot_petg" if "petg" in m else None):
            if key and key in f:
                out["tap"] = float(f[key])
                break
    # horizontal printed pilot (hole axis in the layer plane, e.g. a teardrop): the same Bambu table gives a larger
    # pilot there (stair-stepped round); applied as the table's horizontal - vertical difference to the pilot above
    out["tap_h"] = out["tap"]
    if f and "self_tap_pilot_horizontal" in f:
        out["tap_h"] = out["tap"] + float(f["self_tap_pilot_horizontal"]) - float(f["self_tap_pilot"])
    if f:
        out["nut_pocket_af"] = _first(f, "nut_pocket_af", "nut_trap_af", "captive_nut_af", default=out["nut_af"] + 0.3)
        out["insert_hole"] = _first(f, "heatset_hole_d", "insert_hole_d", "heat_set_hole_d", default=0) or None
        out["insert_len"] = _first(f, "heatset_length", "insert_length", "heat_set_length", default=0) or None
        out["insert_depth"] = _first(f, "heatset_min_depth", "insert_min_hole_depth", "heat_set_min_depth", default=0) or None
        out["insert_wall"] = _first(f, "heatset_min_wall", "insert_min_wall", default=0) or None
    # the printer's measured fit (kerf calibrate / kerf feedback); 0 unless a profile is active for this part
    out["clearance"] += calibrate.offset("hole", size)
    out["tap"] += calibrate.offset("tap", size)
    out["tap_h"] += calibrate.offset("tap", size)
    if out.get("insert_hole"):
        out["insert_hole"] += calibrate.offset("insert", size)
    return out


# ---------------------------------------------------------------- patterns (points in the loc's XY plane)
def rect(w: float, h: float):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def square(s: float):
    return rect(s, s)


def circle(n: int, dia: float, start_deg: float = 0.0):
    return [(dia / 2 * math.cos(math.radians(start_deg + 360 * k / n)), dia / 2 * math.sin(math.radians(start_deg + 360 * k / n)))
            for k in range(n)]


def _cyl(r, z0, z1):
    return Pos(0, 0, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _hex(af, z0, z1):
    sk = RegularPolygon(af / math.sqrt(3), 6)
    return Pos(0, 0, z0) * extrude(sk, z1 - z0)


def _cone(r0, r1, z0, z1):
    return Pos(0, 0, z0) * Cylinder(r0, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN)) if r0 == r1 else \
        Pos(0, 0, z0) * _frustum(r0, r1, z1 - z0)


def _frustum(r_bottom, r_top, h):
    from build123d import Cone
    return Cone(r_bottom, r_top, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


KINDS_MALE = ("clearance", "counterbore", "countersink")
KINDS_FEMALE = ("heatset", "tap", "nut_trap")


def print_up_deg(ctx, loc: Location, vertical_tol_deg: float = 30.0) -> float | None:
    """Teardrop angle for a hole cut at `loc` (hole axis = loc's +Z) in this part: the direction, in loc's XY plane, that
    is UP on the printer for the part's `print_rot`. None when the hole prints within `vertical_tol_deg` of vertical
    (it needs no teardrop). Pass the result as `teardrop=` so a part keeps working if its print orientation changes."""
    rot = ((getattr(ctx, "meta", None) or {}).get("spec") or {}).get("print_rot") or [0, 0, 0]
    up = Location((0, 0, 0), tuple(float(a) for a in rot)).inverse() * Location((0, 0, 1))
    up = up.position
    o = loc.position
    ax = [(loc * Location(v)).position - o for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    if abs(up.dot(ax[2])) > math.cos(math.radians(vertical_tol_deg)):
        return None
    return math.degrees(math.atan2(up.dot(ax[1]), up.dot(ax[0])))


def _teardrop(r, z0, z1, up_deg):
    """Horizontal-hole shape for FDM: a circle with a 45-degree pointed roof toward `up_deg` (direction that is UP
    on the printer, measured in the hole's XY plane). Prints without sagging or supports."""
    from build123d import Polygon
    a = r / math.sqrt(2)
    roof = Pos(0, 0, z0) * extrude(Polygon((-a, a), (a, a), (0, r * math.sqrt(2)), align=None), z1 - z0)
    return Rot(0, 0, up_deg - 90) * roof + _cyl(r, z0, z1)


def hole(screw: str, kind: str, depth: float, counterbore_depth: float | None = None, teardrop: float | None = None,
         material: str | None = None, nut_recess: float = 0.0, relief: float = 0.0):
    """Cutter for one hole at the origin, axis Z, surface at z=0, material at z<0. Returns (solid, grip, engage, min_engage).
    relief (heatset): a screw-clearance bore this much deeper than the insert, so a screw may run on through the insert
    (lets a standard length fit a fixed grip such as a flight stack); the fastener check allows that much more length.
    teardrop: for holes that print horizontally, the direction (deg, in the hole's XY plane) that is UP on the printer.
    nut_recess (nut_trap): sink the nut this far below the far face, so the shortest screw that fills the nut ends
    below that face instead of standing proud of it (nothing lying on the face meets a thread end)."""
    sp = screw_spec(screw, material)
    if teardrop is not None and kind not in ("clearance", "tap", "heatset"):
        raise ValueError(f"teardrop is not available for a {kind} hole (only clearance, tap, heatset); print it vertical "
                         f"or bridge it with a sacrificial layer")
    if kind == "clearance":
        if teardrop is not None:
            return _teardrop(sp["clearance"] / 2, -depth - EXTRA, EXTRA, teardrop), depth, 0.0, 0.0
        return _cyl(sp["clearance"] / 2, -depth - EXTRA, EXTRA), depth, 0.0, 0.0
    if kind == "counterbore":
        cb = counterbore_depth if counterbore_depth is not None else sp["head_h"] + 0.3
        if cb >= depth - 1.0:
            raise ValueError(f"counterbore {cb:.1f} mm leaves less than 1 mm under a {screw} head in a {depth} mm plate")
        s = _cyl(sp["clearance"] / 2, -depth - EXTRA, EXTRA) + _cyl(sp["head_d"] / 2 + 0.3, -cb, EXTRA)
        return s, depth - cb, 0.0, 0.0
    if kind == "countersink":
        r_top = sp["csk_d"] / 2 + 0.2
        r_bot = sp["clearance"] / 2
        h = r_top - r_bot  # 90 degree head
        s = _cyl(r_bot, -depth - EXTRA, EXTRA) + Pos(0, 0, -h) * _frustum(r_bot, r_top, h) + _cyl(r_top, 0, EXTRA)
        return s, depth - h * 0.0, 0.0, 0.0
    if kind == "heatset":
        if not sp.get("insert_hole") or not sp.get("insert_len"):
            raise ValueError(f"catalog fdm_holes.{screw} has no heat-set insert size")
        hd = sp.get("insert_depth") or sp["insert_len"] + 1.0
        if hd + relief > depth - 0.8:
            raise ValueError(f"{screw} heat-set insert needs a {hd:.1f} mm deep hole plus a 0.8 mm floor; only {depth:.1f} mm of material")
        # brass threads: ~1.3 d of engagement holds an M2-M5 screw to its proof load
        c = _cyl(sp["insert_hole"] / 2, -hd, EXTRA) if teardrop is None else _teardrop(sp["insert_hole"] / 2, -hd, EXTRA, teardrop)
        if relief > 0:
            c += _cyl(sp["clearance"] / 2, -hd - relief, -hd + EXTRA)
        return c, 0.0, hd - 0.5 + relief, min(sp["insert_len"] * 0.7, 1.5 * sp["d"])
    if kind == "tap":
        hd = min(depth - 0.8, 2.5 * sp["d"] + 1.0)
        if hd < sp["min_engage"] + 0.5:
            raise ValueError(f"{screw} pilot hole needs {sp['min_engage'] + 1.3:.1f} mm of material; only {depth:.1f} mm")
        # a teardrop = the hole prints horizontal: use the horizontal pilot (catalog self_tap_pilot_horizontal)
        c = _cyl(sp["tap"] / 2, -hd, EXTRA) if teardrop is None else _teardrop(sp["tap_h"] / 2, -hd, EXTRA, teardrop)
        return c, 0.0, hd - 0.5, sp["min_engage"]
    if kind == "nut_trap":
        # clearance through the plate, hex pocket open to the far face, nut pushed in from the far side.
        # Only sensible for plates up to ~3 d + nut height; thicker parts should use a heat-set insert.
        af = sp["nut_pocket_af"]
        nh = sp["nut_h"] + 0.3
        if depth > 3 * sp["d"] + nh + 2:
            raise ValueError(f"{screw} nut trap in {depth:.1f} mm of material needs a very long screw; use kind='heatset' or a thinner flange")
        if nut_recess and depth - nut_recess - nh < 1.0:
            raise ValueError(f"{screw} nut recessed {nut_recess} mm leaves less than 1 mm of a {depth} mm plate under the nut")
        s = _cyl(sp["clearance"] / 2, -depth - EXTRA, EXTRA) + _hex(af, -depth - EXTRA, -depth + nh + nut_recess)
        return s, 0.0, depth + 4.0, depth - nut_recess - nh + sp["nut_h"] * 0.9
    raise ValueError(f"unknown hole kind '{kind}' (use {KINDS_MALE + KINDS_FEMALE})")


def bolt_pattern(ctx, group: str, screw: str, points, loc: Location, kind: str, depth: float,
                 counterbore_depth: float | None = None, teardrop: float | None = None, nut_recess: float = 0.0,
                 relief: float = 0.0):
    """Holes at `points` (in loc's XY plane) through/into `depth` mm of material below loc.
    Registers one site per hole: male for clearance/counterbore/countersink, female for heatset/tap/nut_trap."""
    role = "male" if kind in KINDS_MALE else "female"
    cut = None
    for (x, y) in points:
        mat = (getattr(ctx, "meta", None) or {}).get("spec", {}).get("material") if ctx is not None else None
        c, grip, engage, mn = hole(screw, kind, depth, counterbore_depth, teardrop, mat, nut_recess, relief)
        hl = loc * Location((x, y, 0))
        placed = hl * c
        cut = placed if cut is None else cut + placed
        surf = hl if kind != "counterbore" else hl * Location((0, 0, -(counterbore_depth if counterbore_depth is not None else screw_spec(screw)["head_h"] + 0.3)))
        ctx.site(Site(group, role, screw, kind, surf, grip=grip, engage=engage, min_engage=mn))
    return cut


# ---------------------------------------------------------------- purchased-part mounts
def servo_dims(path: str) -> dict:
    """Normalised servo geometry in the proxy frame: origin at the centre of the tab underside, +Z toward the output."""
    e = catalog.get(path)
    L = _first(e, "body_l", "body_length", "length")
    W = _first(e, "body_w", "body_width", "width")
    H = _first(e, "body_h", "body_height", "height")
    span = _first(e, "tab_span", "mounting_tab_span", "overall_tab_length", "tab_overall_length")
    hx = _first(e, "hole_spacing_l", "mount_hole_spacing_l", "mounting_hole_spacing", "hole_spacing", "hole_spacing_length")
    hy = _first(e, "hole_spacing_w", "mount_hole_spacing_w", "hole_spacing_width", default=0.0)
    hd = _first(e, "hole_d", "mounting_hole_d", "mount_hole_d", "mounting_hole_diameter")
    tab_t = _first(e, "tab_t", "tab_thickness")
    tab_z = _first(e, "tab_z", "tab_height_from_bottom", "tab_bottom_height", "tab_height")
    shaft_off = _first(e, "shaft_offset", "output_shaft_offset", "shaft_offset_from_end", "output_offset_from_end")
    shaft_h = _first(e, "shaft_h", "output_shaft_height", "spline_height_above_body", default=4.0)
    spline_d = _first(e, "spline_d", "spline_od", "spline_outer_d", "output_spline_od", default=6.0)
    screw = "M3" if hd >= 3.3 else ("M2.5" if hd >= 2.8 else "M2")
    return {"L": L, "W": W, "H": H, "span": span, "hx": hx, "hy": hy, "hole_d": hd, "tab_t": tab_t,
            "tab_z": tab_z, "out_x": L / 2 - shaft_off, "top": H - tab_z, "shaft_h": shaft_h, "spline_d": spline_d,
            "screw": screw, "holes": [(sx * hx / 2, sy * hy / 2) for sx in (-1, 1) for sy in ((-1, 1) if hy else (0,))]}


def servo_mount(ctx, servo: str, loc: Location, group: str, plate_t: float, kind: str = "heatset",
                clearance: float = 0.6, top_through: bool = False, lead_in: float = 0.5, teardrop: float | None = None):
    """Cutter for a plate a servo's mounting tabs bolt to: a window plus the four tab screw holes.

    Default (top_through=False): the body drops through the window from the TOP and the tabs rest ON the plate.
      loc: on the face the tab undersides rest on, +Z toward the servo top; material below loc (z < 0).
      Matches the servo proxy's 'tabs' joint directly. A catalog lead exit (cable_boss_*) below the tabs is cleared
      where the plate reaches it (SG90: from 3 mm under the tabs on the output end; route the lead out from there).
    top_through=True: the servo goes in top-first from BEHIND; only the case top (above the tabs) passes the window and
      the tab tops press against the plate. Use this when the body has bumps low down (MG996R cable boss).
      loc: on the face the tab TOPS press against, +Z toward the servo top; material above loc (0 < z < plate_t).
      The servo proxy's 'tabs' joint (tab underside) sits at loc * Location((0, 0, -tab_t)). Set the servo's
      `tab_screws_from: bottom` in project.yaml so its screws come from behind the tabs.
    lead_in: 45-degree chamfer (mm) around the window on its ENTRY face (z = 0 in both modes): guides the body in and
      absorbs elephant's foot when that face prints on the bed. 0 disables it. It is reduced (see servo_lead_in) so the
      wall between the widened window and every tab screw hole keeps docs/ENGINEERING.md section 5's minimum.
    teardrop: when the plate prints standing (tab screw holes horizontal), the direction (deg in loc's XY plane) that
      is UP on the printer; see print_up_deg."""
    d = servo_dims(servo)
    clearance += calibrate.offset("servo_window")
    wx, wy = d["L"] + clearance, d["W"] + clearance
    z0 = -plate_t - EXTRA if not top_through else -EXTRA
    pocket = Pos(0, 0, z0) * Box(wx, wy, plate_t + 2 * EXTRA, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # corner reliefs ("dog-bones"): remove the sharp inside corners without rounding into the square servo body
    for sx in (-1, 1):
        for sy in (-1, 1):
            pocket += Pos(sx * (wx / 2 - 0.35), sy * (wy / 2 - 0.35), 0) * _cyl(1.0, z0, z0 + plate_t + 2 * EXTRA)
    mat = (getattr(ctx, "meta", None) or {}).get("spec", {}).get("material") if ctx is not None else None
    lead_in = servo_lead_in(servo, kind, plate_t, lead_in, clearance, mat)
    if lead_in > 0:
        from build123d import Rectangle, extrude
        # frustum: (window + 2*lead_in) at the entry face, shrinking at 45 deg to the window lead_in deep into material
        g = lead_in + EXTRA
        cone = Pos(0, 0, -EXTRA) * extrude(Rectangle(wx + 2 * g, wy + 2 * g), amount=g, taper=45)
        pocket += cone if top_through else Rot(180, 0, 0) * cone
    e = catalog.get(servo)
    if not top_through and "cable_boss_protrusion" in e:
        # the lead exit (catalog cable_boss_*, on one end face below the tabs): clear it with the window clearance
        # wherever the plate reaches down that far, so the plate never traps the lead
        bp, bh, bz, bw = (catalog.num(e, k) for k in ("cable_boss_protrusion", "cable_boss_h", "cable_boss_z0", "cable_boss_w"))
        lo, hi = max(-d["tab_z"] + bz - clearance / 2, -plate_t - EXTRA), min(-d["tab_z"] + bz + bh + clearance / 2, 0.0)
        if hi > lo:
            sx = 1 if e.get("cable_boss_end", "output") == "output" else -1
            ledge = -hi                                      # plate left between the tabs and the lead exit
            mat = (getattr(ctx, "meta", None) or {}).get("spec", {}).get("material") if ctx is not None else None
            hole_depth = -hole(d["screw"], kind, plate_t, material=mat)[0].bounding_box().min.Z
            if any(sx * x > d["L"] / 2 for x, _ in d["holes"]) and hole_depth > ledge + 1e-6:
                raise ValueError(
                    f"servo_mount({servo}): the lead leaves the {'output' if sx > 0 else 'far'} end {ledge:.1f} mm under "
                    f"the tabs (catalog cable_boss_*), but a {kind} {d['screw']} hole there is {hole_depth:.1f} mm deep and "
                    f"would break into it. Use top_through=True (tabs against the plate's far face), a plate <= "
                    f"{ledge:.1f} mm thick at that end, or kind='tap' with a hole no deeper than the ledge")
            pocket += Pos(sx * (d["L"] / 2 + (bp + clearance / 2) / 2), 0, lo) * Box(
                bp + clearance / 2 + 0.02, bw + clearance, hi - lo, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cut = loc * pocket
    if not top_through:
        cut += bolt_pattern(ctx, group, d["screw"], d["holes"], loc, kind, plate_t, teardrop=teardrop)
    else:
        # female holes face the servo tabs (-Z of loc); flip the frame and mirror Y so the holes land in place
        cut += bolt_pattern(ctx, group, d["screw"], [(x, -y) for (x, y) in d["holes"]], loc * Rot(180, 0, 0), kind, plate_t,
                            teardrop=None if teardrop is None else -teardrop)
    return cut


MIN_WALL_AROUND_HOLE = 2.4  # docs/ENGINEERING.md section 5: around heat-set inserts and screw bosses


def servo_lead_in(servo: str, kind: str, plate_t: float, lead_in: float, clearance: float = 0.6,
                  material: str | None = None) -> float:
    """Largest lead-in chamfer <= lead_in that keeps MIN_WALL_AROUND_HOLE (or the catalog's heat-set min wall, if
    larger) between the widened window and every tab screw hole, measured with that hole's real cutter size.
    Returns 0 when less than 0.2 mm would remain (a chamfer that small does nothing useful)."""
    if lead_in <= 0:
        return 0.0
    d = servo_dims(servo)
    a, b = (d["L"] + clearance) / 2, (d["W"] + clearance) / 2
    bb = hole(d["screw"], kind, plate_t, material=material)[0].bounding_box()
    r = max(bb.size.X, bb.size.Y) / 2
    need = MIN_WALL_AROUND_HOLE
    if kind == "heatset":
        need = max(need, float(screw_spec(d["screw"], material).get("insert_wall") or 0.0))

    def wall(c):
        return min(math.hypot(max(abs(x) - a - c, 0.0), max(abs(y) - b - c, 0.0)) - r for x, y in d["holes"])

    if wall(lead_in) >= need:
        return lead_in
    lo, hi = 0.0, lead_in
    if wall(0.0) < need:
        return 0.0
    for _ in range(40):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if wall(m) >= need else (lo, m)
    return round(lo, 3) if lo >= 0.2 else 0.0


def horn_dims(path: str) -> dict:
    """hub_total: hub bottom to disc top. engage: how far the servo spline slides up into the hub (catalog
    spline_engage, 0 if unknown). hub_h: what layouts add above the servo's spline top to reach the horn face
    (= hub_total - engage), so a horn that slides over its spline sits that much lower."""
    e = catalog.get(path)
    total = _first(e, "hub_height", "hub_h", "total_height", default=0.0)
    engage = _first(e, "spline_engage", default=0.0)
    arms = e.get("arms")          # arm horns (stock plastic SG90 horns): no disc, no bolt circle
    reach = max(catalog.num(a, "tip_r") + catalog.num(a, "tip_w") / 2 for a in arms) if arms else 0.0
    return {
        "od": 2 * reach if arms else _first(e, "outer_d", "od", "outer_diameter", "diameter"),
        "t": _first(e, "thickness", "disc_thickness", "plate_thickness"),
        "hub_total": total, "engage": engage, "spline_d": _first(e, "spline_d", default=0.0),
        "hub_h": total - engage,
        "hub_d": _first(e, "hub_d", "hub_diameter", default=0.0),
        "arms": arms, "hole_d": _first(e, "hole_d", default=0.0),
        "bc": 0.0 if arms else _first(e, "bolt_circle_d", "hole_circle_d", "bolt_circle_diameter", "pcd"),
        "n": sum(len(a["hole_r"]) for a in arms) if arms else int(_first(e, "hole_count", "holes", "n_holes", "number_of_holes")),
        "screw": str(e.get("hole_thread", e.get("thread", "M3"))).split("x")[0].split("-")[0].strip() or "M3",
        "center_screw": str(e.get("center_screw", "M3")).split("x")[0].split("-")[0].strip(),
    }


def horn_holes(horn: str, start_deg: float | None = None, use: str = "ends", all_holes: bool = False):
    """Screw-hole centres on a horn face (servo axis at the origin).
    Disc horns: hole_count holes on the bolt circle, the first at start_deg (default 45).
    Arm horns (catalog `arms`: [{deg, tip_r, tip_w, hole_r: [...]}]): every arm is turned by start_deg (default 0);
    use='ends' (default) screws through the innermost and outermost hole of each arm, 'all' through every hole.
    all_holes=True returns every hole regardless of `use` (the proxy cuts them all)."""
    h = horn_dims(horn)
    if not h["arms"]:
        return circle(h["n"], h["bc"], 45.0 if start_deg is None else start_deg)
    if use not in ("ends", "all"):
        raise ValueError(f"horn_holes: use must be 'ends' or 'all', not {use!r}")
    pts = []
    for a in h["arms"]:
        ang = math.radians(catalog.num(a, "deg") + (start_deg or 0.0))
        rs = [float(r) for r in a["hole_r"]]
        if not all_holes and use == "ends":
            rs = sorted({min(rs), max(rs)})
        pts += [(r * math.cos(ang), r * math.sin(ang)) for r in rs]
    return pts


def horn_mount(ctx, horn: str, loc: Location, group: str, plate_t: float, kind: str = "clearance",
               start_deg: float | None = None, teardrop: float | None = None, use: str = "ends"):
    """Holes in a printed link that bolts flat onto a servo horn face, plus an access hole for the horn's centre screw.
    loc: on the link's OUTER face (the screw-head side, away from the horn), +Z away from the horn, origin on the
    servo axis. plate_t: link thickness at the hub. teardrop: for a link printed with the horn axis horizontal, the
    direction (deg, in loc's XY plane) that is UP on the printer; every hole gets a 45-degree roof.
    start_deg / use: which horn holes (see horn_holes); give the horn item the same `hole_start_deg` / `use_holes`."""
    h = horn_dims(horn)
    pts = horn_holes(horn, start_deg, use)
    cut = bolt_pattern(ctx, group, h["screw"], pts, loc, kind, plate_t, teardrop=teardrop)
    cs = screw_spec(h["center_screw"])
    r = cs["head_d"] / 2 + 0.75                                            # driver + head access to the centre screw
    cut += loc * (_cyl(r, -plate_t - EXTRA, EXTRA) if teardrop is None else _teardrop(r, -plate_t - EXTRA, EXTRA, teardrop))
    return cut


def bearing_dims(path: str) -> dict:
    e = catalog.get(path)
    return {"d": _first(e, "bore", "d", "bore_d", "inner_d"), "D": _first(e, "outer_d", "D", "od", "outer"),
            "B": _first(e, "width", "B", "w", "length")}


FIT = {"press": 0.05, "snug": 0.2, "free": 0.35}


def bearing_seat(ctx, bearing: str, loc: Location, fit: str = "press", depth: float | None = None, shaft_clear: float = 1.0,
                 through: float = 0.0):
    """Pocket for a bearing's outer race (diameter D + fit) plus clearance for whatever passes through the bore.
    loc: on the face the bearing enters from, +Z out of the material, origin on the bearing axis."""
    b = bearing_dims(bearing)
    dep = depth if depth is not None else b["B"]
    cut = loc * _cyl((b["D"] + FIT[fit] + calibrate.offset("bearing", bearing.split(".")[-1])) / 2, -dep, EXTRA)
    if through > 0:
        cut += loc * _cyl(b["d"] / 2 + shaft_clear, -dep - through - EXTRA, 0)
    return cut


def motor_holes(motor: str):
    """Mount-hole centres of a brushless motor, from the catalog. Hobby '16x16' / '19x19' / '9x9' patterns are four
    holes on a bolt CIRCLE of that diameter (90 deg apart), not a square; use bolt_circle_d when the catalog has it."""
    e = catalog.get(motor)
    screw = str(e.get("mount_screw", e.get("screw", "M3")))
    if "bolt_circle_d" in e:
        bcd = catalog.num(e, "bolt_circle_d")
        start = catalog.num(e, "hole_start_deg", default=45.0)
        n = int(catalog.num(e, "hole_count", default=4))
        return circle(n, bcd, start), screw
    pat = e.get("mount_pattern") or e.get("bolt_pattern")
    if isinstance(pat, dict):
        sx, sy = _first(pat, "x", "spacing_x", "a"), _first(pat, "y", "spacing_y", "b")
    elif isinstance(pat, (list, tuple)):
        sx, sy = pat[0], pat[1]
    else:
        sx = sy = _first(e, "mount_spacing", "pattern_mm", "bolt_spacing")
    return rect(sx, sy), screw


def motor_mount(ctx, motor: str, loc: Location, group: str, plate_t: float, kind: str = "clearance", center_hole: float | None = None,
                counterbore_depth: float | None = None):
    """Holes for a brushless motor's base pattern. loc: on the plate face OPPOSITE the motor (screw-head side), +Z
    away from the motor, origin on the motor axis. The hole angle matches the motor proxy (same catalog data).
    counterbore_depth (kind='counterbore'): sink the heads so the grip suits a stock screw length; motor threads are
    shallow (catalog max_screw_depth), so grip + thread depth must land on a standard length."""
    ch = motor_center_hole(motor, center_hole)
    pts, screw = motor_holes(motor)
    cut = bolt_pattern(ctx, group, screw, pts, loc, kind, plate_t, counterbore_depth=counterbore_depth)
    cut += loc * _cyl(ch / 2, -plate_t - EXTRA, EXTRA)
    return cut


CENTER_WALL = 1.2  # mm of plate left between the motor's centre hole and each mount hole (ENGINEERING.md walls)


def motor_center_hole(motor: str, center_hole: float | None = None) -> float:
    """Diameter of the hole under a motor for the shaft end / circlip. Catalog value if given, else 8 mm shrunk so a
    1.2 mm wall stays between it and the mount-hole clearance holes (small motors: 9 mm bolt circle). Raises if an
    explicit or catalog size would cut into the mount holes or not clear the shaft."""
    e = catalog.get(motor)
    pts, screw = motor_holes(motor)
    r_pat = min(math.hypot(x, y) for x, y in pts)
    limit = 2 * (r_pat - screw_spec(screw)["clearance"] / 2 - CENTER_WALL)
    ch = center_hole if center_hole is not None else (_first(e, "center_clearance_d", "shaft_clearance_d", default=0) or None)
    if ch is None:
        ch = min(8.0, limit)
    shaft = _first(e, "shaft_d", "shaft_diameter", default=5.0)
    if ch > limit + 1e-9:
        raise ValueError(f"{motor}: a {ch:.1f} mm centre hole leaves less than {CENTER_WALL} mm to the mount holes (max {limit:.1f} mm)")
    if ch < shaft + 1.0:
        raise ValueError(f"{motor}: centre hole {ch:.1f} mm does not clear the {shaft} mm shaft with 0.5 mm per side")
    return ch


def stack_mount(ctx, stack: str, loc: Location, group: str, depth: float, kind: str = "heatset", relief: float = 0.0):
    """Four holes for a flight-controller/ESC stack (30.5, 20, 25.5 mm patterns from the catalog).
    loc: on the frame face the stack sits on, +Z toward the stack."""
    e = catalog.get(stack)
    s = _first(e, "spacing", "hole_spacing", "pattern")
    screw = str(e.get("screw", "M3"))
    return bolt_pattern(ctx, group, screw, square(s), loc, kind, depth, relief=relief)


# ---------------------------------------------------------------- pins (printed hinges, dowels, screw pivots)
PIN_FITS = ("free", "press", "heatset", "tap")


def pin_dims(pin: str) -> dict:
    """Pin geometry: a catalog dowel ("motion.pin_3mm") or a screw size used as a pivot ("M3")."""
    if pin in catalog.load()["screws"]:
        sp = screw_spec(pin)
        from .assembly import STANDARD_SCREW_LENGTHS
        return {"d": sp["d"], "screw": True, "lengths": list(STANDARD_SCREW_LENGTHS)}
    e = catalog.get(pin)
    if e.get("thread"):   # shoulder screw: d = the shoulder (the bearing), `thread` goes into the fixed part
        return {"d": _first(e, "d"), "screw": True, "shoulder": True, "thread": e["thread"],
                "thread_len": float(e["thread_len"]), "head_d": e.get("head_d"), "head_h": e.get("head_h"),
                "lengths": [float(x) for x in e.get("lengths", [])]}
    return {"d": _first(e, "d", "diameter", "od"), "screw": False, "lengths": [float(x) for x in e.get("lengths", [])]}


def pin_hole(ctx, pin: str, loc: Location, group: str, depth: float, fit: str = "free", through: bool = True,
             teardrop: float | None = None):
    """Cutter for one knuckle/boss of a pinned hinge. Every part the pin passes through calls this with the same group.

    loc: on the face the hole enters from, origin on the pin axis, +Z along the axis OUT of the material; the hole runs
      `depth` mm into -Z (the knuckle or boss length along the pin). through=True overshoots the far face as well.
    pin: a catalog dowel ("motion.pin_3mm"), a screw size ("M3") or a shoulder screw ("motion.shoulder_4_m3": the
      shoulder turns in the free holes, its thread goes into the heatset/tap hole, the shoulder end bottoms on it).
    fit: free  - the pin turns in this hole (moving knuckle), d + fdm_fits.pin.free_allowance_d
         press - a steel dowel is pressed in and held here, d + fdm_fits.pin.press_allowance_d
         heatset / tap - a screw used as the pivot threads in here (pin = "M3" etc.; blind, from iface.hole)
    teardrop: for horizontal holes, the direction (deg in loc's XY plane) that is UP on the printer.
    The assembled check (kerf/pins.py) proves all holes of a group are coaxial, that the pin is held on one side and
    free on the other side of every moving joint, that the joint turns about the pin axis, and picks the pin length."""
    if fit not in PIN_FITS:
        raise ValueError(f"unknown pin fit '{fit}' (use {PIN_FITS})")
    pd = pin_dims(pin)
    if fit in ("heatset", "tap"):
        if not pd["screw"]:
            raise ValueError(f"fit '{fit}' needs a screw pivot (pin='M3' or a shoulder screw), not dowel '{pin}'")
        c, _, engage, _ = hole(pd.get("thread", pin), fit, depth, teardrop=teardrop)
        ctx.pin_site(PinSite(group, pin, fit, loc, engage, pd["d"]))  # deepest the tip may go
        return loc * c
    if fit == "press" and pd["screw"]:
        raise ValueError("a screw cannot be pressed in; use fit='heatset' or 'tap' for a screw pivot")
    f = catalog.get("fdm_fits.pin")
    r = (pd["d"] + calibrate.pin_allowance(fit, _first(f, f"{fit}_allowance_d"))) / 2
    z1 = -depth - (EXTRA if through else 0.0)
    c = _teardrop(r, z1, EXTRA, teardrop) if teardrop is not None else _cyl(r, z1, EXTRA)
    ctx.pin_site(PinSite(group, pin, fit, loc, depth, pd["d"]))
    return loc * c


TRIPOD_SCREW_D = 6.35   # 1/4-20 UNC major diameter (ISO 1222 / ASME B1.1: 1/4 in)


def tripod_socket(ctx, loc: Location, floor_t: float = 1.5, nut: str = "tripod_nut_1_4_20", slip: float = 0.2,
                  free: float = 0.55, pocket_h: float | None = None, lead_in: float = 0.8):
    """Cutter for a camera-tripod mount: a 1/4-20 clearance hole through a `floor_t` floor and a hex pocket for a
    captive catalog nut above it, so the tripod screw pulls the nut down onto the floor (pure compression, it can't
    pull out). `loc` is the screw axis on the part's bottom face, +Z into the part. The pocket is the nut's max
    across-flats + `slip` and its thickness + 0.3 (or `pocket_h`, e.g. to run it up into a cavity the nut drops
    down). Size `floor_t` so a standard tripod screw (about 4.5-6 mm protrusion) reaches through the floor into
    the nut: floor_t + nut thickness >= the screw's protrusion keeps its tip inside the nut. The nut goes into the
    BOM through ctx."""
    if isinstance(ctx, Location):
        raise TypeError("tripod_socket(ctx, loc, ...): pass the part's ctx first (it puts the nut in the BOM)")
    n = catalog.get(nut)
    if ctx is not None:
        ctx.bom_item(str(n.get("name", "1/4-20 UNC hex nut")), 1, f"catalog {nut}",
                     "captive in the tripod socket; drop it in before closing the pocket", str(n.get("buy", n.get("source", ""))))
    af, h = float(n["across_flats"]) + slip, float(n["thickness"])
    top = floor_t + (h + 0.3 if pocket_h is None else pocket_h)
    r = TRIPOD_SCREW_D / 2 + free / 2
    c = _hex(af, floor_t, top) + _cyl(r, -1.0, floor_t + 0.01)
    if lead_in:
        c += _cone(r + lead_in, r, -0.01, lead_in)
    return loc * c
