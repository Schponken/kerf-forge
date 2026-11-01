"""Wrist stand (STUB): a copy of the desk robot arm forearm's wrist end on a foot, so the claw can be bench-tested and
its fit to the arm is checked. Stand frame (parts/layout.py): wrist axis = Z through the origin, X toward the claw,
plate A outer face at z = 0 (wrist servo hung below it, top-first), plate B outer face at z = w_f."""
from build123d import *
from kerf import iface

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"


def build(ctx):
    p = ctx.p
    t, r, wf = p.plate_t, p.r_w, p.w_f
    back = p.fa_web_x - p.fa_web_t / 2 - 8.0
    with BuildSketch() as sa:                       # forearm plate A: wrist disc + band back + front tab extension
        Circle(r)
        with Locations(((back + p.fa_a_front) / 2, 0)):
            Rectangle(p.fa_a_front - back, 2 * r)
    a = extrude(sa.sketch, t)
    a = fillet(a.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().X > r), r * 0.5)
    with BuildSketch() as sb:                       # forearm plate B: wrist disc + band back
        Circle(r)
        with Locations((back / 2, 0)):
            Rectangle(-back, 2 * r)
    body = a + Pos(0, 0, wf - t) * extrude(sb.sketch, t)
    body += Pos(p.fa_web_x, 0, t - 0.01) * Box(p.fa_web_t, 2 * r, wf - 2 * t + 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # stub column + foot (behind the plates; the area under the wrist servo stays open)
    body += Pos(back, 0, -45.0) * Box(8.0, 2 * r, wf + 45.0, align=(Align.MIN, Align.CENTER, Align.MIN))
    body += Pos(back, 0, -45.0) * Box(40.0, 80.0, 5.0, align=(Align.MIN, Align.CENTER, Align.MIN))
    loc = Location((p.fa_servo_x, 0, 0))
    body -= iface.servo_mount(ctx, SERVO, loc, group="wr_servo", plate_t=t, kind="tap", top_through=True)
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, wf)), "wr_pivot", depth=t, fit="free")
    for (hx, hy) in iface.circle(4, iface.horn_dims(HORN)["bc"], 45.0):     # hex key to the claw's wrist-horn screws
        body -= Pos(hx, hy, wf - t - 1) * Cylinder(2.0, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.mg_tab_t)))
    return ctx.finish(body)
