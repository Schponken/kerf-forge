"""Right yoke (+Y): the cheek the shoulder servo (DS3225) bolts to from outside, top-first through a window, with a
foot bolted to the turntable platform (3 x M3) and two gussets. Built in the turntable (world) frame.
Printed lying on the cheek's outer face: window and tab holes vertical; the foot holes print horizontally (teardrops)."""
from build123d import *
from kerf import iface

SERVO = "servos.DS3225"
FOOT_X = (-29.0, -14.0, 10.0)
FOOT_T = 6.0


def yoke(p, side):
    """Cheek + foot + gussets for side +1 (+Y) or -1 (-Y), world frame. Returns (body, foot bolt points)."""
    xc = p.x_sh - p.sh_out_x
    x0, x1 = xc - p.ds_span / 2 - 6.0, xc + p.ds_span / 2 + 6.0
    z0, z1 = p.z_plat1, p.z_sh + p.ds_W / 2 + 8.0
    y_in, y_out = side * p.cheek_in, side * p.cheek_out
    cheek = Pos((x0 + x1) / 2, (y_in + y_out) / 2, z0) * Box(x1 - x0, p.plate_t, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cheek = fillet(cheek.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 8.0)
    fx0, fx1, foot_w = -35.0, 14.0, 20.0
    fy0 = y_in - side * foot_w
    foot = Pos((fx0 + fx1) / 2, (y_in + fy0) / 2, z0) * Box(fx1 - fx0, foot_w + 0.01, FOOT_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = cheek + foot
    zt = z0 + FOOT_T - 0.01
    for gx in (-21.0, -8.5):                   # gussets carry the cheek tipping moment; between the foot screws, behind the servo case top
        tri = Polygon((y_in + side * 0.01, zt), (y_in - side * (foot_w - 3.0), zt), (y_in + side * 0.01, zt + 24.0), align=None)
        body += Plane.YZ.offset(gx) * extrude(tri, 2.5, both=True)
    pts = [(x, side * (p.cheek_in - 10.0)) for x in FOOT_X]
    return body, pts


def build(ctx):
    p = ctx.p
    body, pts = yoke(p, +1)
    body -= iface.bolt_pattern(ctx, "yoke_r_foot", "M3", pts, Location((0, 0, p.z_plat1 + FOOT_T)), kind="clearance",
                               depth=FOOT_T, teardrop=-90)
    loc = Location((p.x_sh - p.sh_out_x, p.cheek_out, p.z_sh), (90, 0, 0))   # cheek outer face; +Z into the fork
    body -= iface.servo_mount(ctx, SERVO, loc, group="sh_servo", plate_t=p.plate_t, kind="tap", top_through=True)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.sh_tab_t)))
    return ctx.finish(body)
