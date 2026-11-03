"""Fuselage: rounded-box shell (L.fuse_stations) from the front bulkhead (x -120) to the boom socket (x 300), PETG, 3
perimeters, printed standing on its tail end (X up) so the bay walls are vertical and the socket funnel grows at < 15 deg.

Load path: glove lift enters through 4 M3 inserts in bosses hanging from the saddle (webbed to the side walls); the motor
thrust + torque enter the front bulkhead (8 mm, 4 M3 inserts) and spread into the shell; the tail's loads go through the
boom into the funnel-shaped socket (wall to wall at x 212, 3 mm stop wall, boom axis 8.2 bore). Material sits at the
bulkhead, the glove bosses and the socket; the middle is a thin shell, the top under the glove is open (the glove's
lower skin closes it) so the wires reach the glove directly.

Inside, front to back: bulkhead + wire hole, shelf (ESC / FC / RX), hatch opening above it, battery floor with two strap
slots, XT60 ahead of the pack, glove screw bosses at x 30, VTX floor at x 205, the socket. The boom is held POSITIVELY by
one M3: it passes down through the boom clamp, a 3.2 mm cross hole in the boom (55 mm from its front end) and into a
heat-set insert below the bore, so the boom can neither slide nor roll (tail incidence returns after a field swap).
"""
from build123d import *
import importlib.util, pathlib
from kerf import aero, iface
from kerf.features import fillet_inside, teardrop_hole

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

SKIN = 1.6                      # structural wall >= 1.6 (ENGINEERING s5)
BULK_T = 8.0                    # front bulkhead: 6.7 insert hole + 0.8 floor + margin
HATCH_X = (-112.0, -8.0)        # hatch opening in x, |y| < HATCH_HW
HATCH_HW = 27.0
LEDGE_W, LEDGE_T, LEDGE_UP = 3.0, 3.0, 0.0     # ledge the lid rests on: width, thickness, lid sits on it
CAVITY_X1 = 212.0               # cavity ends; boom socket stop wall 212..215
SEAT_Z = -17.0                  # flat seat for the boom clamp (boom top is -21)
CLAMP_X = 270.0                 # clamp screw + boom cross hole: 55 mm from the boom's front end (boom_x0 215), aft of the glove's trailing edge (x 260) so a hex key reaches the head
SEAT_X = (241.0, 283.0)         # seat span; the lip over the clamp tongue is in front of it
TONGUE_X0 = 233.5               # tongue tip
POCKET_Z = -19.4                # tongue pocket floor (boom top -21 + 1.5 mm wall)
REAR_SCREW = (-13.5, 0.0)       # hatch screw (x, y)
FRONT_INSERTS = [(15.0, 15.0), (-15.0, 15.0), (15.0, -15.0), (-15.0, -15.0)]   # (dy, dz) round the motor axis: stand-off flange
NOSE_SCREWS = [(22.0, -50.0), (-22.0, -50.0)]            # (y, z) at the bulkhead face, lugs of the nose cap


def _face(p, x, k=0.0, dz=0.0, r=None):
    hw, zb, zt, rr = L.fuse_section(p, x)
    rr = rr if r is None else r
    hw, zb, zt = hw - k, zb + k, zt - k + dz
    rad = max(1.0, min(rr - k, hw - 0.1, (zt - zb) / 2 - 0.1))
    return Plane(origin=(x, 0, (zb + zt) / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0)) * RectangleRounded(2 * hw, zt - zb, rad)


def _xs(p, x0, x1):
    return [x0] + [s[0] for s in L.fuse_stations(p) if x0 < s[0] < x1] + [x1]


def inset_solid(p, k, x0=-120.0, x1=215.0):
    """The fuselage envelope shrunk by k on every side, x0..x1 (lid, ledge, cavity are all cut from these, so they conform)."""
    return loft([_face(p, x, k) for x in _xs(p, x0, x1)], ruled=True)


def opening_prism(grow=0.0, z0=5.0):
    x0, x1 = HATCH_X
    return Pos((x0 + x1) / 2, 0, z0) * extrude(RectangleRounded(x1 - x0 + 2 * grow, 2 * HATCH_HW + 2 * grow, max(1.0, 4.0 + grow)), 40)


