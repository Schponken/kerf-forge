"""STUB pod (pod_r / pod_l): sweep-servo nacelle under the glove's trailing-edge corner, pin floor plate."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    ctx.stub("sweep servo nacelle being designed")
    x0, x1 = p.pinion_x - 45.0, p.pivot_x + 22.0
    body = Pos((x0 + x1) / 2, s * p.pivot_y, -33.0) * Box(x1 - x0, 40, 50)
    ctx.rigid("base", Location())
    ctx.rigid("servo", L.sweep_servo_loc(p, s))
    ctx.rigid("pin", L.pin_loc(p, s, L.POD_FLOOR_Z0))
    ctx.revolute("pivot", L.pivot_axis(p, s), range=(0, p.fold_max))
    return ctx.finish(body)
