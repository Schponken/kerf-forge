"""Purchased parts and keep-out volumes, modelled from the catalog so collisions, fastener alignment and mass are real.

project.yaml:  purchased: {servo: {catalog: servos.MG996R, proxy: servo, groups: {tabs: bracket_servo}}}
`proxy` defaults from the catalog category. `groups` maps this proxy's fastener-site sets to group names.

Every proxy documents its frame and joints below. Add new proxy kinds with @proxy("name").
"""
from __future__ import annotations

import math

from build123d import Align, Axis, Box, Cylinder, Location, Pos, Rot

from . import catalog, iface
from .ctx import Site

REG = {}
DEFAULT_BY_CATEGORY = {"servos": "servo", "servo_horns": "horn", "bearings": "bearing", "steppers": "stepper",
                       "rods": "rod", "boards": "board"}


def proxy(name):
    def deco(fn):
        REG[name] = fn
        return fn
    return deco


def build(ctx, spec: dict):
    kind = spec.get("proxy") or DEFAULT_BY_CATEGORY.get(str(spec.get("catalog", "")).split(".")[0])
    if kind not in REG:
        raise ValueError(f"{ctx.id}: unknown proxy '{kind}' (have {sorted(REG)}); set proxy: in project.yaml")
    return REG[kind](ctx, spec)


def _g(spec, key, default=None):
    g = (spec.get("groups") or {}).get(key, default)
    return g


def _box(x, y, z, z0=0.0):
    return Pos(0, 0, z0) * Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _cyl(r, h, z0=0.0):
    return Pos(0, 0, z0) * Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


