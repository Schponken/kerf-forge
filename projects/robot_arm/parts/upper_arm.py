"""Upper arm: a fork of two side plates joined by two webs. Plate A bolts to the shoulder horn (4 x M3) and carries
the elbow servo (DS3218, hung outside, top-first through a window); plate B turns on the shoulder pivot screw
(heat-set insert in a boss) and is the free side of the elbow pivot.
Frame: shoulder horn face on the shoulder axis; X along the arm, Y up (home), Z across the fork (world -Y).
Printed standing on the plates' lower edges (print_rot [90,0,0]): webs vertical, window top bridges 41 mm."""
from build123d import *
from kerf import iface
from kerf.features import safe_fillet

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.DS3218"


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
    t, W, L, r = p.plate_t, p.w_u, p.L1, p.link_h / 2
    xc = L - p.el_out_x
    a = plate(L, r, xc + p.ds_span / 2 + 5.0, t)
    b = Pos(0, 0, W - t) * plate(L, r, L, t)
    body = a + b
    webs = (22.0, xc - p.ds_L / 2 - 9.0)
    for wx in webs:
        body += Pos(wx, 0, t - 0.01) * Box(4.0, 2 * r, W - 2 * t + 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # 1.5 mm fillets where the webs meet the plates (docs/ENGINEERING.md section 5): the webs carry plate B's share
    corners = body.edges().filter_by(Axis.Y).filter_by(
        lambda e: any(abs(abs(e.center().X - wx) - 2.0) < 0.05 for wx in webs) and min(abs(e.center().Z - t), abs(e.center().Z - (W - t))) < 0.05)
    body, failed = safe_fillet(body, [(corners, 1.5)])
    if failed or len(corners) != 8:
        raise ValueError(f"web fillets: {len(corners)} edges found, failed {failed}")
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))   # pivot boss
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="sh_horn", plate_t=t)
    # cable-tie slot pair: servo leads run along the outside of plate A
    for sy in (-6.0, 6.0):
        body -= Pos(35.0, sy, t / 2) * Box(1.8, 3.2, t + 2)
    loc = Location((xc, 0, 0))                     # plate A outer face: tab tops press here, case top points into the fork
    body -= iface.servo_mount(ctx, SERVO, loc, group="el_servo", plate_t=t, kind="tap", top_through=True)
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, W)), "sh_pivot", depth=t + 3.0, fit="heatset")
    body -= iface.pin_hole(ctx, "M3", Location((L, 0, W)), "el_pivot", depth=t, fit="free")
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    # servo-lead waypoints (wiring routes): along the outside of plate A, above the plate's top edge
    ctx.rigid("lead_1", Location((0, 24, -3)))          # 24 mm from the shoulder axis: clear of the plate end at any angle
    ctx.rigid("lead_2", Location((L, 30, -3)))          # 30 mm above the elbow axis: the hop to the forearm clears both plate ends at +-60 deg
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.el_tab_t)))
    # a point on the shoulder axis level with the gripper's tcp (across the fork), so `reach` is measured square to it
    ctx.rigid("shoulder_ref", Location((0, 0, p.face_el + p.face_wr + p.w_g / 2 + 4.25)))
    return ctx.finish(body)
