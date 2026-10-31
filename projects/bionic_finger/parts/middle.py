"""Middle phalanx: child of pip, parent of dip. Origin on the pip axis, dip axis at x = L2. Prints on its side."""
import importlib.util as _iu
import pathlib as _pl

from build123d import *
from kerf import iface

_s = _iu.spec_from_file_location("bionic_fingerlib", _pl.Path(__file__).with_name("fingerlib.py"))
F = _iu.module_from_spec(_s)
_s.loader.exec_module(F)


def build(ctx):
    p = ctx.p
    L = p.L2
    b = -F.SIDES["pip"]
    assert b == F.SIDES["dip"], "knuckle sides must alternate so both knuckles print on the bed"
    body = F.rect(0, L, -F.H, F.H)
    bottom, top = F.child_end(body)
    bottom, top = F.parent_end(bottom, top, L)
    part = F.assemble(bottom, top, b)
    part -= F.pin_holes(ctx, 0.0, "pip", "child")
    part -= F.pin_holes(ctx, L, "dip", "parent")
    up = -b
    jm, jp = F.joint_points(0.0), F.joint_points(L)
    cut = F.runs([[jm["flex_c"], jp["flex_p"]], [jm["ext_wc"], jp["ext_wp"]]], up)
    cut += F.crossing_cuts(0.0, p.pip_max, "child", up) + F.crossing_cuts(L, p.dip_max, "parent", up)
    part = F.cut_all(part, cut)
    ctx.rigid("pip", F.CHILD_FRAME)
    ctx.revolute("dip", Axis((L, 0, 0), (0, 1, 0)), range=(0, p.dip_max))
    return ctx.finish(part)
