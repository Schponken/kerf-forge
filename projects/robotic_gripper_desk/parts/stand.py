"""Bench stand: the desk robot arm's forearm wrist end (projects/robot_arm/parts/forearm.py) on a base, so the checks
prove the gripper fits and clears the real wrist, and so the gripper can be tested on the bench before it goes on the arm.

Wrist end, copied from the forearm: plate A (7 mm) carries the wrist MG996R hung outside it, top-first through a window
(4 x M3 self-tapping into the tab pilots); plate B (7 mm, w_f outer width) has the free M3 pivot hole and four 4 mm
hex-key holes over the gripper's wrist-horn screws. Behind the wrist each plate turns down into a tapered 5 mm leg
(front post + diagonal back strut carry the wrist moment as a couple, a printable window between them) standing on
two cross bars; a web with 45 deg haunches ties the plates together just behind the wrist servo.

Frames: stand frame S = world: bench at z = 0, Z up, X toward the gripper. Forearm frame F = S at (0, 0, stand_h)
turned (90, 0, 0): F x = S x, F y = S z - stand_h, F z = -S y; the wrist axis is F's Z axis (layout.py).
Keep-out: the gripper swings +-75 deg about the wrist; below the bands (F y < -r) nothing of the stand is ahead of
S x = X_SWEEP, the swing envelope's back edge (DESIGN.md contract).

In use (the bench is not modelled): put the base's front edge (S x = X_SWEEP) on the bench's front edge, so the gripper
hangs over it when the wrist points down. Fix it with two M4 or 4 mm wood screws through the bar holes (diagonal), or
stand it at a bench CORNER and put a C-clamp on the back bar round the SIDE edge. Never clamp round the front edge:
the gripper head (100 mm wide, as wide as the whole base) swings down past the clamp's frame there.
Printed on its base (print_rot [0, 0, 0]): the plates stand vertical (the leg bending crosses the layers: FEA in z),
the tab pilots and pivot are teardrops, the web and windows have 45 deg roofs. The two bands ahead of the column are
flat ceilings 7 mm wide and need support (the swing envelope leaves no room under them); the servo window's top
bridges 41 mm, as on the forearm."""
from build123d import *
from kerf import iface
from kerf.features import safe_fillet, bed_chamfer

SERVO = "servos.MG996R"

X_SWEEP = -45.0     # contract: the gripper's swing envelope ends here below the bands; base front = bench edge
R1, R2, R4 = 1.0, 2.0, 4.0   # project style radii (project.yaml style.radii)
BREAK = 0.6         # project style edge break
LEG_T = 5.0         # legs + band behind the column (the forearm's 7 mm is kept where the wrist parts mount)
BAR_T = 4.0         # cross bars on the bench
POST_W = 7.0        # leg front post width (x)
STRUT_W = 7.0       # leg back strut width (normal to its edge)
WEB_T = 3.0         # web between the plates
LEAD_Z = -3.0       # wire tie line: 3 mm outside plate A (F z), as forearm.py's lead_* points


def concave_edges(shape):
    """Straight re-entrant edges between two flat faces (the kerf/edges.py sharp-inside-corner test)."""
    owners = {}
    for f in shape.faces():
        if f.geom_type == GeomType.PLANE:
            for e in f.edges():
                owners.setdefault(e, []).append(f)
    out = []
    for e, fs in owners.items():
        if len(fs) != 2 or e.geom_type != GeomType.LINE or e.length < 0.5:
            continue
        c = e.center()
        n1, n2 = fs[0].normal_at(c), fs[1].normal_at(c)
        if abs(n1.dot(n2)) < 0.97 and shape.is_inside(c + n1 * 0.2 - n2 * 0.2):
            out.append(e)
    return out


