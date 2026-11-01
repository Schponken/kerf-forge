"""Forearm: a fork of two side plates joined by two webs. Plate A bolts to the elbow horn (4 x M3) and carries
the wrist servo (MG996R, hung outside, top-first through a window); plate B turns on the elbow pivot screw
(heat-set insert in a boss) and is the free side of the wrist pivot.
Frame: elbow horn face on the elbow axis; X along the arm, Y up (home), Z across the fork (world -Y).
Printed standing on the plates' lower edges (print_rot [90,0,0]): webs vertical, window top bridges 41 mm."""
from build123d import *
from kerf import idioms, iface, features

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"


def build(ctx):
    p = ctx.p
    t, W, L, r = p.plate_t, p.w_f, p.L2, p.link_h / 2
    xc = L - p.wr_out_x
    webs = (22.0, xc - p.mg_L / 2 - 9.0)
    # fork of two side plates joined by two webs, 1.5 mm web-root fillets (kerf.idioms.clevis; ENGINEERING.md s5):
    # the webs carry plate B's share of the load. Plate A runs on past the pivot to seat the servo.
    body = idioms.clevis(L, r, W, t, webs, web_t=4.0, web_r=1.5, x_end_a=xc + p.mg_span / 2 + 5.0)
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))   # pivot boss
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="el_horn", plate_t=t,
                               teardrop=iface.print_up_deg(ctx, Location((0, 0, t))))
    # cable-tie slot pair: servo leads run along the outside of plate A
    for sy in (-6.0, 6.0):
        body -= Pos(30.0, sy, t / 2) * Box(1.8, 3.2, t + 2)
    loc = Location((xc, 0, 0))                     # plate A outer face: tab tops press here, case top points into the fork
    body -= iface.servo_mount(ctx, SERVO, loc, group="wr_servo", plate_t=t, kind="tap", top_through=True,
                              teardrop=iface.print_up_deg(ctx, loc))   # tab pilots print horizontal
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, W)), "el_pivot", depth=t + 3.0, fit="heatset",
                           teardrop=iface.print_up_deg(ctx, Location((0, 0, W))))
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
    # why: every remaining sharp inside corner rounded (r 1, 0.5 where 1 does not fit; ENGINEERING.md s5); interface
    # features exempt, corners under a ceiling as printed stay square (a fillet there would overhang)
    body, left = features.fillet_inside(ctx, body, 1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(body)
