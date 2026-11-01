"""Wrist stand: a bench copy of the desk robot arm forearm's wrist end (robot_arm/parts/forearm.py), so the claw can be
bench-tested on its own wrist servo before it goes on the arm, and `kerf check` proves it fits the arm: the wrist sweep
swings the claw +-75 deg against this copy (tests/test_claw_fits_arm.py proves the copy holds all of the forearm's
material from its rear web forward).

Stand frame (parts/layout.py): wrist axis = Z through the origin, X toward the claw, Y = the forearm's up; plate A outer
face at z = 0 (wrist MG996R hung below it top-first, tab screws from below), plate B outer face at z = w_f.
Everything at z >= 0 is the forearm verbatim (no edge breaks there: they would remove forearm material). The stand's
own material is all below plate A, where the claw never reaches: two side walls leaning out to the bench.
"""
import math

from build123d import *
from kerf import iface
from kerf.features import safe_fillet

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"
Z_BENCH = -40.0    # bench face (= stand_fea's fixed box): 10.7 mm under the hung servo's case (catalog: tab_z may be 3.4 more)
SPLAY = 40.0       # walls lean out this far from vertical: wide footprint, and a 40 deg overhang printed upside down
FRONT = 47.0       # front struts' slope from horizontal: reach toward the claw, a 43 deg overhang printed upside down
WALL_T = 2.4       # ENGINEERING.md s5 structural wall (>= 1.6); the walls only carry ~30 N of shear each


