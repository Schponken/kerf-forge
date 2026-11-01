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
import importlib.util as _iu
import pathlib as _pl

_d = _iu.spec_from_file_location("claw_detail", _pl.Path(__file__).with_name("detail.py"))
detail = _iu.module_from_spec(_d)
_d.loader.exec_module(detail)
from kerf.features import safe_fillet

R_POST = 5.0         # plate around each post screw: >= 1.5 d + wall from the M3 hole (ENGINEERING.md s7), 0.6 past the post
R_DRIVE = 5.5        # plate around the drive dowel
R_IDLER = 5.5        # plate around the idler dowel
BOSS_DRIVE = 3.7     # drive boss: the horn-screw heads sweep r 4.25..9.75 about the drive axis, so <= 3.75 (0.55 clear)
BOSS_IDLER = 5.0     # idler boss: nothing turns over the idler gear's top (r 7 was tried: no stiffer, the node turns as a whole)
MEMBER = 6.0         # frame member width (centre line +-3); window corners rounded WIN_R
WIN_R = 2.0


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
    # Triangulated frame: members on the lines post A - post B (rear), post B - idler (side), post A - idler (diagonal),
    # post A - drive (side), drive - idler (front tie); two triangular windows where nothing flows.
    A, B, D, I = ((p.x_post, p.z_post_a), (p.x_post, p.z_post_b), (p.x_g, p.z_d), (p.x_g, p.z_i))
    for tri in ((A, B, I), (A, D, I)):
        with BuildSketch(pl) as wk:
            Polygon(*[(x, -z) for x, z in tri], align=None)
            offset(amount=-(MEMBER / 2 + WIN_R), mode=Mode.REPLACE)
            offset(amount=WIN_R, kind=Kind.ARC, mode=Mode.REPLACE)
        plate -= ctx.cut(extrude(wk.sketch, p.cover_t), why="window: the frame members carry the dowel loads, the middle idles", kind="lightening")
    # why: 0.6 edge break on the bed face (top face, printed down): elephant's foot and a clean first layer
    body, f0 = safe_fillet(plate, [([e for e in plate.edges() if abs(e.center().Y - p.y_c1) < 1e-6], 0.6)], kind="chamfer")
    for z, r, why in ((p.z_d, BOSS_DRIVE, "drive dowel boss: holds the top dowel 0.5 mm over the drive finger (r < the horn-screw heads' sweep)"),
                      (p.z_i, BOSS_IDLER, "idler dowel boss: the idler dowel runs in 9 mm of cover 0.5 mm over the idler finger")):
        boss = Pos(p.x_g, p.y_cb, z) * Rot(-90, 0, 0) * Cylinder(r, p.y_c0 - p.y_cb + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body += ctx.add(boss, why=why, kind="boss")
    # why: the members on the idler side run the full 7 mm down to the boss faces (0.5 mm over the gears): the dowels'
    # lever moments bend the cover out of its plane, and depth goes in cubed (cover_fea deflection). The drive side
    # stays plate-deep: the drive finger's horn-screw heads turn under it.
    deep = None
    for (x0, z0), (x1, z1) in ((A, B), (B, I), (A, I)):
        L, ang = math.hypot(x1 - x0, z1 - z0), math.atan2(z1 - z0, x1 - x0)
        bar = Pos((x0 + x1) / 2, p.y_cb, (z0 + z1) / 2) * Rot(0, -math.degrees(ang), 0) * Box(L, p.y_c0 - p.y_cb + 0.01, MEMBER, align=(Align.CENTER, Align.MIN, Align.CENTER))
        deep = bar if deep is None else deep + bar
    for z in (p.z_post_a, p.z_post_b):          # the palm posts stand under the plate there: keep 0.2 mm off them
        deep -= Pos(p.x_post, p.y_cb - 1, z) * Box(2 * p.post_r + 0.4, p.y_c0 - p.y_cb + 1.0, 2 * (p.post_r + 0.2) + 2 * 0.4 + 0.01, align=(Align.CENTER, Align.MIN, Align.CENTER))
    body += ctx.add(deep, why="deep members on the idler side: out-of-plane stiffness where the dowel moments enter", kind="rib")
    roots = [e for e in body.edges() if abs(e.center().Y - p.y_c0) < 1e-6
             and min(math.hypot(e.center().X - p.x_g, e.center().Z - z) for z in (p.z_d, p.z_i)) < BOSS_IDLER + 0.1
             and e.geom_type == GeomType.CIRCLE and e.radius in (BOSS_DRIVE, BOSS_IDLER)]
    body, failed = safe_fillet(body, [(roots, 1.0)])     # why: r 1 boss roots (the dowel's bending enters here)
    if failed:
        raise ValueError(f"boss roots: {failed}")
    ends = [e for e in body.edges() if abs(e.center().Y - p.y_cb) < 1e-6]
    body, failed = safe_fillet(body, [(ends, 0.4)], kind="chamfer")   # why: edge break on the boss and member faces (last layers)
    if failed:
        raise ValueError(f"boss end break: {failed}")
    # why: r 1 on the inside corners (members into the plate and bosses); not where a palm post's top edge sits beside
    # a member (a fillet there would sit on the post)
    near_post = lambda at: abs(at[0] - p.x_post) < p.post_r + 1.2 and min(abs(at[2] - p.z_post_a), abs(at[2] - p.z_post_b)) < p.post_r + 1.5  # noqa: E731
    body, half_r, failed = detail.fillet_inside(ctx, body, 1.0, keep=near_post)
    if half_r or failed:
        ctx.notes.append(f"inside corners at r 0.5 (r 1 does not fit): {half_r}; left sharp: {failed}")
    if f0:
        ctx.notes.append(f"edge breaks skipped: {f0}")
    span = p.y_c1 - p.y_cb
    body -= iface.pin_hole(ctx, "motion.pin_3mm", up(p.x_g, p.y_c1, p.z_d), "gr_top", depth=span, fit="press")
    body -= iface.pin_hole(ctx, "motion.pin_3mm", up(p.x_g, p.y_c1, p.z_i), "gr_idler", depth=span, fit="free")
    for z in (p.z_post_a, p.z_post_b):
        body -= iface.bolt_pattern(ctx, "cover", "M3", [(0, 0)], up(p.x_post, p.y_c1, z), kind="clearance", depth=p.cover_t)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
