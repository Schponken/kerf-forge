"""Top plate on four posts: carries the 6S battery (strap through two slots), the VTX hanging underneath on two
M2-tapped bosses, and the XT60 in a cradle under the rear tab. Frame: z = 0 at the post feet (= body top),
plate from z = post_h to post_h + top_t. Prints upside down (plate on the bed; posts, bosses and cradle point up),
so no supports. Posts take M3 heat-set inserts from the feet.

Battery strap: one 20 mm strap around the pack's width (over the pack, down its sides, past 1 mm notches in the plate
edges and under the plate) in the band x 4.5..24.5, which is clear of the VTX (x -27.5..0.5) and the front pillar;
loop about 170 mm on a 250 mm strap (review round 3: the old lengthwise run under the plate hit the VTX bosses).

XT60 (mates along its length, x): the rear end of the cradle is fully open for the battery plug, the front end has
a 1 mm stop each side that the housing pushes against when plugging in, with the solder cups and the lead to the
ESC passing through the gap between them. The cradle walls are shorter than the connector, so its lower 4 mm hangs
out; a cable tie goes down through a vertical slot just outside one wall, under the connector and up the other slot,
so it holds the connector up into the cradle and against pull-out by friction (review round 2: the old side slot ran
through the connector itself).

Each post pair (16 mm apart) is filled in to one solid 9 x 25 mm stadium pillar, so a side hit on the battery bends
two pillars instead of four thin posts (the posts print upright: that bending runs across the layers; checked by
the top_plate_x / top_plate_y FEA cases). Leads pass outside the pillars (|y| > 12.5 mm; the plate is 42 mm wide).
"""
from build123d import *
from kerf import iface

POSTS = [(33.0, 8), (33.0, -8), (-33.0, 8), (-33.0, -8)]   # must match parts/body.py
XT60_X = -59.0  # cradle x -71.55..-46.45: the solder cups end 9 mm behind the rear pillar so the 12 AWG leads can turn
VTX = "drone.vtx.tx800"
BOSS_H = 3.0
VTX_X = -13.5    # VTX centre: its 28 mm board spans x -27.5..0.5, 1 mm from the rear pillar, clear of the strap band
STRAP_X0, STRAP_X1 = 4.5, 24.5   # width-wise battery strap band (20 mm strap), clear of the VTX and the front pillar
STRAP_T = 1.8
ROOF_X1 = 58.0   # camera roof front edge (lens front is at x 61.9-64.8 over the tilt range)
ANT_X = -78.0    # VTX antenna head centre (tab ends at x -72; head is 11 mm across)
TAB_W = 28.0     # rear tab width: XT60 cradle + its tie slots + the antenna tie slots with >= 2.5 mm edge margin
RX_X, RX_Y = 46.5, 0.0     # receiver (13 x 11 mm) under the camera roof: >= 5 mm above the camera at full tilt,
#                            clear of the pillars, VTX and the strap's under-run


