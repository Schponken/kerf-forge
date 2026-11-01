"""Cover: the top support of both gear axes, screwed to the palm's two posts. Claw frame (parts/layout.py).

Load path (DESIGN.md 'Load -> section'): at grip-servo stall each gear axis pushes its dowel ~45 N sideways, in the
plane of this plate (38.4 N along X, 24.2 N across). The two dowels' separating forces are equal and opposite, so the
front member between the two dowel bosses is a tie that holds the gear centre distance; what is left goes back to the
two post screws through the side members. In-plane loads make a flat frame the right section (a membrane is stiffest in
its own plane); the middle, where nothing flows, is a window.

Heights: the plate clears the drive finger's horn-screw heads by 0.5 mm; under each dowel a boss reaches down to 0.5 mm
over the gear so the dowels are held right next to the fingers (short lever on the steel, 7 mm of hole in the plastic).
Prints top face down (print_rot [-90, 0, 0]): the plate is the first layers, the bosses grow up from it.
"""
import math

from build123d import *
from kerf import iface
from kerf.features import safe_fillet

R_POST = 4.4         # plate around each post screw (= the palm post, layout post_r)
R_DRIVE = 5.5        # plate around the drive dowel
R_IDLER = 5.5        # plate around the idler dowel
BOSS_DRIVE = 3.7     # drive boss: the horn-screw heads sweep r 4.25..9.75 about the drive axis, so <= 3.75 (0.55 clear)
BOSS_IDLER = 5.0     # idler boss: nothing turns over the idler gear's top
RIM = 4.5            # frame member width around the window (in-plane bending: FEA cover_fea)


def up(x, y, z):
    return Plane((x, y, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0)).location


def build(ctx):
    p = ctx.p
    pts = [(p.x_post, p.z_post_a, R_POST), (p.x_post, p.z_post_b, R_POST), (p.x_g, p.z_d, R_DRIVE), (p.x_g, p.z_i, R_IDLER)]
    # plan sketch on a plane whose local (x, y) = claw (x, z); extruded toward claw +Y
    pl = Plane((0, p.y_c0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    with BuildSketch(pl) as sk:
        for x, z, r in pts:
            with Locations((x, -z)):        # plane local y = -claw z (x_dir X, z_dir Y -> y_dir = -Z)
                Circle(r)
        make_hull()                          # why: outline wraps the four load points (two posts, two dowels)
    plate = extrude(sk.sketch, p.cover_t)
    # why: window where no load flows (between the members joining posts and dowels)
    x0, x1 = p.x_post + R_POST + 1.0, p.x_g - R_DRIVE - 1.0
    z0, z1 = p.z_d + R_DRIVE + RIM - 1.0, p.z_i - R_IDLER - RIM + 1.0
    with BuildSketch(pl) as wk:
        with Locations(((x0 + x1) / 2, -(z0 + z1) / 2)):
            RectangleRounded(x1 - x0, z1 - z0, 2.0)
    plate -= ctx.cut(extrude(wk.sketch, p.cover_t), why="window: the frame members carry the in-plane dowel loads, the middle idles", kind="lightening")
    edges = plate.edges().filter_by(lambda e: abs(e.center().Y - p.y_c0) < 1e-6 or abs(e.center().Y - p.y_c1) < 1e-6)
    plate, failed = safe_fillet(plate, [(edges, 0.6)], kind="chamfer")   # why: edge break, outline and window
    if failed:
        raise ValueError(f"cover edge break: {failed}")
    body = plate
    for z, r, why in ((p.z_d, BOSS_DRIVE, "drive dowel boss: holds the top dowel 0.5 mm over the drive finger (r < the horn-screw heads' sweep)"),
                      (p.z_i, BOSS_IDLER, "idler dowel boss: the idler dowel runs in 7 mm of cover 0.5 mm over the idler finger")):
        boss = Pos(p.x_g, p.y_cb, z) * Rot(-90, 0, 0) * Cylinder(r, p.y_c0 - p.y_cb + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body += ctx.add(boss, why=why, kind="boss")
    roots = [e for e in body.edges() if abs(e.center().Y - p.y_c0) < 1e-6
             and min(math.hypot(e.center().X - p.x_g, e.center().Z - z) for z in (p.z_d, p.z_i)) < BOSS_IDLER + 0.1
             and e.geom_type == GeomType.CIRCLE and e.radius in (BOSS_DRIVE, BOSS_IDLER)]
    body, failed = safe_fillet(body, [(roots, 1.0)])     # why: r 1 boss roots (the dowel's bending enters here)
    if failed:
        raise ValueError(f"boss roots: {failed}")
    ends = [e for e in body.edges() if abs(e.center().Y - p.y_cb) < 1e-6]
    body, failed = safe_fillet(body, [(ends, 0.4)], kind="chamfer")   # why: edge break on the boss faces (last layer)
    if failed:
        raise ValueError(f"boss end break: {failed}")

    span = p.y_c1 - p.y_cb
    body -= iface.pin_hole(ctx, "motion.pin_3mm", up(p.x_g, p.y_c1, p.z_d), "gr_top", depth=span, fit="press")
    body -= iface.pin_hole(ctx, "motion.pin_3mm", up(p.x_g, p.y_c1, p.z_i), "gr_idler", depth=span, fit="free")
    for z in (p.z_post_a, p.z_post_b):
        body -= iface.bolt_pattern(ctx, "cover", "M3", [(0, 0)], up(p.x_post, p.y_c1, z), kind="clearance", depth=p.cover_t)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
