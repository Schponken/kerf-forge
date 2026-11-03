"""Pod (pod_r / pod_l): the sweep-servo nacelle under the glove's trailing-edge corner; it carries the pivot pin.

Load path (DESIGN.md "Load -> section"): the pin's lower reaction (196 N bearing couple) goes into an 11 mm floor
disc under the boss (pin pressed 8 mm), out along four 3.2 mm ribs (full 11 mm deep) into a closed 3 mm wall ring
round the swept volume (sector r 24.8 + pinion r 16.5 + the servo with its tabs), and from the ring's top rim into the glove
through 2 M3 from below (inboard flange lugs) and 2 M3 from the cap side (insert lugs). The servo hangs by its tabs from
an 8 mm plate (heat-set inserts) inside a deep skirt; its lead leaves through a slot in the inboard skirt wall.
Two stop posts inside the ring are met by the hub sector's radial ear faces just past 0 and just past 65 deg.
Open on top and printed upright (the glove closes it): no ceilings except the 8 mm bridge over the servo's cable boss
pocket (supports: needed). Outboard of y 149.5 the rim drops to z -6, under the hub's lower surface.
"""
from build123d import *
import math
import importlib.util, pathlib
from kerf import iface, features

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

WALL = 3.0               # ring and skirt wall (structural: >= 1.6, 2.4 round heat-set bosses)
RING_Z0 = -38.5          # ring and floor disc bottom (pin hole 8 deep from the disc top z -27.5 leaves 3 mm under it)
RIM_OUT_Z = -6.0         # rim height outboard of the glove (y > 149.5): clears the hub's lower surface (-4.5 at x 157)
PLATE_T = 8.0            # servo plate: M3 heat-set insert + 2 mm under it
SKIRT_Z0 = -62.3         # lowest point: servo bottom -59.7 - 0.6 clearance - 2 mm floor (fuselage belly -70)
SERVO_CLR = 0.6          # servo window clearance (matches iface.servo_mount)
RIB_T = 3.2
OVER = 2.7               # deg past 0 / 65 where the sector's ears meet the posts (stop_* beyond -3 / 68; 2.2 deg x r 14.5 = 0.5 mm clear at 0.5 deg)
EAR = 4.0                # hub.py: tooth-less ear past the teeth at each end of the sector
POST_Z = (-28.0, -7.0)   # sector band is z -16..-6; the post stands on the floor disc and runs out to the ring wall
POST_R = (14.5, 26.0)    # the ears are r 18.4 (hub.py: clear of the pinion's tip circle); boss r 11
LUG_R = 5.5              # screw lug radius: 2.4 mm round the M3 head / insert
FLANGE_Z0 = -11.0        # pod-screw lugs: 8 thick, counterbore from below (head 3.3 deep)
INSERT_Z0 = -13.0        # cap-screw (insert) lugs


def _lug(a, b, r, z0, z1):
    d = math.dist(a, b)
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return Pos((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z0) * Rot(0, 0, ang) * extrude(SlotCenterToCenter(d, 2 * r), z1 - z0)


def _wedge(c, a0, a1, r0, r1, z0, z1):
    n = max(3, int(abs(a1 - a0) / 5) + 2)
    pts = [(c[0] + r1 * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))), c[1] + r1 * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]
    pts += [(c[0] + r0 * math.cos(math.radians(a1 + (a0 - a1) * k / (n - 1))), c[1] + r0 * math.sin(math.radians(a1 + (a0 - a1) * k / (n - 1)))) for k in range(n)]
    return Pos(0, 0, z0) * extrude(Polygon(*pts, align=None), z1 - z0, dir=(0, 0, 1))


