"""ring_top: caps the three tubes (blind bores, radial M3 locks) and carries the 6S battery on a 20 mm strap that
runs across the pack's width through two slots beside it. The XT60 hangs on a short 14 AWG pigtail just outside the
plate edge between two tubes, so it is gripped by hand to (un)plug and no pull reaches the solder joints; the pigtail
is cable-tied to the plate through two slots.
Frame: origin at the tube tops on the axis, plate above (0..6), bosses below. Printed upside down."""
import math

from build123d import *
from kerf import features, iface

XT60 = "drone.connectors.XT60"
XT60_ANG, XT60_R = 30.0, 45.0       # between the tubes at 330 and 90 deg; body r 34.4..55.6, past the plate (r 39)
TIE_R = 33.0                        # pigtail tie slots
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
        lock = Pos(c[0], c[1], -7) * Rot(0, 0, a) * Rot(0, 90, 0) * Pos(0, 0, 14)   # radial M3 lock, +Z outward
        up = iface.print_up_deg(ctx, lock)          # radial holes are always horizontal in these flat prints
        body -= lock * features.teardrop_hole(iface.screw_spec("M3")["tap"], 14, 0.0 if up is None else up)
    bw = ctx.cat.num(ctx.cat.get("drone.batteries.6S_1100"), "width")
    for sy in (-1, 1):  # 20 mm strap slots either side of the pack: the strap goes over it, across its width
        body -= Pos(p.batt_dx + STRAP_DX, p.batt_dy + sy * (bw / 2 + 2.5), -1) * Box(23, 3.5, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # XT60 pigtail: one cable tie round the 14 AWG pair, through two slots 6 mm apart
    rot = Rot(0, 0, XT60_ANG)
    for sy in (-1, 1):
        body -= rot * Pos(TIE_R, sy * 3.0, -1) * Box(3.0, 1.6, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("battery_seat", Location((p.batt_dx, p.batt_dy, t)))
    a = math.radians(XT60_ANG)
    ctx.rigid("xt60_seat", Location((XT60_R * math.cos(a), XT60_R * math.sin(a), 0)) * Rot(0, 0, XT60_ANG) * Rot(180, 0, 0))
    return ctx.finish(body)
