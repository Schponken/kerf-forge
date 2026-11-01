"""STUB gripper body: wrist fork + bulkhead + rod cheeks. Interfaces and joints are final; geometry is a placeholder."""
from build123d import *
from kerf import iface

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"
ROD = "motion.pin_3mm"


def build(ctx):
    p = ctx.p
    t, W, r = p.plate_t, p.grip_w, p.link_h / 2
    zc = p.z_c
    body = Pos((p.x_bulk - 2) / 2 - 0, -10, t / 2) * Box(p.x_bulk - 2 + 2 * r, 2 * r + 30, t)
    body += Pos((p.x_bulk - 2) / 2 - 0, -10, W - t / 2) * Box(p.x_bulk - 2 + 2 * r, 2 * r + 30, t)
    zl, zr = zc - p.z_stop - p.cheek_t, zc + p.z_stop + p.cheek_t
    body += Pos(p.x_bulk + p.bulk_t / 2, -8, (zl + zr) / 2) * Box(p.bulk_t, 66, zr - zl)
    for z0 in (zl, zc + p.z_stop):
        body += Pos((p.x_bulk + p.x_c1) / 2, 0, z0 + p.cheek_t / 2) * Box(p.x_c1 + 2 - p.x_bulk, 2 * p.rod_y + 12, p.cheek_t)
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="wr_horn", plate_t=t)
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, W)), "wr_pivot", depth=t + 3.0, fit="heatset")
    loc = Location(Plane((p.x_bulk, p.y_s, zc), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    body -= iface.servo_mount(ctx, SERVO, loc, group="gr_servo", plate_t=p.bulk_t, kind="tap", top_through=True)
    for g, y in (("rod_top", p.rod_y), ("rod_bot", -p.rod_y)):
        # cheek R: blind seat entered from its inner face; cheek L: through, entered from its outer face
        body -= iface.pin_hole(ctx, ROD, Location((p.x_rod, y, zc + p.z_stop), (180, 0, 0)), g, depth=p.cheek_t - 1.5,
                               fit="press", through=False)
        body -= iface.pin_hole(ctx, ROD, Location((p.x_rod, y, zl), (180, 0, 0)), g, depth=p.cheek_t, fit="press")
    body -= iface.bolt_pattern(ctx, "keeper", "M3", [(0, 0)], Location((p.x_rod, 0, zl), (180, 0, 0)), "heatset", p.cheek_t)
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.mg_tab_t)))
    ctx.linear("jaw_r_slide", Axis((p.x_c0, 0, zc + p.z_in), (0, 0, 1)), range=(0, p.s_max))
    ctx.linear("jaw_l_slide", Axis((p.x_c0, 0, zc - p.z_in), (0, 0, -1)), range=(0, p.s_max))
    ctx.rigid("keeper_seat", Location((p.x_rod, 0, zl), (180, 0, 0)))
    ctx.rigid("tcp", Location((p.x_tcp, 0, zc)))
    return ctx.finish(body)
