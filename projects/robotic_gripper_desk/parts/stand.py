"""STUB bench stand: reproduces the robot_arm forearm's wrist end (wrist MG996R top-through on plate A, free M3 pivot
hole in plate B, w_f apart) on a base. Stand frame: bench at z = 0, Z up; forearm frame F (see layout.py)."""
from build123d import *
from kerf import iface

SERVO = "servos.MG996R"


def build(ctx):
    p = ctx.p
    t, r = p.plate_t, p.link_h / 2
    F = Location((0, 0, p.stand_h), (90, 0, 0))
    pa = Pos(-30, 0, t / 2) * Box(104, 2 * r, t)                 # F frame: x -82..22
    pb = Pos(-32.5, 0, p.w_f - t / 2) * Box(99, 2 * r, t)        # x -82..17
    body = F * (pa + pb)
    body += Pos(-72, -p.w_f / 2, p.stand_h / 2) * Box(20, p.w_f, p.stand_h)
    body += Pos(-80, -p.w_f / 2, 2.5) * Box(60, p.w_f + 30, 5)
    loc = F * Location((-p.mg_out_x, 0, 0))
    body -= iface.servo_mount(ctx, SERVO, loc, group="wr_servo", plate_t=t, kind="tap", top_through=True)
    body -= iface.pin_hole(ctx, "M3", F * Location((0, 0, p.w_f)), "wr_pivot", depth=t, fit="free")
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.mg_tab_t)))
    return ctx.finish(body)
