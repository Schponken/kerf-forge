"""Nose block on section 4's front end (block frame: origin on the end face at the rail's bottom centre, body x < 0, pulley ahead).

Load path (DESIGN.md "Nose pulley", 948 N rearward on the axle): axle -> the two boss+strut cheeks (|y| 35.5..50, in line with
the load, compression) -> the 18 mm deep cap beam (x -10..8, spans y 50 -> 10) -> the rail's end face (|y| <= 10, z 0..40).
Side walls and the bottom plate clamp the block to the rail with the s4_front tee-nut screws (backup shear path, and they hold
the block on when the strands relax). Printed on its side (y up): every layer is the same x-z slice, so no ceilings; axle bores
and side screws are vertical, the bottom screw gets a teardrop roof.
Top at rail z 40 (a tractor prop flies over it, limit 80); the sled plate (z >= 42, |y| <= 36) runs over the cap at the end of a stop.
"""
from build123d import *
from kerf import features, iface

AXLE = "motion.rod_8mm_smooth"
GRIP = 6.0               # printed wall under an M5 tee-nut screw head (layout TNUT_GRIP)
CAP_T = 8.0              # cap over the rail end face, x 0..8 (contract)
BEAM_X = 10.0            # cap beam extends this far behind the end face: stops short of the screw heads at x = -15 (head r 4.25)
Y_OUT = 50.0             # axle cheek outer face = axle end (100 mm axle)
Y_IN = 35.5              # cheek inner face: 1 mm off the pulley's 69 mm width
BOSS_R = 12.0            # boss round the axle: 8 mm bore leaves 8 mm of wall
Z_TOP, Z_BOT = 40.0, -GRIP   # cap top = rail top; bottom plate underside


def _box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


def _prism(pts, y0, y1):
    """Polygon (x, z) extruded along y from y0 to y1."""
    return Pos(0, y1, 0) * extrude(Plane.XZ * Polygon(*pts, align=None), y1 - y0)


def _tnuts(ctx, group, xs, bottom):
    """M5 tee-nut screws: side screws at xs on both rail faces (heads out) at z = 10, bottom screw at x = bottom."""
    cut = None
    for x in xs:
        for sy in (1, -1):
            c = iface.bolt_pattern(ctx, group, "M5", [(0, 0)], Location((x, sy * (10 + GRIP), 10), (-90 * sy, 0, 0)), "clearance", GRIP, teardrop="auto")
            cut = c if cut is None else cut + c
    return cut + iface.bolt_pattern(ctx, group, "M5", [(0, 0)], Location((bottom, 0, -GRIP), (180, 0, 0)), "clearance", GRIP, teardrop="auto")


def build(ctx):
    p = ctx.p
    px, pz = p.pulley_dx, p.Z_MID
    body = ctx.add(_box(-60, 0, -16, 16, Z_BOT, 0), why="bottom plate under the rail: bottom tee-nut screw clamps the block up onto the rail", kind="clamp")
    for sy in (1, -1):
        y0, y1 = sorted((sy * 10, sy * (10 + GRIP)))
        body += ctx.add(_box(-60, 0, y0, y1, 0, 22), why="side wall on the rail's lower side face: carries the tee-nut screws (6 mm grip)", kind="clamp")
    body += ctx.add(_box(0, CAP_T, -Y_OUT, Y_OUT, Z_BOT, Z_TOP) + _box(-BEAM_X, 0, 10, Y_OUT, Z_BOT, Z_TOP) + _box(-BEAM_X, 0, -Y_OUT, -10, Z_BOT, Z_TOP),
                    why="cap over the rail end face takes the 948 N in compression; the 10 mm beam behind it (18 mm deep) spans y 50 -> 10 so the cheek loads reach the end face without bending the cap across layers",
                    kind="cap")
    for sy in (1, -1):
        y0, y1 = sorted((sy * Y_IN, sy * Y_OUT))
        # why: axle cheek = strut in line with the 948 N: full depth at the cap, tapering to the axle boss
        strut = _prism([(CAP_T - 1, Z_BOT), (CAP_T - 1, Z_TOP), (px, pz + BOSS_R + 2), (px, pz - BOSS_R - 2)], y0, y1)
        boss = Pos(px, (y0 + y1) / 2, pz) * Rot(90, 0, 0) * Cylinder(BOSS_R, y1 - y0)
        body += ctx.add(strut + boss, why="axle cheek: compression strut from the axle boss back to the cap (474 N each), 14.5 mm thick", kind="strut")
        body -= ctx.cut(iface.pin_hole(ctx, AXLE, Location((px, sy * Y_OUT, pz), (-90 * sy, 0, 0)), "axle", Y_OUT - Y_IN, fit="press", teardrop="auto"),
                        why="press seat for the 8 mm axle", kind="axle bore")
    body -= ctx.cut(_tnuts(ctx, "s4_front", [-15, -45], -30), why="s4_front tee-nut screw holes", kind="screw holes")

    def keep(at):
        x, y, z = at
        if abs(y) <= 10.6 and z <= 0.6 and x > -61 and x < 1:
            return "the rail's square end/bottom edge sits in this corner"
        if abs(x) < 0.6 and abs(abs(y) - 10) < 0.6 and z > 0:
            return "the rail's square end/side edge sits in this corner"
        return None

    body, left = features.fillet_inside(ctx, body, 2.0, keep=keep)
    ctx.rigid("section", Location((0, 0, 0)))
    ctx.rigid("axle", Location((px, 0, pz), (-90, 0, 0)))
    ctx.rigid("pulley", Location((px, 0, pz), (-90, 0, 0)))
    ctx.rigid("strand_exit", Location((px - 35, p.STRAND_Y[3], p.Z_BOT)))
    ctx.rigid("strand_exit_out", Location((px - 35, p.STRAND_Y[5], p.Z_BOT)))
    return ctx.finish(body)
