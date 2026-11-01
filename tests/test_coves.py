"""kerf/coves.py: concave fillets by boolean union (the fallback for bodies whose OCC fillet crashes)."""
import math

from build123d import Align, Box, Pos, Rot, Vector

from kerf.coves import cove_fillets
from kerf.edges import sharp_inside


def _sharp_edges(shape):
    cs = sharp_inside(shape)
    return [e for e in shape.edges() if any((e.center() - Vector(*c["at"])).length < 0.1 for c in cs)]


def test_right_angle_cove_matches_fillet_area():
    L = Box(20, 10, 4, align=Align.MIN) + Box(4, 10, 20, align=Align.MIN)
    out, skipped = cove_fillets(L, _sharp_edges(L), 2.0)
    assert not skipped and out.is_valid and len(out.solids()) == 1
    assert abs((out.volume - L.volume) - (4 - math.pi) * 10) < 0.05      # r^2 (1 - pi/4) x length
    assert sharp_inside(out) == []


def test_oblique_corner():
    L = Box(20, 10, 4, align=Align.MIN) + Rot(0, -30, 0) * Box(4, 10, 20, align=Align.MIN)
    out, skipped = cove_fillets(L, _sharp_edges(L), 2.0)
    phi = math.radians(120)                                              # air angle between the faces
    assert not skipped and sharp_inside(out) == []
    assert abs((out.volume - L.volume) - 4 * (1 / math.tan(phi / 2) - (math.pi - phi) / 2) * 10) < 0.05


def test_short_face_is_skipped_not_lumped():
    # a 1 mm step: a 2 mm cove would stick out past its top into the air
    L = Box(20, 10, 4, align=Align.MIN) + Pos(0, 0, 4) * Box(4, 10, 1, align=Align.MIN)
    out, skipped = cove_fillets(L, _sharp_edges(L), 2.0)
    assert len(skipped) == 1 and abs(out.volume - L.volume) < 1e-6
