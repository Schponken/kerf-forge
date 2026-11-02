"""STUB fin."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    x0 = p.boom_x1 - p.fin_root
    body = Pos(x0, 0, p.boom_z + 8) * Box(p.fin_root * p.rud_hinge_frac, 6, p.fin_h, align=(Align.MIN, Align.CENTER, Align.MIN))
    ctx.rigid("base", Location())
    xh = x0 + p.fin_root * p.rud_hinge_frac
    ctx.revolute("rudder", Axis((xh, 0, p.boom_z + 8), (0, 0, 1)), range=(-p.rud_throw, p.rud_throw))
    return ctx.finish(body)
