"""STUB fuselage: loft of the outer stations with the glove's saddle cut; joints for everything it carries."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    ctx.stub("fuselage shell, bay, shelf, bulkhead, saddle, boom socket being designed")
    body = loft([L.section_face(p, s[0]) for s in L.fuse_stations(p)[1:]], ruled=True)
    body = body - aero.wing_solid(L.planform(p), -p.pivot_y, p.pivot_y, stations=3)
    for k in ("nose", "motor_mount", "glove", "hatch", "boom_clamp", "tail"):
        ctx.rigid(k, Location())
    ctx.rigid("boom", L.boom_loc(p))
    for k, loc in L.item_locs(p).items():
        ctx.rigid(k, loc)
    return ctx.finish(body)
