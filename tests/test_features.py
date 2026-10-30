"""Every kerf.features helper builds valid geometry of the expected size, and refuses unprintable/overstrained input."""
import math

import pytest
from build123d import Align, Axis, Box, Location, Pos

from kerf import catalog, drives, features as F


def _valid_one(s):
    assert s.is_valid and len(s.solids()) == 1


def test_channel_volume_and_breakout():
    pts = [(0, 0, 0), (10, 0, 5), (20, 5, 5)]
    c = F.channel(pts, d=1.6, extend=1.0)
    _valid_one(c)
    from build123d import Spline, Vector
    L = Spline(*[Vector(*p) for p in pts]).length + 2.0
    assert c.volume == pytest.approx(math.pi * 0.8 ** 2 * L, rel=0.02)
    # a tendon channel through a block opens on both faces
    blk = Pos(10, 2, 2.5) * Box(16, 12, 12)
    cut = blk - c
    assert cut.is_valid and blk.volume - cut.volume > 0
    with pytest.raises(ValueError):
        F.channel(pts, d=0.5)


def test_shell_uniform_wall():
    b = Box(20, 20, 20)
    s = F.shell(b, 2.0, b.faces().sort_by(Axis.Z)[-1:])
    _valid_one(s)
    assert s.volume == pytest.approx(20 ** 3 - 16 * 16 * 18, rel=1e-4)  # open top, 2 mm walls and floor
    with pytest.raises(ValueError):
        F.shell(b, 0.6)


def test_gusset_triangle():
    g = F.gusset((0, 0, 0), (1, 0, 0), (0, 0, 1), 12, 10, t=2.4)
    _valid_one(g)
    assert g.volume == pytest.approx(0.5 * 12 * 10 * 2.4, rel=1e-6)
    bb = g.bounding_box()
    assert (bb.size.X, bb.size.Y, bb.size.Z) == pytest.approx((12, 2.4, 10))
    with pytest.raises(ValueError):
        F.gusset((0, 0, 0), (1, 0, 0), (2, 0, 0), 5, 5, 2)


def test_teardrop_hole():
    t = F.teardrop_hole(3.4, 10, up_deg=90)
    bb = t.bounding_box()
    assert bb.size.X == pytest.approx(3.4, abs=1e-3)
    assert bb.size.Y == pytest.approx(1.7 + 1.7 * math.sqrt(2), abs=1e-3)  # circle + 45 deg roof point toward +Y
    assert bb.max.Y == pytest.approx(1.7 * math.sqrt(2), abs=1e-3)


def test_printed_threads_mesh_without_overlap():
    rod = F.threaded_rod(10, 1.5, 8)
    _valid_one(rod)
    assert rod.bounding_box().size.X == pytest.approx(10 - F.THREAD_CLEARANCE_D / 2, abs=0.05)
    nut = F.threaded_hole(Box(20, 20, 8, align=(Align.CENTER, Align.CENTER, Align.MIN)), Location((0, 0, 8)), 10, 1.5, 8)
    _valid_one(nut)
    assert (rod & nut).volume < 1e-3
    assert rod.distance_to(nut) > 0.05  # real running clearance, not just touching
    with pytest.raises(ValueError):
        F.threaded_rod(10, 0.5, 8)     # too fine to print
    with pytest.raises(ValueError):
        F.threaded_rod(4, 0.7, 8)      # below M6: use an insert


def test_gear_pair_centre_distance():
    g1, g2, info = F.gear_pair(1.5, 12, 24, 6)
    assert info.center == pytest.approx(drives.center_distance(1.5, 12, 24)) == pytest.approx(27.0)
    assert (g1 & (Pos(info.center, 0, 0) * g2)).volume < 1e-3


