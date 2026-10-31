"""Base: a solid block that screws onto a 1/4-20 tripod screw and holds the pan SG90 upright.

The servo drops into a pocket from the top and its tabs rest on the top face (two M2 screws into printed pilot holes).
The 1/4-20 nut is dropped down the same pocket before the servo, into a hex pocket on a 1.5 mm floor: tightening the
tripod screw pulls the nut down onto that floor, so the clamp load is pure compression of the floor (it can't pull
the nut out). The servo body sits above the tripod-screw tip zone (servo_floor_z). A slot in the -X end lets the
servo lead out. Origin: tripod-screw axis on the bottom face; the pan axis is pan_x ahead (+X).
Printed upright on its bottom face: the pocket and slot are open to the top, so there are no bridges.
"""
import math

from build123d import *
from kerf import iface, features

SERVO = "servos.SG90"
CLEAR = 1.0   # 0.5 mm per side: drop-in fit for the SG90 width spread (11.8-12.2, catalog note) and FDM shrinkage


def build(ctx):
    p = ctx.p
    H = p.tab_z
    L, W = p.base_l, p.base_w
    body = Box(L, W, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = fillet(body.edges().filter_by(Axis.Z), 4.0)
    body = chamfer(body.edges().group_by(Axis.Z)[0], 0.6)      # bed edge: no elephant's foot lip
    body = chamfer(body.edges().group_by(Axis.Z)[-1], 0.8)

    # servo: window + two M2 pilot holes (servo body centre over the nut axis; output on the pan axis at +pan_x)
    seat = Location((0, 0, H))
    deck = H - p.servo_floor_z                                  # material the tab pilots go into
    body -= iface.servo_mount(ctx, SERVO, seat, group="base_pan", plate_t=deck, kind="tap", clearance=CLEAR)
    # body pocket below the window, down to the nut pocket (same footprint as the window)
    wx, wy = p.servo_L + CLEAR, p.servo_W + CLEAR
    nut_top = p.floor_t + p.nut_h + 0.3
    body -= Pos(0, 0, nut_top) * Box(wx, wy, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sx in (-1, 1):
        for sy in (-1, 1):
            body -= Pos(sx * (wx / 2 - 0.35), sy * (wy / 2 - 0.35), nut_top) * Cylinder(1.0, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # 1/4-20 nut pocket (flats across Y so the nut fits down the 12.8 mm pocket), +0.2 mm slip on the across-flats
    af = p.nut_af + 0.2
    hexp = extrude(RegularPolygon(af / math.sqrt(3), 6), nut_top - p.floor_t)
    body -= Pos(0, 0, p.floor_t) * hexp
    # tripod screw clearance through the floor (1/4 in = 6.35 mm, +0.55 free) with a lead-in chamfer at the bottom
    body -= Pos(0, 0, -1) * Cylinder(3.45, p.floor_t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos(0, 0, -0.01) * Cone(3.45 + 0.8, 3.45, 0.8, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # servo-lead slot through the -X end, open to the top, offset in Y so it clears the end tab screw
    sl_y0, sl_y1 = 2.2, wy / 2                                  # 4.7 mm wide, 1.3 mm wall to the tab pilot
    slot = Pos(-(L / 2 + wx / 2) / 2 - 0.5, (sl_y0 + sl_y1) / 2, p.servo_floor_z) * Box(
        L / 2 - wx / 2 + 3.0, sl_y1 - sl_y0, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= slot

    # label on the +Y side
    body -= features.label("PT1", 5.0, depth=0.6, loc=Location((0, W / 2, H / 2), (90, 0, 180)), emboss=False)

    ctx.rigid("pan_seat", seat)
    ctx.rigid("tripod", Location((0, 0, 0)))
    # off-head electrics, modelled hanging/strapped 150 mm below the head (on the tripod centre column or the desk):
    # 5 V adapter, barrel-jack terminal adapter, Raspberry Pi Zero 2 W (DESIGN.md 'Electrics')
    ctx.rigid("below_jack", Location((-40, 0, -150)))
    ctx.rigid("below_pi", Location((-40, 50, -150)))
    ctx.rigid("below_psu", Location((-40, -110, -175)))
    return ctx.finish(body)
