"""Both sides of every interface, assembled and proven to line up with the right fit. Run: .venv/bin/pytest -q"""
import textwrap

import pytest
from build123d import Align, Box, Location

from kerf import assembly as A, geom, iface, project as P


def _proj(tmp, yaml_text, parts):
    d = tmp / "p"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(yaml_text))
    for n, src in parts.items():
        (d / "parts" / f"{n}.py").write_text(textwrap.dedent(src))
    proj = P.build(P.load(str(d)))
    errs = {k: v.error for k, v in proj.items.items() if v.error}
    assert not errs, errs
    asm = A.plan(proj)
    A.solve(asm)
    return proj, asm


PLATE_ON_BLOCK = """
name: t
parts:
  block: {file: parts/block.py}
  plate: {file: parts/plate.py}
assembly:
  root: block
  joints: [{parent: block.top, child: plate.bottom}]
"""
BLOCK = """
from build123d import *
from kerf import iface
def build(ctx):
    H = {H}
    s = Box(40, 40, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "g", "M3", iface.rect(24, 24), Location((0, 0, H)), kind="{female}", depth=H)
    ctx.rigid("top", Location((0, 0, H)))
    return ctx.finish(s)
"""
PLATE = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(40, 40, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "g", "M3", iface.rect(24, 24), Location((0, 0, 6)), kind="{male}", depth=6)
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(s)
"""


@pytest.mark.parametrize("male", ["clearance", "counterbore", "countersink"])
@pytest.mark.parametrize("female", ["heatset", "tap", "nut_trap"])
def test_bolt_pattern_pairs(tmp_path, male, female):
    proj, asm = _proj(tmp_path, PLATE_ON_BLOCK, {"block": BLOCK.replace("{female}", female).replace("{H}", "8" if female == "nut_trap" else "20"),
                                                  "plate": PLATE.replace("{male}", male)})
    joints, problems = A.fasteners(asm)
    assert problems == [], problems
    assert len(joints) == 4
    assert all(j["length_mm"] is not None for j in joints)
    assert A.interference(asm) == []
    # the plate keeps one solid with 4 holes, the block too
    assert len(geom.solids(proj.items["plate"].shape)) == 1


def test_hole_sizes_come_from_catalog():
    sp = iface.screw_spec("M3")
    c, *_ = iface.hole("M3", "clearance", 5)
    bb = c.bounding_box()
    assert bb.size.X == pytest.approx(sp["clearance"], abs=1e-6)
    c, *_ = iface.hole("M3", "heatset", 10)
    assert c.bounding_box().size.X == pytest.approx(sp["insert_hole"], abs=1e-6)


def test_heatset_refuses_thin_plate():
    with pytest.raises(ValueError):
        iface.hole("M3", "heatset", 3)


def test_nut_trap_refuses_thick_block():
    with pytest.raises(ValueError):
        iface.hole("M3", "nut_trap", 25)


def test_nut_trap_recess_sinks_the_nut():
    # 7 mm plate: the plain pocket is nut_h + 0.3 deep from the far face, the recessed one 1 mm deeper; the minimum
    # engagement (screw must reach 90 % through the nut) drops by the same 1 mm, so a 1 mm shorter screw fills it and
    # its tip ends 1 mm below the far face instead of level with the pocket top
    sp = iface.screw_spec("M3")
    c0, _, _, mn0 = iface.hole("M3", "nut_trap", 7)
    c1, _, _, mn1 = iface.hole("M3", "nut_trap", 7, nut_recess=1.0)
    assert mn0 - mn1 == pytest.approx(1.0)
    assert mn1 == pytest.approx(7 - 1.0 - (sp["nut_h"] + 0.3) + 0.9 * sp["nut_h"])
    assert c1.volume > c0.volume                                 # the pocket is deeper
    assert c1.bounding_box().min.Z == pytest.approx(c0.bounding_box().min.Z)   # opens on the same far face
    with pytest.raises(ValueError):
        iface.hole("M3", "nut_trap", 4, nut_recess=1.0)           # < 1 mm of plate would be left under the nut


SERVO_YAML = """
name: t
parts:
  plate: {file: parts/plate.py}
purchased:
  servo: {catalog: servos.MG996R, proxy: servo, groups: {tabs: s}}
  horn: {catalog: servo_horns.aluminum_25T, proxy: horn, groups: {holes: h}}
  link: {proxy: box, size: [1, 1, 1]}
parts_link: {}
assembly:
  root: plate
  joints:
    - {parent: plate.seat, child: servo.tabs}
    - {parent: servo.output, child: horn.spline, name: out, range: [-90, 90]}
    - {parent: horn.face, child: arm.mount}
