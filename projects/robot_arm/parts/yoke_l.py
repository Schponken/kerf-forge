"""Left yoke (-Y): the cheek the upper arm's pivot screw turns in (M3 socket-head screw through a free hole into a heat-set
insert in the upper arm, coaxial with the shoulder servo), with a foot bolted to the turntable platform (3 x M3) and
two gussets. Built in the turntable (world) frame. Printed lying on the cheek's outer face (-Y)."""
from build123d import *
from kerf import iface

import importlib.util as _iu
import pathlib as _pl
_s = _iu.spec_from_file_location("robot_armlib", _pl.Path(__file__).with_name("armlib.py"))
armlib = _iu.module_from_spec(_s)
_s.loader.exec_module(armlib)
yoke, FOOT_T = armlib.yoke, armlib.FOOT_T


def build(ctx):
    p = ctx.p
    body, pts = yoke(p, -1)
    body -= iface.bolt_pattern(ctx, "yoke_l_foot", "M3", pts, Location((0, 0, p.z_plat1 + FOOT_T)), kind="clearance",
                               depth=FOOT_T, teardrop=90)
    # pivot: free hole, entered from the outer face; +Z of the loc points out of the cheek (-Y)
    body -= iface.pin_hole(ctx, "M3", Location((p.x_sh, -p.cheek_out, p.z_sh), (90, 0, 0)), "sh_pivot", depth=p.plate_t, fit="free")
    # lightening window where the servo window is on the other cheek
    xc = p.x_sh - p.sh_out_x
    body -= Pos(xc - 12.0, -p.cheek_out + p.plate_t / 2, p.z_sh) * Box(18.0, p.plate_t + 2, 18.0)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
