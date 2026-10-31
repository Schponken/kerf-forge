"""iface.print_up_deg: teardrop direction from a part's print_rot (hand-checked cases)."""
import pytest
from build123d import Location, Plane

from kerf import iface
from kerf.ctx import Ctx


def ctx(rot):
    return Ctx("p", {}, {"spec": {"print_rot": rot}})


def test_flat_print_vertical_hole_needs_none():
    assert iface.print_up_deg(ctx([0, 0, 0]), Location((5, 5, 0))) is None


def test_flat_print_horizontal_hole_points_to_world_z():
    # hole along +X; loc x_dir = +Y, so loc's y = z_dir x x_dir = X x Y = +Z (world up) -> 90 deg
    loc = Location(Plane(origin=(0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    assert iface.print_up_deg(ctx([0, 0, 0]), loc) == pytest.approx(90)


def test_upside_down_print_flips_up():
    loc = Location(Plane(origin=(0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    assert iface.print_up_deg(ctx([180, 0, 0]), loc) == pytest.approx(-90)


def test_on_its_side_print_rot_90_x():
    # Rot(90,0,0) maps part +Y to printer up: a hole along part X with x_dir = +Y -> up is loc x -> 0 deg
    loc = Location(Plane(origin=(0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    assert iface.print_up_deg(ctx([90, 0, 0]), loc) == pytest.approx(0, abs=1e-6)
    # and a part-Z hole is then horizontal too, while a part-Y hole is vertical
    assert iface.print_up_deg(ctx([90, 0, 0]), Location((0, 0, 0))) is not None
    assert iface.print_up_deg(ctx([90, 0, 0]), Location(Plane(origin=(0, 0, 0), z_dir=(0, 1, 0)))) is None


def test_servo_mount_accepts_teardrop():
    c0 = iface.servo_mount(ctx([0, 0, 0]), "servos.MG90S", Location(), "g", plate_t=5, kind="tap")
    c1 = iface.servo_mount(ctx([0, 0, 0]), "servos.MG90S", Location(), "g", plate_t=5, kind="tap", teardrop=90)
    assert c1.volume > c0.volume


def test_heatset_relief_allows_a_longer_screw():
    from kerf import iface as i
    c0, _, e0, _ = i.hole("M2", "heatset", 8)
    c1, _, e1, _ = i.hole("M2", "heatset", 8, relief=2.0)
    assert e1 == pytest.approx(e0 + 2.0) and c1.volume > c0.volume
    with pytest.raises(ValueError):
        i.hole("M2", "heatset", 5, relief=2.0)       # 4 mm insert hole + 2 relief + 0.8 floor > 5