@proxy("servo")
def servo(ctx, spec):
    """Frame: origin at the centre of the tab underside, X along the body length (output end at +X), +Z toward the output.
    Joints: tabs (rigid, origin), output (revolute about the output axis, at the top of the spline).
    Sites: group[tabs] male screws through the 4 tab holes, head on top of the tabs."""
    d = iface.servo_dims(spec["catalog"])
    body = _box(d["L"], d["W"], d["H"], z0=-d["tab_z"])
    tabs = _box(d["span"], d["W"], d["tab_t"], z0=0)
    shaft = Pos(d["out_x"], 0, 0) * _cyl(d["spline_d"] / 2, d["shaft_h"], z0=d["top"])
    for (x, y) in d["holes"]:
        tabs -= Pos(x, y, -1) * Cylinder(d["hole_d"] / 2, d["tab_t"] + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = body + tabs + shaft
    if _g(spec, "tabs"):
        for (x, y) in d["holes"]:
            ctx.site(Site(_g(spec, "tabs"), "male", d["screw"], "clearance", Location((x, y, d["tab_t"])), grip=d["tab_t"]))
    ctx.rigid("tabs", Location((0, 0, 0)))
    top = d["top"] + d["shaft_h"]
    rng = tuple(spec.get("range", (-90, 90)))
    ctx.revolute("output", Axis((d["out_x"], 0, top), (0, 0, 1)), range=rng)
    ctx.rigid("output_base", Location((d["out_x"], 0, d["top"])))
    return ctx.finish(s, color="#30343a")


@proxy("horn")
def horn(ctx, spec):
    """Round disc horn. Frame: origin on the servo axis at the hub's bottom (where it seats on the spline top), +Z up.
    Joints: spline (rigid, origin), face (rigid, top face of the disc).
    Sites: group[holes] female threaded holes on the top face."""
    h = iface.horn_dims(spec["catalog"])
    hub_h = h["hub_h"] or h["t"]
    hub_d = h["hub_d"] or h["od"] * 0.45
    # the disc sits on top of the hub; the hub wraps the spline (modelled as an overlap allowed with the servo)
    disc_z = max(hub_h - h["t"], 0.0)
    s = _cyl(h["od"] / 2, h["t"], z0=disc_z)
    if hub_h > h["t"]:
        s += _cyl(hub_d / 2, hub_h - h["t"] + 0.01, z0=0)
    top = disc_z + h["t"]
    for (x, y) in iface.circle(h["n"], h["bc"], spec.get("hole_start_deg", 45.0)):
        s -= Pos(x, y, disc_z - 1) * Cylinder(iface.screw_spec(h["screw"])["tap"] / 2, h["t"] + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if _g(spec, "holes"):
            ctx.site(Site(_g(spec, "holes"), "female", h["screw"], "threaded", Location((x, y, top)),
                          engage=h["t"] + 2.0, min_engage=h["t"] * 0.8))
    ctx.rigid("spline", Location((0, 0, 0)))
    ctx.rigid("face", Location((0, 0, top)))
    return ctx.finish(s, color="#9aa3ad")


@proxy("bearing")
def bearing(ctx, spec):
    """Ball bearing ring. Frame: origin on the axis at one face, +Z through the bearing. Joints: face (origin), top."""
    b = iface.bearing_dims(spec["catalog"])
    s = _cyl(b["D"] / 2, b["B"]) - Pos(0, 0, -1) * Cylinder(b["d"] / 2, b["B"] + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("face", Location((0, 0, 0)))
    ctx.rigid("top", Location((0, 0, b["B"])))
    rng = tuple(spec.get("range", (-180, 180)))
    ctx.revolute("spin", Axis((0, 0, b["B"]), (0, 0, 1)), range=rng)
    return ctx.finish(s, color="#b8c0c8")


@proxy("rod")
def rod(ctx, spec):
    """Rod or tube of length spec['length'] (mm). Frame: origin at the centre of one end, +Z along the rod.
    Joints: end_a (origin), end_b (far end), mid."""
    e = catalog.get(spec["catalog"])
    od = catalog.num(e, "od", "outer_d", "diameter")
    idd = catalog.num(e, "id", "inner_d", default=0.0)
    L = float(spec["length"])
    s = _cyl(od / 2, L)
    if idd > 0:
        s -= Pos(0, 0, -1) * Cylinder(idd / 2, L + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("end_a", Location((0, 0, 0)))
    ctx.rigid("end_b", Location((0, 0, L)))
    ctx.rigid("mid", Location((0, 0, L / 2)))
    return ctx.finish(s, color="#1f2326")


@proxy("box")
def box(ctx, spec):
    """Generic block for parts without a dedicated proxy (battery, camera, XT60, stack...). spec: size [x, y, z] or a
    catalog entry with L/W/H; joints: {label: [x, y, z]} extra rigid joints. Frame: origin at the centre of the bottom face.
    Joints: bottom (origin), top (centre of the top face)."""
    if "size" in spec:
        x, y, z = spec["size"]
    else:
        e = catalog.get(spec["catalog"])
        x = catalog.num(e, "length", "l", "L")
        y = catalog.num(e, "width", "w", "W")
        z = catalog.num(e, "height", "h", "H", "thickness")
    s = _box(x, y, z)
    ctx.rigid("bottom", Location((0, 0, 0)))
    ctx.rigid("top", Location((0, 0, z)))
    for lab, p in (spec.get("joints") or {}).items():
        ctx.rigid(lab, Location(tuple(p)))
    return ctx.finish(s, color=spec.get("color", "#2b2f33"))


@proxy("motor")
def motor(ctx, spec):
    """Outrunner brushless motor. Frame: origin at the centre of the base (mounting face), +Z toward the prop.
    Joints: base (origin), prop (top of the shaft = prop seat).
    Sites: group[mount] female threaded holes in the base, +Z pointing out of the base (toward the frame, i.e. -Z)."""
    e = catalog.get(spec["catalog"])
    bell_d = catalog.num(e, "bell_d", "bell_diameter", "diameter", "outer_d")
    body_h = catalog.num(e, "body_h", "height", "bell_height", default=bell_d * 0.6)
    shaft_d = catalog.num(e, "shaft_d", "shaft_diameter", default=5.0)
    shaft_h = catalog.num(e, "shaft_h", "shaft_length", default=12.0)
    s = _cyl(bell_d / 2, body_h) + _cyl(shaft_d / 2, shaft_h, z0=body_h)
    pts, screw = iface.motor_holes(spec["catalog"])
    depth = catalog.num(e, "max_screw_depth", "thread_depth", default=4.0)
    sp = iface.screw_spec(screw)
    for (x, y) in pts:
        s -= Pos(x, y, 0) * Cylinder(sp["tap"] / 2, depth, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if _g(spec, "mount"):
            ctx.site(Site(_g(spec, "mount"), "female", screw, "threaded", Location((x, y, 0)) * Rot(180, 0, 0),
                          engage=depth, min_engage=min(depth, 1.5 * sp["d"]) * 0.9))
    ctx.rigid("base", Location((0, 0, 0)))
    ctx.rigid("prop", Location((0, 0, body_h + shaft_h * 0.4)))
    return ctx.finish(s, color="#3b4148")


@proxy("prop_disc")
def prop_disc(ctx, spec):
    """Keep-out: the disc a spinning prop sweeps. diameter from catalog (or spec['diameter']), thickness spec['h']
    (default 10 mm). Frame: origin at the centre of the disc's bottom face. Joint: hub (origin)."""
    if "diameter" in spec:
        dia = float(spec["diameter"])
    else:
        e = catalog.get(spec["catalog"])
        dia = catalog.num(e, "diameter_mm", "diameter", "d")
    s = _cyl(dia / 2, float(spec.get("h", 10.0)))
    ctx.rigid("hub", Location((0, 0, 0)))
    return ctx.finish(s)


@proxy("stepper")
def stepper(ctx, spec):
    """NEMA stepper. Frame: origin at the centre of the front face, +Z along the shaft (out of the motor).
    Joints: face (origin), shaft (revolute at the shaft tip). Sites: group[face] female threaded holes."""
    e = catalog.get(spec["catalog"])
    a = catalog.num(e, "face", "face_size", "width")
    L = float(spec.get("length", catalog.num(e, "body_length", "length", default=40.0)))
    sp = catalog.num(e, "hole_spacing", "bolt_spacing")
    boss_d = catalog.num(e, "boss_d", "center_boss_d", "pilot_d")
    boss_h = catalog.num(e, "boss_h", "center_boss_h", "pilot_h", default=2.0)
    sd = catalog.num(e, "shaft_d", "shaft_diameter")
    sl = catalog.num(e, "shaft_length", "shaft_l", default=24.0)
    screw = str(e.get("thread", e.get("screw", "M3"))).split("x")[0].strip()
    s = _box(a, a, L, z0=-L) + _cyl(boss_d / 2, boss_h) + _cyl(sd / 2, sl)
    for (x, y) in iface.square(sp):
        s -= Pos(x, y, -4.5) * Cylinder(iface.screw_spec(screw)["tap"] / 2, 4.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if _g(spec, "face"):
            ctx.site(Site(_g(spec, "face"), "female", screw, "threaded", Location((x, y, 0)), engage=4.5, min_engage=3.0))
    ctx.rigid("face", Location((0, 0, 0)))
    ctx.revolute("shaft", Axis((0, 0, sl), (0, 0, 1)), range=tuple(spec.get("range", (-180, 180))))
    return ctx.finish(s, color="#3b4148")


@proxy("board")
def board(ctx, spec):
    """Circuit board as a plate with its mounting holes. Frame: origin at the board centre, bottom face, +Z up.
    Joints: bottom (origin). Sites: group[holes] male screws through the board from the top (grip = board thickness)."""
    e = catalog.get(spec["catalog"])
    L = catalog.num(e, "length", "board_length", "l")
    W = catalog.num(e, "width", "board_width", "w")
    t = catalog.num(e, "thickness", "pcb_thickness", default=1.6)
    comp = float(spec.get("component_height", catalog.num(e, "component_height", default=0.0)))
    s = _box(L, W, t)
    if comp > 0:
        s += _box(L * 0.9, W * 0.9, comp, z0=t)
    holes = e.get("holes")
    screw = str(e.get("hole_screw", "M2.5"))
    if holes and _g(spec, "holes"):
        for (x, y) in holes:
            ctx.site(Site(_g(spec, "holes"), "male", screw, "clearance", Location((x, y, t)), grip=t))
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(s, color="#1e6b3a")


@proxy("stack")
def stack(ctx, spec):
    """Flight-controller/ESC stack. Frame: origin at the centre of the bottom face (on the frame), +Z up.
    Joints: bottom (origin), top. Sites: group[holes] male screws from the top through the whole stack
    (grip = stack height), into the frame's inserts/nuts. Catalog: drone.stacks.* {spacing, screw, board_size, height}."""
    e = catalog.get(spec["catalog"])
    s_ = catalog.num(e, "spacing")
    size = catalog.num(e, "board_size", default=s_ + 6.0)
    h = float(spec.get("height", catalog.num(e, "height", default=15.0)))
    screw = str(e.get("screw", "M3"))
    body = _box(size, size, h)
    for (x, y) in iface.square(s_):
        body -= Pos(x, y, -1) * Cylinder(iface.screw_spec(screw)["clearance"] / 2, h + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if _g(spec, "holes"):
            ctx.site(Site(_g(spec, "holes"), "male", screw, "clearance", Location((x, y, h)), grip=h))
    ctx.rigid("bottom", Location((0, 0, 0)))
    ctx.rigid("top", Location((0, 0, h)))
    return ctx.finish(body, color="#1e3b6b")
