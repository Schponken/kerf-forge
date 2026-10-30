"""One bolt-on arm (arm_1..arm_4 share this file; the item id picks the fastener groups).

Frame: X along the arm from the frame centre, arm TOP face at z = 0 (it sits under the body plate), bottom at
z = -arm_t. The root end (r = arm_r0) is clamped under the body by two M3 screws from below into nut traps in the
body; the motor sits on the top face at r = motor_r on four M3 x 10 screws (counterbored so the grip is 7 mm
and the screw ends inside the motor's ~3 mm deep threads). Prints flat (top face up), so bending runs along layers.
"""
from build123d import *
from kerf import iface, features as F

MOTOR = "drone.motors.2207_1855kv_6s"


def build(ctx):
    p = ctx.p
    n = ctx.id.split("_")[1]
    t, w = p.arm_t, p.arm_w
    pad_d = 32.0                                    # motor bell 29.1 mm + margin: a solid pad under the whole motor base
    L = p.motor_r - p.arm_r0
    body = Pos(p.arm_r0, 0, -t) * Box(L, w, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    body += Pos(p.motor_r, 0, -t) * Cylinder(pad_d / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += Pos(p.arm_r0, 0, -t) * Cylinder(w / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN))  # rounded root
    # fillet the arm-to-pad junction (vertical edges) where bending stress is highest at the pad
    body, failed = F.safe_fillet(body, [(body.edges().filter_by(Axis.Z).filter_by_position(Axis.X, p.motor_r - pad_d / 2, p.motor_r), 4.0)])
    for f in failed:
        ctx.notes.append(f"fillet skipped: {f}")
    # root: two M3 from below into nut traps in the body (group arm_<n>)
    under = Location((0, 0, -t), (180, 0, 0))       # bottom face, +Z toward the screw heads (down)
    body -= iface.bolt_pattern(ctx, f"arm_{n}", "M3", [(p.arm_hole_1, 0), (p.arm_hole_2, 0)], under, "counterbore",
                               depth=t, counterbore_depth=t - 6.0)  # grip 6 -> M3 x 12 into the body nut
    # motor: 4 x M3 on the 16 mm bolt circle from below, heads sunk to a 7 mm grip
    body -= iface.motor_mount(ctx, MOTOR, Location((p.motor_r, 0, -t), (180, 0, 0)), f"motor_{n}", plate_t=t,
                              kind="counterbore", counterbore_depth=t - 7.0)  # grip 7 -> M3 x 10, ~3 mm into the motor
    # motor-wire tie slots either side of the arm, mid-length (2.5 mm cable tie)
    for x in (p.arm_r0 + 0.45 * L,):
        body -= Pos(x, 0, -t / 2) * Box(3.0, w + 2, 1.6, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    ctx.rigid("root", Location((0, 0, 0)))
    ctx.rigid("motor", Location((p.motor_r, 0, 0)))
    return ctx.finish(body, color="#2a2d31")