"""
SERVO_PLATE = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(90, 60, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.servo_mount(ctx, "servos.MG996R", Location((0, 0, 8)), group="s", plate_t=8, kind="heatset")
    ctx.rigid("seat", Location((0, 0, 8)))
    return ctx.finish(s)
"""
ARM = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(30, 30, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.horn_mount(ctx, "servo_horns.aluminum_25T", Location((0, 0, 5)), group="h", plate_t=5)
    ctx.rigid("mount", Location((0, 0, 0)))
    return ctx.finish(s)
"""


def test_servo_and_horn_mounts(tmp_path):
    y = SERVO_YAML.replace("  link: {proxy: box, size: [1, 1, 1]}\n", "").replace("parts_link: {}\n", "")
    y = y.replace("parts:\n  plate: {file: parts/plate.py}", "parts:\n  plate: {file: parts/plate.py}\n  arm: {file: parts/arm.py}")
    proj, asm = _proj(tmp_path, y, {"plate": SERVO_PLATE, "arm": ARM})
    joints, problems = A.fasteners(asm)
    assert problems == [], problems
    assert len([j for j in joints if j["group"] == "s"]) == 4
    assert len([j for j in joints if j["group"] == "h"]) == iface.horn_dims("servo_horns.aluminum_25T")["n"]
    assert A.interference(asm) == [], A.interference(asm)
    sw = A.sweeps(asm, samples=5)
    assert all(s["clear"] for s in sw)


def test_bearing_seat_press_fit():
    b = iface.bearing_dims("bearings.608")
    cut = iface.bearing_seat(None, "bearings.608", Location((0, 0, 0)), fit="press")
    assert cut.bounding_box().size.X == pytest.approx(b["D"] + iface.FIT["press"], abs=1e-6)


MOTOR_YAML = """
name: t
parts:
  arm: {file: parts/arm.py}
purchased:
  motor: {catalog: drone.motors.2207_1855kv_6s, proxy: motor, groups: {mount: m}}
  stack: {catalog: drone.stacks.fc_30_5, proxy: stack, groups: {holes: s}}
keepouts:
  prop: {catalog: drone.props.5_1in, proxy: prop_disc, owner: motor}
assembly:
  root: arm
  joints:
    - {parent: arm.motor_seat, child: motor.base}
    - {parent: arm.stack_seat, child: stack.bottom}
    - {parent: motor.prop, child: prop.hub}
"""
MOTOR_ARM = """
from build123d import *
from kerf import iface
M = "drone.motors.2207_1855kv_6s"
def build(ctx):
    t = 5.5   # M3 x 8 leaves 2.5 mm in the 3 mm motor thread: bottoming margin for the screw length tolerance
    s = Box(140, 40, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    # screws come up from underneath: loc on the bottom face, +Z pointing down (toward the screw heads)
    s -= iface.motor_mount(ctx, M, Location((120, 0, 0), (180, 0, 0)), group="m", plate_t=t)
    s -= iface.stack_mount(ctx, "drone.stacks.fc_30_5", Location((25, 0, t)), group="s", depth=t, kind="nut_trap")
    ctx.rigid("motor_seat", Location((120, 0, t)))
    ctx.rigid("stack_seat", Location((25, 0, t)))
    return ctx.finish(s)
"""


def test_motor_and_stack_mounts_align(tmp_path):
    proj, asm = _proj(tmp_path, MOTOR_YAML, {"arm": MOTOR_ARM})
    joints, problems = A.fasteners(asm)
    assert problems == [], problems
    assert len([j for j in joints if j["group"] == "m"]) == 4
    assert len([j for j in joints if j["group"] == "s"]) == 4
    # motor screws must not reach deeper than the catalog's max_screw_depth into the motor base
    from kerf import catalog
    depth = catalog.num(catalog.get("drone.motors.2207_1855kv_6s"), "max_screw_depth")
    for j in joints:
        if j["group"] == "m":
            assert j["length_mm"] - j["grip_mm"] <= depth + 1e-6
    hits = A.interference(asm)
    assert hits == [], hits


def test_teardrop_hole_points_up():
    c, *_ = iface.hole("M3", "clearance", 5, teardrop=90)       # roof toward +Y
    bb = c.bounding_box()
    r = iface.screw_spec("M3")["clearance"] / 2
    assert bb.max.Y == pytest.approx(r * 2 ** 0.5, abs=1e-3) and bb.min.Y == pytest.approx(-r, abs=1e-3)
    c, *_ = iface.hole("M3", "clearance", 5, teardrop=0)        # roof toward +X
    assert c.bounding_box().max.X == pytest.approx(r * 2 ** 0.5, abs=1e-3)


def test_pilot_hole_uses_material_specific_size():
    pla = iface.screw_spec("M3")["tap"]
    petg = iface.screw_spec("M3", "PETG")["tap"]
    assert petg == pytest.approx(2.60) and pla == pytest.approx(2.72)
    assert iface.screw_spec("M3", "CF-PETG")["tap"] == pytest.approx(2.60)
    c, *_ = iface.hole("M3", "tap", 8, material="PETG")
    assert c.bounding_box().size.X == pytest.approx(2.60, abs=1e-6)


TOP_YAML = """
name: t
parts:
  wall: {file: parts/wall.py, material: PETG}
purchased:
  servo: {catalog: servos.MG996R, proxy: servo, groups: {tabs: s}, tab_screws_from: bottom}
assembly:
  root: wall
  joints: [{parent: wall.seat, child: servo.tabs}]
"""
TOP_WALL = """
from build123d import *
from kerf import iface
def build(ctx):
    t = 8
    s = Box(80, 50, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    face = Location((0, 0, 0))                       # tab tops press on the underside; servo top goes up through
    s -= iface.servo_mount(ctx, "servos.MG996R", face, group="s", plate_t=t, kind="tap", top_through=True)
    tab_t = iface.servo_dims("servos.MG996R")["tab_t"]
    ctx.rigid("seat", face * Location((0, 0, -tab_t)))
    return ctx.finish(s)
"""


def test_servo_mount_top_through(tmp_path):
    proj, asm = _proj(tmp_path, TOP_YAML, {"wall": TOP_WALL})
    joints, problems = A.fasteners(asm)
    assert problems == [], problems
    assert len(joints) == 4 and all(abs(j["gap_mm"]) < 1e-6 for j in joints)
    assert A.interference(asm) == [], A.interference(asm)       # only the case top passes the window
    d = iface.servo_dims("servos.MG996R")
    sbb = proj.items["servo"].shape.bounding_box()
    assert sbb.min.Z == pytest.approx(-d["tab_t"] - d["tab_z"], abs=1e-3)   # body hangs below the plate


def test_part_notes_reach_the_report(tmp_path):
    from kerf import pipeline
    d = tmp_path / "n"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text("name: n\nparts:\n  a: {file: parts/a.py}\nassembly:\n  root: a\n  joints: []\n")
    (d / "parts" / "a.py").write_text("from build123d import *\ndef build(ctx):\n    ctx.notes.append('fillet skipped')\n"
                                      "    return ctx.finish(Box(20, 20, 5))\n")
    rep = pipeline.run(str(d), sweeps=False)
    assert rep["parts"]["a"]["notes"] == ["fillet skipped"]
    assert any("fillet skipped" in w for w in rep["warnings"])


@pytest.mark.parametrize("top_through", [False, True])
def test_servo_window_lead_in(top_through):
    """The window is c wider per side at its entry face (z = 0), tapers at 45 degrees, is nominal past the chamfer,
    and c is the largest value <= 0.5 that leaves the minimum wall to every tab screw hole on the entry face."""
    from build123d import Box as _Box, Pos
    from kerf.ctx import Ctx
    d = iface.servo_dims("servos.MG996R")
    wx, wy = d["L"] + 0.6, d["W"] + 0.6
    c0 = iface.servo_lead_in("servos.MG996R", "tap", 8, 0.5)
    assert 0.2 <= c0 <= 0.5
    cut = iface.servo_mount(Ctx("t", {}), "servos.MG996R", Location((0, 0, 0)), group="s", plate_t=8, kind="tap",
                            top_through=top_through, lead_in=0.5)
    sgn = 1 if top_through else -1   # material side of the mount face

    def widths(z):
        """Window width along X (strip at y=0) and along Y (strip at x=0): clear of the corner dog-bones."""
        sx = (cut & (Pos(0, 0, z) * _Box(200, 0.2, 0.002))).solids()
        sy = (cut & (Pos(0, 0, z) * _Box(0.2, 200, 0.002))).solids()
        wxz = max(b.bounding_box().size.X for b in sx if abs(b.bounding_box().center().X) < 1)
        wyz = max(b.bounding_box().size.Y for b in sy if abs(b.bounding_box().center().Y) < 1)
        return wxz, wyz

    for z in (0.01, c0 / 2, c0 - 0.05, 2.0, 7.5):
        c = max(0.0, c0 - (z - 0.001))   # the slab's face-side edge sets the measured width
        x, y = widths(sgn * z)
        assert x == pytest.approx(wx + 2 * c, abs=0.01), (z, x)
        assert y == pytest.approx(wy + 2 * c, abs=0.01), (z, y)
    # the wall between the window and each screw hole, measured on the entry face itself, meets the rule
    face = (cut & (Pos(0, 0, sgn * 0.001) * _Box(200, 200, 0.002))).solids()
    window = max(face, key=lambda s_: s_.volume)
    holes = [s_ for s_ in face if s_ is not window and abs(s_.bounding_box().center().X) > wx / 2]
    assert len(holes) == len(d["holes"])
    assert min(window.distance_to(h) for h in holes) >= iface.MIN_WALL_AROUND_HOLE - 0.01
    # lead_in=0 gives the plain window; a hole too big for any chamfer drops it
    plain = iface.servo_mount(Ctx("t", {}), "servos.MG996R", Location((0, 0, 0)), group="s", plate_t=8, kind="tap",
                              top_through=top_through, lead_in=0)
    assert plain.volume < cut.volume
    assert iface.servo_lead_in("servos.MG996R", "clearance", 8, 0.5) == 0.0
