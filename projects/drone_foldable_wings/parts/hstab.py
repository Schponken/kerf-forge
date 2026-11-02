"""STUB horizontal stabiliser."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

from kerf import aero

def build(ctx):
    p = ctx.p
    pf = L.tail_planform(p)
    body = aero.wing_solid(pf, -p.htail_span / 2, p.htail_span / 2)
    ctx.rigid("base", Location())
    x = p.htail_x_le0 + p.elev_hinge_frac * p.htail_root_chord
    ctx.revolute("elevator", Axis((x, 0, p.htail_z0), (0, 1, 0)), range=(-p.elev_throw, p.elev_throw))
    return ctx.finish(body)