def build(ctx):
    p = ctx.p
    t, r, wf = p.plate_t, p.r_w, p.w_f
    wx = p.fa_web_x
    back = wx - p.fa_web_t / 2 - 3.0                # why: plates stop 3 mm behind the web: its 1.5 mm rear fillets + a land
    # ---- the forearm's wrist end, verbatim
    with BuildSketch() as sa:                       # why: forearm plate A: band (holds the r disc) to the front tab margin
        with Locations(((back + p.fa_a_front) / 2, 0)):
            Rectangle(p.fa_a_front - back, 2 * r)
    a = extrude(sa.sketch, t)
    a = fillet(a.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().X > r), r * 0.5)   # why: forearm's front corners
    with BuildSketch() as sb:                       # why: forearm plate B: wrist disc + band back to the web
        Circle(r)
        with Locations((back / 2, 0)):
            Rectangle(-back, 2 * r)
    body = a + Pos(0, 0, wf - t) * extrude(sb.sketch, t)    # why: the fork: plate A (servo side) + plate B (pivot side)
    # why: forearm rear web: carries plate B (the claw's pivot) on plate A
    body += Pos(wx, 0, t - 0.01) * Box(p.fa_web_t, 2 * r, wf - 2 * t + 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
    corners = body.edges().filter_by(Axis.Y).filter_by(
        lambda e: abs(abs(e.center().X - wx) - p.fa_web_t / 2) < 0.05 and min(abs(e.center().Z - t), abs(e.center().Z - (wf - t))) < 0.05)
    body, failed = safe_fillet(body, [(corners, 1.5)])     # why: forearm's 1.5 mm web-to-plate fillets (stress relief)
    if failed or len(corners) != 4:
        raise ValueError(f"web fillets: {len(corners)} edges found, failed {failed}")

    rear = [e for e in body.edges() if abs(e.center().X - back) < 0.05 and e.center().Z > t - 0.5]  # plate A's sides run on into the walls
    body, failed = safe_fillet(body, [(rear, 0.6)], kind="chamfer")   # why: edge break on the plates' cut-off rear ends
    if failed:
        raise ValueError(f"rear edge break: {failed}")

    # ---- the stand: two side walls hang from plate A's long edges and lean out to the bench. The servo's stall couple
    # (in plate A's plane) reaches the bench as in-plane shear in the two walls; the lean gives the footprint the claw
    # needs at +-75 deg; the open bottom and front let the servo in from below, the tab-screw key in and the lead out.
    # Root and strut blends are rounded in the 2D profiles (3D fillets there collide with the edge breaks).
    tn = math.tan(math.radians(SPLAY))
    h = WALL_T / math.cos(math.radians(SPLAY))     # horizontal width of a leaning wall
    yo = lambda z: r - z * tn                       # noqa: E731  outer face, flush with plate A's long edge at z = 0
    yi = yo(0) - h                                  # inner face where it meets plate A
    x_top = p.fa_a_front - r / 2                    # plate A's straight long edge ends here (its r/2 front fillet starts)
    x_toe = x_top - Z_BENCH / math.tan(math.radians(FRONT))
    at = lambda f, *pts: [f.vertices().sort_by_distance(Vector(*q))[0] for q in pts]   # noqa: E731
    # cross-section (YZ, +y wall); the strip at z 0..1 sits inside plate A and only gives root and knee a corner to round
    sec = Polygon((yi - 8, 1), (yi - 8, 0), (yi, 0), (yo(Z_BENCH) - h, Z_BENCH), (yo(Z_BENCH), Z_BENCH), (r, 0), (r, 1), align=None)
    sec = fillet(at(sec, (yi, 0), (r, 0)), 2.0)          # why: r 2 root under plate A and knee off its side (the shear path)
    sec = chamfer(at(sec, (yo(Z_BENCH) - h, Z_BENCH), (yo(Z_BENCH), Z_BENCH)), 0.6)   # why: edge break along the bench
    # side view (XZ): along plate A's edge, then the front strut down to the toe on the bench
    sv = Polygon((back, 1), (x_top + 8, 1), (x_top + 8, 0), (x_top, 0), (x_toe, Z_BENCH), (back, Z_BENCH), align=None)
    sv = fillet(at(sv, (x_top, 0)), 2.0)                                   # why: r 2 where the strut leaves plate A
    sv = chamfer(at(sv, (x_toe, Z_BENCH), (back, Z_BENCH)), 0.6)            # why: edge break at toe and heel
    wall = extrude(Plane.XZ * sv, amount=4 * r, both=True) & Pos(back - 1, 0, 0) * extrude(Plane.YZ * sec, amount=200, dir=(1, 0, 0))
    wall -= Pos(x_top, 0, 0) * Box(100, 400, 10, align=(Align.MIN, Align.CENTER, Align.MIN))   # keep plate A's front corners clean
    slopes = [e for e in wall.edges() if e.geom_type == GeomType.LINE and e.length > 3 and e.center().Z < -1
              and max(abs(e.tangent_at(0.5).X), abs(e.tangent_at(0.5).Y)) < 0.999]
    wall, failed = safe_fillet(wall, [(slopes, 0.6)])                      # why: edge break on the strut and heel edges
    if failed or len(slopes) != 4:
        raise ValueError(f"wall edge break: {len(slopes)} edges, failed {failed}")
    body += wall + mirror(wall, Plane.XZ)          # why: two leaning side walls: load path to the bench + the footprint
    # lightening window through both walls: each becomes a frame (chord on plate A, bench chord, heel post, front strut).
    # Point-down triangle, sides 50 deg from horizontal: upside down on the bed its edges overhang only 40 deg.
    zt, zb = -5.0, Z_BENCH + 6.0                   # 5 mm chord under plate A (+ the r 2 roots), 6 mm bench chord
    x0 = back + 6.0                                # 6 mm heel post
    x1 = x_top - zt / math.tan(math.radians(FRONT)) - 6.0 / math.sin(math.radians(FRONT))   # 6 mm front strut
    half = min((x1 - x0) / 2, (zt - zb) / math.tan(math.radians(50)))
    xm, cs = (x0 + x1) / 2, math.cos(math.radians(SPLAY))
    # drawn in the wall's own plane (u = x, v = z / cos(SPLAY) up the slant) so the window cuts square through the wall
    win = Polygon((xm - half, zt / cs), (xm + half, zt / cs), (xm, (zt - half * math.tan(math.radians(50))) / cs), align=None)
    win = fillet(win.vertices(), 3.0)              # why: r 3 window corners (no sharp inside corners on the frame)
    mid = Plane(origin=(0, r - h / 2, 0), x_dir=(1, 0, 0), z_dir=(0, -cs, -math.sin(math.radians(SPLAY))))
    win = extrude(mid * win, amount=5, both=True)
    body -= win + mirror(win, Plane.XZ)            # why: take out the walls' idle middle (fixture: keep it light)

    loc = Location((p.fa_servo_x, 0, 0))            # plate A outer face: tab tops press here, case top points into the fork
    body -= iface.servo_mount(ctx, SERVO, loc, group="wr_servo", plate_t=t, kind="tap", top_through=True,
                              teardrop=iface.print_up_deg(ctx, loc))      # why: the arm's wrist-servo window + tab pilots
    piv = Location((0, 0, wf))
    body -= iface.pin_hole(ctx, "M3", piv, "wr_pivot", depth=t, fit="free",
                           teardrop=iface.print_up_deg(ctx, piv))         # why: the arm's free wrist pivot hole
    for (hx, hy) in iface.circle(4, iface.horn_dims(HORN)["bc"], 45.0):   # why: hex key through plate B to the claw's horn screws
        body -= Pos(hx, hy, wf - t - 1) * Cylinder(2.0, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.mg_tab_t)))
    return ctx.finish(body)
