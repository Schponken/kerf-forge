"""STUB hatch."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    body = Pos(-180, -24, p.fuse_top - 2) * Box(220, 48, 2, align=(Align.MIN,) * 3)
    ctx.rigid("base", Location())
    return ctx.finish(body)
