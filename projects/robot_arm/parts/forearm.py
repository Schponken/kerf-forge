"""Forearm: a fork of two side plates joined by two webs. Plate A bolts to the elbow horn (4 x M3) and carries
the wrist servo (MG996R, hung outside, top-first through a window); plate B turns on the elbow pivot screw
(heat-set insert in a boss) and is the free side of the wrist pivot.
Frame: elbow horn face on the elbow axis; X along the arm, Y up (home), Z across the fork (world -Y).
Printed standing on the plates' lower edges (print_rot [90,0,0]): webs vertical, window top bridges 41 mm."""
from build123d import *
from kerf import iface
from kerf.features import safe_fillet

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"


def plate(L, r, x_end, t):
    """Side-plate outline: rounded at the pivot (x = 0) and at x = L, extended straight to x_end; t thick from z = 0."""
    with BuildSketch() as sk:
        Circle(r)
        with Locations((L, 0)):
            Circle(r)
        with Locations(((max(L, x_end)) / 2, 0)):
            Rectangle(max(L, x_end), 2 * r)
    s = extrude(sk.sketch, t)
    if x_end > L + r:
        s = fillet(s.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().X > L + r), r * 0.5)
    return s


def build(ctx):
    p = ctx.p
    t, W, L, r = p.plate_t, p.w_f, p.L2, p.link_h / 2
    xc = L - p.wr_out_x
    a = plate(L, r, xc + p.mg_span / 2 + 5.0, t)
    b = Pos(0, 0, W - t) * plate(L, r, L, t)
    body = a + b
    webs = (22.0, xc - p.mg_L / 2 - 9.0)
    for wx in webs:
        body += Pos(wx, 0, t - 0.01) * Box(4.0, 2 * r, W - 2 * t + 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # 1.5 mm fillets where the webs meet the plates (docs/ENGINEERING.md section 5): the webs carry plate B's share
    corners = body.edges().filter_by(Axis.Y).filter_by(
        lambda e: any(abs(abs(e.center().X - wx) - 2.0) < 0.05 for wx in webs) and min(abs(e.center().Z - t), abs(e.center().Z - (W - t))) < 0.05)
    body, failed = safe_fillet(body, [(corners, 1.5)])
    if failed or len(corners) != 8:
        raise ValueError(f"web fillets: {len(corners)} edges found, failed {failed}")
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))   # pivot boss
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="el_horn", plate_t=t)
    # cable-tie slot pair: servo leads run along the outside of plate A
    for sy in (-6.0, 6.0):
        body -= Pos(30.0, sy, t / 2) * Box(1.8, 3.2, t + 2)
    loc = Location((xc, 0, 0))                     # plate A outer face: tab tops press here, case top points into the fork
    body -= iface.servo_mount(ctx, SERVO, loc, group="wr_servo", plate_t=t, kind="tap", top_through=True)
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, W)), "el_pivot", depth=t + 3.0, fit="heatset")
    body -= iface.pin_hole(ctx, "M3", Location((L, 0, W)), "wr_pivot", depth=t, fit="free", teardrop=90)   # prints horizontal: roof up (+Y)
    # hex-key access through plate B to the gripper's horn screws (the gripper's own fork is too narrow for a key)
    for (hx, hy) in iface.circle(4, iface.horn_dims(HORN)["bc"], 45.0):
        body -= Pos(L + hx, hy, W - t - 1) * Cylinder(2.0, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    # servo-lead waypoints (wiring routes): along the outside of plate A, above the plate's top edge
    ctx.rigid("lead_1", Location((0, 30, -3)))
    ctx.rigid("lead_2", Location((55, 20, -3)))         # down to the wrist servo from here
    ctx.rigid("lead_3", Location((L, 30, -3)))          # over the wrist axis toward the gripper
    ctx.rigid("lead_4", Location((L, 30, p.face_wr - 3)))   # ...and over plate A's top into the gripper's plane (gripper z = -3)
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.wr_tab_t)))
    return ctx.finish(body)
