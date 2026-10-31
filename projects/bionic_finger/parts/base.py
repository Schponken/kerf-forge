"""Knuckle mount: bolts to the hand frame with two M3 screws across its width; holds the mcp dowel (pressed) in its
knuckle disc; both tendons leave through its back face toward the actuator.
Origin on the mcp axis. Prints on its side (knuckle band on the bed)."""
import importlib.util as _iu
import pathlib as _pl

from build123d import *
from kerf import iface

_s = _iu.spec_from_file_location("bionic_fingerlib", _pl.Path(__file__).with_name("fingerlib.py"))
F = _iu.module_from_spec(_s)
_s.loader.exec_module(F)


def build(ctx):
    p = ctx.p
    b = F.SIDES["mcp"]                                     # base is the parent at mcp: knuckle band = bottom
    body = F.rect(-p.base_len, 0, -F.H, F.H)
    bottom, top = F.parent_end(body, body, 0.0)
    part = F.assemble(bottom, top, b)
    part -= F.pin_holes(ctx, 0.0, "mcp", "parent")
    m3 = iface.screw_spec("M3")
    for u in (p.mount_u1, p.mount_u2):                     # mounting holes along Y (vertical on the printer: round)
        part -= Pos(u, 0, 0) * Rot(90, 0, 0) * Cylinder(m3["clearance"] / 2, F.W + 2)
    up = -b
    j = F.joint_points(0.0)
    cut = F.runs([[(-p.base_len - 1, 0, -F.FLEX), j["flex_p"]],
                  [(-p.base_len - 1, 0, j["ext_wp"][2]), j["ext_wp"]]], up)
    cut += F.crossing_cuts(0.0, p.mcp_max, "parent", up)
    part = F.cut_all(part, cut)
    ctx.revolute("mcp", Axis((0, 0, 0), (0, 1, 0)), range=(0, p.mcp_max))
    ctx.rigid("flex_exit", Location((-p.base_len, 0, -F.FLEX)))
    ctx.rigid("ext_exit", Location((-p.base_len, 0, j["ext_wp"][2])))
    return ctx.finish(part)
