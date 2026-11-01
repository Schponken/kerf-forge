"""Middle phalanx: child of pip, parent of dip. Origin on the pip axis, dip axis at x = L2. Prints on its side."""
import importlib.util as _iu
import pathlib as _pl

from build123d import *
from kerf import features, iface

_s = _iu.spec_from_file_location("bionic_fingerlib", _pl.Path(__file__).with_name("fingerlib.py"))
F = _iu.module_from_spec(_s)
_s.loader.exec_module(F)


def build(ctx):
    p = ctx.p
    L = p.L2
    b = -F.SIDES["pip"]
    assert b == F.SIDES["dip"], "knuckle sides must alternate so both knuckles print on the bed"
    body = F.rect(0, L, -F.H, F.H)
    bottom, top = F.child_end(body, p.pip_max)
    bottom, top = F.parent_end(bottom, top, L, p.dip_max)
    part = F.assemble(bottom, top, b)
    part -= F.pin_holes(ctx, 0.0, "pip", "child")
    part += F.insert_boss(L, "dip")
    part -= F.pin_holes(ctx, L, "dip", "parent")
    up = -b
    jm, jp = F.joint_points(0.0), F.joint_points(L)
    cut = F.runs([[jm["flex_c"], jp["flex_p"]], [jm["ext_wc"], jp["ext_wp"]]], up)
    cut += F.crossing_cuts(0.0, p.pip_max, "child", up) + F.crossing_cuts(L, p.dip_max, "parent", up)
    part = F.cut_all(part, cut)
    part, _ = F.edge_chamfers(ctx, part)
    ctx.rigid("pip", F.CHILD_FRAME)
    ctx.revolute("dip", Axis((L, 0, 0), (0, 1, 0)), range=(0, p.dip_max))
    # why: every remaining sharp inside corner rounded (r 0.8, 0.4 where it does not fit): stress raisers and weak
    # layer seams (ENGINEERING.md s5); pin, insert and screw features are exempt
    part, left = features.fillet_inside(ctx, part, 0.8, keep=lambda at: (
        "where the knuckle's clearance cut meets the dorsal face across the lap band at the joint axis: OCC cannot "
        "fillet it (0.8 and 0.4 mm both fail); the pin carries the joint load, FEA use there is under 20 %")
        if min(abs(at[0] - j) for j in (0.0, p.L2)) < 0.6 and abs(at[2]) > F.H - 0.3 else None)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(part)
