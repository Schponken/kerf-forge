"""STUB battery hatch."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    ctx.stub("hatch being designed")
    body = Pos(-60, 0, p.fuse_top - 1.0) * Box(100, 50, 2)
    ctx.rigid("base", Location())
    return ctx.finish(body)
