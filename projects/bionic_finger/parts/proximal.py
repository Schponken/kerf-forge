"""Proximal phalanx: child of mcp (turns on the mcp shoulder screw), parent of pip (heat-set insert for the pip shoulder
screw in its distal knuckle).
Origin on the mcp axis, pip axis at x = L1. Prints on its side."""
import importlib.util as _iu
import pathlib as _pl

from build123d import *
from kerf import features, iface

_s = _iu.spec_from_file_location("bionic_fingerlib", _pl.Path(__file__).with_name("fingerlib.py"))
F = _iu.module_from_spec(_s)
_s.loader.exec_module(F)


def build(ctx):
    p = ctx.p
    L = p.L1
    b = -F.SIDES["mcp"]
    assert b == F.SIDES["pip"], "knuckle sides must alternate so both knuckles print on the bed"
    body = F.rect(0, L, -F.H, F.H)
    bottom, top = F.child_end(body, p.mcp_max)
    bottom, top = F.parent_end(bottom, top, L, p.pip_max)
    part = F.assemble(bottom, top, b)
    part -= F.pin_holes(ctx, 0.0, "mcp", "child")
    part += F.insert_boss(L, "pip")
    part -= F.pin_holes(ctx, L, "pip", "parent")
    up = -b
    jm, jp = F.joint_points(0.0), F.joint_points(L)
    cut = F.runs([[jm["flex_c"], jp["flex_p"]], [jm["ext_wc"], jp["ext_wp"]]], up)
    cut += F.crossing_cuts(0.0, p.mcp_max, "child", up) + F.crossing_cuts(L, p.pip_max, "parent", up)
    part = F.cut_all(part, cut)
    part, _ = F.edge_chamfers(ctx, part)
    ctx.rigid("mcp", F.CHILD_FRAME)
    ctx.revolute("pip", Axis((L, 0, 0), (0, 1, 0)), range=(0, p.pip_max))
    # why: every remaining sharp inside corner rounded (r 0.8, 0.4 where it does not fit): stress raisers and weak
    # layer seams (ENGINEERING.md s5); pin, insert and screw features are exempt
    part, left = features.fillet_inside(ctx, part, 0.8, occ=True, keep=lambda at: (
        "where the knuckle's clearance cut meets the dorsal face across the lap band at the joint axis: OCC cannot "
        "fillet it (0.8 and 0.4 mm both fail); the pin carries the joint load")
        if min(abs(at[0] - j) for j in (0.0, p.L1)) < 0.6 and abs(at[2]) > F.H - 0.3 else None)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(part)
