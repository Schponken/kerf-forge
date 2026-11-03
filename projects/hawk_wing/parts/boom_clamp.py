"""STUB boom clamp."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    ctx.stub("boom clamp being designed")
    body = Pos(p.fuse_x1 - 25, 0, p.boom_z + 10) * Box(30, 16, 5)
    ctx.rigid("base", Location())
    return ctx.finish(body)
