"""STUB pivot cap (cap_r / cap_l): holds the pin's top; 2 M3 through the glove into the pod."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    ctx.stub("pivot cap being designed")
    body = Pos(p.pivot_x, s * (p.pivot_y - 14.0), (L.CAP_Z0 + L.CAP_Z1) / 2) * Box(28, 54, L.CAP_Z1 - L.CAP_Z0)
    ctx.rigid("base", Location())
    return ctx.finish(body)
