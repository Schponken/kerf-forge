"""Palm: the claw's frame. Wrist fork (plate A on the wrist horn, plate B on the wrist pivot, exactly as the arm's old
gripper), the palm plate the grip MG996R hangs under, the idler-dowel pedestal and two posts the cover screws to.

Claw frame (parts/layout.py): origin on the wrist axis at the wrist-horn face, X forward along the claw, Y up (arm
home), Z across the fork (plate A outer face z = 0, plate B outer face z = W). The palm plate is y 0..t.

Section from the load (DESIGN.md 'Load -> section'): the grip servo's stall couple and side loads enter the palm plate
in its own plane; the idler pin's side load enters the pedestal 6-20 mm above it and bends the palm about Z and X back
to the wrist. So the palm is a U channel standing on the bed: the palm plate is the flange, plate B runs on forward
under the pedestal as a deep keel (its plane carries the pedestal's moment), a second web on the far side of the servo
closes the U, and plates A/B rise as cheeks behind the gears to carry the cover posts.
"""
from build123d import *
from kerf import iface
import importlib.util as _iu
import pathlib as _pl

_d = _iu.spec_from_file_location("claw_detail", _pl.Path(__file__).with_name("detail.py"))
detail = _iu.module_from_spec(_d)
_d.loader.exec_module(detail)

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"
Y_BED = -17.0                  # = -r_w: the wrist discs' lowest point, the print bed
IDLER_PRESS = 8.0              # idler dowel pressed this deep: 8 + 0.5 + finger 12 + 0.5 + cover 9 = a stocked 3 x 30
FAR_T = 3.0                    # far web thickness (6 mm was tried: no gain, the compliance is at the root)
TAN50 = 1.19                   # 50 deg rise for the web ends (prints without support: steeper than 45 deg)


def posts(p):
    """Cover-post axes (x, z), from parts/layout.py (cover.py uses the same)."""
    return [(p.x_post, p.z_post_a), (p.x_post, p.z_post_b)]


def up(x, y, z):
    return Plane((x, y, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0)).location


def side(pts, z0, z1, disc_r=None):
    """Prism in the XY plane between z0 and z1 from a polygon (plus the wrist disc)."""
    with BuildSketch(Plane.XY.offset(z0)) as s:
        if disc_r:
            Circle(disc_r)
        Polygon(*pts, align=None)
    return extrude(s.sketch, z1 - z0)


