"""Every function in kerf/iface.py, proven on real assembled geometry.

For each interface both sides are built, assembled with the joint solver, and then the CUT HOLES themselves are probed
(not just the fastener-site bookkeeping): a probe slightly smaller than the catalog size must miss the part and one
slightly larger must hit it, so each hole is exactly the catalog size and exactly on the site axis. Window, bearing and
centre-hole clearances are probed the same way against the purchased-part proxies.
Run: .venv/bin/pytest -q tests/test_iface_fit.py
"""
import math
import textwrap

import pytest
from build123d import Align, Box, Cylinder, Location, Pos

from kerf import assembly as A, catalog, geom, iface, project as P

TOL = 0.02   # probe step on diameter (mm): proves each size to +-0.02 mm
HIT = 1e-4   # mm^3: any real overlap


# ----------------------------------------------------------------------------------------------- helpers
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


def _overlap(shape, probe) -> float:
    return geom.volume(shape & probe)


def _cyl(r, z0, z1):
    return Pos(0, 0, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def assert_size(shape, world, make, size, z0, z1, what):
    """make(size, z0, z1) builds a probe in the hole's frame. Proves the opening is exactly `size` (+-TOL) over z0..z1."""
    assert z1 > z0
    small = _overlap(shape, world * make(size - TOL, z0, z1))
    big = _overlap(shape, world * make(size + TOL, z0, z1))
    assert small < HIT, f"{what}: material inside {size - TOL:.2f} mm (expected an opening of {size:.2f} mm), overlap {small:.4f} mm^3"
    assert big > HIT, f"{what}: opening is wider than {size + TOL:.2f} mm (expected {size:.2f} mm)"


def bore(shape, world, d, z0, z1, what):
    assert_size(shape, world, lambda s, a, b: _cyl(s / 2, a, b), d, z0, z1, what)


def hexagon(shape, world, af, z0, z1, what):
    assert_size(shape, world, lambda s, a, b: iface._hex(s, a, b), af, z0, z1, what)


def has_floor(shape, world, z, what):
    assert _overlap(shape, world * _cyl(0.4, z - 0.3, z)) > HIT, f"{what}: blind hole has no floor below {z:.2f} mm"


def check_printed_holes(proj, material=None):
    """Probe every fastener hole cut into every PRINTED part against the catalog sizes for its kind. Returns the count."""
    n = 0
    for iid, it in proj.items.items():
        if it.role != "printed":
            continue
        shape = it.shape
        for s in shape.kerf_sites:
            w = shape.location * s.loc
            sp = iface.screw_spec(s.screw, (it.spec or {}).get("material", material))
            tag = f"{iid} {s.screw} {s.kind}"
            if s.kind == "clearance":
                bore(shape, w, sp["clearance"], -s.grip + 0.2, -0.2, tag)
                assert sp["clearance"] > sp["d"], f"{tag}: clearance hole not larger than the screw"
            elif s.kind == "counterbore":
                bore(shape, w, sp["clearance"], -s.grip + 0.2, -0.2, tag)
                bore(shape, w, sp["head_d"] + 0.6, 0.2, 0.2 + 0.5, tag + " head pocket")
                assert sp["head_d"] + 0.6 > sp["head_d"]
            elif s.kind == "countersink":
                r_top = sp["csk_d"] / 2 + 0.2
                h = r_top - sp["clearance"] / 2
                bore(shape, w, sp["clearance"], -s.grip + 0.2, -h - 0.2, tag)
                bore(shape, w, 2 * r_top, -0.004, 0.0, tag + " countersink rim")
                assert 2 * r_top > sp["csk_d"]
            elif s.kind == "heatset":
                hd = s.engage + 0.5
                bore(shape, w, sp["insert_hole"], -hd + 0.2, -0.2, tag)
                has_floor(shape, w, -hd, tag)
                assert hd >= sp["insert_depth"] - 1e-9 and hd > sp["insert_len"]
            elif s.kind == "tap":
                hd = s.engage + 0.5
                bore(shape, w, sp["tap"], -hd + 0.2, -0.2, tag)
                has_floor(shape, w, -hd, tag)
                assert sp["tap"] < sp["d"], f"{tag}: pilot must be smaller than the thread to cut it"
            elif s.kind == "nut_trap":
                depth = s.engage - 4.0
                nh = sp["nut_h"] + 0.3
                bore(shape, w, sp["clearance"], -depth + nh + 0.2, -0.2, tag)
                hexagon(shape, w, sp["nut_pocket_af"], -depth + 0.1, -depth + nh - 0.1, tag + " nut pocket")
                assert sp["nut_pocket_af"] > sp["nut_af"]
                assert nh > sp["nut_h"]
            else:
                raise AssertionError(f"untested hole kind {s.kind}")
            n += 1
    return n


def assert_assembly_ok(asm, n_joints=None):
    joints, problems = A.fasteners(asm)
    assert problems == [], problems
    if n_joints is not None:
        assert len(joints) == n_joints
    assert all(j["length_mm"] is not None and abs(j["gap_mm"]) < 1e-6 for j in joints), joints
    hits = A.interference(asm)
    assert hits == [], hits
    return joints


# ----------------------------------------------------------------------------------------------- pure helpers
def test_patterns():
    assert iface.rect(30, 20) == [(-15, -10), (15, -10), (15, 10), (-15, 10)]
    assert iface.square(16) == iface.rect(16, 16)
    pts = iface.circle(4, 16, 45)
    assert len(pts) == 4
    for k, (x, y) in enumerate(pts):
        assert math.hypot(x, y) == pytest.approx(8)
        assert math.degrees(math.atan2(y, x)) % 360 == pytest.approx((45 + 90 * k) % 360)


@pytest.mark.parametrize("size", sorted(catalog.get("fdm_holes")))
def test_screw_spec_is_the_catalog(size):
    if not isinstance(catalog.get(f"fdm_holes.{size}"), dict) or not size.startswith("M"):
        pytest.skip("not a metric screw entry")
    f, s = catalog.get(f"fdm_holes.{size}"), catalog.get(f"screws.{size}")
    sp = iface.screw_spec(size)
    assert sp["d"] == float(size[1:])
    assert sp["clearance"] == f["clearance_hole"] and sp["tap"] == f["self_tap_pilot"]
    assert sp["nut_pocket_af"] == f["nut_pocket_af"]
    if "heatset_hole_d" in f:
        assert sp["insert_hole"] == f["heatset_hole_d"] and sp["insert_len"] == f["heatset_length"]
    # physical sanity of the catalog itself: screw passes the clearance, pilot is under the thread, nut fits its pocket
    assert sp["tap"] < sp["d"] < sp["clearance"] < sp["head_d"]
    if sp["nut_af"]:
        assert sp["nut_af"] < sp["nut_pocket_af"] <= sp["nut_af"] + 0.5


@pytest.mark.parametrize("path", [f"servos.{k}" for k in catalog.get("servos")])
def test_servo_dims_are_the_catalog(path):
    d, e = iface.servo_dims(path), catalog.get(path)
    assert d["L"] == catalog.num(e, "body_l", "body_length", "length")
    assert d["span"] > d["L"] and d["hx"] < d["span"] and d["hx"] > d["L"], "tab holes must sit on the tabs, outside the body"
    assert d["hole_d"] >= iface.screw_spec(d["screw"])["d"], "chosen screw must pass the tab hole"
    assert 0 < d["out_x"] < d["L"] / 2


def test_horn_and_bearing_dims_are_the_catalog():
    h, e = iface.horn_dims("servo_horns.aluminum_25T"), catalog.get("servo_horns.aluminum_25T")
    assert (h["od"], h["bc"], h["n"], h["screw"]) == (e["outer_d"], e["bolt_circle_d"], e["hole_count"], "M3")
    for k, b in catalog.get("bearings").items():
        if not isinstance(b, dict) or "outer_d" not in b:
            continue
        d = iface.bearing_dims(f"bearings.{k}")
        assert (d["d"], d["D"], d["B"]) == (b["bore"], b["outer_d"], b["width"])


@pytest.mark.parametrize("motor", sorted(catalog.get("drone.motors")))
def test_motor_holes_are_the_catalog(motor):
    e = catalog.get(f"drone.motors.{motor}")
    pts, screw = iface.motor_holes(f"drone.motors.{motor}")
    assert screw == e["mount_screw"] and len(pts) == 4
    for x, y in pts:
        assert math.hypot(x, y) == pytest.approx(e["bolt_circle_d"] / 2)


# ----------------------------------------------------------------------------------------------- bolt_pattern / hole
PAIR_YAML = """
name: t
parts:
  block: {file: parts/block.py, material: PETG}
  plate: {file: parts/plate.py, material: PETG}
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
    s -= iface.bolt_pattern(ctx, "g", "{S}", iface.rect(24, 24), Location((0, 0, H)), kind="{female}", depth=H)
    ctx.rigid("top", Location((0, 0, H)))
    return ctx.finish(s)
"""
PLATE = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(40, 40, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "g", "{S}", iface.rect(24, 24), Location((0, 0, 5)), kind="{male}", depth=5)
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(s)
"""


@pytest.mark.parametrize("screw", ["M2", "M2.5", "M3"])
@pytest.mark.parametrize("male,female", [("clearance", "heatset"), ("counterbore", "tap"), ("countersink", "nut_trap"),
                                         ("clearance", "nut_trap"), ("countersink", "heatset"), ("counterbore", "heatset")])
def test_bolt_pattern_holes_are_catalog_size_and_on_axis(tmp_path, screw, male, female):
    H = {"nut_trap": "6" if screw != "M3" else "8"}.get(female, "16")
    src = {"block": BLOCK.replace("{female}", female).replace("{H}", H).replace("{S}", screw),
           "plate": PLATE.replace("{male}", male).replace("{S}", screw)}
    proj, asm = _proj(tmp_path, PAIR_YAML, src)
    assert_assembly_ok(asm, 4)
    assert check_printed_holes(proj) == 8
    # the screw itself (nominal diameter, along the matched axis, through the whole grip) clears the male part
    plate = proj.items["plate"].shape
    for s in plate.kerf_sites:
        w = plate.location * s.loc
        assert _overlap(plate, w * _cyl(iface.screw_spec(screw)["d"] / 2, -5.5, 0.5)) < HIT


def test_teardrop_clearance_still_passes_the_screw():
    sp = iface.screw_spec("M3")
    c, *_ = iface.hole("M3", "clearance", 5, teardrop=90)
    body = Box(20, 20, 5, align=(Align.CENTER, Align.CENTER, Align.MAX)) - c
    bore(body, Location(), sp["clearance"], -4.8, -0.2, "teardrop round part")


# ----------------------------------------------------------------------------------------------- servo_mount
SERVO_YAML = """
name: t
parts:
  plate: {file: parts/plate.py, material: PETG}
purchased:
  servo: {catalog: SERVO, proxy: servo, groups: {tabs: s}FROM}
assembly:
  root: plate
  joints: [{parent: plate.seat, child: servo.tabs}]
"""
SERVO_PLATE = """
from build123d import *
from kerf import iface
S = "SERVO"
def build(ctx):
    d = iface.servo_dims(S)
    t = T
    s = Box(d["span"] + 14, d["W"] + 20, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if TOP:
        s -= iface.servo_mount(ctx, S, Location((0, 0, 0)), group="s", plate_t=t, kind="KIND", top_through=True)
        ctx.rigid("seat", Location((0, 0, -d["tab_t"])))
    else:
        s -= iface.servo_mount(ctx, S, Location((0, 0, t)), group="s", plate_t=t, kind="KIND")
        ctx.rigid("seat", Location((0, 0, t)))
    return ctx.finish(s)
"""


@pytest.mark.parametrize("servo", sorted(catalog.get("servos")))
@pytest.mark.parametrize("top", [False, True])
def test_servo_mount_window_and_tab_holes(tmp_path, servo, top):
    path = f"servos.{servo}"
    d = iface.servo_dims(path)
    t = 8.0
    kind = "heatset"
    y = SERVO_YAML.replace("SERVO", path).replace("FROM", ", tab_screws_from: bottom" if top else "")
    src = SERVO_PLATE.replace("SERVO", path).replace("TOP", str(top)).replace("KIND", kind).replace("T\n", f"{t}\n")
    proj, asm = _proj(tmp_path, y, {"plate": src})
    n = len(d["holes"])
    assert n in (2, 4)
    assert_assembly_ok(asm, n)
    assert check_printed_holes(proj) == n
    # window: the body passes with exactly clearance/2 on every side (default clearance 0.6 -> 0.3 per side,
    # ENGINEERING.md "sliding printed-on-printed 0.3-0.4 per side"; the servo case is a loose drop-in)
    plate, servo_s = proj.items["plate"].shape, proj.items["servo"].shape
    z0, z1 = (d["tab_t"] + 0.2, d["tab_t"] + t - 0.2) if top else (-t + 0.2, -0.2)
    w = servo_s.location
    c = 0.6
    for axis in ("L", "W"):
        def probe(s, a, b, axis=axis):
            x = s if axis == "L" else d["L"] + c - 2.6       # stay clear of the dog-bone corners on the other axis
            yy = s if axis == "W" else d["W"] + c - 2.6
            return Pos(0, 0, a) * Box(x, yy, b - a, align=(Align.CENTER, Align.CENTER, Align.MIN))
        assert_size(plate, w, probe, d[axis] + c, z0, z1, f"{servo} window {axis}")
    # the proxy body really sits inside that window (no contact) and the tabs really rest on the plate face
    assert _overlap(plate, servo_s) < HIT
    tab_face = Location((0, 0, d["tab_t"] if top else 0.0))
    side = 0.15 if top else -0.15
    assert _overlap(plate, w * tab_face * Pos(d["span"] / 2 - 1.0, 0, side - 0.1) * Box(1, 1, 0.2)) > HIT


# ----------------------------------------------------------------------------------------------- horn_mount
HORN_YAML = """
name: t
parts:
  plate: {file: parts/plate.py}
  arm: {file: parts/arm.py}
purchased:
  servo: {catalog: servos.MG996R, proxy: servo, groups: {tabs: s}}
  horn: {catalog: servo_horns.aluminum_25T, proxy: horn, groups: {holes: h}}
assembly:
  root: plate
  joints:
    - {parent: plate.seat, child: servo.tabs}
    - {parent: servo.output, child: horn.spline, name: out, range: [-90, 90]}
    - {parent: horn.face, child: arm.mount}
"""
HORN_PLATE = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(90, 60, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.servo_mount(ctx, "servos.MG996R", Location((0, 0, 8)), group="s", plate_t=8, kind="heatset")
    ctx.rigid("seat", Location((0, 0, 8)))
    return ctx.finish(s)
"""
HORN_ARM = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(30, 30, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.horn_mount(ctx, "servo_horns.aluminum_25T", Location((0, 0, 5)), group="h", plate_t=5, kind="KIND")
    ctx.rigid("mount", Location((0, 0, 0)))
    return ctx.finish(s)
"""


@pytest.mark.parametrize("kind", ["clearance", "counterbore"])
def test_horn_mount_holes_and_centre_access(tmp_path, kind):
    proj, asm = _proj(tmp_path, HORN_YAML, {"plate": HORN_PLATE, "arm": HORN_ARM.replace("KIND", kind)})
    h = iface.horn_dims("servo_horns.aluminum_25T")
    joints = assert_assembly_ok(asm, 4 + h["n"])
    assert len([j for j in joints if j["group"] == "h"]) == h["n"]
    assert check_printed_holes(proj) == 4 + h["n"]
    # the hole circle lands on the horn's bolt circle, and the centre access hole fits the centre screw head + driver
    arm = proj.items["arm"].shape
    for s in arm.kerf_sites:
        p = geom.world_point(arm.location * s.loc, (0, 0, 0)) - geom.world_point(arm.location, (0, 0, 0))
        assert math.hypot(p[0], p[1]) == pytest.approx(h["bc"] / 2, abs=1e-6)
    cs = iface.screw_spec(h["center_screw"])
    bore(arm, arm.location * Location((0, 0, 5)), cs["head_d"] + 1.5, -4.8, -0.2, "horn centre access")
    assert all(s["clear"] for s in A.sweeps(asm, samples=5))


# ----------------------------------------------------------------------------------------------- bearing_seat
BEARING_YAML = """
name: t
parts:
  housing: {file: parts/housing.py}
purchased:
  brg: {catalog: BRG, proxy: bearing}
assembly:
  root: housing
  joints: [{parent: housing.seat, child: brg.face}]
"""
HOUSING = """
from build123d import *
from kerf import iface
def build(ctx):
    b = iface.bearing_dims("BRG")
    H = b["B"] + 4
    s = Box(b["D"] + 12, b["D"] + 12, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bearing_seat(ctx, "BRG", Location((0, 0, H)), fit="FIT", through=4)
    ctx.rigid("seat", Location((0, 0, 4)))      # bearing face on the pocket floor
    return ctx.finish(s)
"""


@pytest.mark.parametrize("brg", [k for k, v in catalog.get("bearings").items() if isinstance(v, dict) and "outer_d" in v])
@pytest.mark.parametrize("fit", sorted(iface.FIT))
def test_bearing_seat_fit(tmp_path, brg, fit):
    path = f"bearings.{brg}"
    b = iface.bearing_dims(path)
    proj, asm = _proj(tmp_path, BEARING_YAML.replace("BRG", path),
                      {"housing": HOUSING.replace("BRG", path).replace("FIT", fit)})
    assert A.interference(asm) == []
    housing, bearing = proj.items["housing"].shape, proj.items["brg"].shape
    w = bearing.location
    # outer race pocket = catalog D + the fit allowance, over the whole bearing width, centred on the bearing axis
    bore(housing, w, b["D"] + iface.FIT[fit], 0.2, b["B"] - 0.2, f"{brg} {fit} pocket")
    lo, hi = {"press": (0.0, 0.1), "snug": (0.2, 0.2), "free": (0.3, 0.4)}[fit]     # ENGINEERING.md section 6
    assert lo - 1e-9 <= iface.FIT[fit] <= hi + 1e-9
    # the pocket floor supports the outer race, and the through hole clears the inner race / shaft
    assert _overlap(housing, w * _cyl(b["D"] / 2 - 0.1, -0.3, 0)) > HIT
    bore(housing, w, b["d"] + 2.0, -3.8, -0.2, f"{brg} shaft clearance")
    assert b["d"] + 2.0 < b["D"], "shaft clearance must leave a shoulder for the outer race"


# ----------------------------------------------------------------------------------------------- motor_mount / stack_mount
MOTOR_YAML = """
name: t
parts:
  arm: {file: parts/arm.py}
purchased:
  motor: {catalog: drone.motors.MOTOR, proxy: motor, groups: {mount: m}}
  stack: {catalog: drone.stacks.STACK, proxy: stack, groups: {holes: s}}
assembly:
  root: arm
  joints:
    - {parent: arm.motor_seat, child: motor.base}
    - {parent: arm.stack_seat, child: stack.bottom}
"""
MOTOR_ARM = """
from build123d import *
from kerf import iface
M = "drone.motors.MOTOR"
def build(ctx):
    t, boss = T_ARM, BOSS
    s = Box(150, 50, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    s += Pos(35, 0, 0) * Box(48, 48, boss, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.motor_mount(ctx, M, Location((120, 0, 0), (180, 0, 0)), group="m", plate_t=t, kind="MKIND")
    s -= iface.stack_mount(ctx, "drone.stacks.STACK", Location((35, 0, boss)), group="s", depth=boss, kind="SKIND")
    ctx.rigid("motor_seat", Location((120, 0, t)))
    ctx.rigid("stack_seat", Location((35, 0, boss)))
    return ctx.finish(s)
"""
MOTOR_CASES = [(m, s) for m, s in zip(sorted(catalog.get("drone.motors")), ["fc_30_5", "fc_20", "aio_25_5", "fc_30_5"])]


def _std_length(grip, eng_min, eng_max):
    return any(grip + eng_min - 1e-3 <= L <= grip + eng_max + 1e-3 for L in A.STANDARD_SCREW_LENGTHS)


def _thickness_for(screw, kind, grip_of, eng, candidates):
    """First material thickness for which hole() accepts the kind AND a standard screw length fits (what a designer
    would pick). grip_of(depth, hole_result) -> clamped length; eng(depth, hole_result) -> (min, max) engagement."""
    for t in candidates:
        try:
            r = iface.hole(screw, kind, t)
        except ValueError:
            continue
        if _std_length(grip_of(t, r), *eng(t, r)):
            return t
    raise AssertionError(f"no thickness in {candidates} gives a standard {screw} length for {kind}")


# Heat-set inserts fix the thread depth, so with a 14-22 mm stack no standard screw length lands in the insert window
# (that is the fastener check working); heat-set stack mounts are covered with the 5 mm AIO board.
STACK_KINDS = [(m, s, mk, sk) for m, s in MOTOR_CASES for mk, sk in [("clearance", "nut_trap"), ("countersink", "tap")]] + \
    [(m, "aio_25_5", "counterbore", "heatset") for m in sorted(catalog.get("drone.motors"))]


@pytest.mark.parametrize("motor,stack,mkind,skind", STACK_KINDS)
def test_motor_and_stack_mounts(tmp_path, motor, stack, mkind, skind):
    e = catalog.get(f"drone.motors.{motor}")
    pts, mscrew = iface.motor_holes(f"drone.motors.{motor}")
    dep = catalog.num(e, "max_screw_depth")
    md = iface.screw_spec(mscrew)["d"]
    t = _thickness_for(mscrew, mkind, lambda t, r: r[1], lambda t, r: (min(dep, 1.5 * md) * 0.9, dep),
                       [x / 2 for x in range(5, 17)])
    se = catalog.get(f"drone.stacks.{stack}")
    h = catalog.num(se, "height")
    boss = _thickness_for(str(se["screw"]), skind, lambda t, r: h, lambda t, r: (r[3], r[2]), [x / 2 for x in range(10, 31)])
    src = (MOTOR_ARM.replace("MOTOR", motor).replace("STACK", stack).replace("MKIND", mkind).replace("SKIND", skind)
           .replace("T_ARM", str(t)).replace("BOSS", str(boss)))
    proj, asm = _proj(tmp_path, MOTOR_YAML.replace("MOTOR", motor).replace("STACK", stack), {"arm": src})
    joints = assert_assembly_ok(asm, 8)
    assert check_printed_holes(proj) == 8
    e = catalog.get(f"drone.motors.{motor}")
    for j in joints:
        if j["group"] == "m":   # screw tip never bottoms out in (or punches through) the motor's stator base
            assert j["length_mm"] - j["grip_mm"] <= catalog.num(e, "max_screw_depth") + 1e-6
    # centre hole: clears the shaft end and leaves a printable wall to every mount hole
    arm = proj.items["arm"].shape
    pts, screw = iface.motor_holes(f"drone.motors.{motor}")
    ch = iface.motor_center_hole(f"drone.motors.{motor}")
    bore(arm, arm.location * Location((120, 0, t)), ch, -t + 0.2, -0.2, f"{motor} centre hole")
    assert ch >= catalog.num(e, "shaft_d") + 1.0
    wall = math.hypot(*pts[0]) - ch / 2 - iface.screw_spec(screw)["clearance"] / 2
    assert wall >= 1.2 - 1e-9, f"{motor}: only {wall:.2f} mm between the centre hole and a mount hole"
    # stack holes sit exactly on the catalog square
    sp = catalog.num(catalog.get(f"drone.stacks.{stack}"), "spacing")
    xs = sorted({round(geom.world_point(arm.location * s.loc, (0, 0, 0))[1], 6) for s in arm.kerf_sites if s.group == "s"})
    assert xs == pytest.approx([-sp / 2, sp / 2])


def test_motor_center_hole_refuses_to_cut_into_mount_holes():
    with pytest.raises(ValueError):
        iface.motor_mount(None, "drone.motors.1404_3800kv_3in", Location(), "m", 4, center_hole=8.0)
