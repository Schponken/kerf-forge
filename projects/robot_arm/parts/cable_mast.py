"""Cable mast: a post on the turntable platform, just behind the yaw axis, that the servo-lead bundle is tied across.
From its top the bundle spans to the base's cable post above everything the arm sweeps, so the free loop crossing the
yaw joint stays short (its span changes only 68-95 mm over +-90 deg of yaw) and hangs well clear of the gears.
Built in the turntable (world) frame; bolted down with 2 x M3 into heat-set inserts in the platform.
Printed lying on its side (print_rot [90, 0, 0]), foot and column flush (10 mm) so it needs no support; layers
run along the column."""
from build123d import *
from kerf import iface

TOP = 132.0                 # mm above the desk, level with the base cable post
X_COL = -10.0               # column centre (between the axis and the yaw-servo hex-key holes at x = -30.7)
SCREWS = [(-19.0, 0.0), (-1.0, 0.0)]
FOOT_T = 5.0


def build(ctx):
    p = ctx.p
    z0 = p.z_plat1
    foot = Pos(-10.0, 0, z0) * Box(28.0, 10.0, FOOT_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    col = Pos(X_COL, 0, z0 + FOOT_T - 0.01) * Box(8.0, 10.0, TOP - z0 - FOOT_T + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    col = chamfer(col.edges().group_by(Axis.Z)[-1], 1.0)
    body = foot + col
    body -= iface.bolt_pattern(ctx, "cable_mast", "M3", SCREWS, Location((0, 0, z0 + FOOT_T)), kind="clearance", depth=FOOT_T)
    for sy in (-2.5, 2.5):                                   # tie slots under the top, front to back
        body -= Pos(X_COL, sy, TOP - 6.0) * Box(10.0, 1.8, 3.2)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("cable_top", Location((X_COL, 0, TOP + 3.5)))   # bundle centre, tied across the top
    return ctx.finish(body)