def build(ctx):
    p = ctx.p
    t, W, r = p.plate_t, p.W, p.r_w
    (xp, zpa), (_, zpb) = posts(p)
    POST_R = p.post_r
    x_front = p.x_sc + p.mg_span / 2 + 3.0          # 3 mm past the front servo tab
    c45 = r * 0.7071
    foot = [(-c45, -c45), (-c45 + (r - c45), Y_BED)]  # 45-deg tangent from the disc down to the flat bed edge
    # plate A: wrist disc + foot + the deep root under the palm + the cheek up to cover post A
    xa = 19.4                                        # why: stays 1 mm behind the servo's rear tab (x 21.45) incl. fillet
    body = side(foot + [(xa, Y_BED), (xa, 0.5), (xp + POST_R, 0.5), (xp + POST_R, p.y_c0), (xp - POST_R, p.y_c0), (0, r)], 0, t, r)
    # plate B: same, plus the keel under the palm and the pedestal (z 28..35) to the front
    xk = 50.0
    # why: above the palm plate plate B rises as a wall to 0.5 mm under the idler gear (y_top) from its cheek past the
    # pedestal, then drops at 45 deg: the pedestal's pin moment goes straight into a 30 mm deep web, and the deeper
    # channel stiffens the palm in bending and twist (palm_fea deflection)
    y_top = p.y_g0 - 0.5
    x_ped = p.x_g + 5.0
    keel = foot + [(xk, Y_BED), (xk - Y_BED / TAN50, 0.5), (x_ped + (y_top - t), t), (x_ped, y_top), (xp + POST_R, y_top),
                   (xp + POST_R, p.y_c0), (xp - POST_R, p.y_c0), (0, r)]
    body += side(keel, W - t, W, r)
    # far web (other side of the servo): below z -6.9 the claw passes the forearm's plate A, whose outline reaches at
    # most 24.1 mm from the wrist axis (21.55 long, r 8.5 front corners); the web starts 25.5 out and overlaps the root
    # beam, so no section between the wrist and the gear axes lacks a wall on this side (the wrist sweep proves it)
    zw = -6.5                                        # why: the window lead-in cone overshoots 1 mm below the palm to z -6.3
    xw0, xw1 = 25.5, x_front - 2.0
    # why: the far web also rises to 0.5 mm under the drive finger (y_top): the channel's second deep wall; its front
    # edge drops at 45 deg above the plate and runs back at 50 deg below it (prints unsupported, the end stays low)
    body += side([(xw0, Y_BED), (xw1 + Y_BED / TAN50, Y_BED), (xw1, 0.5), (xw1 - (y_top - 0.5), y_top), (xw0, y_top)], zw - FAR_T, zw)
    # palm plate y 0..t
    with BuildSketch(Plane.XZ) as s:
        Polygon((8.0, 0.0), (8.0, W), (x_front, W), (x_front, zw - FAR_T), (xw0, zw - FAR_T), (xw0, zw), (xa, zw), (xa, 0.0), align=None)
    body += extrude(s.sketch, -t)
    # why: root beam across the claw on top of the palm plate, between plate A's end (xa) and the servo case / grip horn
    # (0.5-1 mm clear), up to 0.5 mm under the gears: behind the servo the channel had no wall on the servo side, so
    # everything forward of the gear axes rotated about this root (palm_fea deflection); the beam ties both cheeks,
    # both cover posts and the keel wall into one deep section
    x_rb = p.x_g - iface.horn_dims(HORN)["od"] / 2 - 1.0
    x_rb0 = xp - POST_R                              # flush with the posts' rear faces (no step against their round edges)
    body += ctx.add(Pos(x_rb0, t - 0.01, zw) * Box(x_rb - x_rb0, y_top - t + 0.01, W - t - zw + 0.01, align=(Align.MIN, Align.MIN, Align.MIN)),
                    why="root beam: deep section between the wrist fork and the gear axes (stiffness, palm_fea)", kind="beam")
    # idler pedestal
    body += Pos(p.x_g, t - 0.01, p.z_i) * Rot(-90, 0, 0) * Cylinder(5.0, p.y_g0 - 0.5 - t + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for z0, z1, inner in ((0.0, zpa + POST_R, 1), (zpb - POST_R, W, 0)):
        post = Pos(xp, (t + p.y_c0) / 2, (z0 + z1) / 2) * Box(2 * POST_R, p.y_c0 - t, z1 - z0)
        body += fillet(post.edges().filter_by(Axis.Y).group_by(Axis.Z)[-inner], 2.0)
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))   # pivot boss

    hl = Location((0, 0, t))
    body -= iface.horn_mount(ctx, HORN, hl, group="wr_horn", plate_t=t, teardrop=iface.print_up_deg(ctx, hl))
    sloc = Plane((p.x_sc, 0, p.z_d), x_dir=(-1, 0, 0), z_dir=(0, 1, 0)).location   # tab tops on the palm underside, output toward the wrist
    body -= iface.servo_mount(ctx, SERVO, sloc, group="gr_servo", plate_t=t, kind="tap", top_through=True,
                              teardrop=iface.print_up_deg(ctx, sloc))
    pl = Location((0, 0, W))
    body -= iface.pin_hole(ctx, "M3", pl, "wr_pivot", depth=t + 3.0, fit="heatset", teardrop=iface.print_up_deg(ctx, pl))
    for (hx, hy) in iface.circle(4, iface.horn_dims(HORN)["bc"], 45.0):     # hex key to the wrist-horn screws
        body -= Pos(hx, hy, W - t - 4) * Cylinder(2.0, t + 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    il = up(p.x_g, p.y_g0 - 0.5, p.z_i)
    body -= iface.pin_hole(ctx, "motion.pin_3mm", il, "gr_idler", depth=IDLER_PRESS, fit="press", through=False,
                           teardrop=iface.print_up_deg(ctx, il))
    body -= Pos(p.x_g, Y_BED - 1, p.z_i) * Rot(-90, 0, 0) * Cylinder(1.0, p.y_g0 - 0.5 - IDLER_PRESS - Y_BED + 1.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos(p.x_g, (Y_BED - 1) / 2, p.z_i - 1.25) * Box(2.0, -Y_BED + 1, 2.5)   # why: the push-out hole runs on as a groove open to the keel's inner face (no 0.5 mm skin)
    for (x, z) in posts(p):
        body -= iface.bolt_pattern(ctx, "cover", "M3", [(0, 0)], up(x, p.y_c0, z), kind="heatset", depth=p.y_c0 - t)
    body, half_r, failed = detail.fillet_inside(ctx, body, 1.0)   # why: r 1 on every inside corner (ENGINEERING.md s5; style radii)
    if half_r or failed:
        ctx.notes.append(f"inside corners at r 0.5 (r 1 does not fit): {half_r}; left sharp: {failed}")
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    ctx.rigid("servo_seat", sloc * Location((0, 0, -p.mg_tab_t)))
    ctx.revolute("idler", Axis((p.x_g, p.y_g0, p.z_i), (0, 1, 0)), range=(-p.grip_open, 0))
    ctx.rigid("cover_seat", Location((0, 0, 0)))
    ctx.rigid("tcp", Location((p.x_tcp, p.y_pad, p.z_tcp)))
    ctx.rigid("lead_1", Location((0, 30, -3)))
    ctx.rigid("lead_2", Location((12, -12, -1.5)))
    return ctx.finish(body)
