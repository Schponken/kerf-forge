"""One bolt-on arm (arm_1..arm_4 share this file; the item id picks the fastener groups).

Frame: X along the arm from the frame centre, arm TOP face at z = 0 (it sits under the body plate), bottom at
z = -arm_t. The root is clamped under the body by two M3 x 12 from below into nut traps in the body; two 1.5 mm
ridges on the top edges sit in grooves in the body underside, so side hits load the ridges, not the two screws.
The motor sits on the top face at r = motor_r on four M3 x 10 (counterbored for a 7.5 mm grip: 2.5 mm into the
motor's ~3 mm deep threads, a screw-length tolerance short of the bottom). Prints flat, top up: bending runs along
the layers, the ridges print on top.
"""
from build123d import *
from kerf import iface, features as F

MOTOR = "drone.motors.2207_1855kv_6s"
RIDGE_W, RIDGE_H, RIDGE_R1 = 3.0, 1.5, 58.0     # key ridges: width, height, outer end radius


def build(ctx):
    p = ctx.p
    n = ctx.id.split("_")[1]
    t, w = p.arm_t, p.arm_w
    pad_d = 32.0                                    # motor bell 29.1 mm + margin: a solid pad under the whole motor base
    L = p.motor_r - p.arm_r0
    body = Pos(p.arm_r0, 0, -t) * Box(L, w, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    body += Pos(p.motor_r, 0, -t) * Cylinder(pad_d / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += Pos(p.arm_r0, 0, -t) * Cylinder(w / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN))  # rounded root
    body, failed = F.safe_fillet(body, [(body.edges().filter_by(Axis.Z).filter_by_position(Axis.X, p.motor_r - pad_d / 2, p.motor_r), 4.0)])
    for f in failed:
        ctx.notes.append(f"fillet skipped: {f}")
    for sy in (1, -1):                              # key ridges along both top edges under the body
        body += Pos(p.arm_r0, sy * (w / 2 - RIDGE_W / 2), 0) * Box(RIDGE_R1 - p.arm_r0, RIDGE_W, RIDGE_H,
                                                                  align=(Align.MIN, Align.CENTER, Align.MIN))
    under = Location((0, 0, -t), (180, 0, 0))       # bottom face, +Z toward the screw heads (down)
    body -= iface.bolt_pattern(ctx, f"arm_{n}", "M3", [(p.arm_hole_1, 0), (p.arm_hole_2, 0)], under, "counterbore",
                               depth=t, counterbore_depth=t - 6.0)  # grip 6 -> M3 x 12 into the body nut
    body -= iface.motor_mount(ctx, MOTOR, Location((p.motor_r, 0, -t), (180, 0, 0)), f"motor_{n}", plate_t=t,
                              kind="counterbore", counterbore_depth=t - 7.5)  # grip 7.5 -> M3 x 10, 2.5 mm in the motor
    for x in (p.arm_r0 + 0.4 * L, p.arm_r0 + 0.75 * L):  # two motor-wire tie slots through the arm (2.5 mm ties)
        body -= Pos(x, 0, -t / 2) * Box(3.0, w + 2, 1.6, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    ctx.rigid("root", Location((0, 0, 0)))
    ctx.rigid("motor", Location((p.motor_r, 0, 0)))
    return ctx.finish(body, color="#2a2d31")
