"""Section generators (kerf/sections.py, re-exported in kerf.features): textbook sections match the hand formulas for
area and second moment (measured with requirements.section_props on a cut of the built beam); the print-ready forms
have no unsupported overhang on their intended side; fork_link and rib_along build valid, support-free solids."""
import math

import pytest
from build123d import Align, Axis, Box, Location, Rot, Vector

from kerf import features as F, geom

D, W, T, L = 20.0, 12.0, 2.0, 40.0


def _cut(b, depth_dir=(0, 0, 1)):
    return F.bending_I(b, (L / 2, 0, 0), (1, 0, 0), depth_dir)


def _hand(section):
    if section == "rect":
        return W * D, W * D ** 3 / 12
    if section in ("I", "C"):                 # C with its web vertical: same as an I about the horizontal axis
        return W * D - (W - T) * (D - 2 * T), (W * D ** 3 - (W - T) * (D - 2 * T) ** 3) / 12
    if section == "box":
        return W * D - (W - 2 * T) * (D - 2 * T), (W * D ** 3 - (W - 2 * T) * (D - 2 * T) ** 3) / 12
    if section == "tube":
        return math.pi / 4 * (D ** 2 - (D - 2 * T) ** 2), math.pi / 64 * (D ** 4 - (D - 2 * T) ** 4)
    if section == "T":                        # flange W x T on the bed, web T x (D - T) up
        a1, y1, a2, y2 = W * T, T / 2, T * (D - T), T + (D - T) / 2
        yb = (a1 * y1 + a2 * y2) / (a1 + a2)
        return a1 + a2, W * T ** 3 / 12 + a1 * (yb - y1) ** 2 + T * (D - T) ** 3 / 12 + a2 * (y2 - yb) ** 2


@pytest.mark.parametrize("section", ["rect", "I", "T", "C", "box", "tube"])
def test_textbook_area_and_second_moment(section):
    b = F.beam([(0, 0, 0), (L, 0, 0)], section, depth=D, width=W, wall=T, printable=False)
    area, inertia = _cut(b)
    a_hand, i_hand = _hand(section)
    assert area == pytest.approx(a_hand, rel=2e-3)
    assert inertia == pytest.approx(i_hand, rel=2e-3)


def test_u_channel_lying_flat_bends_about_its_depth():
    """bed across `up`: a C opens upward, its standing walls are the flanges of the depth-wise bending."""
    b = F.beam([(0, 0, 0), (L, 0, 0)], "C", depth=D, width=W, wall=T, up=(0, 1, 0), bed=(0, 0, -1), printable=False)
    area, inertia = _cut(b, (0, 1, 0))
    walls = 2 * ((W - T) * T ** 3 / 12 + (W - T) * T * (D / 2 - T / 2) ** 2)
    assert area == pytest.approx(D * T + 2 * T * (W - T), rel=2e-3)
    assert inertia == pytest.approx(T * D ** 3 / 12 + walls, rel=2e-3)


def _overhang(shape):
    v, f = geom.mesh(shape)
    return geom.overhang(v, f, 45)[0]


@pytest.mark.parametrize("section,bed", [(s, (0, 0, -1)) for s in ("rect", "I", "T", "C", "box", "tube")]
                         + [(s, (0, -1, 0)) for s in ("rect", "C", "box", "tube")])
def test_print_ready_sections_need_no_support(section, bed):
    b = F.beam([(0, 0, 0), (L, 0, 0)], section, depth=D, width=W, wall=T, up=(0, 0, 1), bed=bed)
    if bed == (0, -1, 0):
        b = Rot(90, 0, 0) * b                  # put that side on the bed (-Z)
    assert _overhang(b) == pytest.approx(0, abs=0.5)
    plain = F.beam([(0, 0, 0), (L, 0, 0)], section, depth=D, width=W, wall=T, up=(0, 0, 1), bed=bed, printable=False)
    if bed == (0, -1, 0):
        plain = Rot(90, 0, 0) * plain
    depth_dir = (0, 0, 1) if bed == (0, 0, -1) else (0, 1, 0)    # bending direction after the turn
    assert _cut(b, depth_dir)[1] >= 0.98 * _cut(plain, depth_dir)[1]   # the 45 deg material never weakens it


def test_textbook_shapes_would_need_support():
    """The 45 deg treatment is what makes them printable: the plain I and box overhang."""
    for s in ("I", "box"):
        assert _overhang(F.beam([(0, 0, 0), (L, 0, 0)], s, depth=D, width=W, wall=T, printable=False)) > 100


def test_refusals():
    with pytest.raises(ValueError, match="use section='C'"):
        F.beam([(0, 0, 0), (L, 0, 0)], "I", depth=D, width=W, wall=T, up=(0, 0, 1), bed=(0, -1, 0))
    with pytest.raises(ValueError, match="minimum"):
        F.beam([(0, 0, 0), (L, 0, 0)], "box", depth=D, width=W, wall=0.8)
    with pytest.raises(ValueError, match="chamfer"):
        F.beam([(0, 0, 0), (L, 0, 0)], "I", depth=8, width=30, wall=T)


def test_tapered_beam_follows_depth_function():
    b = F.beam([(0, 0, 0), (L, 0, 0)], "box", depth=lambda s: 24 - 12 * s, width=W, wall=T)
    bb0 = (b & Box(0.2, 100, 100).moved(Location((0.5, 0, 0)))).bounding_box()
    bb1 = (b & Box(0.2, 100, 100).moved(Location((L - 0.5, 0, 0)))).bounding_box()
    assert bb0.size.Z == pytest.approx(24 - 12 * 0.5 / L, abs=0.2) and bb1.size.Z == pytest.approx(12 + 12 * 0.5 / L, abs=0.2)


def test_fork_link():
    ends = [{"bore": 3.4, "boss_d": 16, "length": 12}, {"bore": 3.4, "boss_d": 14, "length": 12}]
    for section in ("box", "C", "rect"):
        link, info = F.fork_link(100, ends, section, depth=14, taper=0.7, channel_d=2.5)
        assert link.is_valid and len(link.solids()) == 1, section
        assert info["failed_fillets"] == [], section
        assert _overhang(link) == pytest.approx(0, abs=0.5), section          # prints flat as built
        for (x, y, _), e in zip(info["pivots"], ends):                        # through bores at the pivots
            assert not link.is_inside(Vector(x, y, 6))
            assert link.is_inside(Vector(x + e["bore"] / 2 + 1.0, y, 6))
    box, _ = F.fork_link(100, ends, "box", depth=14, taper=0.7)
    rect, _ = F.fork_link(100, ends, "rect", depth=14, taper=0.7)
    assert box.volume < 0.9 * rect.volume                                     # really hollow between the bosses
    with pytest.raises(ValueError, match="prints flat"):
        F.fork_link(100, ends, "I")


def test_rib_along():
    plate = Box(60, 40, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    top = plate.faces().sort_by(Axis.Z)[-1]
    rib = F.rib_along(top, [(-25, -15, 4), (0, 10, 4), (25, -15, 4)], h=8, t=1.6)
    both = plate + rib
    assert both.is_valid and len(both.solids()) == 1 and both.bounding_box().max.Z == pytest.approx(12)
    assert _overhang(both) == pytest.approx(0, abs=0.5)
    legs = math.hypot(25, 25) * 2
    assert rib.volume == pytest.approx(legs * 1.6 * 8, rel=0.08)
