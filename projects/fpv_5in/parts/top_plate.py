"""Top plate on four posts: carries the 6S battery (strap through two slots) and the XT60 in a cradle under the
rear tab. Frame: z = 0 at the post feet (= body top), plate from z = post_h to post_h + top_t. Prints upside down
(plate on the bed, posts and cradle pointing up), so no supports. Posts take M3 heat-set inserts from the feet."""
from build123d import *
from kerf import iface

POSTS = [(30, 14), (30, -14), (-30, 14), (-30, -14)]
XT60_X = -51.0


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
    # XT60 cradle hanging under the rear tab: 1.6 mm walls, 0.3 mm clearance, 12 mm deep, open at the back for the lead
    cw, cl = xw + 0.6 + 3.2, xl + 0.6 + 3.2
    cradle = Pos(XT60_X, 0, H - 12) * Box(cl, cw, 12, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle -= Pos(XT60_X, 0, H - 13) * Box(xl + 0.6, xw + 0.6, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cradle -= Pos(XT60_X - cl / 2, 0, H - 13) * Box(6, xw - 2, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s += cradle
    s -= Pos(XT60_X + 4, 0, H - 6) * Box(3, cw + 2, 1.6, align=(Align.CENTER, Align.CENTER, Align.CENTER))  # tie slot
    # battery strap slots (20 mm strap)
    for x in (-18, 18):
        s -= Pos(x, 0, H - 1) * Box(3, 22, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # heat-set inserts in the post feet (screws come up through the body)
    s -= iface.bolt_pattern(ctx, "posts", "M3", [(x, -y) for x, y in POSTS], Location((0, 0, 0), (180, 0, 0)),
                            "heatset", depth=H)
    ctx.rigid("base", Location((0, 0, 0)))
    ctx.rigid("battery", Location((0, 0, H + T)))
    ctx.rigid("xt60", Location((XT60_X, 0, H - xh + 0.0)))
    return ctx.finish(s, color="#2a2d31")
