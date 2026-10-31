"""ring_top: caps the three tubes (blind bores, radial M3 locks) and carries the 6S battery on a 20 mm strap that
runs across the pack's width through two slots beside it, and the XT60 (cable-tied under the plate, pointing out
radially between two tubes so the battery lead plugs in from outside, with a stop block behind it).
Frame: origin at the tube tops on the axis, plate above (0..6), bosses below. Printed upside down."""
import math

from build123d import *
from kerf import iface

XT60 = "drone.connectors.XT60"
XT60_ANG, XT60_R = 30.0, 27.0       # between the tubes at 330 and 90 deg; outer end at r 37.65 (plate r 39)
STRAP_DX = 5.0                      # strap centre from the battery centre (clears the 210 deg tube boss under the plate)


def build(ctx):
    p = ctx.p
    t = 6.0
    body = Cylinder(p.rod_r + 9, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += Pos(p.batt_dx, p.batt_dy, 0) * Box(70, 52, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body += Pos(c[0], c[1], -14) * Cylinder(6.0, 14.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body -= Pos(c[0], c[1], -20) * Cylinder(2.75, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body -= Pos(c[0], c[1], -7) * Rot(0, 0, a) * Rot(0, 90, 0) * Cylinder(
            iface.screw_spec("M3")["tap"] / 2, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bw = ctx.cat.num(ctx.cat.get("drone.batteries.6S_1100"), "width")
    for sy in (-1, 1):  # 20 mm strap slots either side of the pack: the strap goes over it, across its width
        body -= Pos(p.batt_dx + STRAP_DX, p.batt_dy + sy * (bw / 2 + 2.5), -1) * Box(23, 3.5, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # XT60 under the plate: a stop block behind its inner end and one cable-tie loop round its outer half
    xl = ctx.cat.num(ctx.cat.get(XT60), "length")
    xw = ctx.cat.num(ctx.cat.get(XT60), "width")
    rot = Rot(0, 0, XT60_ANG)
    body += rot * Pos(XT60_R - xl / 2 - 2.0, 0, -8) * Box(4, xw + 4, 8.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sy in (-1, 1):
        body -= rot * Pos(XT60_R + 6, sy * (xw / 2 + 1.3), -1) * Box(3.0, 1.6, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("battery_seat", Location((p.batt_dx, p.batt_dy, t)))
    a = math.radians(XT60_ANG)
    ctx.rigid("xt60_seat", Location((XT60_R * math.cos(a), XT60_R * math.sin(a), 0)) * Rot(0, 0, XT60_ANG) * Rot(180, 0, 0))
    return ctx.finish(body)
