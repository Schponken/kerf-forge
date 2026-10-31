"""leg: one of three splayed landing legs. A pad bolts under a ring_low lug with two M3 screws (heads below, flanking
the strut, so a straight key reaches them); a tapered strut runs out and down, outside the props at every gimbal
angle, to a round foot on the ground. Frame: origin at the attachment point on ring_low's underside, +X radially
outward, +Z up. Printed on its side (the X-Z profile on the bed) so bending runs along the layers."""
from build123d import *
from kerf import iface


def build(ctx):
    p = ctx.p
    dx = p.foot_r - p.leg_r0                     # foot centre, radially out from the attachment
    dz = p.ground_z - p.ring_low_z               # ground, below the attachment (negative)
    pad = Pos(0, 0, -6) * Box(20, 34, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    prof = Polygon((-9, -3), (9, -3), (dx + 6, dz + 5), (dx - 6, dz + 5), align=None)
    strut = Plane.XZ * extrude(prof, 7, both=True)
    foot = Pos(dx, 0, dz) * Cylinder(10, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = pad + strut + foot
    body -= iface.bolt_pattern(ctx, "leg", "M3", [(0, -11), (0, 11)], Location((0, 0, -6), (180, 0, 0)),
                               kind="clearance", depth=6)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("foot", Location((dx, 0, dz)))
    return ctx.finish(body)
