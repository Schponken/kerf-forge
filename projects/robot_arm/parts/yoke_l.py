"""Left yoke (-Y): the cheek the upper arm's pivot screw turns in (M3 shoulder screw through a free hole into a heat-set
insert in the upper arm, coaxial with the shoulder servo), with a foot bolted to the turntable platform (3 x M3) and
two gussets. Built in the turntable (world) frame. Printed lying on the cheek's outer face (-Y)."""
from build123d import *
from kerf import iface
from kerf.features import safe_fillet

FOOT_X = (-29.0, -14.0, 10.0)
FOOT_T = 6.0


def yoke(p, side):
    """Cheek + foot + gussets for side +1 (+Y) or -1 (-Y), world frame. Returns (body, foot bolt points)."""
    xc = p.x_sh - p.sh_out_x
    x0, x1 = xc - p.ds_span / 2 - 6.0, xc + p.ds_span / 2 + 6.0
    z0, z1 = p.z_plat1, p.z_sh + p.ds_W / 2 + 8.0
    y_in, y_out = side * p.cheek_in, side * p.cheek_out
    cheek = Pos((x0 + x1) / 2, (y_in + y_out) / 2, z0) * Box(x1 - x0, p.plate_t, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cheek = fillet(cheek.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 8.0)
    fx0, fx1, foot_w = -35.0, 14.0, 20.0
    fy0 = y_in - side * foot_w
    foot = Pos((fx0 + fx1) / 2, (y_in + fy0) / 2, z0) * Box(fx1 - fx0, foot_w, FOOT_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = cheek + foot
    # 2 mm fillet in the cheek-to-foot inside corner (docs/ENGINEERING.md section 5: no sharp corner on a load path)
    corner = body.edges().filter_by(Axis.X).filter_by(lambda e: abs(e.center().Y - y_in) < 0.05 and abs(e.center().Z - (z0 + FOOT_T)) < 0.05
                                                    and e.center().X > x0)   # only where the cheek stands on the foot
    body, failed = safe_fillet(body, [(corner, 2.0)])
    if failed or len(corner) != 1:
        raise ValueError(f"yoke cheek-to-foot fillet failed: {failed or 'edge not found'}")
    zt = z0 + FOOT_T - 0.01
    for gx in (-21.0, -8.5):                   # gussets carry the cheek tipping moment; between the foot screws, behind the servo case top
        tri = Polygon((y_in + side * 0.01, zt), (y_in - side * (foot_w - 3.0), zt), (y_in + side * 0.01, zt + 24.0), align=None)
        body += Plane.YZ.offset(gx) * extrude(tri, 2.5, both=True)
    pts = [(x, side * (p.cheek_in - 10.0)) for x in FOOT_X]
    return body, pts


def build(ctx):
    p = ctx.p
    body, pts = yoke(p, -1)
    body -= iface.bolt_pattern(ctx, "yoke_l_foot", "M3", pts, Location((0, 0, p.z_plat1 + FOOT_T)), kind="clearance",
                               depth=FOOT_T, teardrop=90)
    # pivot: free hole, entered from the outer face; +Z of the loc points out of the cheek (-Y)
    body -= iface.pin_hole(ctx, "M3", Location((p.x_sh, -p.cheek_out, p.z_sh), (90, 0, 0)), "sh_pivot", depth=p.plate_t, fit="free")
    # lightening window where the servo window is on the other cheek
    xc = p.x_sh - p.sh_out_x
    body -= Pos(xc - 12.0, -p.cheek_out + p.plate_t / 2, p.z_sh) * Box(18.0, p.plate_t + 2, 18.0)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
