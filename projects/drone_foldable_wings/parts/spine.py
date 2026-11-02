"""Spine: the lid over the aft fuselage's top opening, the ridge between the two wing roots and the upper pivot plates.
PETG, 4 perimeters. Printed upright (cover underside on the bed): the cover is a flat plate and the ridge stands on
it; only the two arms over the pins overhang (supports under the arms: the hub bosses sit right under them, so
there is no room for a 45 deg gusset).

Load path: each wing's pin is pressed into an arm (6 mm plate, z spine_arm_z0..+6). Under lift the boss tilts and
pushes the arm's pin inboard (the deck end outboard): the two arms push on each other through the 28 mm wide ridge
(a strut in compression), and the lift's upward share goes through the 4 M3 (counterbored down wells in the ridge) into
the aft fuselage's heat-set lugs. The cover (2.5 mm, top flush with fuse_top) lies on the opening's rim ledges.
Holes: round each hub boss (r 11, widened to r 16 where the aileron lead swings), over each pinion (r 10.5: its
4 horn screw heads turn in it, and a hex key reaches them and the horn centre screw without taking the spine off),
the GPS lead behind the GPS pad.
"""
from build123d import *
import importlib.util, pathlib
from kerf import iface
from kerf.features import fillet_inside

_here = pathlib.Path(__file__)
_spec = importlib.util.spec_from_file_location("dfw_layout", _here.with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_aspec = importlib.util.spec_from_file_location("dfw_aft_fuse", _here.with_name("aft_fuse.py"))
A = importlib.util.module_from_spec(_aspec); _aspec.loader.exec_module(A)   # opening outline, cover, bolt sites

RIDGE_HW = 14.0         # ridge half width (DESIGN: |y| <= 14 between the wing roots)
ARM_R = 8.0             # arm end round the pin
GRIP = 4.0              # spine material under each screw head (well floor above the cover underside)
GPS_X = 150.0
GPS_LEAD = (170.0, 0.0, 6.0)   # x, y, diameter


def build(ctx):
    p = ctx.p
    z0, z1 = A.cover_z0(p), p.fuse_top
    ztop = p.spine_arm_z0 + L.PLATE_T
    x0, x1 = A.OPEN_X[0] + A.GAP_COVER, A.OPEN_X[1] - A.GAP_COVER
    cover = Pos(0, 0, z0) * extrude(offset(A.opening(p), -A.GAP_COVER), A.COVER_T)
    body = ctx.add(cover, why="lid over the aft fuselage opening, flush with its top", kind="plate")
    ridge = Pos(x0, -RIDGE_HW, z0) * Box(x1 - x0, 2 * RIDGE_HW, ztop - z0, align=(Align.MIN, Align.MIN, Align.MIN))
    ridge = chamfer(ridge.edges().filter_by(Axis.Y).group_by(Axis.X)[0].sort_by(Axis.Z)[-1], 12.0)   # front: 45 deg nose
    body += ctx.add(ridge, why="ridge between the wing roots: strut between the two arms, GPS pad on top", kind="ridge")
    for s in (1, -1):
        c = (p.pivot_x, s * p.pivot_y)
        sk = make_hull((Pos(*c) * Circle(ARM_R)).edges() + (Pos(c[0], s * RIDGE_HW / 2) * Rectangle(2 * ARM_R + 8, RIDGE_HW)).edges())
        arm = Pos(0, 0, p.spine_arm_z0) * extrude(make_face(sk), L.PLATE_T)
        body += ctx.add(arm, why="upper pivot plate: holds the top of the steel pin", kind="arm")
        # hub boss (r 10 + 1) with room for the aileron lead (r 12, swings 0..fold_max ahead of the pin)
        hole = Pos(*c) * Circle(p.boss_r + 1.0) + (Pos(*c) * Circle(16.0) & Pos(c[0], s * 22.0 + (s - 1) * 15) * Rectangle(60, 30, align=(Align.CENTER, Align.MIN)))
        body -= ctx.cut(Pos(0, 0, z0 - 1) * extrude(hole, A.COVER_T + 2), why="hub boss and aileron lead pass the cover", kind="hole")
        pc = (p.pinion_x, s * p.pivot_y)
        body -= ctx.cut(Pos(pc[0], pc[1], z0 - 1) * Cylinder(10.5, A.COVER_T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                        why="pinion screw heads turn here; key access to the horn + pinion screws", kind="hole")
        body -= iface.pin_hole(ctx, L.PIN, Location((c[0], c[1], ztop)), f"pivot_{'l' if s < 0 else 'r'}",
                               depth=L.PLATE_T, fit="press", teardrop="auto")
    body -= ctx.cut(Pos(GPS_LEAD[0], GPS_LEAD[1], z0 - 1) * Cylinder(GPS_LEAD[2] / 2, ztop - z0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="GPS lead into the fuselage", kind="wire hole")
    # 4 M3 down counterbored wells into the aft fuselage's spine lugs; heads on a 4 mm floor above the cover underside
    body -= iface.bolt_pattern(ctx, "spine", "M3", A.SPINE_BOLTS, Location((0, 0, ztop)), kind="counterbore",
                               depth=ztop - z0, counterbore_depth=ztop - z0 - GRIP)
    def keep(at):
        if abs(at[2] - p.spine_arm_z0) < 0.2 and abs(abs(at[1]) - RIDGE_HW) < 0.2:
            return "arm underside to ridge side: the hub boss turns 0.5 mm under the arm, a fillet would reach into it"
        return None
    body, failed = fillet_inside(ctx, body, r=2.0, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    ctx.rigid("base", Location())
    ctx.rigid("gps", Location((GPS_X, 0, ztop)))
    return ctx.finish(body)
