"""STUB motor mount: stand-off from the front bulkhead to the motor plate."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    ctx.stub("motor mount stand-off being designed")
    x0, x1, z = p.nose_x0 - 6.0, p.nose_x1, p.motor_z
    body = Pos((x0 + x1) / 2, 0, z) * Box(x1 - x0, 30, 30)
    ctx.rigid("base", Location())
    ctx.rigid("motor", Location(Plane(origin=(x0, 0, z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    return ctx.finish(body)
