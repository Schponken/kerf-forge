"""The sharp-inside-corner finder: an L-bracket's inside corner is found, and is gone once filleted."""
from build123d import Align, Axis, Box, fillet

from kerf import edges


def _l_bracket():
    return Box(40, 20, 5, align=(Align.MIN, Align.MIN, Align.MIN)) + Box(5, 20, 40, align=(Align.MIN, Align.MIN, Align.MIN))


def test_l_bracket_inside_corner_found_then_filleted_away():
    s = _l_bracket()
    found = edges.sharp_inside(s)
    assert len(found) == 1 and found[0]["at"][0] == 5.0 and found[0]["at"][2] == 5.0 and found[0]["len"] == 20.0
    inner = s.edges().filter_by(Axis.Y).sort_by_distance((5, 10, 5))[0]
    assert edges.sharp_inside(fillet(inner, 3)) == []


def test_plain_box_and_outside_edges_are_not_flagged():
    assert edges.sharp_inside(Box(30, 20, 10)) == []


def test_corners_at_interface_sites_are_exempt():
    from build123d import Location
    s = _l_bracket()
    site = type("S", (), {"loc": Location((5, 10, 5))})()
    assert edges.sharp_inside(s, [site]) == []


def test_advice_puts_stressed_corners_first():
    corners = [{"at": [0, 0, 0], "len": 10}, {"at": [50, 0, 0], "len": 30}]
    msg = edges.advice("arm", corners, hot_zones=[{"at": [1, 0, 0]}], cell=5)
    assert "1 in a highly stressed zone" in msg and msg.index("[0, 0, 0]") < len(msg)
    assert edges.advice("arm", []) is None
