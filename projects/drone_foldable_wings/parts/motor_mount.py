"""STUB motor mount."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    body = Pos(p.fuse_x0 - 6, 0, p.motor_z) * Box(6, 40, 40, align=(Align.MIN, Align.CENTER, Align.CENTER))
    ctx.rigid("base", Location())
    ctx.rigid("motor", Location(Plane(origin=(p.fuse_x0 - 6, 0, p.motor_z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    return ctx.finish(body)
