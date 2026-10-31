"""Top plate on four posts: carries the 6S battery (strap through two slots), the VTX hanging underneath on two
M2-tapped bosses, and the XT60 in a cradle under the rear tab. Frame: z = 0 at the post feet (= body top),
plate from z = post_h to post_h + top_t. Prints upside down (plate on the bed; posts, bosses and cradle point up),
so no supports. Posts take M3 heat-set inserts from the feet.

XT60 (mates along its length, x): the rear end of the cradle is fully open for the battery plug, the front end has
a 1 mm stop each side that the housing pushes against when plugging in, with the solder cups and the lead to the
ESC passing through the gap between them; a cable tie through the side slot holds it in.
"""
from build123d import *
from kerf import iface

POSTS = [(31.5, 5), (31.5, -5), (-31.5, 5), (-31.5, -5)]   # must match parts/body.py
XT60_X = -51.0
VTX = "drone.vtx.tx800"
BOSS_H = 3.0
RX_X, RX_Y = -27.0, 15.5   # receiver (13 x 11 mm) under the plate, clear of the posts, VTX and strap slots


def build(ctx):
    p = ctx.p
    H, T = p.post_h, p.top_t
    xl, xw, xh = [ctx.cat.num(ctx.cat.get("drone.connectors.XT60"), k) for k in ("length", "width", "height")]
    plate = Pos(0, 0, H) * Box(80, 42, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    plate = plate.fillet(4.0, plate.edges().filter_by(Axis.Z))
    tab = Pos(-40 - 22 / 2 + 2, 0, H) * Box(22 + 4, 20, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = plate + tab
    for (x, y) in POSTS:
        s += Pos(x, y, 0) * Cylinder(4.5, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # VTX bosses under the plate, M2 pilot holes (light part, rarely removed: ENGINEERING.md section 7)
    sp = ctx.cat.num(ctx.cat.get(VTX), "spacing")
    for (x, y) in iface.square(sp):
        s += Pos(x, y, H - BOSS_H) * Cylinder(3.0, BOSS_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.stack_mount(ctx, VTX, Location((0, 0, H - BOSS_H), (180, 0, 0)), "vtx", depth=BOSS_H + T, kind="tap")
    # XT60 cradle under the rear tab: 1.6 mm side walls, 0.3 mm clearance, 12 mm deep
    cw, cl = xw + 0.6 + 3.2, xl + 0.6 + 3.2
    cradle = Pos(XT60_X, 0, H - 12) * Box(cl, cw, 12, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle -= Pos(XT60_X, 0, H - 13) * Box(xl + 0.6, xw + 0.6, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle -= Pos(XT60_X - cl / 2, 0, H - 13) * Box(4, xw + 0.6, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))  # rear: open
    cradle -= Pos(XT60_X + cl / 2, 0, H - 13) * Box(4, xw - 2, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))   # front: stops
    s += cradle
    s -= Pos(XT60_X + 4, 0, H - 6) * Box(3, cw + 2, 1.6, align=(Align.CENTER, Align.CENTER, Align.CENTER))  # tie slot
    for x in (-58.0, -46.0):                     # antenna / receiver lead tie slots through the rear tab
        for sy in (1, -1):
            s -= Pos(x, sy * 8.0, H - 1) * Box(3, 1.6, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (RX_X - 8.5, RX_X + 8.5):             # receiver tie slots either side of it
        s -= Pos(x, RX_Y, H - 1) * Box(1.6, 3, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (-18, 18):                            # battery strap slots (20 mm strap)
        s -= Pos(x, 0, H - 1) * Box(3, 22, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "posts", "M3", [(x, -y) for x, y in POSTS], Location((0, 0, 0), (180, 0, 0)),
                            "heatset", depth=H)
    ctx.rigid("base", Location((0, 0, 0)))
    ctx.rigid("battery", Location((0, 0, H + T)))
    ctx.rigid("xt60", Location((XT60_X, 0, H - xh)))
    ctx.rigid("vtx", Location((0, 0, H - BOSS_H), (180, 0, 0)))
    ctx.rigid("rx", Location((RX_X, RX_Y, H), (180, 0, 0)))       # receiver tied flat under the plate
    return ctx.finish(s, color="#2a2d31")
