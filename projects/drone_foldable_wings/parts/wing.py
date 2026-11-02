"""STUB wing skin segment."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

from kerf import aero

def build(ctx):
    p = ctx.p
    s = -1 if "_l" in ctx.id else 1
    inner = ctx.id.endswith("1")
    pf = L.planform(p)
    ya, yb = (p.hub_y1, p.seg_split_y) if inner else (p.seg_split_y, p.semi)
    y0, y1 = (ya, yb) if s > 0 else (-yb, -ya)
    body = aero.wing_solid(pf, y0, y1)
    if inner:
        ctx.rigid("root", Location())
    else:
        ctx.rigid("joint", Location())
        hx = pf.x_le(p.ail_y0) + p.ail_hinge_frac * pf.chord(p.ail_y0)
        a = (hx, s * p.ail_y0, 0.0); b = (pf.x_le(p.ail_y1) + p.ail_hinge_frac * pf.chord(p.ail_y1), s * p.ail_y1, 0.0)
        ctx.revolute("aileron", Axis(a, tuple(bb - aa for aa, bb in zip(a, b))), range=(-p.ail_throw, p.ail_throw))
        ctx.rigid("servo", Location(Plane(origin=(90, s * 360, 0), x_dir=(1, 0, 0), z_dir=(0, -s, 0))))
    return ctx.finish(body)