def build(ctx):
    p = ctx.p
    H, T = p.post_h, p.top_t
    xl, xw, xh = [ctx.cat.num(ctx.cat.get("drone.connectors.XT60"), k) for k in ("length", "width", "height")]
    plate = Pos(0, 0, H) * Box(80, 42, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    plate = plate.fillet(4.0, plate.edges().filter_by(Axis.Z))
    tab = Pos(-54, 0, H) * Box(36, TAB_W, T, align=(Align.CENTER, Align.CENTER, Align.MIN))   # x -72..-36: the cradle walls
    #                                                                                   (to x -71.55) start on the plate
    # camera roof: a 24 mm wide tongue of the plate reaching forward over the camera (top of the camera at 40 deg tilt
    # is z 35.2 above the body bottom = 28 here, the roof underside is at 38), ending 4 mm behind the lens front, so
    # a pole or branch coming from above hits the roof, not the camera (review round 2)
    roof = Pos(38, 0, H) * Box(ROOF_X1 - 38, 24, T, align=(Align.MIN, Align.CENTER, Align.MIN))
    roof = roof.fillet(4.0, roof.edges().filter_by(Axis.Z).filter_by_position(Axis.X, ROOF_X1 - 1, ROOF_X1 + 1))
    s = plate + tab + roof
    for sy in (1, -1):   # 1 mm edge notches locate the width-wise strap so it can't slide along the pack
        s -= Pos((STRAP_X0 + STRAP_X1) / 2, sy * 21, H - 1) * Box(STRAP_X1 - STRAP_X0 + 1, 2, T + 2,
                                                                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    for (x, y) in POSTS:
        s += Pos(x, y, 0) * Cylinder(4.5, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in sorted({x for x, _ in POSTS}):         # web each post pair into one pillar
        s += Pos(x, 0, 0) * Box(9.0, 16.0, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # VTX bosses under the plate, M2 pilot holes (light part, rarely removed: ENGINEERING.md section 7)
    sp = ctx.cat.num(ctx.cat.get(VTX), "spacing")
    for (x, y) in iface.square(sp):
        s += Pos(VTX_X + x, y, H - BOSS_H) * Cylinder(3.0, BOSS_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.stack_mount(ctx, VTX, Location((VTX_X, 0, H - BOSS_H), (180, 0, 0)), "vtx", depth=BOSS_H + T, kind="tap")
    # XT60 cradle under the rear tab: 1.6 mm side walls, 0.3 mm clearance, 12 mm deep
    cw, cl = xw + 0.6 + 3.2, xl + 0.6 + 3.2
    cradle = Pos(XT60_X, 0, H - 12) * Box(cl, cw, 12, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle -= Pos(XT60_X, 0, H - 13) * Box(xl + 0.6, xw + 0.6, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle -= Pos(XT60_X - cl / 2, 0, H - 13) * Box(4, xw + 0.6, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))  # rear: open
    cradle -= Pos(XT60_X + cl / 2, 0, H - 13) * Box(4, xw - 2, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))   # front: stops
    s += cradle
    for sy in (1, -1):                           # XT60 tie: down outside one wall, under the connector, up the other
        s -= Pos(XT60_X, sy * (cw / 2 + 0.8), H - 1) * Box(3, 1.6, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (-66.0, -54.0):                     # VTX antenna tie slots through the rear tab (y -10.5, clear of the cradle)
        s -= Pos(x, -10.5, H - 1) * Box(3, 1.6, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sy in (1, -1):                           # receiver T-antenna legs tied up and out in a V at the roof's front
        s -= Pos(52.0, sy * 9.0, H - 1) * Box(3, 1.6, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (RX_X - 8.5, RX_X + 8.5):             # receiver tie slots either side of it
        s -= Pos(x, RX_Y, H - 1) * Box(1.6, 3, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "posts", "M3", [(x, -y) for x, y in POSTS], Location((0, 0, 0), (180, 0, 0)),
                            "heatset", depth=H)
    ctx.rigid("base", Location((0, 0, 0)))
    ctx.rigid("battery", Location((0, 0, H + T)))
    ctx.rigid("xt60", Location((XT60_X, 0, H - xh)))
    ctx.rigid("vtx", Location((VTX_X, 0, H - BOSS_H), (180, 0, 0)))
    ctx.rigid("rx", Location((RX_X, RX_Y, H), (180, 0, 0)))
    # VTX antenna (Lollipop 4+ 95 mm tube): from the VTX's rear corner outside the rear pillar (y -15), under the tab
    # where one tie through the slot pair at y -10.5 holds it, out past the tab end and up; head above the tab end
    ctx.rigid("vant", Location((ANT_X, -10.5, H + T)))
    # strap: under-run below the plate and the two side runs past the notched edges (keep-outs, owner strap)
    ctx.rigid("strap_u", Location(((STRAP_X0 + STRAP_X1) / 2, 0, H - STRAP_T)))
    for tag, sy in (("strap_l", 1), ("strap_r", -1)):
        ctx.rigid(tag, Location(((STRAP_X0 + STRAP_X1) / 2, sy * (20 + STRAP_T / 2), H - STRAP_T)))
    ctx.rigid("strap_top", Location(((STRAP_X0 + STRAP_X1) / 2, 0, H + T)))
    return ctx.finish(s, color="#2a2d31")
