"""Arm: bolts flat onto the aluminium servo horn with its 4 M3 holes; points straight up at swing = 0.
Origin: on the servo axis at the face that touches the horn; thickness along +Z; the arm runs along -Y."""
from build123d import *
from kerf import iface

HORN = "servo_horns.aluminum_25T"


def build(ctx):
    p = ctx.p
    h = iface.horn_dims(HORN)
    hub_r = max(h["od"] / 2 + 2.0, p.arm_w / 2 + 3.0)
    with BuildSketch() as sk:
        Circle(hub_r)
        with Locations((0, -p.arm_len / 2)):
            Rectangle(p.arm_w, p.arm_len)
        with Locations((0, -p.arm_len)):
            Circle(p.arm_w / 2)
    arm = extrude(sk.sketch, p.arm_t)
    concave = arm.edges().filter_by(Axis.Z).filter_by(lambda e: -hub_r * 1.2 < e.center().Y < -hub_r * 0.3)
    if concave:
        arm = fillet(concave, 4.0)
    arm = chamfer(arm.edges().group_by(Axis.Z)[-1], 0.6)
    arm -= iface.horn_mount(ctx, HORN, Location((0, 0, p.arm_t)), group="horn_arm", plate_t=p.arm_t)
    # test-mass hole at the tip: an M3 screw carries the 50 g weight (see DESIGN.md)
    m3 = iface.screw_spec("M3")
    arm -= Pos(0, -p.arm_len, -1) * Cylinder(m3["clearance"] / 2, p.arm_t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    ctx.rigid("tip", Location((0, -p.arm_len, p.arm_t / 2)))
    return ctx.finish(arm)
