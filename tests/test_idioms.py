"""Mechanical idioms (kerf/idioms.py): each builds a valid single solid with its detail features (root fillets,
gussets, wall around holes), prints without support, and fits the catalog part it is for."""
import math

import pytest
from build123d import Align, Box, Cylinder, Location, Plane, Pos, Vector

from kerf import catalog, geom, iface, idioms as I
from kerf.ctx import Ctx


def _overhang(shape):
    v, f = geom.mesh(shape)
    return geom.overhang(v, f, 45)[0]


def _slab_bb(shape, z, dz=0.02):
    return (shape & Pos(0, 0, z) * Box(200, 200, dz)).bounding_box()


def test_boss_root_fillet_and_bore():
    base = Box(40, 40, 3, align=(Align.CENTER, Align.CENTER, Align.MAX))
    b = I.boss(10, 6, bore=3.4, root_r=1.5)
    both = base + b
    assert both.is_valid and len(both.solids()) == 1
    assert _slab_bb(b, 0.01).size.X == pytest.approx(13.0, abs=0.05)        # flares to d + 2 r at the root
    assert _slab_bb(b, 3.0).size.X == pytest.approx(10.0, abs=0.01)         # plain d above it
    assert not b.is_inside(Vector(0, 0, 3)) and b.is_inside(Vector(3.4 / 2 + 0.5, 0, 3))
    plain = math.pi * (25 - 1.7 ** 2) * 6
    assert b.volume > plain                                                  # the fillet adds material
    assert _overhang(both) == pytest.approx(0, abs=0.3)
    with pytest.raises(ValueError):
        I.boss(5, 4, bore=4)


def test_clevis():
    c = I.clevis(100, 13, 40, 4, webs=(22, 70), x_end_a=120)
    assert c.is_valid and len(c.solids()) == 1
    bb = c.bounding_box()
    assert (bb.min.X, bb.max.X, bb.size.Y, bb.size.Z) == pytest.approx((-13, 120, 26, 40), abs=0.01)
    assert not c.is_inside(Vector(50, 0, 20))                               # open between the webs
    assert c.is_inside(Vector(22, 0, 20)) and c.is_inside(Vector(70, 0, 20))
    with pytest.raises(ValueError, match="narrow"):
        I.clevis(100, 13, 10, 4, webs=(50,))


def test_yoke_cheek():
    y = I.yoke_cheek(-30, 30, 0, 60, y_in=20, side=+1, t=4, foot=(-35, 14, 20, 6), gussets=(-21, -8.5))
    assert y.is_valid and len(y.solids()) == 1
    bb = y.bounding_box()
    assert (bb.min.Y, bb.max.Y, bb.max.Z) == pytest.approx((0, 24, 60), abs=0.01)
    for gx in (-21, -8.5):                                                   # gusset in the cheek-foot corner
        assert y.is_inside(Vector(gx, 18, 9))
    assert not y.is_inside(Vector(0, 18, 9))
    m = I.yoke_cheek(-30, 30, 0, 60, y_in=-20, side=-1, t=4, foot=(-35, 14, 20, 6), gussets=(-21, -8.5))
    assert m.volume == pytest.approx(y.volume, rel=1e-6)                     # mirror twin


def test_servo_cradle_holds_the_servo():
    ctx = Ctx("t", {}, {"spec": {"material": "PETG"}})
    servo = "servos.MG996R"
    plate, cut = I.servo_cradle(ctx, servo, Location((0, 0, 0)), "s", plate_t=6)
    part = plate - cut
    assert part.is_valid and len(part.solids()) == 1
    d = iface.servo_dims(servo)
    assert len(ctx.sites) == len(d["holes"])
    sp = iface.screw_spec(d["screw"], "PETG")
    bb = plate.bounding_box()
    for x, y in d["holes"]:                                                  # every hole inside the plate with its wall
        assert bb.max.X - abs(x) >= iface.MIN_WALL_AROUND_HOLE + sp["tap"] / 2 - 1e-6
    assert not part.is_inside(Vector(d["L"] / 2 - 0.2, d["W"] / 2 - 0.2, -3))   # window clears the body corner


def test_cable_saddle():
    pad, cut = I.cable_saddle(6.0)
    s = pad - cut
    assert s.is_valid and len(s.solids()) == 1
    zc = pad.bounding_box().max.Z
    cable = Pos(-20, 0, zc) * (Plane.YZ * Cylinder(3.0, 40, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    assert geom.overlap(s, cable) < geom.OVERLAP_TOL_MM3                     # the cable lies in the groove
    tie = catalog.get(I.TIE)
    tunnel = (cut & Pos(0, 0, 0) * Box(100, 100, 100)).bounding_box()
    assert tunnel.size.X >= catalog.num(tie, "width") + 0.5
    assert _overhang(s) == pytest.approx(0, abs=0.3)


def test_grip_pad():
    add, cut = I.grip_pad(30, 20, "serrations", pitch=1.6)
    assert cut is None and add.is_valid
    jaw = Box(30, 20, 4, align=(Align.CENTER, Align.CENTER, Align.MAX)) + add
    assert jaw.is_valid and len(jaw.solids()) == 1
    assert add.bounding_box().max.Z == pytest.approx(0.8, abs=1e-6)          # 90 deg V: pitch / 2 high
    ridges = [y for y in [-9.6 + 0.8 + 1.6 * i for i in range(12)] if jaw.is_inside(Vector(0, y, 0.6))]
    assert len(ridges) == 12
    assert _overhang(jaw) == pytest.approx(0, abs=0.3)
    add, cut = I.grip_pad(30, 20, "tpu_pocket", insert_t=2.0, lip=1.0)
    jaw = Box(36, 26, 6, align=(Align.CENTER, Align.CENTER, Align.MAX)) - cut
    assert add is None and jaw.is_valid
    assert _slab_bb(cut, -1.95).size.X > _slab_bb(cut, -0.05).size.X + 1.5   # dovetail: wider at the floor
    assert _overhang(jaw) == pytest.approx(0, abs=0.3)
    with pytest.raises(ValueError):
        I.grip_pad(30, 20, "serrations", pitch=1.0)


def test_robot_arm_uses_the_idioms():
    """The copy-pasted yoke() / plate() are gone from robot_arm; both yokes and both arm links use kerf.idioms."""
    from pathlib import Path
    parts = Path(__file__).resolve().parent.parent / "projects" / "robot_arm" / "parts"
    for f in ("yoke_l.py", "yoke_r.py", "upper_arm.py", "forearm.py"):
        src = (parts / f).read_text(encoding="utf-8")
        assert "def yoke(" not in src and "def plate(" not in src, f
    assert "idioms.yoke_cheek" in (parts / "armlib.py").read_text(encoding="utf-8")
    assert all("idioms.clevis" in (parts / f).read_text(encoding="utf-8") for f in ("upper_arm.py", "forearm.py"))