def test_snap_hook_strain_hand_calc():
    hook, info = F.snap_hook(length=16, t=2, width=6, undercut=1, material="PETG")
    _valid_one(hook)
    bb = hook.bounding_box()
    assert (bb.size.X, bb.size.Y) == pytest.approx((16, 6))
    assert bb.max.Z == pytest.approx(2.0)  # tip t/2 = 1 + undercut 1
    assert info["strain"] == pytest.approx(1 * 2 / (1.09 * 16 ** 2), rel=1e-3)
    m = catalog.get("materials.PETG")
    assert info["allowable"] == pytest.approx(0.7 * m["tensile_strength_xy_mpa"] / m["youngs_modulus_mpa"], rel=1e-3)
    # same hook, constant section: eps = y h / (0.67 l^2)
    _, info2 = F.snap_hook(length=16, t=2, width=6, undercut=1, material="PETG", taper=False)
    assert info2["strain"] == pytest.approx(2 / (0.67 * 256), rel=1e-3)
    # short stiff PLA hook is refused, with the minimum length in the message
    with pytest.raises(ValueError, match="lengthen"):
        F.snap_hook(length=6, t=2, width=6, undercut=1, material="PLA")


def test_living_hinge_strain_hand_calc():
    h, info = F.living_hinge(length=6, width=10, t=0.5, angle_deg=15, material="PETG")
    _valid_one(h)
    assert info["strain"] == pytest.approx(0.5 * math.radians(15) / 12, rel=1e-3)
    assert info["allowable"] == pytest.approx(F.allowable_strain("PETG", frequent=True), rel=1e-3)
    with pytest.raises(ValueError, match="max"):
        F.living_hinge(length=6, width=10, t=0.5, angle_deg=90, material="PETG")
    F.living_hinge(length=6, width=10, t=0.5, angle_deg=90, material="TPU")  # flexible filament takes it


def test_label_emboss_and_deboss():
    e = F.label("KF v1", size=6, depth=0.6)
    bb = e.bounding_box()
    assert bb.size.Z == pytest.approx(0.6) and 10 < bb.size.X < 20
    plate = Box(30, 12, 3, align=(Align.CENTER, Align.CENTER, Align.MAX))
    d = plate - F.label("KF", size=6, depth=0.6, emboss=False)
    assert d.is_valid and d.volume < plate.volume
    with pytest.raises(ValueError):
        F.label("x", size=3)
    with pytest.raises(ValueError):
        F.label("x", size=6, depth=0.3)


def test_pockets_keep_min_web():
    w, h, web = 60, 30, 2.0
    p = F.pockets(w, h, depth=4, cell=12, web=web)
    sols = p.solids()
    assert len(sols) == 8  # 4 x 2 cells
    bbs = sorted((s.bounding_box() for s in sols), key=lambda b: (round(b.min.Y), b.min.X))
    assert min(b.min.X for b in bbs) == pytest.approx(-w / 2 + web) and max(b.max.Y for b in bbs) == pytest.approx(h / 2 - web)
    gaps = [b2.min.X - b1.max.X for b1, b2 in zip(bbs, bbs[1:]) if round(b1.min.Y) == round(b2.min.Y)]
    assert gaps and min(gaps) == pytest.approx(web)
    plate = Box(w, h, 6, align=(Align.CENTER, Align.CENTER, Align.MAX))
    assert (plate - p).is_valid
    with pytest.raises(ValueError):
        F.pockets(60, 30, 4, 12, web=0.8)


def test_safe_fillet_reports_failures_instead_of_crashing():
    bx = Box(20, 20, 10)
    good = bx.edges().filter_by(Axis.Z)
    out, failed = F.safe_fillet(bx, [(good, 1.0), (bx.edges().filter_by(Axis.X), 20.0)])
    assert out.is_valid
    assert bx.volume - out.volume == pytest.approx(4 * (1 - math.pi / 4) * 10, rel=1e-3)  # four r=1 vertical fillets
    assert len(failed) == 4 and all("fillet 20" in f for f in failed)
    out2, failed2 = F.safe_fillet(bx, [(bx.edges().filter_by(Axis.Z), 0.5)], kind="chamfer")
    assert not failed2 and bx.volume - out2.volume == pytest.approx(4 * 0.5 * 0.5 ** 2 * 10, rel=1e-3)
