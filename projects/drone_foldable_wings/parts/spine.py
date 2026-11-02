"""STUB spine (upper pivot plates + cover)."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    body = Pos(100, -14, p.fuse_top) * Box(125, 28, p.boss_z1 + 6.5 - p.fuse_top, align=(Align.MIN,) * 3)
    ctx.rigid("base", Location())
    ctx.rigid("gps", Location((150, 0, p.boss_z1 + 6.5)))
    return ctx.finish(body)
