"""Cable mast: a post on the turntable platform, just behind the yaw axis, that the servo-lead bundle is tied across.
From its top the bundle spans to the base's cable post above everything the arm sweeps, so the free loop crossing the
yaw joint stays short (its span changes only 68-95 mm over +-90 deg of yaw) and hangs well clear of the gears.
Built in the turntable (world) frame; bolted down with 4 x M3 into heat-set inserts in the platform, spread in X and Y
(foot 34 x 26) so a sideways pull on the bundle at |yaw| ~ 90 is taken by two screws 12 mm apart, not by one foot edge;
2 mm fillet at the column root.
Printed lying on its side (print_rot [90, 0, 0]), foot and column flush (10 mm) so it needs no support; layers
run along the column."""
from build123d import *
from kerf import iface
from kerf.features import safe_fillet

TOP = 132.0                 # mm above the desk, level with the base cable post
X_COL = -10.0               # column centre (between the axis and the yaw-servo hex-key holes at x = -30.7)
SCREWS = [(-20.0, -6.0), (-20.0, 6.0), (0.0, -6.0), (0.0, 6.0)]   # 7 mm from every foot edge (>= 1.5 d + wall)
FOOT = (-27.0, 7.0, 26.0)   # x0, x1, width (Y)
FOOT_T = 5.0


def build(ctx):
    p = ctx.p
    z0 = p.z_plat1
    fx0, fx1, fw = FOOT
    foot = Pos((fx0 + fx1) / 2, 0, z0) * Box(fx1 - fx0, fw, FOOT_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    foot = fillet(foot.edges().filter_by(Axis.Z), 3.0)
    col = Pos(X_COL, 0, z0 + FOOT_T - 0.01) * Box(8.0, 10.0, TOP - z0 - FOOT_T + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    col = chamfer(col.edges().group_by(Axis.Z)[-1], 1.0)
    body = foot + col
    root = body.edges().filter_by(lambda e: abs(e.center().Z - (z0 + FOOT_T)) < 0.05 and abs(e.center().X - X_COL) < 4.1
                                  and abs(e.center().Y) < 5.1)
    body, failed = safe_fillet(body, [(root, 2.0)])
    if failed or len(root) != 4:
        raise ValueError(f"mast root fillet: {failed or f'{len(root)} edges'}")
    body -= iface.bolt_pattern(ctx, "cable_mast", "M3", SCREWS, Location((0, 0, z0 + FOOT_T)), kind="clearance", depth=FOOT_T)
    for sy in (-2.5, 2.5):                                   # tie slots under the top, front to back
        body -= Pos(X_COL, sy, TOP - 6.0) * Box(10.0, 1.8, 3.2)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("cable_top", Location((X_COL, 0, TOP + 3.5)))   # bundle centre, tied across the top
    return ctx.finish(body)
