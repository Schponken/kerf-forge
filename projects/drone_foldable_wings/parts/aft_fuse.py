"""Aft fuselage: the airframe's backbone between the forward fuselage (joint face x = fuse_joint_x) and the tail boom.
PETG, 4 perimeters (2 mm skin), printed standing on its front face (world -X on the bed, X up), so every internal
plate below is a vertical wall on the printer and each one starts from a wall or the floor at 45 degrees.

Load path: each wing half's pivot pin is pressed into the pivot deck (lower plate, 6 mm, wall to wall) and the
spine arm (upper plate, spine.py); the deck carries the pin's bearing couple into the side walls, the keel rib and
the servo plate, the spine carries the upper end across its ridge to the other wing and down 4 M3 into the lugs
here. Fuselage bending goes through the rounded-box skin to the 4 M3 joint inserts in the front bulkhead and to the
boom socket at the tail end.

Inside, front to back: front bulkhead (4 M3 heat-set inserts for fwd_fuse + a wire pass-through), the front spine lug,
the servo plate (two MG996R sweep servos in top-first from below: their case tops pass its windows, their tabs press
on its underside, 4 M3 heat-set inserts each, tab screws from below through the belly openings), the pivot deck
(pin press holes, the sector stops, an arc slot for each aileron lead), the rear spine lug, the boom socket.
The top is open from x 100 to 221 for the spine; near the pivots the top corners are squared (r 3 instead of 12) so
the sector gears' sweep (r 23.5 round each pin) stays inside a 2.5 mm side wall.
"""
from build123d import *
import math
import importlib.util, pathlib
from kerf import iface
from kerf.features import fillet_inside

_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_hspec = importlib.util.spec_from_file_location("dfw_hub", pathlib.Path(__file__).with_name("hub.py"))
H = importlib.util.module_from_spec(_hspec); _hspec.loader.exec_module(H)     # sector angles (hub.py owns them)

SKIN = 2.0              # 4 x 0.42 perimeters + gap fill: solid skin (ENGINEERING s5 structural >= 1.6)
BULK_T = 3.0            # front bulkhead
SHOULDER_R = 3.0        # top-corner radius at the pivots (fuse_stations use 12): sector sweep clearance
COVER_T = 2.5           # spine cover thickness; its top is flush with fuse_top (spine.py reads this)
GAP_COVER = 0.3         # spine cover to opening edge, per side
OPEN_X = (100.0, 221.0)  # top opening for the spine
CLEAR = 0.5             # moving printed parts (ENGINEERING s6)
STOP_GAP = 0.55         # sector end face to stop post at each end of the fold range
LEDGE_W, LEDGE_T = 3.0, 3.0
SPINE_BOLTS = [(108.0, -7.0), (108.0, 7.0), (215.0, -6.0), (215.0, 6.0)]   # (x, y): wells in the spine ridge
FRONT_LUG_Z = -21.0     # bottom of the front spine lug (insert 6.7 + 0.8 floor + margin)


def cover_z0(p):
    return p.fuse_top - COVER_T


def stations(p):
    """Outer sections (x, half width, z bottom, z top, corner radius): layout's fuse_stations from fuse_joint_x aft,
    with the top corners squared between x 178 and 218 (the sector sweep) and blended back over 160..178."""
    st = [s for s in L.fuse_stations(p) if s[0] >= p.fuse_joint_x]
    out = []
    for x, hw, zb, zt, r in st:
        out.append((x, hw, zb, zt, SHOULDER_R if x == 218.0 else r))
        if x == 140.0:
            for xs, rs in ((160.0, r), (178.0, SHOULDER_R)):
                hw2, zb2, zt2, _ = L.fuse_section(p, xs)
                out.append((xs, hw2, zb2, zt2, rs))
    return out


