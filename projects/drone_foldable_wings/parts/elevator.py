"""STUB elevator."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    x = p.htail_x_le0 + p.elev_hinge_frac * p.htail_root_chord
    body = Pos(x + 1, 0, p.htail_z0) * Box(25, p.htail_span - 10, 4, align=(Align.MIN, Align.CENTER, Align.CENTER))
    ctx.rigid("hinge", Axis((x, 0, p.htail_z0), (0, 1, 0)).location)
    return ctx.finish(body)