def build(ctx):
    p = ctx.p
    bz = p.boom_z
    pf = L.planform(p)
    wing = aero.wing_solid(pf, -p.pivot_y + 0.5, p.pivot_y - 0.5, stations=3)
    # 0.3 mm relief round the glove (offset() fails on the lofted solid): the solid shifted down, up and forward
    wing_off = Pos(0, 0, -0.3) * wing + Pos(0, 0, 0.3) * wing + Pos(-0.3, 0, 0) * wing

    # ---- outer: rounded stations, top corners squared from x 0 aft so the walls reach the glove's flat underside
    outer = loft([_face(p, s[0]) for s in L.fuse_stations(p)[1:]], ruled=True)
    sq = loft([_face(p, 0.0), _face(p, 40.0, r=3.0), _face(p, 60.0, r=3.0), _face(p, 200.0, r=3.0), _face(p, 215.0, r=3.0)], ruled=True)
    outer += ctx.add(sq & Pos(0, -100, -30) * Box(215, 200, 120, align=(Align.MIN, Align.MIN, Align.MIN)),
                     why="squared top corners under the glove: the side walls reach its flat underside (a rounded corner would leave a gap)", kind="saddle")
    # why: socket funnel: aft of the cavity only a cone round the boom is kept (weight), 12 deg flank prints without support
    cone = Pos(CAVITY_X1, 0, bz) * Rot(0, 90, 0) * Cone(26.0, 10.5, p.fuse_x1 - CAVITY_X1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    keep = Pos(-130, -100, -100) * Box(CAVITY_X1 + 130, 200, 200, align=(Align.MIN, Align.MIN, Align.MIN))
    body = outer & (keep + cone)     # why: funnel the aft end to a socket around the boom
    body -= ctx.cut(wing_off, why="saddle: the glove sits in the fuselage top, 0.3 mm clear", kind="saddle")

    # ---- cavity: chamfered at the bulkhead (bridge on the printer), open on top under the glove
    cav = loft([_face(p, -112.0, SKIN, dz=-4.0), _face(p, -108.0, SKIN)] +
               [_face(p, x, SKIN) for x in (-60.0, 60.0, 200.0, CAVITY_X1)], ruled=True)
    body -= ctx.cut(cav, why="hollow shell, 1.6 mm walls; 8 mm front bulkhead, 45 deg chamfer under its ceiling", kind="cavity")
    up = loft([_face(p, x, SKIN, dz=60.0) for x in (0.0, 60.0, 200.0, CAVITY_X1)], ruled=True)
    body -= ctx.cut(up, why="open top under the glove: wires go straight up into it, the VTX antenna stands through it", kind="wire hole")

    # ---- floor (top at BAY_FLOOR_Z), strap slots, VTX floor and pocket
    # belly pan: the layout's hull bottom rises to -64 at the bulkhead, above the pack's pad (z -66) and the XT60: a wedge
    # under x -113..0 gives the floor its 1.6 mm skin below the -66 floor top (ramps out into the hull by x -60)
    zf = L.BAY_FLOOR_Z
    body -= ctx.cut(Pos(-56.0, 0, zf + 10.0) * Box(112.0, 61.0, 20.0), why="floor top at the layout's -66 where the hull's own floor skin rises above it (toward the bulkhead)", kind="floor")
    pan = extrude(Plane(origin=(0, 31, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)) *
                  Polygon((-113, zf), (-113, zf - SKIN), (-60, p.fuse_bottom), (0, p.fuse_bottom), (0, zf), align=None), 62)
    body += ctx.add(pan, why="battery bay floor, top at -66 (floor 4 mm at the pack), strap slots cut through it", kind="floor")
    for sx in (p.bat_x - 20.0, p.bat_x + 20.0):
        for sy in (-30.0, 30.0):
            body -= ctx.cut(Pos(sx, sy, L.BAY_FLOOR_Z - 3.0) * Box(22.0, 2.6, 8.0), why="strap slot: the 20 mm Velcro strap goes through the floor", kind="slot")
    vz = L.item_locs(p)["vtx"].position.Z
    zv = vz - 0.2                                   # floor top 0.2 under the VTX
    body -= ctx.cut(Pos(200.0, 0, zv + 10.0) * Box(24.0, 34.0, 20.0), why="hull skin there rises above the VTX's seat height: cut to it", kind="floor")
    vf = Pos(200.0, 0, zv - 1.7) * Box(24.0, 34.0, 3.4)
    body += ctx.add(vf & (outer + Pos(200.0, 0, zv - 1.7) * Box(24.0, 34.0, 3.4)), why="VTX floor: tape seat at the VTX's height (a 2 mm belly bump under it: the hull rises here)", kind="floor")
    body -= ctx.cut(Pos(216.0, 0, vz - 0.5) * Box(11.0, 31.0, 14.0, align=(Align.CENTER, Align.CENTER, Align.MIN)) , why="VTX pocket: the 28 mm VTX runs 7 mm past the cavity end under the boom socket", kind="pocket")

    # ---- shelf (ESC / FC / RX), merges into the walls
    sh = Pos(-56.0, 0, L.SHELF_TOP - 1.0) * Box(112.0, 80.0, 2.0) - Pos(-102.0, 0, L.SHELF_TOP) * Box(26.0, 14.0, 6.0)   # window over the XT60
    body += ctx.add(sh & outer, why="electronics shelf (ESC, FC, RX) over the pack, 2.4 mm, tied to both walls", kind="shelf")

    # ---- front bulkhead: motor stand-off inserts, nose inserts, wire hole
    face = Location(Plane(origin=(p.nose_x1, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))          # local (u, v) = world (y, -z)
    body -= iface.bolt_pattern(ctx, "motor_mount", "M3", [(dy, -(p.motor_z + dz)) for dy, dz in FRONT_INSERTS], face,
                               kind="heatset", depth=BULK_T)
    body -= iface.bolt_pattern(ctx, "nose", "M3", [(y, -z) for y, z in NOSE_SCREWS], face, kind="heatset", depth=BULK_T)
    body -= ctx.cut(Pos(p.nose_x1 + BULK_T - 0.6, 0, -45.5) * Box(2.4, 12.0, 42.0), why="pocket: the XT60 (20.5 long) lies against the bulkhead", kind="pocket")
    body -= ctx.cut(Pos(p.nose_x1 + BULK_T / 2, 0, p.motor_z) * Rot(0, 90, 0) * Cylinder(8.0, BULK_T + 2), why="wire hole: motor phase leads and camera lead pass the bulkhead inside the stand-off", kind="wire hole")

    # ---- glove screws: boss + web per screw, hanging from the glove's lower surface
    for (x, y) in L.GLOVE_SCREWS:
        zs = (wing & Pos(x, y, -30) * Box(0.4, 0.4, 60)).bounding_box().min.Z
        boss = Pos(x, y, zs - 7.0) * Cylinder(5.0, 18.0)
        hwi = L.fuse_section(p, x)[0] - SKIN
        ya, yb = sorted((y, y + (hwi - abs(y) + 0.5) * (1 if y > 0 else -1)))
        web = Pos(x, (ya + yb) / 2, zs - 7.0) * Box(3.0, yb - ya, 18.0)
        blk = ((boss + web) - wing) & outer      # trimmed by the glove itself: the boss top touches it
        body += ctx.add(blk, why="glove screw boss with web to the side wall: lift of the glove enters the shell here", kind="boss")
        body -= iface.bolt_pattern(ctx, "glove", "M3", [(x, y)], Location((0, 0, zs)), kind="heatset", depth=10.0, teardrop="auto")

    # ---- hatch: opening, ledges, front lip + tongue slot, rear insert
    body -= ctx.cut(opening_prism(0.0), why="hatch opening above the shelf: XT60, ESC, FC, RX reached from above", kind="opening")
    ring = (opening_prism(0, -10) - opening_prism(-LEDGE_W, -10) - Pos(-13.0, 0, 0) * Box(12.0, 13.0, 200)) & Pos(HATCH_X[0] + 4.0, -100, -100) * Box(300, 200, 400, align=(Align.MIN, Align.MIN, Align.MIN))
    ledge = (ring & inset_solid(p, SKIN + LEDGE_UP)) - inset_solid(p, SKIN + LEDGE_UP + LEDGE_T)
    body += ctx.add(ledge, why="ledge the hatch lid rests on (side edges and rear)", kind="ledge")
    slot = ((inset_solid(p, SKIN) - inset_solid(p, SKIN + 2.4)) &
            Pos(-118.5, -19, -5) * Box(6.5, 38, 100, align=(Align.MIN, Align.MIN, Align.MIN)))
    body -= ctx.cut(slot, why="slot under the front lip: the hatch tongue slides in", kind="slot")
    rx, ry = REAR_SCREW
    zu = L.fuse_section(p, rx)[2] - SKIN - LEDGE_UP - 1.6          # boss top: under the lid's 1.6 mm pad
    rib = Pos(-6.75, 0, zu - 6.0) * Box(2.5, 2 * (L.fuse_section(p, -7)[0] - SKIN) + 1.0, 12.0)
    boss = Pos(-11.75, 0, zu - 6.0) * Box(12.5, 9.0, 12.0)
    body += ctx.add((rib & outer) + (boss & inset_solid(p, SKIN + LEDGE_UP + 1.6)), why="rear hatch screw boss on a cross rib", kind="boss")
    body -= iface.bolt_pattern(ctx, "hatch", "M3", [(rx, ry)], Location(Plane(origin=(0, 0, zu), x_dir=(1, 0, 0), z_dir=(0, 0, 1))),
                               kind="heatset", depth=9.0, teardrop="auto")

    # ---- boom socket: bore, stop wall, lead hole, clamp seat, tongue pocket, positive-lock insert
    bl = L.boom_loc(p)
    body -= ctx.cut(bl * Pos(0, 0, 0) * Cylinder((p.boom_od + 0.2) / 2, p.fuse_x1 - p.boom_x0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="boom bore, OD + 0.2 dry slip fit; the 3 mm wall at x 212..215 is the end stop", kind="bore")
    body -= ctx.cut(Pos(CAVITY_X1 + 2.0, 0, bz) * Rot(0, 90, 0) * Cylinder(2.75, 8.0), why="tail servo leads run from the bay into the boom tube", kind="wire hole")
    body -= ctx.cut(Pos(SEAT_X[0], -40, SEAT_Z) * Box(SEAT_X[1] - SEAT_X[0], 80, 60, align=(Align.MIN, Align.MIN, Align.MIN)),
                    why="flat seat for the boom clamp, 4 mm over the boom", kind="seat")
    body -= ctx.cut(Pos(CLAMP_X, 0, bz) * Cylinder(5.0, SEAT_Z - bz + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="pocket for the clamp's rib down to the boom", kind="pocket")
    body -= ctx.cut(Pos(TONGUE_X0 - 0.5, -7.0, POCKET_Z) * Box(SEAT_X[0] + 3.0 - (TONGUE_X0 - 0.5), 14.0, SEAT_Z - POCKET_Z, align=(Align.MIN, Align.MIN, Align.MIN)),
                    why="pocket under the lip: the clamp's tongue holds its front end down", kind="pocket")
    body -= iface.bolt_pattern(ctx, "boom_clamp", "M3", [(0, 0)], Location((CLAMP_X, 0, bz - (p.boom_od + 0.2) / 2)), kind="heatset", depth=8.0, teardrop="auto")

    # Tail leads leave beside the VTX, then run externally under the boom clear of its transverse clamp screw.
    lead_exit = Plane(origin=(190.0, 40.0, -38.0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    body -= ctx.cut(lead_exit * teardrop_hole(9.0, 24.0, up_deg=iface.print_up_deg(ctx, Location(lead_exit)) or 0.0),
                    why="tail servo plugs exit to the boom exterior; 45-degree roof follows the declared print orientation", kind="wire hole")

    # ---- joints
    for k in ("nose", "motor_mount", "glove", "hatch", "boom_clamp", "tail"):
        ctx.rigid(k, Location())
    ctx.rigid("boom", bl)
    for k, loc in L.item_locs(p).items():
        ctx.rigid(k, loc)

    def keep_sharp(at):
        if abs(at[0] - p.nose_x1) < 12 and abs(at[1]) < 22:
            return "motor stand-off flange sits square on the bulkhead"
        if at[2] > 0 and HATCH_X[0] - 1 < at[0] < HATCH_X[1] + 1 and abs(at[1]) < HATCH_HW + 1:
            return "the hatch lid's edge sits square in the opening"
        if abs(at[2] - L.BAY_FLOOR_Z) < 2 and abs(at[1]) > 29:
            return "strap slot edge: the Velcro strap passes over it"
        return None
    body, left = fillet_inside(ctx, body, 1.0, keep=keep_sharp)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(body)
