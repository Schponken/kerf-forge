"""STUB wing root hub (boss + sector + root block + spar sockets)."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

from kerf import aero

def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    pf = L.planform(p)
    y0, y1 = sorted((s * p.pivot_y, s * p.hub_y1))
    body = aero.wing_solid(pf, y0, y1)
    body += Pos(p.pivot_x, s * p.pivot_y, p.boss_z0) * Cylinder(p.boss_r, p.boss_z1 - p.boss_z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("pivot", L.pivot_axis(p, s).location)
    ctx.rigid("wing", Location())
    ctx.rigid("main", L.tube_loc(p, "main", s))
    ctx.rigid("rear", L.tube_loc(p, "rear", s))
    return ctx.finish(body)
