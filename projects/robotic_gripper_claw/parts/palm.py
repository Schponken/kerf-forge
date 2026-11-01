"""Palm (STUB): wrist fork (as the arm's old gripper), palm plate the grip servo hangs under, idler pedestal, cover posts.
Claw frame (parts/layout.py): origin on the wrist axis at the wrist horn face, X forward, Y up (arm home), Z across."""
from build123d import *
from kerf import iface

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"
POST_X = (15.5, 23.5)          # posts behind the gears (drive gear tips reach x_g - r_tip)


def up(x, y, z):
    return Plane((x, y, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0)).location


def build(ctx):
    p = ctx.p
    t, W, r = p.plate_t, p.W, p.r_w
    disc = extrude(Circle(r), t)
    body = disc + Pos(0, 0, W - t) * disc
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))   # pivot boss
    x0, x1 = 8.0, p.x_sc + p.mg_span / 2 + 3.0
    body += Pos((x0 + x1) / 2, t / 2, (W + 1) / 2 - 3.5) * Box(x1 - x0, t, W + 7)            # palm plate y 0..7
    body += Pos(p.x_g, t, p.z_i) * Rot(-90, 0, 0) * Cylinder(6.0, p.y_g0 - 0.5 - t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    zs = (p.z_d - 2.0, p.z_i + 2.0)
    for z in zs:
        body += Pos(sum(POST_X) / 2, (t + p.y_c0) / 2, z) * Box(POST_X[1] - POST_X[0], p.y_c0 - t + 0.01, 8.0)
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="wr_horn", plate_t=t)
    sloc = Plane((p.x_sc, 0, p.z_d), x_dir=(-1, 0, 0), z_dir=(0, 1, 0)).location   # tab tops on the palm underside, output toward the wrist
    body -= iface.servo_mount(ctx, SERVO, sloc, group="gr_servo", plate_t=t, kind="tap", top_through=True)
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, W)), "wr_pivot", depth=t + 3.0, fit="heatset")
    for (hx, hy) in iface.circle(4, iface.horn_dims(HORN)["bc"], 45.0):     # hex key to the wrist-horn screws
        body -= Pos(hx, hy, W - t - 4) * Cylinder(2.0, t + 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= iface.pin_hole(ctx, "motion.pin_3mm", up(p.x_g, p.y_g0 - 0.5, p.z_i), "gr_idler", depth=8.0, fit="press", through=False)
    body -= iface.bolt_pattern(ctx, "cover", "M3", [(0, 0)], up(sum(POST_X) / 2, p.y_c0, zs[0]), kind="heatset", depth=8.0)
    body -= iface.bolt_pattern(ctx, "cover", "M3", [(0, 0)], up(sum(POST_X) / 2, p.y_c0, zs[1]), kind="heatset", depth=8.0)
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    ctx.rigid("servo_seat", sloc * Location((0, 0, -p.mg_tab_t)))
    ctx.revolute("idler", Axis((p.x_g, p.y_g0, p.z_i), (0, 1, 0)), range=(-p.grip_open, 0))
    ctx.rigid("cover_seat", Location((0, 0, 0)))
    ctx.rigid("tcp", Location((p.x_tcp, p.y_pad, p.z_tcp)))
    ctx.rigid("lead_1", Location((0, 30, -3)))
    ctx.rigid("lead_2", Location((12, -20, -3)))
    return ctx.finish(body)
