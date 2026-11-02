"""STUB pinion."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    g1, _ = L.gears()
    ctx.rigid("horn", Location((p.pinion_x, s * p.pivot_y, L.PINION_Z0)))
    return ctx.finish(Pos(p.pinion_x, s * p.pivot_y, L.PINION_Z0) * g1)
