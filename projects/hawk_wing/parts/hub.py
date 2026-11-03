"""STUB hub (hub_r / hub_l): panel root block, boss with two 625 bearings, sector gear, spar sockets."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    ctx.stub("root hub being designed")
    pf = L.planform(p)
    y0, y1 = (p.pivot_y, p.hub_y1) if s > 0 else (-p.hub_y1, -p.pivot_y)
    body = aero.wing_solid(pf, y0, y1)
    body = body + Pos(p.pivot_x, s * p.pivot_y, L.BOSS_Z0) * Cylinder(L.BOSS_R, L.BOSS_Z1 - L.BOSS_Z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("pivot", L.pivot_axis(p, s).location)
    ctx.rigid("wing", Location())
    for w in ("main", "rear"):
        ctx.rigid(w, L.tube_loc(p, w, s))
    ctx.rigid("bear_top", L.pin_loc(p, s, L.BOSS_Z1 - 5.0))
    ctx.rigid("bear_bot", L.pin_loc(p, s, L.BOSS_Z0))
    return ctx.finish(body)
