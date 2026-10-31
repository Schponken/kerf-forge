"""Distal phalanx (fingertip): child of dip. Both tendons end here in knot pockets open to the top face (tie a
stopper knot, pull it into the pocket, wick CA glue in). Origin on the dip axis, fingertip at x = L3. Prints on its side."""
import importlib.util as _iu
import pathlib as _pl

from build123d import *
from kerf import iface

_s = _iu.spec_from_file_location("bionic_fingerlib", _pl.Path(__file__).with_name("fingerlib.py"))
F = _iu.module_from_spec(_s)
_s.loader.exec_module(F)


def build(ctx):
    p = ctx.p
    L = p.L3
    r_tip = 6.0
    b = -F.SIDES["dip"]
    body = Polygon((0, -F.H), (L - r_tip - 2, -F.H), (L - r_tip, -r_tip), (L - r_tip, r_tip), (L - r_tip - 2, F.H), (0, F.H),
                   align=None) + F.disc(L - r_tip, r_tip)
    bottom, top = F.child_end(body)
    part = F.assemble(bottom, top, b)
    part -= F.pin_holes(ctx, 0.0, "dip", "child")
    up = -b
    jd = F.joint_points(0.0)
    fa, ea = (p.flex_anchor_u, 0, -F.FLEX), (p.ext_anchor_u, 0, jd["ext_wc"][2])
    cut = F.runs([[jd["flex_c"], fa], [jd["ext_wc"], ea]], up)
    cut += F.crossing_cuts(0.0, p.dip_max, "child", up)
    for a in (fa, ea):                                     # knot pockets: vertical (round) holes from the top face
        y_top = up * F.W / 2
        cut.append(Pos(a[0], (y_top + 0.0) / 2 + (-up) * 0.6, a[2]) * Rot(90, 0, 0)
                   * Cylinder(p.knot_d / 2, F.W / 2 + 1.2 + 1.0))
    part = F.cut_all(part, cut)
    ctx.rigid("dip", F.CHILD_FRAME)
    ctx.rigid("tip", Location((L, 0, 0)))
    ctx.rigid("flex_anchor", Location(fa))
    ctx.rigid("ext_anchor", Location(ea))
    return ctx.finish(part)
