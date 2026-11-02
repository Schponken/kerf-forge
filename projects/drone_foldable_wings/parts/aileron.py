"""STUB aileron."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    pf = L.planform(p)
    hx = pf.x_le(p.ail_y0) + p.ail_hinge_frac * pf.chord(p.ail_y0)
    a = (hx, s * p.ail_y0, 0.0); b = (pf.x_le(p.ail_y1) + p.ail_hinge_frac * pf.chord(p.ail_y1), s * p.ail_y1, 0.0)
    body = Pos(hx + 2, s * (p.ail_y0 + p.ail_y1) / 2, 0) * Box(25, p.ail_y1 - p.ail_y0, 4, align=(Align.MIN, Align.CENTER, Align.CENTER))
    ctx.rigid("hinge", Axis(a, tuple(bb - aa for aa, bb in zip(a, b))).location)
    return ctx.finish(body)
