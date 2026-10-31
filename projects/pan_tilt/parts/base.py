"""Base: screws onto a 1/4-20 tripod screw and holds the pan SG90 upright, hung from a deck by its tabs.

The SG90's lead leaves its OUTPUT end somewhere between the case bottom and ~3 mm under the tabs (catalog
servos.SG90 cable_boss_*), right under the output-end tab screw, so the tabs can't screw down into a deep pocket wall.
Instead the servo slides in sideways (+Y) from the open -Y side: its case top passes into a slot in the deck, the tab
TOPS press against the deck's underside, and two M2 screws go in from below (through key holes in the floor) into
pilots in the deck (servo_mount top_through). The lead leaves through the open side.
The 1/4-20 nut drops into a hex pocket on a 1.5 mm floor before the servo goes in: tightening the tripod screw pulls
it down onto that floor (pure compression). The servo bottom sits above the tripod-screw tip zone (servo_floor_z).
Origin: tripod-screw axis on the bottom face; the pan axis is pan_x ahead (+X).
Printed upright on its bottom face; the deck over the cavity is a bridge between the end walls (see DESIGN.md).
"""
import math

from build123d import *
from kerf import iface, features

SERVO = "servos.SG90"
CLEAR = 1.0   # 0.5 mm per side: slide-in fit for the SG90 width spread (11.8-12.2, catalog note) and FDM shrinkage
CAV_DROP = 1.0   # cavity floor this far below the nominal servo bottom (tab-height spread 0.4 + 0.6 slide clearance)


def build(ctx):
    p = ctx.p
    L, W = p.base_l, p.base_w
    deck_z = p.tab_z + p.servo_tab_t                            # deck underside = servo tab tops
    H = deck_z + p.deck_t
    body = Box(L, W, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = fillet(body.edges().filter_by(Axis.Z), 4.0)
    body = chamfer(body.edges().group_by(Axis.Z)[0], 0.6)      # bed edge: no elephant's foot lip
    body = chamfer(body.edges().group_by(Axis.Z)[-1], 0.8)

    # cavity the servo slides into from -Y: tabs + lead envelope wide, from the servo bottom up to the deck
    wy = p.servo_W + CLEAR
    cav_x = p.servo_span + CLEAR
    # floor CAV_DROP below the servo bottom: the tab height spreads 15.6-16.0 between drawings (catalog note), and the
    # servo must slide in with its tab tops on the deck whatever its tab height (review round 1)
    cav_z = p.servo_floor_z - CAV_DROP
    cav = Pos(0, -W / 2 - 1, cav_z) * Box(cav_x, W / 2 + 1 + wy / 2, deck_z - cav_z,
                                         align=(Align.CENTER, Align.MIN, Align.MIN))
    body -= cav
    # deck: window + tab pilots from below (top_through), and the window opened to -Y so the case top slides in
    seat = Location((0, 0, deck_z))
    body -= iface.servo_mount(ctx, SERVO, seat, group="base_pan", plate_t=p.deck_t, kind="tap", clearance=CLEAR,
                              top_through=True)
    wx = p.servo_L + CLEAR
    body -= Pos(0, -W / 2 - 1, deck_z - 0.01) * Box(wx, W / 2 + 1, p.deck_t + 1, align=(Align.CENTER, Align.MIN, Align.MIN))

    # 1/4-20 nut pocket (flats across Y so the nut slides in from the open side too), +0.2 mm slip on the
    # across-flats, open to the cavity above
    af = p.nut_af + 0.2
    body -= Pos(0, 0, p.floor_t) * extrude(RegularPolygon(af / math.sqrt(3), 6), cav_z - p.floor_t + 0.01)
    # tripod screw clearance through the floor (1/4 in = 6.35 mm, +0.55 free) with a lead-in chamfer at the bottom
    body -= Pos(0, 0, -1) * Cylinder(3.45, p.floor_t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos(0, 0, -0.01) * Cone(3.45 + 0.8, 3.45, 0.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # hex-key + screw holes up through the floor under the two tab screws (screw head 3.8 + 1.0)
    head_r = iface.screw_spec("M2")["head_d"] / 2 + 0.5
    for sx in (-1, 1):
        body -= Pos(sx * p.servo_hx / 2, 0, -1) * Cylinder(head_r, cav_z + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # label on the +Y side
    body -= features.label("PT1", 5.0, depth=0.6, loc=Location((0, W / 2, H / 2), (90, 0, 180)), emboss=False)

    ctx.rigid("pan_seat", Location((0, 0, p.tab_z)))
    ctx.rigid("tripod", Location((0, 0, 0)))
    # off-head electrics, modelled hanging/strapped 150 mm below the head (on the tripod centre column or the desk):
    # 5 V adapter, barrel-jack terminal adapter, Raspberry Pi Zero 2 W (DESIGN.md 'Electrics')
    ctx.rigid("below_jack", Location((-40, 0, -150)))
    ctx.rigid("below_pi", Location((-40, 50, -150)))
    ctx.rigid("below_psu", Location((-40, -110, -175)))
    return ctx.finish(body)
