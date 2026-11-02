"""holewall: an insert on a plate edge (the tvc_drone A-1 blocker) fails; the same insert moved in passes."""
import types

from build123d import Align, Box, Location

from kerf import holewall, iface
from kerf.ctx import Ctx


def _part(y):
    ctx = Ctx("lug", {}, {"spec": {"material": "PETG"}})
    plate = Box(40, 22, 8, align=(Align.CENTER, Align.CENTER, Align.MAX))       # top face z = 0, edges at y = +/-11
    shape = plate - iface.bolt_pattern(ctx, "leg", "M3", [(0, y)], Location(), kind="heatset", depth=8)
    shape = ctx.finish(shape)
    return types.SimpleNamespace(id="lug", shape=shape, spec={"material": "PETG"})


def test_insert_on_the_edge_is_a_problem():
    p, w, r = holewall.check(_part(11.0))
    assert p and "breaks out" in p[0] and r[0]["wall_frac"] < 0.95


def test_insert_near_edge_warns_and_centred_is_clean():
    p, w, _ = holewall.check(_part(7.5))         # wall 7.5 - 2 - 1.6 = 3.9 mm left, but 1.5 d = 4.5 > 3.5 to the edge
    assert not p and w and "1.5 x d" in w[0]
    p, w, _ = holewall.check(_part(0.0))
    assert not p and not w


def test_hole_lost_to_a_later_fillet_is_a_problem():
    """A fillet built from the pre-cut shape's edges brings the blank back (fpv_wing splice plates): the registered
    hole is filled in the finished part, and the check says so."""
    from build123d import Axis, fillet
    ctx = Ctx("plate", {}, {"spec": {"material": "PETG"}})
    blank = Box(40, 22, 4, align=(Align.CENTER, Align.CENTER, Align.MAX))
    cut = blank - iface.bolt_pattern(ctx, "g", "M3", [(0, 0)], Location(), kind="clearance", depth=4)
    lost = fillet(cut.edges().filter_by(Axis.Z), 2.0)          # what splice.py did: works from the topo parent
    if abs(lost.volume - blank.volume) > 50:                    # this build123d keeps the hole: nothing to prove here
        lost = blank
    item = types.SimpleNamespace(id="plate", shape=ctx.finish(lost), spec={"material": "PETG"})
    p, _, _ = holewall.check(item)
    assert p and "is filled in the finished part" in p[0]
    ctx2 = Ctx("plate", {}, {"spec": {"material": "PETG"}})
    good = ctx2.finish(blank - iface.bolt_pattern(ctx2, "g", "M3", [(0, 0)], Location(), kind="clearance", depth=4))
    assert not holewall.check(types.SimpleNamespace(id="plate", shape=good, spec={"material": "PETG"}))[0]
