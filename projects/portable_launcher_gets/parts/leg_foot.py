"""Foot on a bipod leg's lower end (frame: tube end centre, +Z along the leg toward the ground).

A sleeve over the tube end (bore 20.4, 30 deep) on a solid core that ends in a flat pad. The pad's ground face is the
plane through (0, 0, foot_t) with outward normal n (world down in this frame), so it lies flat at home. Four ribs carry
the ground reaction from the sleeve into the pad. Printed pad down: print_rot puts n straight down.
No spike: a spike below the pad would become the only ground contact in the tip_over check (see report).
"""
import math
from build123d import *
from kerf import features

BORE_D, WALL, SLEEVE = 20.4, 3.3, 30.0
PAD_X, PAD_Y, PAD_T = 60.0, 45.0, 5.0
RIB_T = 2.4


def build(ctx):
    p = ctx.p
    sd = int(p.side)
    r, s = math.radians(float(p.rail_deg)), math.radians(float(p.leg_splay))
    n = Vector(-math.sin(r), sd * math.cos(r) * math.sin(s), math.cos(r) * math.cos(s))
    xd = (Vector(1, 0, 0) - n * n.X).normalized()                # in-plane x: along the rail
    pl = Plane(origin=(0, 0, float(p.foot_t)), x_dir=xd, z_dir=n)  # ground plane, +Z (n) out of the part toward the ground
    ro = BORE_D / 2 + WALL

    core = Pos(0, 0, -SLEEVE) * Cylinder(ro, SLEEVE + p.foot_t + 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = ctx.add(core, why="sleeve over the tube end on a solid core: the tube bears on its floor at z = 0", kind="sleeve")
    pad = Pos(0, 0, -PAD_T) * Box(PAD_X, PAD_Y, PAD_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pad = fillet(pad.edges().filter_by(Axis.Z), 4.0)
    body += ctx.add(pl.location * pad, why="ground pad 60 x 45: the bipod's footprint, flat at the home angle", kind="pad")
    for ang, leg1 in ((0, 15.0), (90, 9.0), (180, 15.0), (270, 9.0)):
        rib = features.gusset((ro - 2, 0, 0), (1, 0, 0), (0, 0, -1), leg1 + 2, 16.0, RIB_T)
        body += ctx.add(pl.location * (Rot(0, 0, ang) * Pos(0, 0, -PAD_T) * rib), why="rib from the sleeve to the pad edge: carries the ground reaction", kind="rib")
    # why: cut everything below the ground plane flat, and open the bore
    body -= pl.location * Pos(0, 0, 50) * Box(300, 300, 100)
    body -= Pos(0, 0, -SLEEVE - 1) * Cylinder(BORE_D / 2, SLEEVE + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("leg", Location((0, 0, 0)))
    body, left = features.fillet_inside(ctx, body, 2.0)
    return ctx.finish(body)
