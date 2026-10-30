"""Servo bracket: an upright wall the MG996R's tabs bolt to (M3 heat-set inserts), a foot screwed to the base,
two gussets. Origin: bottom of the wall's back face, centred; wall from y=0 (back) to y=wall_t (front, servo side).
Printed lying on its back face so the servo window needs no bridge and the inserts face up for installation."""
from build123d import *
from kerf import iface


def build(ctx):
    p = ctx.p
    wall = Box(p.wall_w, p.wall_t, p.wall_h, align=(Align.CENTER, Align.MIN, Align.MIN))
    foot = Pos(0, p.wall_t - 0.01, 0) * Box(p.wall_w, p.foot_d, p.foot_t, align=(Align.CENTER, Align.MIN, Align.MIN))
    body = wall + foot
    # fillet the inside corner between wall and foot: it carries the whole servo moment
    inner = body.edges().filter_by(Axis.X).filter_by(lambda e: abs(e.center().Y - p.wall_t) < 0.05 and abs(e.center().Z - p.foot_t) < 0.05)
    body = fillet(inner, 4.0)
    gh = min(p.pivot_h - p.servo_W / 2 - 6.0, p.foot_d * 1.3)
    tri = Polygon((p.wall_t - 0.5, p.foot_t - 0.5), (p.wall_t + p.foot_d - 3.0, p.foot_t - 0.5), (p.wall_t - 0.5, gh), align=None)
    for sx in (-1, 1):
        g = Plane.YZ * extrude(tri, p.gusset_t / 2, both=True)
        body += Pos(sx * p.gusset_x, 0, 0) * g
    # 1.5 mm fillets where the gussets meet the wall and the foot (inside corners on the load path)
    roots = body.edges().filter_by(lambda e: abs(abs(abs(e.center().X) - p.gusset_x) - p.gusset_t / 2) < 0.05
                                   and ((abs(e.center().Y - p.wall_t) < 0.05 and e.center().Z > p.foot_t)
                                        or (abs(e.center().Z - p.foot_t) < 0.05 and e.center().Y > p.wall_t)))
    try:
        body = fillet(roots, 1.5)
    except Exception:  # noqa: BLE001 - keep the part buildable; reviewer sees the corners in the renders
        ctx.notes.append("gusset root fillets could not be applied")
    body = chamfer(body.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 1.0)
    seat = Location((0, p.wall_t, p.pivot_h), (-90, 0, 0))   # servo +Z (output side) points out of the wall front
    # Servo tabs: thread-forming M3 into pilot holes (how servos are normally mounted). Heat-set inserts would leave
    # only 2.1 mm of wall between the insert and the servo window (rule: 2.4 mm) and could bulge into it when melted.
    body -= iface.servo_mount(ctx, "servos.MG996R", seat, group="bracket_servo", plate_t=p.wall_t, kind="tap")
    # Foot holes print horizontally (part +Y is up on the printer), so they are teardrops pointing +Y.
    pts = [(sx * p.foot_hx, y) for sx in (-1, 1) for y in (p.foot_y1, p.foot_y2)]
    body -= iface.bolt_pattern(ctx, "base_bracket", "M3", pts, Location((0, 0, p.foot_t)), kind="clearance",
                               depth=p.foot_t, teardrop=90)
    # Cable-tie anchor under the servo window: two through-slots for a 2.5 mm tie, to strain-relieve the servo lead.
    for sx in (-1, 1):
        body -= Pos(sx * 5.0, p.wall_t / 2, p.pivot_h - p.servo_W / 2 - 7.0) * Box(3.2, p.wall_t + 2, 1.8)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("servo_seat", seat)
    return ctx.finish(body)