def _sec(st, x):
    for a, b in zip(st[:-1], st[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(a[i] + t * (b[i] - a[i]) for i in range(1, 5))
    raise ValueError(x)


def _loft(st, shrink=0.0):
    secs = []
    for x, hw, zb, zt, r in st:
        w, h = 2 * (hw - shrink), (zt - zb) - 2 * shrink
        rr = max(1.0, min(r - shrink, w / 2 - 0.5, h / 2 - 0.5))
        pl = Plane(origin=(x, 0, (zb + zt) / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        secs.append(pl * RectangleRounded(w, h, rr))
    return loft(secs, ruled=True)


def outer(p):
    return _loft(stations(p))


def cavity(p):
    st = stations(p)
    xs = [p.fuse_joint_x + BULK_T] + [s[0] for s in st if p.fuse_joint_x + BULK_T < s[0] < 220] + [240.0, 258.0]
    return _loft([(x, *_sec(st, x)) for x in xs], SKIN)


def opening(p):
    """Top opening outline (XY sketch) the spine cover fills: the flat top, widened to y +-42 from x 140 so the
    pinions (r 15 at y 26) can be lowered in, rounded r 4 in plan."""
    x0, x1 = OPEN_X
    hw0 = L.fuse_section(p, x0)[0]
    pts = [(x0, -(hw0 - 10)), (140.0, -42.0), (x1, -42.0), (x1, 42.0), (140.0, 42.0), (x0, hw0 - 10)]
    sk = Polygon(*pts, align=None)
    return fillet(sk.vertices(), 4.0)


def _prism_xy(pts, z0, z1):
    return Pos(0, 0, z0) * extrude(Polygon(*pts, align=None), z1 - z0)


def _prism_xz(pts, y0, y1):
    """Polygon in the XZ plane (points (x, z)) extruded from y0 to y1."""
    pl = Plane(origin=(0, y1, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))   # local (u, v) = world (x, z), extruded -Y
    return extrude(pl * Polygon(*pts, align=None), y1 - y0)


def _wedge(c, a0, a1, r, z0, z1):
    """Pie slice centre c (x, y), angles a0..a1 deg (CCW from +X), radius r, z0..z1."""
    n = max(3, int(abs(a1 - a0) / 10) + 2)
    pts = [(c[0], c[1])] + [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))),
                             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]
    return _prism_xy(pts, z0, z1)


def stop_post(c, phi, side, r0, r1, span, z0, z1):
    """Stop post beside a sector end face lying on the ray at angle phi (deg) from c: its face is parallel to that
    ray, STOP_GAP away on the `side` (+1 = increasing angle), so the face meets the sector's end face flat."""
    u = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
    n = (-u[1], u[0])
    g = side * STOP_GAP
    u2 = (math.cos(math.radians(phi + side * span)), math.sin(math.radians(phi + side * span)))
    pts = [(c[0] + r * u[0] + g * n[0], c[1] + r * u[1] + g * n[1]) for r in (r0, r1)]
    pts += [(c[0] + r * u2[0], c[1] + r * u2[1]) for r in (r1, r0)]
    return _prism_xy(pts, z0, z1)


def _td_hole(ctx, at, d, depth):
    """Vertical (world) hole from `at` (top surface) down `depth`, teardrop toward print-up (+X when standing)."""
    loc = Location(at)
    up = iface.print_up_deg(ctx, loc)
    from kerf.features import teardrop_hole
    return loc * (teardrop_hole(d, depth, up) if up is not None else Pos(0, 0, -depth) * Cylinder(d / 2, depth + 1, align=(Align.CENTER, Align.CENTER, Align.MIN)))


def build(ctx):
    p = ctx.p
    cz0 = cover_z0(p)
    hull = outer(p)
    body = hull - ctx.cut(cavity(p), why="hollow rounded-box fuselage, 2 mm skin; bulkhead at the front", kind="cavity")
    body -= ctx.cut(Pos(0, 0, cz0) * extrude(opening(p), 40), why="top opening closed by the spine cover", kind="opening")

    # ---- top rim: ledges the spine cover rests on (3 mm in from the opening edge, merged into the skin)
    frame = offset(opening(p), 8.0) - offset(opening(p), -LEDGE_W)
    ledge = (Pos(0, 0, cz0 - LEDGE_T) * extrude(frame, LEDGE_T)) & hull
    ledge &= Pos(OPEN_X[0] + 3, -100, -100) * Box(300, 200, 200, align=(Align.MIN, Align.MIN, Align.MIN))
    body += ctx.add(ledge, why="rim ledge the spine cover sits on", kind="ledge")

    # ---- servo plate: tab tops press on its underside, case tops through its windows; V front (45 deg in plan) so
    # it grows out of the side walls on the printer instead of bridging
    d = iface.servo_dims(L.SWEEP_SERVO)
    sp = iface.screw_spec(d["screw"])
    plate_t = sp["insert_depth"] + 0.8                       # heat-set hole + 0.8 mm floor (catalog fdm_holes)
    tab_top = L.sweep_servo_loc(p, 1).position.Z + d["tab_t"]
    vx = 95.0
    plate = _prism_xy([(vx, -60), (vx, -50), (vx + 50, 0), (vx, 50), (vx, 60), (186, 60), (186, -60)],
                      tab_top, tab_top + plate_t) & hull
    body += ctx.add(plate, why="sweep servo plate: both MG996R hang from it by their tabs", kind="plate")

    # ---- pivot deck: lower pin plate, wall to wall, 45 deg chamfer up from the servo plate at its front
    deck = _prism_xz([(178, p.deck_z0), (222, p.deck_z0), (222, p.deck_z1), (178 + p.deck_z1 - p.deck_z0, p.deck_z1)], -60, 60) & hull
    body += ctx.add(deck, why="pivot deck: lower pin plate, carries the pin bearing couple to the walls", kind="plate")

    # ---- keel rib on the centreline: floor to servo plate and deck, front edge rising 45 deg off the floor
    zf = p.fuse_bottom + SKIN
    rib = _prism_xz([(116, zf - 1), (222, zf - 1), (222, p.deck_z0), (186, p.deck_z0), (186, tab_top),
                     (116 + tab_top - (zf - 1), tab_top)], -1.5, 1.5) & hull
    body += ctx.add(rib, why="keel rib: ties servo plate and deck to the floor", kind="rib")

    # ---- spine lugs: front under the top skin (45 deg underside), rear on the deck (V front in plan)
    flug = _prism_xz([(88, p.fuse_top - SKIN), (114, p.fuse_top - SKIN), (114, FRONT_LUG_Z), (88 + p.fuse_top - SKIN - FRONT_LUG_Z, FRONT_LUG_Z)], -12, 12)
    body += ctx.add(flug & hull, why="front spine lug: 2 M3 heat-set inserts", kind="lug")
    rlug = _prism_xy([(202, 0), (214, -12), (226, -12), (226, 12), (214, 12)], p.deck_z1 - 0.01, cz0) & hull
    body += ctx.add(rlug, why="rear spine lug on the deck: 2 M3 heat-set inserts; carries the rear top skin edge", kind="lug")
    for s in (1, -1):
        web = _prism_xy([(211, s * 26), (212.5, s * 24.5), (226, s * 24.5), (226, s * 27.5), (212.5, s * 27.5)],
                        p.deck_z1 - 0.01, cz0 - 0.1) & hull
        body += ctx.add(web, why="web behind the pin: supports the rear top skin edge (bridge < 15 mm)", kind="web")

    # ---- per side: sector sweep clearance, stops, pin, lead slot, pinion clearance, servo mount
    a0, a1 = H.sector_deg(p)
    for s in (1, -1):
        n = "r" if s > 0 else "l"
        c = (p.pivot_x, s * p.pivot_y)
        # the sector only sweeps the half in front of the pin (angles a0 - fold_max .. a1): r 23 + 0.5
        sweep = Pos(c[0], c[1], p.deck_z1) * Cylinder(p.sector_ro + CLEAR, p.sector_z1 + CLEAR - p.deck_z1,
                                                      align=(Align.CENTER, Align.CENTER, Align.MIN))
        sweep &= Pos(c[0] + 2.0, 0, 0) * Box(100, 400, 400, align=(Align.MAX, Align.CENTER, Align.CENTER))
        body -= ctx.cut(sweep, why="sector gear sweep, 0..fold_max", kind="clearance")
        body -= ctx.cut(Pos(c[0], c[1], p.deck_z1) * Cylinder(p.boss_r + CLEAR, 40, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                        why="hub boss", kind="clearance")
        pc = (p.pinion_x, s * p.pivot_y)
        body -= ctx.cut(Pos(pc[0], pc[1], p.deck_z1) * Cylinder(p.pinion_ro + CLEAR, cz0 - p.deck_z1, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                        why="pinion + horn", kind="clearance")
        # stop posts on the deck, mirrored for the left: spread stop just past face B at fold 0, fold stop past
        # face A at fold_max (kerf hard_stop: aft_fuse vs hub beyond each end)
        posts = stop_post((c[0], p.pivot_y), a1, +1, p.boss_r + 1.5, p.sector_ro - 0.5, 35, p.deck_z1 - 0.01, cz0 - 0.5)
        posts += stop_post((c[0], p.pivot_y), a0 - p.fold_max, -1, p.boss_r + 1.5, 30, 35, p.deck_z1 - 0.01, cz0 - 0.5) & hull
        if s < 0:
            posts = mirror(posts, Plane.XZ)
        body += ctx.add(posts, why="mechanical stops: sector end faces meet them at 0 and fold_max", kind="stop")
        # aileron lead: through the hub's sector web at r 12 (hub angle 180), down through this arc slot
        ang = (180 - p.fold_max - 10, 190)
        slot = _wedge(c, *(ang if s > 0 else (-ang[1], -ang[0])), 14.5, p.deck_z0 - 1, p.deck_z1 + 1) \
            - Pos(c[0], c[1], p.deck_z0 - 2) * Cylinder(9.5, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body -= ctx.cut(slot, why="aileron lead passes down through the deck as the wing folds", kind="wire slot")
        # pivot pin pressed into the deck from its top face
        body -= iface.pin_hole(ctx, L.PIN, Location((c[0], c[1], p.deck_z1)), f"pivot_{n}",
                               depth=p.deck_z1 - p.deck_z0, fit="press", teardrop="auto")
        # sweep servo: top-first from below, tab tops against the plate's underside, heat-set inserts
        sl = L.sweep_servo_loc(p, s)
        body -= iface.servo_mount(ctx, L.SWEEP_SERVO, sl * Location((0, 0, d["tab_t"])), f"sweep_servo_{n}", plate_t,
                                  kind="heatset", top_through=True, teardrop="auto")
        # belly opening: the servo goes up through it, a 2.5 mm key reaches the tab screws; pointed rear end (print)
        sx = sl.position.X
        xa, xb = sx - d["span"] / 2 - 1.0, sx + d["L"] / 2 + 8.0
        ya, yb = s * (p.pivot_y - d["W"] / 2 - 1), s * (p.pivot_y + d["W"] / 2 + 1)
        hole = _prism_xy([(xa, ya), (xb, ya), (xb + abs(yb - ya) / 2, s * p.pivot_y), (xb, yb), (xa, yb)],
                         p.fuse_bottom - 5, zf + 0.5)
        body -= ctx.cut(hole, why="belly opening: servo in from below, key to its tab screws", kind="opening")
        body -= ctx.cut(_td_hole(ctx, (c[0], c[1], zf), 6.0, SKIN + 1), why="drift hole: push the pivot pin out from below", kind="hole")
        ctx.revolute(f"pivot_{n}", L.pivot_axis(p, s), range=(0, p.fold_max))
        ctx.rigid(f"sweep_servo_{n}", sl)

    # ---- front bulkhead: insert bosses + wire pass-through
    jx = p.fuse_joint_x
    for (y, z) in L.JOINT_BOLTS:
        bos = Pos(jx, y, z) * Rot(0, 90, 0) * Cylinder(5.0, 10.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        bos += Pos(jx + 10.0, y, z) * Rot(0, 90, 0) * Cone(5.0, 0.6, 4.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body += ctx.add(bos & hull, why="fuselage joint insert boss", kind="boss")
    front = Location(Plane(origin=(jx, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))     # local (u, v) = world (y, -z)
    body -= iface.bolt_pattern(ctx, "fuse_joint", "M3", [(y, -z) for (y, z) in L.JOINT_BOLTS], front, kind="heatset", depth=10.0)
    zc = (p.fuse_bottom + p.fuse_top) / 2
    pas = Plane(origin=(jx - 1, 0, zc - 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0)) * RectangleRounded(28, 30, 5)
    body -= ctx.cut(extrude(pas, BULK_T + 2), why="wire pass-through to the forward bay (servo, GPS, aileron, tail leads)", kind="wire hole")

    # ---- spine inserts (vertical; teardrop on the printer)
    top = Location((0, 0, cz0))
    body -= iface.bolt_pattern(ctx, "spine", "M3", SPINE_BOLTS[:2], top, kind="heatset", depth=cz0 - FRONT_LUG_Z, teardrop="auto")
    body -= iface.bolt_pattern(ctx, "spine", "M3", SPINE_BOLTS[2:], top, kind="heatset", depth=cz0 - p.deck_z1, teardrop="auto")

    # ---- boom socket: r 9 tube along the boom axis, 45 deg cone at its front, bore boom OD + 0.2 (epoxied)
    bl = L.boom_loc(p)
    sock = Pos(212.0, 0, p.boom_z) * Rot(0, 90, 0) * (Cone(0.6, 9.0, 8.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
                                                      + Pos(0, 0, 8.4) * Cylinder(9.0, 60, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    body += ctx.add(sock & hull, why="boom socket", kind="socket")
    body -= ctx.cut(bl * Pos(0, 0, -0.5) * Cylinder((p.boom_od + 0.2) / 2, p.fuse_x1 - p.boom_x0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="boom bore, OD + 0.2 slip for epoxy", kind="bore")
    body -= ctx.cut(_td_hole(ctx, (238.0, 12.0, -52.0), 6.0, 14.0), why="tail servo leads enter from under the boom", kind="wire hole")

    body, failed = fillet_inside(ctx, body, r=1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    for k in ("fwd", "spine", "tail"):
        ctx.rigid(k, Location())
    ctx.rigid("boom", bl)
    return ctx.finish(body)
