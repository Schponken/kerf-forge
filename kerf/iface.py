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

from . import catalog
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
    if f:
        out["nut_pocket_af"] = _first(f, "nut_pocket_af", "nut_trap_af", "captive_nut_af", default=out["nut_af"] + 0.3)
        out["insert_hole"] = _first(f, "heatset_hole_d", "insert_hole_d", "heat_set_hole_d", default=0) or None
        out["insert_len"] = _first(f, "heatset_length", "insert_length", "heat_set_length", default=0) or None
        out["insert_depth"] = _first(f, "heatset_min_depth", "insert_min_hole_depth", "heat_set_min_depth", default=0) or None
        out["insert_wall"] = _first(f, "heatset_min_wall", "insert_min_wall", default=0) or None
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


def _teardrop(r, z0, z1, up_deg):
    """Horizontal-hole shape for FDM: a circle with a 45-degree pointed roof toward `up_deg` (direction that is UP
    on the printer, measured in the hole's XY plane). Prints without sagging or supports."""
    from build123d import Polygon
    a = r / math.sqrt(2)
    roof = Pos(0, 0, z0) * extrude(Polygon((-a, a), (a, a), (0, r * math.sqrt(2)), align=None), z1 - z0)
    return Rot(0, 0, up_deg - 90) * roof + _cyl(r, z0, z1)


def hole(screw: str, kind: str, depth: float, counterbore_depth: float | None = None, teardrop: float | None = None,
         material: str | None = None):
    """Cutter for one hole at the origin, axis Z, surface at z=0, material at z<0. Returns (solid, grip, engage, min_engage).
    teardrop: for holes that print horizontally, the direction (deg, in the hole's XY plane) that is UP on the printer."""
    sp = screw_spec(screw, material)
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
        if hd > depth - 0.8:
            raise ValueError(f"{screw} heat-set insert needs a {hd:.1f} mm deep hole plus a 0.8 mm floor; only {depth:.1f} mm of material")
        # brass threads: ~1.3 d of engagement holds an M2-M5 screw to its proof load
        return _cyl(sp["insert_hole"] / 2, -hd, EXTRA), 0.0, hd - 0.5, min(sp["insert_len"] * 0.7, 1.5 * sp["d"])
    if kind == "tap":
        hd = min(depth - 0.8, 2.5 * sp["d"] + 1.0)
        if hd < sp["min_engage"] + 0.5:
            raise ValueError(f"{screw} pilot hole needs {sp['min_engage'] + 1.3:.1f} mm of material; only {depth:.1f} mm")
        return _cyl(sp["tap"] / 2, -hd, EXTRA), 0.0, hd - 0.5, sp["min_engage"]
    if kind == "nut_trap":
        # clearance through the plate, hex pocket open to the far face, nut pushed in from the far side.
        # Only sensible for plates up to ~3 d + nut height; thicker parts should use a heat-set insert.
        af = sp["nut_pocket_af"]
        nh = sp["nut_h"] + 0.3
        if depth > 3 * sp["d"] + nh + 2:
            raise ValueError(f"{screw} nut trap in {depth:.1f} mm of material needs a very long screw; use kind='heatset' or a thinner flange")
        s = _cyl(sp["clearance"] / 2, -depth - EXTRA, EXTRA) + _hex(af, -depth - EXTRA, -depth + nh)
        return s, 0.0, depth + 4.0, depth - nh + sp["nut_h"] * 0.9
    raise ValueError(f"unknown hole kind '{kind}' (use {KINDS_MALE + KINDS_FEMALE})")


