"""STUB rudder."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    xh = p.boom_x1 - p.fin_root + p.fin_root * p.rud_hinge_frac
    body = Pos(xh + 1, 0, p.boom_z + 10) * Box(30, 5, p.fin_h - 5, align=(Align.MIN, Align.CENTER, Align.MIN))
    ctx.rigid("hinge", Axis((xh, 0, p.boom_z + 8), (0, 0, 1)).location)
    return ctx.finish(body)
