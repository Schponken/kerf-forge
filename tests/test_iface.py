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
    t = 5
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
