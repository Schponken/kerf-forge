"""STUB glove: the fixed inner wing |y| <= pivot_y."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    ctx.stub("glove: centre wing box, pivot notches, pod / cap seats, GPS pocket being designed")
    body = aero.wing_solid(L.planform(p), -p.pivot_y + 0.5, p.pivot_y - 0.5, stations=3)
    for k in ("base", "pod_r", "pod_l", "cap_r", "cap_l"):
        ctx.rigid(k, Location())
    ctx.rigid("gps", L.gps_loc(p))
    return ctx.finish(body)
