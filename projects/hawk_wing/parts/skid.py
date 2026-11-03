"""STUB wingtip skid (skid_r / skid_l)."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    ctx.stub("wingtip skid being designed")
    pf = L.planform(p)
    y = p.wing_span / 2 - 15.0
    body = Pos(pf.x_le(y) + pf.chord(y) / 2, s * y, -6) * Box(60, 20, 4)
    ctx.rigid("base", Location())
    return ctx.finish(body)
