"""ring_top: caps the three tubes (blind bores, radial M3 locks) and carries the 6S battery on a strap through two
slots. Frame: origin at the tube tops on the axis, plate above (0..6), bosses below. Printed upside down."""
import math

from build123d import *
from kerf import iface


def build(ctx):
    p = ctx.p
    t = 6.0
    body = Cylinder(p.rod_r + 9, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += Pos(p.batt_dx, p.batt_dy, 0) * Box(70, 46, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body += Pos(c[0], c[1], -14) * Cylinder(6.0, 14.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body -= Pos(c[0], c[1], -20) * Cylinder(2.75, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body -= Pos(c[0], c[1], -7) * Rot(0, 0, a) * Rot(0, 90, 0) * Cylinder(
            iface.screw_spec("M3")["tap"] / 2, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sx in (-1, 1):  # 20 mm battery strap slots across the battery
        body -= Pos(p.batt_dx + sx * 22, p.batt_dy, -1) * Box(3.5, 23, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("battery_seat", Location((p.batt_dx, p.batt_dy, t)))
    return ctx.finish(body)