def build(ctx):
    p = ctx.p
    t, r, W, H = p.plate_t, p.link_h / 2, p.w_f, p.stand_h
    F = Location((0, 0, H), (90, 0, 0))
    xc = X_SWEEP - R4                       # column front face: the r4 band/post fillet stays behind X_SWEEP
    yb, ytop = -H, r                        # bench and band top, in F
    xs0, xs1 = xc - 40.0, xc - 20.0         # back strut outer edge at the bench / at the band top (F x)
    x_end = -p.mg_out_x + p.mg_span / 2 + 5.0    # forearm.py: plate A reaches 5 mm past the far tab

    def side(front_x):
        """One plate's outline in F (x, y): wrist disc + band back to the strut + leg down to the bench, less a window."""
        with BuildSketch() as sk:
            Circle(r)                                                        # why: forearm wrist disc (Ø link_h)
            with Locations(((front_x + xs1) / 2, 0)):
                Rectangle(front_x - xs1, 2 * r)                              # why: forearm band, back to the strut top
            Polygon((xc, yb), (xc, ytop), (xs1, ytop), (xs0, yb), align=None)   # why: leg = column to the bench (load path)
            # why: r4 at the band/post re-entrant corner, where the wrist moment turns down the leg
            fillet(sk.vertices().filter_by(lambda v: abs(v.X - xc) < 0.01 and abs(v.Y + r) < 0.01), R4)
            if front_x > r:
                fillet(sk.vertices().filter_by(lambda v: v.X > front_x - 0.01), r / 2)   # why: forearm's r/2 front corners
            # why: rounded back top corner of the column (nothing sharp to catch hands or wires)
            fillet(sk.vertices().filter_by(lambda v: abs(v.X - xs1) < 0.01 and abs(v.Y - ytop) < 0.01), R4)
            d = Vector(xs1 - xs0, ytop - yb).normalized()
            q0 = Vector(xs0, yb) + Vector(d.Y, -d.X) * STRUT_W               # strut inner edge (offset toward +x)
            yw0, yw1 = yb + BAR_T + 3.0, -r - 6.0                            # window floor / apex (F y)
            pa, pb = q0 + d * ((yw0 - q0.Y) / d.Y), q0 + d * ((yw1 - q0.Y) / d.Y)
            xp = xc - POST_W
            with BuildSketch(mode=Mode.SUBTRACT) as win:
                # why: window in the leg: the moment is carried by the post and strut, the middle only shears;
                # 45 deg roof from the post, the strut edge leans in: prints without support
                Polygon((xp, yw0), (xp, yw1 - (xp - pb.X)), (pb.X, yw1), (pa.X, yw0), align=None)
                fillet(win.vertices(), R4)                                   # why: r4 window corners (stress risers)
        x1 = max(front_x, r) + 1.0
        cut = Pos((xc + x1) / 2, 0) * Rectangle(x1 - xc, 4 * r)               # everything ahead of the column front
        return sk.sketch & cut, sk.sketch - cut

    aA, bA = side(x_end)
    aB, bB = side(0.0)
    body = F * extrude(aA, t)                                                # why: plate A wrist end, 7 mm (forearm)
    body += F * extrude(bA, LEG_T)                                           # why: plate A column/leg, outer face flush
    body += F * (Pos(0, 0, W - t) * extrude(aB, t))                          # why: plate B wrist end, 7 mm (forearm)
    body += F * (Pos(0, 0, W - LEG_T) * extrude(bB, LEG_T))                  # why: plate B column/leg, outer face flush

    # why: front wall between the legs, just behind the wrist servo (the forearm's web): ties the plates so the pivot
    # stays coaxial with the servo and closes the column into a channel section; its front face hides the 7/5 mm step
    y0, y1 = -(W - LEG_T), -LEG_T           # the legs' inner faces (S y)
    zs = H + r - 12.0 - (y1 - y0 - 8.0) / 2  # window roof springing: apex 12 mm under the band top
    with BuildSketch(Plane.YZ.offset(xc - WEB_T)) as web:
        with Locations(((y0 + y1) / 2, (BAR_T + H + r) / 2)):
            Rectangle(y1 - y0, H + r - BAR_T)
        with BuildSketch(mode=Mode.SUBTRACT) as wwin:
            # why: window: only the top beam (plate tie) and the edges work; 45 deg roof prints without support
            Polygon((y0 + 4, BAR_T + 4), (y1 - 4, BAR_T + 4), (y1 - 4, zs), ((y0 + y1) / 2, zs + (y1 - y0 - 8) / 2),
                    (y0 + 4, zs), align=None)
            fillet(wwin.vertices(), R4)                                      # why: r4 window corners
    body += extrude(web.sketch, WEB_T)

    # base: the legs stand on their own edges; two bars join them and carry the bench fixings
    yA, yB = 15.0, -(W + 15.0)              # contract footprint across: plate A side + 15, plate B side - 15
    xbar = xs0 + 7.0                        # back bar centre (under the strut feet)
    xf = xc - 6.0                           # front bar centre: front face flush with the posts (one flat front)
    with BuildSketch() as base:
        with Locations((xf, (yA + yB) / 2)):
            Rectangle(12.0, yA - yB)                                         # why: front bar: joins the post feet, front screw
        with Locations((xbar, (yA + yB) / 2)):
            Rectangle(18.0, yA - yB)                                         # why: back bar: joins the strut feet; clamp pad + back screw
        fillet(base.vertices(), R4)                                          # why: r4 corners
    body += extrude(base.sketch, BAR_T)

    # why: fillet every re-entrant junction (bars to legs, wall to legs and bands): stress risers + weak layer seams;
    # r2, except r1 where the front wall meets the 7 mm bands (the band's r4 corner runs out under it)
    corners = concave_edges(body)
    front = [e for e in corners if abs(e.center().X - xc) < 0.1 and e.center().Z > BAR_T + 1]
    rest = [e for e in corners if e not in front]
    body, failed = safe_fillet(body, [(rest, R2), (front, R1)])
    if failed or len(front) != 2:
        raise ValueError(f"junction fillets: {len(front)} front edges (want 2), failed {failed}")
    # why: 0.6 mm elephant's-foot chamfer on the first layer
    body, _ = bed_chamfer(ctx, body, BREAK)

    # why: 2 x M4 / 4 mm wood screws to the bench, diagonal: one resists tipping forward, the other back
    for (x, y) in ((xf, yA - 6.0), (xbar, yB + 7.0)):
        body -= Pos(x, y, BAR_T) * iface.hole("M4", "clearance", BAR_T)[0]

    # interfaces (forearm.py, with its L = 0)
    loc = F * Location((-p.mg_out_x, 0, 0))   # plate A outer face: tab tops press here, case top points into the fork
    # why: wrist servo window + 4 tab pilots (top-through, self-tapping M3), teardrops: the pilots print horizontal
    body -= iface.servo_mount(ctx, SERVO, loc, group="wr_servo", plate_t=t, kind="tap", top_through=True,
                              teardrop=iface.print_up_deg(ctx, loc))
    piv = F * Location((0, 0, W))
    # why: free M3 pivot hole (the gripper's plate B turns on it), teardrop: prints horizontal
    body -= iface.pin_hole(ctx, "M3", piv, "wr_pivot", depth=t, fit="free", teardrop=iface.print_up_deg(ctx, piv))
    for (hx, hy) in iface.circle(4, p.horn_bc, 45.0):
        # why: Ø4 hex-key access through plate B to the gripper's wrist-horn screws (forearm.py)
        body -= F * (Pos(hx, hy, W - t - 1) * Cylinder(2.0, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))

    # wiring: gripper lead over the wrist (lead_b) back above plate A (lead_a), down the outside of plate A's leg past
    # the tie slots (lead_down, above the back bar); the wrist servo's lead from its exit (lead_wr) under it to lead_down
    xt, yd = xc - 11.0, yb + BAR_T + 6.0    # tie-slot centre (F x, on F y = 0); lead_down height
    xd = xbar + 1.0
    for dx in (-5.0, 5.0):
        # why: cable-tie slot pair through plate A's column: ties the lead bundle to the leg (forearm.py)
        body -= F * (Pos(xt + dx, 0, LEG_T / 2) * extrude(SlotOverall(3.2, 1.8, rotation=90), LEG_T + 2, both=True))
    ctx.rigid("lead_b", F * Location((0, 30, LEAD_Z)))
    ctx.rigid("lead_a", F * Location((xt + (xt - xd) / (0 - yd) * 24, 24, LEAD_Z)))   # on the line lead_down -> slots
    ctx.rigid("lead_down", F * Location((xd, yd, LEAD_Z)))
    cb = ctx.cat.get(SERVO)
    # just past the servo's lead exit (catalog cable_boss_*: output end, near the case bottom), 10 mm below the axis
    case_bottom = -(p.mg_tab_t + p.mg_tab_z)
    ctx.rigid("lead_wr", F * Location((-p.mg_out_x + p.mg_L / 2 + ctx.cat.num(cb, "cable_boss_protrusion") + 4.0, -10.0,
                                       case_bottom + ctx.cat.num(cb, "cable_boss_z0") + ctx.cat.num(cb, "cable_boss_h") / 2)))
    # off-board electronics on the bench behind the stand (S z = 0, Z up), >= 40 mm apart (an LRS-100 sized supply fits)
    for name, (x, y) in {"desk_nano": (-185.0, 55.0), "desk_driver": (-195.0, 10.0), "desk_bus": (-170.0, -45.0),
                         "desk_psu": (-265.0, -60.0)}.items():
        ctx.rigid(name, Location((x, y, 0)))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.mg_tab_t)))
    return ctx.finish(body)
