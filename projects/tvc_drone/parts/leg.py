"""leg: one of three splayed landing legs. A pad bolts under a ring_low lug with two M3 screws (heads below, inboard of
the strut, so a straight key reaches them); a tapered strut runs out and down, outside the props at every gimbal
angle, to a round foot on the ground. Frame: origin at the attachment point on ring_low's underside, +X radially
outward, +Z up. Printed on its side (the X-Z profile on the bed; pad, strut and foot share one 14 mm width so the whole
side face lies on the bed) so bending runs along the layers."""
from build123d import *
from kerf import features, iface

LEG_SCREWS = [(-22.0, 0.0), (-13.0, 0.0)]   # same sites as ring_low.LEG_SCREWS (both frames +Z down)


def build(ctx):
    p = ctx.p
    dx = p.foot_r - p.leg_r0                     # foot centre, radially out from the attachment
    dz = p.ground_z - p.ring_low_z               # ground, below the attachment (negative)
    w = 14.0                                     # one width for pad, strut and foot: the whole side face prints on the bed
    pad = Pos(-9.5, 0, -6) * Box(37, w, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    prof = Polygon((-9, -3), (9, -3), (dx + 6, dz + 5), (dx - 6, dz + 5), align=None)
    strut = Plane.XZ * extrude(prof, w / 2, both=True)
    foot = Pos(dx, 0, dz) * (Cylinder(10, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
                             & Box(20, w, 6, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    body = pad + strut + foot
    # 2 mm fillet in the inside corner where the strut leaves the pad underside (the leg's FEA hot spot)
    root = body.edges().filter_by(Axis.Y).filter_by(lambda e: abs(e.center().Z + 6) < 0.3 and -9 < e.center().X < -6)
    body, failed = features.safe_fillet(body, [(root, 2.0)])
    if failed or not root:
        raise ValueError(f"leg root fillet failed: {failed or 'edge not found'}")
    # screws from below, inboard of the strut (a straight key reaches them), into ring_low's inserts
    body -= iface.bolt_pattern(ctx, "leg", "M3", LEG_SCREWS, Location((0, 0, -6), (180, 0, 0)),
                               kind="clearance", depth=6)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("foot", Location((dx, 0, dz)))
    return ctx.finish(body)
