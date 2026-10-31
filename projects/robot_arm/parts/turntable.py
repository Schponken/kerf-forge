"""Turntable: 12 mm spindle through the two 6001 bearings, a shoulder that rests on the upper inner race, the 24 T
yaw gear, and the platform the two yokes bolt onto (M3 into heat-set inserts). Its frame is the world frame at
base_yaw = 0. Printed upside down (platform top on the bed): the gear and spindle grow up from the platform."""
from build123d import *
from kerf import drives, iface

FOOT_X = (-29.0, -14.0, 10.0)


def foot_y(p):
    return p.cheek_in - 10.0                           # yoke foot bolt line (feet reach 20 mm in from the cheeks)


def build(ctx):
    p = ctx.p
    g1, _, info = drives.spur_pair(p.gear_m, int(p.gear_z_tt), int(p.gear_z_yaw), p.gear_w)
    ctx.notes += info.warnings
    r_sp = (p.brg_d - 0.05) / 2                        # printed spindle 0.05 under the bore: slip fit, axially clamped
    body = Pos(0, 0, p.z_blo + 0.2) * Cylinder(r_sp, p.z_tt - p.z_blo - 0.2 + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += Pos(0, 0, p.z_tt) * Cylinder(7.5, p.z_gear0 - p.z_tt + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # 0.3 mm fillet at the spindle-to-collar step (within the 6001's 0.3 mm inner-race edge chamfer)
    step = body.edges().filter_by(GeomType.CIRCLE).filter_by(lambda e: abs(e.center().Z - p.z_tt) < 0.01 and abs(e.radius - r_sp) < 0.01)
    body = fillet(step, 0.3)
    body += Pos(0, 0, p.z_gear0) * (Rot(0, 0, 180) * g1)
    body += Pos(0, 0, p.z_gear1 - 0.01) * Cylinder(14.0, p.z_plat0 - p.z_gear1 + 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
    x0, x1 = -35.0, 15.0                               # rear edge clears the yaw-gear horn screws for a hex key
    plat = Pos((x0 + x1) / 2, 0, p.z_plat0) * Box(x1 - x0, 2 * p.cheek_out, p.plat_t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    plat = fillet(plat.edges().filter_by(Axis.Z), 6.0)
    body += plat
    # hex-key access (at base_yaw = 0) to the two yaw-servo tab screws under the platform
    xs = -p.yaw_c - p.yaw_out_x + p.mg_hx / 2
    for sy in (-1, 1):
        body -= Pos(xs, sy * p.mg_hy / 2, p.z_plat0 - 1) * Cylinder(2.5, p.plat_t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # yoke feet: 3 x M3 heat-set inserts per side, from the platform top
    for side, grp in ((1, "yoke_r_foot"), (-1, "yoke_l_foot")):
        pts = [(x, side * foot_y(p)) for x in FOOT_X]
        body -= iface.bolt_pattern(ctx, grp, "M3", pts, Location((0, 0, p.z_plat1)), kind="heatset", depth=p.plat_t)
    # spindle end: heat-set insert for the retainer screw (screw comes up from below)
    body -= iface.bolt_pattern(ctx, "retainer", "M3", [(0, 0)], Location((0, 0, p.z_blo + 0.2), (180, 0, 0)), kind="heatset",
                               depth=p.z_tt - p.z_blo)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("retainer_seat", Location((0, 0, p.z_blo)))
    ctx.rigid("yoke_r_seat", Location((0, 0, 0)))
    ctx.rigid("yoke_l_seat", Location((0, 0, 0)))
    return ctx.finish(body)
