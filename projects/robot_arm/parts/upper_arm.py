"""Upper arm: a fork of two side plates joined by two webs. Plate A bolts to the shoulder horn (4 x M3) and carries
the elbow servo (DS3218, hung outside, top-first through a window); plate B turns on the shoulder pivot screw
(heat-set insert in a boss) and is the free side of the elbow pivot.
Frame: shoulder horn face on the shoulder axis; X along the arm, Y up (home), Z across the fork (world -Y).
Printed standing on the plates' lower edges (print_rot [90,0,0]): webs vertical, window top bridges 41 mm."""
from build123d import *
from kerf import idioms, iface

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.DS3218"


def build(ctx):
    p = ctx.p
    t, W, L, r = p.plate_t, p.w_u, p.L1, p.link_h / 2
    xc = L - p.el_out_x
    webs = (22.0, xc - p.ds_L / 2 - 9.0)
    # fork of two side plates joined by two webs, 1.5 mm web-root fillets (kerf.idioms.clevis; ENGINEERING.md s5):
    # the webs carry plate B's share of the load. Plate A runs on past the pivot to seat the servo.
    body = idioms.clevis(L, r, W, t, webs, web_t=4.0, web_r=1.5, x_end_a=xc + p.ds_span / 2 + 5.0)
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))   # pivot boss
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="sh_horn", plate_t=t,
                               teardrop=iface.print_up_deg(ctx, Location((0, 0, t))))
    # cable-tie slot pair: servo leads run along the outside of plate A
    for sy in (-6.0, 6.0):
        body -= Pos(35.0, sy, t / 2) * Box(1.8, 3.2, t + 2)
    loc = Location((xc, 0, 0))                     # plate A outer face: tab tops press here, case top points into the fork
    body -= iface.servo_mount(ctx, SERVO, loc, group="el_servo", plate_t=t, kind="tap", top_through=True,
                              teardrop=iface.print_up_deg(ctx, loc))   # tab pilots print horizontal
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, W)), "sh_pivot", depth=t + 3.0, fit="heatset",
                           teardrop=iface.print_up_deg(ctx, Location((0, 0, W))))
    body -= iface.pin_hole(ctx, "M3", Location((L, 0, W)), "el_pivot", depth=t, fit="free", teardrop=90)   # prints horizontal: roof up (+Y)
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    # servo-lead waypoints (wiring routes): along the outside of plate A, above the plate's top edge
    ctx.rigid("lead_1", Location((0, 24, -3)))          # 24 mm from the shoulder axis: clear of the plate end at any angle
    ctx.rigid("lead_2", Location((L, 30, -3)))          # 30 mm above the elbow axis: the hop to the forearm clears both plate ends at +-60 deg
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.el_tab_t)))
    # a point on the shoulder axis level with the gripper's tcp (across the fork), so `reach` is measured square to it
    ctx.rigid("shoulder_ref", Location((0, 0, p.face_el + p.face_wr + p.w_g / 2 + 4.25)))
    return ctx.finish(body)
