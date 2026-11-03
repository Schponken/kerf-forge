"""Bipod leg socket on one side of section 3 (frame: rail bottom centre at the mount; x along the rail, z up).

Load path: leg (axial, ~30 N static, A-frame so side loads arrive axially) -> blind socket (closed end = joint `leg`)
-> arm (z -10..0, widest at the cheek where the moment is) with a 45 degree gusset under it -> cheek on the rail's lower
side face -> 2 M5 tee-nut screws. The split clamp (one M5 screw across a slit in the outboard wall) holds the tube and
lets it slide +-25 mm for levelling. Printed upright; the socket leans 15 degrees, which prints without support.
"""
import math
from build123d import *
from kerf import features, iface

CHEEK_HX, CHEEK_Z0, CHEEK_Z1 = 25.0, -9.0, 21.0     # cheek: z -9..21 stays below the sled's wheels (z >= 23.5)
ARM_Z0, ARM_Z1 = -10.0, 0.0
WALL = 3.3                                           # socket wall round the 20.4 bore
BORE_D = 20.4
EAR_HX, SLIT = 10.0, 2.0
SCREW_R, SCREW_Z = 17.5, 36.0                        # clamp screw: radial offset of its axis, depth along the leg
Y_FREE, Z_FREE = 31.5, -22.5                         # strand channel: nothing below Z_FREE at |y| < Y_FREE (outer strand + 1 mm)


def _box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


def build(ctx):
    p = ctx.p
    sd = int(p.side)
    s = math.radians(float(p.leg_splay))
    ro = BORE_D / 2 + WALL
    leg = Location((0, sd * p.SOCK_Y, p.sock_z), (180 + sd * float(p.leg_splay), 0, 0))

    cheek = _box(-CHEEK_HX, CHEEK_HX, sd * 10, sd * (10 + p.TNUT_GRIP), CHEEK_Z0, CHEEK_Z1)
    body = ctx.add(cheek, why="cheek on the rail's lower side face, 6 mm printed grip under the tee-nut screw heads", kind="cheek")

    arm = Pos(0, 0, ARM_Z0) * extrude(Polygon((-CHEEK_HX, sd * 10), (CHEEK_HX, sd * 10), (ro, sd * (p.SOCK_Y + 4)),
                                              (-ro, sd * (p.SOCK_Y + 4)), align=None), ARM_Z1 - ARM_Z0)
    body += ctx.add(arm, why="arm out to the socket, widest at the cheek where the leg moment is largest", kind="arm")
    wedge = features.gusset((0, sd * 16, ARM_Z0), (0, sd, 0), (0, 0, -1), 9.0, 9.0, 2 * CHEEK_HX - 6)
    body += ctx.add(wedge, why="45 degree gusset under the arm root: stiffens the cheek-arm corner and prints without support", kind="gusset")

    # socket, built in the leg frame (+Z down the leg, closed end at z = 0) and moved into place
    L = 70.0
    outer = Pos(0, 0, -4) * Cylinder(ro, L + 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ear = _box(-EAR_HX, EAR_HX, 0, -sd * (SCREW_R + 7.0), 18, L)     # outboard is -sd * local Y for this leg frame
    sock = ctx.add(outer + ear, why="socket tube round the leg (closed end = joint leg) with clamp ears on the outboard side", kind="socket")
    sock -= Pos(0, 0, 0) * Cylinder(BORE_D / 2, L + 5, align=(Align.CENTER, Align.CENTER, Align.MIN))   # why: blind bore, leg bottoms at z = 0
    sock -= _box(-SLIT / 2, SLIT / 2, 0, -sd * 40, 16, L + 5)   # why: clamp slit through the outboard wall and ears
    # why: clamp screw across the slit: round teardrop clearance + hex nut trap (nut pushed in from the far ear), vertex up
    pl = Plane(origin=(EAR_HX, -sd * SCREW_R, SCREW_Z), x_dir=(0, 0, 1), z_dir=(1, 0, 0)).location
    td = iface.print_up_deg(ctx, leg * pl)
    sock -= pl * iface.hole("M5", "clearance", 2 * EAR_HX, teardrop=td)[0]
    sock -= pl * iface.hole("M5", "nut_trap", 2 * EAR_HX)[0]
    body += leg * sock

    # why: tee-nut screws, same group as section 3's bipod sites
    for x in (-15, 15):
        body -= iface.bolt_pattern(ctx, "s3_bipod", "M5", [(0, 0)], Location((x, sd * (10 + p.TNUT_GRIP), 10), (-90 * sd, 0, 0)), "clearance", p.TNUT_GRIP, teardrop="auto")

    z_cut = p.sock_z - ro * math.sin(s) - 60 * math.cos(s)
    body -= _box(-100, 100, -200, 200, z_cut - 50, z_cut)       # why: flat foot of the socket on the bed; the bore stays >= 60 deep on the short side
    body -= _box(-100, 100, 0, sd * Y_FREE, -100, Z_FREE)       # why: strand channel: nothing inboard of the outer strand below the rail

    ctx.rigid("section", Location((0, 0, 0)))
    ctx.rigid("leg", leg)
    body, left = features.fillet_inside(ctx, body, 2.0)
    return ctx.finish(body)