def _footprint(p, grow):
    """Plan of the swept volume (+grow all round): sector disc, pinion disc and the servo with its tabs."""
    sd = iface.servo_dims(L.SWEEP_SERVO)
    sx = L.sweep_servo_loc(p, 1).position.X
    sy = p.pivot_y
    f = Pos(p.pivot_x, sy) * Circle(L.POD_OPEN_R + 0.3 + grow)
    f += Pos(p.pinion_x, sy) * Circle(L.GEAR_M * (L.Z_PINION + 2) / 2 + 1.5 + grow)
    f += Pos(sx, sy) * Rectangle(sd["span"] + 1.2 + 2 * grow, sd["W"] + SERVO_CLR + 0.4 + 2 * grow)
    return f


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    n = "l" if s < 0 else "r"
    c = (p.pivot_x, p.pivot_y)                     # right-side numbers; mirrored below for the left pod
    sd = iface.servo_dims(L.SWEEP_SERVO)
    loc_r = L.sweep_servo_loc(p, 1)
    sx, tab_z = loc_r.position.X, loc_r.position.Z
    z_top = L.POD_ROOF_Z

    # wall ring: closed box round the swept volume; rim at the glove pad inboard, lower outboard
    ring = extrude(_footprint(p, WALL), z_top - RING_Z0) - extrude(_footprint(p, 0.0), z_top - RING_Z0)
    body = ctx.add(Pos(0, 0, RING_Z0) * ring, why="closed 3 mm wall ring round the sector sweep, pinion and servo: the pin's reaction and the servo "
                   "torque reach the glove through its top rim", kind="wall")
    body -= ctx.cut(Pos(sx, 149.5, RIM_OUT_Z) * Box(400, 300, 10, align=(Align.CENTER, Align.MIN, Align.MIN)),
                    why="rim steps down outboard of the glove (y > 149.5): clears the hub's lower surface, which dips to z -4.5 at x 157", kind="clearance")

    # floor disc under the boss, 4 ribs to the ring: the pin's bending reaction
    body += ctx.add(_cyl_z(c, 14.0, RING_Z0, L.POD_FLOOR_Z1), why="floor disc under the boss: holds the pin pressed 8 mm; ring touches the bearing's inner race", kind="floor")
    for ang in (0, 90, 135, 225, 270):
        r0, r1 = 10.0, L.POD_OPEN_R + WALL - 0.5
        body += ctx.add(Pos(c[0], c[1], 0) * Rot(0, 0, ang) * Pos((r0 + r1) / 2, 0, (RING_Z0 + L.POD_FLOOR_Z1) / 2) * Box(r1 - r0, RIB_T, L.POD_FLOOR_Z1 - RING_Z0),
                        why=f"rib at {ang} deg: floor disc to the wall ring, full depth (pin reaction 196 N)", kind="rib")
    # 0.5 mm ring: touches only the bearing's inner race (r 2.5..4.3) so the hub never rubs the plate
    ring_r = _cyl_z(c, 4.2, L.POD_FLOOR_Z1, L.POD_FLOOR_Z1 + L.GAP) - _cyl_z(c, 3.1, L.POD_FLOOR_Z1 - 1, L.POD_FLOOR_Z1 + 1)
    body += ctx.add(ring_r, why="0.5 mm ring (r 3.1..4.2) touching only the bottom bearing's inner race: the hub's weight goes through the races", kind="thrust ring")

    # servo plate + skirt: servo hangs by its tabs, body in a deep box
    xs, ys = sd["span"] / 2 + WALL + 0.6, sd["W"] / 2 + SERVO_CLR + WALL
    body += ctx.add(Pos(sx, c[1], tab_z - PLATE_T) * Box(2 * xs, 2 * ys, PLATE_T, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="8 mm servo plate: tab screws into heat-set inserts, the servo's torque reaction goes into the ring", kind="plate")
    skirt_x1 = sx + sd["L"] / 2 + 7.0 + 0.5 + WALL                                  # cable boss pocket + wall
    skirt_x0 = sx - sd["L"] / 2 - SERVO_CLR / 2 - WALL
    body += ctx.add(Pos((skirt_x0 + skirt_x1) / 2, c[1], SKIRT_Z0) * Box(skirt_x1 - skirt_x0, sd["W"] + SERVO_CLR + 2 * WALL, tab_z - PLATE_T - SKIRT_Z0,
                    align=(Align.CENTER, Align.CENTER, Align.MIN)), why="deep skirt round the servo body: closed box that carries the plate to the ring", kind="skirt")
    wx, wy = sd["L"] + SERVO_CLR, sd["W"] + SERVO_CLR
    body -= ctx.cut(Pos(sx, c[1], SKIRT_Z0 + 2.0) * Box(wx, wy, tab_z - SKIRT_Z0, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="servo body cavity under the plate (2 mm floor)", kind="cavity")
    zs0 = tab_z - sd["tab_z"] + 2.5 - 0.3
    body -= ctx.cut(Pos(sx + wx / 2, c[1], zs0) * Box(7.0 + 0.6 + 0.4, 8.0 + 0.6, 8.0 + 0.6, align=(Align.MIN, Align.CENTER, Align.MIN)),
                    why="pocket for the servo's lead exit boss (catalog cable_boss_*, output end, 7 x 8 x 8)", kind="clearance")
    # lead slot through the inboard skirt wall, 45 deg roof (prints without support)
    xa, xb = sx + wx / 2 + 1.0, sx + wx / 2 + 7.0
    slot = Plane(origin=(0, c[1] - 3.0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)) * Polygon(
        (xa, zs0), (xb, zs0), (xb, zs0 + 5.0), ((xa + xb) / 2, zs0 + 8.0), (xa, zs0 + 5.0), align=None)
    body -= ctx.cut(extrude(slot, 12.0), why="servo lead leaves through the inboard skirt wall (to the fuselage)", kind="wire channel")

    # stop posts: the sector's ears (hub.py) meet them at -OVER and fold_max + OVER
    a0, a1 = L.sector_deg(p)
    for ang, why in ((a1 + EAR + OVER, "spread stop post (sector ear meets it 2.7 deg past 0)"),
                     (a0 - EAR - OVER - p.fold_max, "folded stop post (sector ear meets it 2.7 deg past fold_max)")):
        lo, hi = (ang, ang + 16.0) if ang > 180 else (ang - 16.0, ang)
        body += ctx.add(_wedge(c, lo, hi, POST_R[0], POST_R[1], POST_Z[0], POST_Z[1]), why=why, kind="stop")

    # screw lugs: pod to glove (from below, inboard flange) and cap to pod (heat-set inserts)
    ps = L.pod_screw_xy(p, 1)
    cavity = Pos(0, 0, RING_Z0 - 1) * extrude(_footprint(p, 0.0), z_top - RING_Z0 + 2)      # lugs never reach into the swept volume
    cs = L.cap_screw_xy(p, 1)
    for (x, y), tgt in zip(ps, ((165.0, 133.0), (ps[1][0], 133.0))):     # lug ends stay out of the swept cavity (y >= 139.5)
        body += ctx.add(_lug((x, y), tgt, LUG_R, FLANGE_Z0, z_top) - cavity, why="inboard flange lug: M3 from below into the glove's insert", kind="lug")
    for (x, y) in cs:
        body += ctx.add(_lug((x, y), (x, y + 3.0), LUG_R, INSERT_Z0, z_top) - cavity, why="lug for the cap screw's heat-set insert, tied into the ring", kind="lug")

    if s < 0:
        body = mirror(body, Plane.XZ)

    # interfaces (same group names as the mating parts)
    body -= iface.servo_mount(ctx, L.SWEEP_SERVO, L.sweep_servo_loc(p, s), f"sweep_servo_{n}", PLATE_T, kind="heatset")
    body -= iface.pin_hole(ctx, L.PIN, L.pin_loc(p, s, L.POD_FLOOR_Z1), f"pivot_{n}", depth=8.0, fit="press", through=False)
    for (x, y) in L.pod_screw_xy(p, s):
        body -= iface.bolt_pattern(ctx, f"pod_{n}", "M3", [(0, 0)], Location((x, y, FLANGE_Z0), (180, 0, 0)), "counterbore", z_top - FLANGE_Z0)
    for (x, y) in L.cap_screw_xy(p, s):
        body -= iface.bolt_pattern(ctx, f"cap_{n}", "M3", [(0, 0)], Location((x, y, z_top)), "heatset", z_top - INSERT_Z0)

    def keep(at):
        if abs(at[0] - sx) < sd["span"] / 2 + 1.2 and abs(abs(at[1]) - p.pivot_y) < sd["W"] / 2 + 1.0 and at[2] < tab_z + sd["top"] + 1.0:
            return "the servo's square body / tabs sit in this corner (0.3 mm clearance)"
        return None
    body, left = features.fillet_inside(ctx, body, 2.0, keep=keep)
    ctx.rigid("base", Location())
    ctx.rigid("servo", L.sweep_servo_loc(p, s))
    ctx.rigid("pin", L.pin_loc(p, s, L.POD_FLOOR_Z0))
    ctx.revolute("pivot", L.pivot_axis(p, s), range=(0, p.fold_max))
    return ctx.finish(body)


def _cyl_z(c, r, z0, z1):
    return Pos(c[0], c[1], z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
