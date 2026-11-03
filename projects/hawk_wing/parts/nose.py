"""STUB nose cap: camera fairing round the motor mount stand-off."""
from build123d import *
import importlib.util, pathlib
from kerf import aero

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    ctx.stub("nose cap fairing + camera cheeks being designed")
    body = loft([L.section_face(p, s[0]) for s in L.fuse_stations(p)[:2]], ruled=True)
    cam, lens = L.camera_locs(p)
    ctx.rigid("base", Location())
    ctx.rigid("camera", cam)
    ctx.rigid("lens", lens)
    return ctx.finish(body)