def bolt_pattern(ctx, group: str, screw: str, points, loc: Location, kind: str, depth: float,
                 counterbore_depth: float | None = None, teardrop: float | None = None):
    """Holes at `points` (in loc's XY plane) through/into `depth` mm of material below loc.
    Registers one site per hole: male for clearance/counterbore/countersink, female for heatset/tap/nut_trap."""
    role = "male" if kind in KINDS_MALE else "female"
    cut = None
    for (x, y) in points:
        mat = (getattr(ctx, "meta", None) or {}).get("spec", {}).get("material") if ctx is not None else None
        c, grip, engage, mn = hole(screw, kind, depth, counterbore_depth, teardrop, mat)
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
                clearance: float = 0.6, top_through: bool = False):
    """Cutter for a plate a servo's mounting tabs bolt to: a window plus the four tab screw holes.

    Default (top_through=False): the body drops through the window from the TOP and the tabs rest ON the plate.
      loc: on the face the tab undersides rest on, +Z toward the servo top; material below loc (z < 0).
      Matches the servo proxy's 'tabs' joint directly.
    top_through=True: the servo goes in top-first from BEHIND; only the case top (above the tabs) passes the window and
      the tab tops press against the plate. Use this when the body has bumps low down (MG996R cable boss).
      loc: on the face the tab TOPS press against, +Z toward the servo top; material above loc (0 < z < plate_t).
      The servo proxy's 'tabs' joint (tab underside) sits at loc * Location((0, 0, -tab_t)). Set the servo's
      `tab_screws_from: bottom` in project.yaml so its screws come from behind the tabs."""
    d = servo_dims(servo)
    wx, wy = d["L"] + clearance, d["W"] + clearance
    z0 = -plate_t - EXTRA if not top_through else -EXTRA
    pocket = Pos(0, 0, z0) * Box(wx, wy, plate_t + 2 * EXTRA, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # corner reliefs ("dog-bones"): remove the sharp inside corners without rounding into the square servo body
    for sx in (-1, 1):
        for sy in (-1, 1):
            pocket += Pos(sx * (wx / 2 - 0.35), sy * (wy / 2 - 0.35), 0) * _cyl(1.0, z0, z0 + plate_t + 2 * EXTRA)
    cut = loc * pocket
    if not top_through:
        cut += bolt_pattern(ctx, group, d["screw"], d["holes"], loc, kind, plate_t)
    else:
        # female holes face the servo tabs (-Z of loc); flip the frame and mirror Y so the holes land in place
        cut += bolt_pattern(ctx, group, d["screw"], [(x, -y) for (x, y) in d["holes"]], loc * Rot(180, 0, 0), kind, plate_t)
    return cut


def horn_dims(path: str) -> dict:
    e = catalog.get(path)
    return {
        "od": _first(e, "outer_d", "od", "outer_diameter", "diameter"),
        "t": _first(e, "thickness", "disc_thickness", "plate_thickness"),
        "hub_h": _first(e, "hub_height", "hub_h", "total_height", default=0.0),
        "hub_d": _first(e, "hub_d", "hub_diameter", default=0.0),
        "bc": _first(e, "bolt_circle_d", "hole_circle_d", "bolt_circle_diameter", "pcd"),
        "n": int(_first(e, "hole_count", "holes", "n_holes", "number_of_holes")),
        "screw": str(e.get("hole_thread", e.get("thread", "M3"))).split("x")[0].split("-")[0].strip() or "M3",
        "center_screw": str(e.get("center_screw", "M3")).split("x")[0].split("-")[0].strip(),
    }


def horn_mount(ctx, horn: str, loc: Location, group: str, plate_t: float, kind: str = "clearance", start_deg: float = 45.0):
    """Holes in a printed link that bolts flat onto a servo horn face, plus an access hole for the horn's centre screw.
    loc: on the link's OUTER face (the screw-head side, away from the horn), +Z away from the horn, origin on the
    servo axis. plate_t: link thickness at the hub."""
    h = horn_dims(horn)
    pts = circle(h["n"], h["bc"], start_deg)
    cut = bolt_pattern(ctx, group, h["screw"], pts, loc, kind, plate_t)
    cs = screw_spec(h["center_screw"])
    cut += loc * _cyl(cs["head_d"] / 2 + 0.75, -plate_t - EXTRA, EXTRA)  # driver + head access to the centre screw
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
    cut = loc * _cyl((b["D"] + FIT[fit]) / 2, -dep, EXTRA)
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


def motor_mount(ctx, motor: str, loc: Location, group: str, plate_t: float, kind: str = "clearance", center_hole: float | None = None):
    """Holes for a brushless motor's base pattern. loc: on the plate face OPPOSITE the motor (screw-head side), +Z
    away from the motor, origin on the motor axis. The hole angle matches the motor proxy (same catalog data)."""
    ch = motor_center_hole(motor, center_hole)
    pts, screw = motor_holes(motor)
    cut = bolt_pattern(ctx, group, screw, pts, loc, kind, plate_t)
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


def stack_mount(ctx, stack: str, loc: Location, group: str, depth: float, kind: str = "heatset"):
    """Four holes for a flight-controller/ESC stack (30.5, 20, 25.5 mm patterns from the catalog).
    loc: on the frame face the stack sits on, +Z toward the stack."""
    e = catalog.get(stack)
    s = _first(e, "spacing", "hole_spacing", "pattern")
    screw = str(e.get("screw", "M3"))
    return bolt_pattern(ctx, group, screw, square(s), loc, kind, depth)


# ---------------------------------------------------------------- pins (printed hinges, dowels, screw pivots)
PIN_FITS = ("free", "press", "heatset", "tap")


def pin_dims(pin: str) -> dict:
    """Pin geometry: a catalog dowel ("motion.pin_3mm") or a screw size used as a pivot ("M3")."""
    if pin in catalog.load()["screws"]:
        sp = screw_spec(pin)
        from .assembly import STANDARD_SCREW_LENGTHS
        return {"d": sp["d"], "screw": True, "lengths": list(STANDARD_SCREW_LENGTHS)}
    e = catalog.get(pin)
    return {"d": _first(e, "d", "diameter", "od"), "screw": False, "lengths": [float(x) for x in e.get("lengths", [])]}


def pin_hole(ctx, pin: str, loc: Location, group: str, depth: float, fit: str = "free", through: bool = True,
             teardrop: float | None = None):
    """Cutter for one knuckle/boss of a pinned hinge. Every part the pin passes through calls this with the same group.

    loc: on the face the hole enters from, origin on the pin axis, +Z along the axis OUT of the material; the hole runs
      `depth` mm into -Z (the knuckle or boss length along the pin). through=True overshoots the far face as well.
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
            raise ValueError(f"fit '{fit}' needs a screw pivot (pin='M3'), not dowel '{pin}'")
        c, _, engage, _ = hole(pin, fit, depth, teardrop=teardrop)
        ctx.pin_site(PinSite(group, pin, fit, loc, engage, pd["d"]))  # deepest the tip may go
        return loc * c
    if fit == "press" and pd["screw"]:
        raise ValueError("a screw cannot be pressed in; use fit='heatset' or 'tap' for a screw pivot")
    f = catalog.get("fdm_fits.pin")
    r = (pd["d"] + _first(f, f"{fit}_allowance_d")) / 2
    z1 = -depth - (EXTRA if through else 0.0)
    c = _teardrop(r, z1, EXTRA, teardrop) if teardrop is not None else _cyl(r, z1, EXTRA)
    ctx.pin_site(PinSite(group, pin, fit, loc, depth, pd["d"]))
    return loc * c
