"""Right yoke (+Y): the cheek the shoulder servo (DS3225) bolts to from outside, top-first through a window, with a
foot bolted to the turntable platform (3 x M3) and two gussets. Built in the turntable (world) frame.
Printed lying on the cheek's outer face: window and tab holes vertical; the foot holes print horizontally (teardrops)."""
from build123d import *
from kerf import iface, features

SERVO = "servos.DS3225"
import importlib.util as _iu
import pathlib as _pl
_s = _iu.spec_from_file_location("robot_armlib", _pl.Path(__file__).with_name("armlib.py"))
armlib = _iu.module_from_spec(_s)
_s.loader.exec_module(armlib)
yoke, FOOT_T = armlib.yoke, armlib.FOOT_T


def build(ctx):
    p = ctx.p
    body, pts = yoke(p, +1)
    body -= iface.bolt_pattern(ctx, "yoke_r_foot", "M3", pts, Location((0, 0, p.z_plat1 + FOOT_T)), kind="clearance",
                               depth=FOOT_T, teardrop=-90)
    loc = Location((p.x_sh - p.sh_out_x, p.cheek_out, p.z_sh), (90, 0, 0))   # cheek outer face; +Z into the fork
    body -= iface.servo_mount(ctx, SERVO, loc, group="sh_servo", plate_t=p.plate_t, kind="tap", top_through=True)
    # cable-tie slots at the back of the cheek: the arm's leads leave the yoke here as a loop down to the base
    x0 = p.x_sh - p.sh_out_x - p.ds_span / 2 - 6.0
    for sz in (p.z_sh - 6.0, p.z_sh + 6.0):
        body -= Pos(x0 + 4.0, p.cheek_in + p.plate_t / 2, sz) * Box(1.8, p.plate_t + 2, 3.2)
    # shoulder-servo lead waypoint: above the cheek top, outside it (the servo hangs outside the cheek)
    ctx.rigid("lead_top", Location((x0 + 10.0, p.cheek_out + 4.0, p.z_sh + p.ds_W / 2 + 12.0)))
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.sh_tab_t)))
    # why: every remaining sharp inside corner rounded (r 1, 0.5 where 1 does not fit; ENGINEERING.md s5); interface
    # features exempt, corners under a ceiling as printed stay square (a fillet there would overhang)
    body, left = features.fillet_inside(ctx, body, 1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(body)
