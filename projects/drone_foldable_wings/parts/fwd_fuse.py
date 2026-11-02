"""Forward fuselage: nose face for the motor mount, battery bay, electronics shelf, top hatch opening, and the aft
bulkhead that bolts to the aft fuselage. PLA, 4 perimeters (1.7 mm skin = solid walls), 15 % infill.

Printed standing on its NOSE face (project.yaml print_rot [0, -90, 0] turns +X up): the nose plate is the first
layers, the tray and the shelf are vertical plates growing out of it, the aft bulkhead is a frame whose inside is a
43 deg funnel (no ceiling), the hatch-screw beam has a 45 deg front.

Inside, front to back (DESIGN.md "Front"):
- nose plate (3.4 mm) with four 7.5 mm bosses for the motor mount's M3 heat-set inserts, outside the motor bell;
  the motor's phase leads come in through the hole above the motor axis (half under the bell's base edge);
- battery tray: the 4S pack sits on a 1.7 mm tray against the nose bosses, raised so its front corners clear the
  nose taper (the height is worked out from the pack size and bat_x); a 20 mm strap goes under the tray through two
  slots beside the pack, over its top and closes in the shelf window above it; the space under the tray is closed;
- shelf 2 mm above the pack: a window over the strap (closing it by hand), then ESC (left) and FC (right) side by
  side, the receiver on the front part of the shelf (its antenna leaves through the right inlet slot); the pack goes
  in through the hatch aft of the shelf and slides forward under it;
- XT60 on the pack's lead, lying on the tray just aft of the shelf, open to the hatch and with a clear plug-in path
  aft along the tray;
- cooling: air in through two slots in the nose taper's sides just above the shelf (the taper faces the prop wash),
  along the shelf past the ESC, out through two side slots behind it;
- aft bulkhead: 4 mm frame at fuse_joint_x, four M3 clearance holes at L.JOINT_BOLTS, heads inside in spot faces
  on the funnel; its 35 x 37 mm opening is the wire pass-through to the aft fuselage; the hatch-screw beam has
  notches so a straight hex key reaches the upper two along the screw axis.
"""
import math

from build123d import *
from kerf import iface
from kerf.features import fillet_inside

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

ESC = "drone.escs.skywalker_40a_v2"
FC = "drone.fcs.f405_wmo"
RX = "electronics.receivers.elrs_nano"
XT60 = "drone.connectors.XT60"

SKIN = 1.7            # 4 perimeters of a 0.42 mm line: solid skin
NOSE_T = 3.4          # nose plate between the bosses
BOSS_L = 7.5          # M3 heat-set: 6.7 mm hole + 0.8 mm floor (iface.hole)
BOSS_R = 5.0          # 4.0 mm insert hole + 3 mm wall (ENGINEERING s5 >= 2.4, s7 1.5 d)
MOUNT_BOLT = 15.0     # motor-mount M3 at (+-15, +-15) from the motor axis: r 21.2, head clear of the 35 mm bell
LEAD_UP = 17.5        # motor lead hole centre above the motor axis (half under the bell's base edge)
LEAD_D = 8.0
BULK_T = 4.0          # aft bulkhead plate = grip of the fuselage-joint M3
FUNNEL = 12.0         # bulkhead frame width at the aft face
FUNNEL_L = FUNNEL * 1.2   # reached over this length: 40 deg from the print axis, corners included
SPOT_R = 3.3          # spot face for the M3 head (5.5 mm) + key
TRAY_T = 1.7
SHELF_T = 2.0
STRAP_GAP = 2.0       # pack top to shelf: the strap's top run
CLEAR = 0.5
STRAP_W = 20.0        # ENGINEERING s9: slots for a 20 mm strap
HATCH_X = (-150.0, 40.0)   # top opening: the flat top only (no slope in the hatch), up to the beam
HATCH_HW = 23.0            # the 39 mm pack goes through; the key rays at y +-22 leave through it
HATCH_CUT_Z = -14.0
BEAM_X = (20.0, 44.0)      # hatch-screw beam under the opening's aft end (45 deg front)
BEAM_Z = -19.5
HATCH_BOLTS_X = 34.0
LEDGE_T = 2.0
VENT_L, VENT_H = 14.0, 6.0


def sec(p, x, shrink=0.0, at=None):
    """Face of the fuselage section at x (L.fuse_section), shrunk by `shrink`, placed at `at` (default x)."""
    hw, zb, zt, r = L.fuse_section(p, x)
    w, h = 2 * (hw - shrink), (zt - zb) - 2 * shrink
    rr = max(1.0, min(r - shrink, w / 2 - 0.5, h / 2 - 0.5))
    pl = Plane(origin=(x if at is None else at, 0, (zb + zt) / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    return pl * RectangleRounded(w, h, rr)


def inner(p, x):
    hw, zb, zt, r = L.fuse_section(p, x)
    return hw - SKIN, zb + SKIN, zt - SKIN, max(r - SKIN, 1.0)


def x_nose(p):
    return p.fuse_x0


def x_bulk(p):
    """Inner face of the aft bulkhead (the fuselage-joint screw heads seat here)."""
    return p.fuse_joint_x - BULK_T


def outer(p):
    st = L.fuse_stations(p)
    body = loft([sec(p, st[0][0]), sec(p, st[1][0]), sec(p, p.fuse_joint_x)], ruled=True)
    ends = body.edges().filter_by_position(Axis.X, p.fuse_x0 - 0.01, p.fuse_x0 + 0.01) + \
        body.edges().filter_by_position(Axis.X, p.fuse_joint_x - 0.01, p.fuse_joint_x + 0.01)
    return chamfer(ends, 0.6)


def cavity(p):
    """Inside of the skin from the nose plate to where the bulkhead funnel starts."""
    st = L.fuse_stations(p)
    x0 = p.fuse_x0 + NOSE_T
    return loft([sec(p, x0, SKIN), sec(p, st[1][0], SKIN), sec(p, x_bulk(p) - FUNNEL_L, SKIN)], ruled=True)


def funnel(p):
    """Opening through the aft bulkhead: the cavity narrowing 12 mm at 40 deg, then straight through the plate."""
    xf, xb, xj = x_bulk(p) - FUNNEL_L, x_bulk(p), p.fuse_joint_x
    return loft([sec(p, xf, SKIN), sec(p, xb, SKIN + FUNNEL), sec(p, xj, SKIN + FUNNEL, at=xj + 1.0)], ruled=True)


def hatch_box(p):
    return Pos(HATCH_X[0], 0, HATCH_CUT_Z) * Box(HATCH_X[1] - HATCH_X[0], 2 * HATCH_HW, 30,
                                                  align=(Align.MIN, Align.CENTER, Align.MIN))


def hatch_solid(p):
    """The top skin over the opening (parts/hatch.py is this, trimmed for a 0.2 mm gap all round)."""
    return (outer(p) & hatch_box(p)) - cavity(p)


def hatch_bolts(p):
    """(x, y) of the hatch's two M3 at its aft end (vertical, into the beam's inserts)."""
    return [(HATCH_BOLTS_X, -10.0), (HATCH_BOLTS_X, 10.0)]


def battery_floor(p, bl, bw):
    """Lowest pack bottom z that clears the inside (with CLEAR) at the pack's front end, its narrowest section."""
    hw, zb, zt, r = inner(p, p.bat_x - bl / 2)
    cy, cz = hw - r, zb + r
    z = zb + CLEAR
    if bw / 2 > cy:
        z = max(z, cz - math.sqrt(max((r - CLEAR) ** 2 - (bw / 2 - cy) ** 2, 0.0)))
    return z


def bay(p, cat):
    """Positions of everything in the bay (x ranges, y centres, z of the tray / shelf tops)."""
    def dims(path):
        e = cat.get(path)
        return cat.num(e, "length"), cat.num(e, "width"), cat.num(e, "height")
    bl, bw, bh = dims(L.BATTERY)
    el, ew, eh = dims(ESC)
    fl, fw, fh = dims(FC)
    rl, rw, rh = dims(RX)
    xl, xw, xh = dims(XT60)
    b = {"bat": (bl, bw, bh), "esc_d": (el, ew, eh), "fc_d": (fl, fw, fh), "rx_d": (rl, rw, rh), "xt_d": (xl, xw, xh)}
    b["tray"] = battery_floor(p, bl, bw)                        # tray top = pack bottom
    b["shelf0"] = b["tray"] + bh + STRAP_GAP                   # shelf underside
    b["shelf"] = b["shelf0"] + SHELF_T                         # shelf top
    b["win"] = (p.bat_x - STRAP_W / 2 - 3, p.bat_x + STRAP_W / 2 + 3, bw / 2 + 1.5)   # strap window x0, x1, half width
    # ESC (left) and FC (right) side by side behind the window; the pair centred 3 mm left of the centreline so the
    # FC stays 2 mm under the hatch skin and the ESC 1.8 mm off the left wall at their tops
    x0 = b["win"][1] + 1.0
    y_mid, gap = -3.0, 1.0
    y_l = y_mid - (ew + fw + gap) / 2
    b["esc"] = (x0, x0 + el, y_l + ew / 2)
    b["fc"] = (x0, x0 + fl, y_l + ew + gap + fw / 2)
    b["shelf_x1"] = max(b["esc"][1], b["fc"][1]) + 3.0
    b["rx"] = (p.fuse_x0 + BOSS_L + 2.0, p.fuse_x0 + BOSS_L + 2.0 + rl, 12.0)
    b["xt"] = (b["shelf_x1"] + 3.0, b["shelf_x1"] + 3.0 + xl, 0.0)
    # the tray stops short of where a straight 2.5 mm key on the lower joint screws ends (x ~0.5), so its handle end
    # is under the open hatch, not shut in under the tray
    b["tray_x1"] = x_bulk(p) - 64.0
    return b


def build(ctx):
    p = ctx.p
    b = bay(p, ctx.cat)
    bl, bw, bh = b["bat"]
    cav = cavity(p)
    out = outer(p)
    body = out - ctx.cut(cav, why="battery and electronics bay", kind="cavity")
    body = body - ctx.cut(funnel(p), why="aft bulkhead frame: 40 deg funnel (prints without a ceiling), wire pass-through",
                          kind="bulkhead")
    hs = hatch_solid(p)
    shell = out - cav
    body = body - ctx.cut(hatch_box(p), why="hatch opening: battery, XT60 and the shelf electronics from above", kind="hatch")

    # nose: insert bosses for the motor mount (outside the bell, so a key reaches the mount screws past the motor)
    zc = p.motor_z
    for sy in (-1, 1):
        for sz in (-1, 1):
            boss = Pos(p.fuse_x0 + BOSS_L / 2, sy * MOUNT_BOLT, zc + sz * MOUNT_BOLT) * Rot(0, 90, 0) * Cylinder(BOSS_R, BOSS_L)
            body = body + ctx.add(boss & out, why="motor-mount heat-set insert boss", kind="boss")

    # battery tray, strap slots beside the pack
    tray = Pos(p.fuse_x0, 0, b["tray"] - TRAY_T) * Box(b["tray_x1"] - p.fuse_x0, 200, TRAY_T, align=(Align.MIN, Align.CENTER, Align.MIN))
    body = body + ctx.add(tray & cav, why="battery tray: the pack's front corners clear the nose taper", kind="tray")
    for s in (-1, 1):
        slot = Pos(p.bat_x, s * (bw / 2 + 1.0 + 1.75), b["tray"]) * Box(STRAP_W + 2, 3.5, 3 * TRAY_T)
        body = body - ctx.cut(slot, why="20 mm battery strap slot", kind="strap slot")

    # shelf over the pack: window over the strap (its aft end a 45 deg V, so the shelf prints without a bridge)
    shelf = Pos(p.fuse_x0, 0, b["shelf0"]) * Box(b["shelf_x1"] - p.fuse_x0, 200, SHELF_T, align=(Align.MIN, Align.CENTER, Align.MIN))
    wx0, wx1, whw = b["win"]
    win = Pos(0, 0, b["shelf0"] - 1) * extrude(Polygon((wx0, -whw), (wx1, -whw), (wx1 + whw, 0), (wx1, whw), (wx0, whw),
                                                        align=None), SHELF_T + 2)
    body = body + ctx.add((shelf & cav) - win, why="electronics shelf over the pack; window to close the strap", kind="shelf")

    # hatch ledges (skipped over the FC, which stands tall there) and the screw beam at the opening's aft end
    fx0, fx1, _ = b["fc"]
    # why: the front segment starts 3 mm under the nose skin, so it merges into it (no edge-to-edge seam)
    for xa, xb in ((HATCH_X[0] - 3.0, fx0 - 3.0), (fx1 + 3.0, -20.0)):
        for s in (-1, 1):
            led = Pos(xa, s * 19.0, HATCH_CUT_Z + 0.3) * Box(xb - xa, 20, 20, align=(Align.MIN, Align.MIN if s > 0 else Align.MAX, Align.MIN))
            body = body + ctx.add((led & out) - hs, why="ledge the hatch edge rests on", kind="ledge")
    zi = p.fuse_top - SKIN
    prof = Polygon((BEAM_X[0], 3), (BEAM_X[1], 3), (BEAM_X[1], BEAM_Z - zi), (BEAM_X[0] + zi - BEAM_Z, BEAM_Z - zi),
                   (BEAM_X[0], 0), align=None)
    beam = Pos(0, -40, zi) * extrude(Plane.XZ * prof, 80)      # Plane.XZ: local (u, v) = world (x, z); extrudes to +y
    keys = None
    for (y, z) in L.JOINT_BOLTS:
        k = Pos((x_bulk(p) - 2) / 2, y, z) * Rot(0, 90, 0) * Cylinder(2.2, x_bulk(p) + 2)
        keys = k if keys is None else keys + k
    body = body + ctx.add(((beam & out) - hs) - keys,
                          why="hatch-screw beam (inserts), notched for the hex key to the upper joint screws", kind="beam")

    # aft bulkhead: spot faces for the joint screw heads on the funnel
    for (y, z) in L.JOINT_BOLTS:
        spot = Pos(x_bulk(p) - 8, y, z) * Rot(0, 90, 0) * Cylinder(SPOT_R, 16)
        body = body - ctx.cut(spot, why="spot face: fuselage-joint screw head seats on the bulkhead", kind="spot face")

    # motor phase leads in through the nose plate
    body = body - ctx.cut(Pos(p.fuse_x0 + NOSE_T / 2, 0, zc + LEAD_UP) * Rot(0, 90, 0) * Cylinder(LEAD_D / 2, NOSE_T + 2),
                          why="motor phase leads into the bay", kind="wire hole")
    # cooling: inlets in the nose taper's sides just above the shelf, outlets behind the ESC
    z0 = b["shelf"] + 2.5          # clear of the shelf-to-wall fillet
    ex1 = b["esc"][1]
    for s in (-1, 1):
        for xa, what in ((p.fuse_x0 + 11.0, "air inlet (taper faces the prop wash); receiver antenna out"),
                         (ex1 - 4.0, "air outlet behind the ESC")):
            # round-ended slot (no sharp inner corners; the upper end prints as an arch), through the skin only
            v = Pos(xa + VENT_L / 2, s * 20.0, z0 + VENT_H / 2) * extrude(Plane.XZ * SlotOverall(VENT_L, VENT_H), 20, both=True)
            body = body - ctx.cut(v & shell, why=what, kind="vent")

    # fasteners: motor mount inserts in the nose face, fuselage-joint clearance holes, hatch inserts in the beam
    nose = Location(Plane(origin=(p.fuse_x0, 0, zc), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    pts = [(sy * MOUNT_BOLT, sz * MOUNT_BOLT) for sy in (-1, 1) for sz in (-1, 1)]
    body = body - iface.bolt_pattern(ctx, "motor_mount", "M3", pts, nose, kind="heatset", depth=BOSS_L)
    bulk = Location(Plane(origin=(x_bulk(p), 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))     # local (u, v) = world (y, -z)
    body = body - iface.bolt_pattern(ctx, "fuse_joint", "M3", [(y, -z) for (y, z) in L.JOINT_BOLTS], bulk,
                                     kind="clearance", depth=BULK_T)
    top = Location(Plane(origin=(0, 0, zi), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))
    body = body - iface.bolt_pattern(ctx, "hatch", "M3", hatch_bolts(p), top, kind="heatset", depth=zi - BEAM_Z,
                                     teardrop="auto")

    def keep(at):
        if abs(at[0] - (p.fuse_x0 + BOSS_L)) < 0.3:
            return "boss end face: the pack's front sits 0.5 mm from it (a cove would reach into the pack); not a load path"
        if abs(at[0] - b["tray_x1"]) < 0.3:
            return "free aft end of the battery tray (1.7 mm edge); the tray's load goes into the side walls along its length"
        if abs(at[0] - (p.fuse_x0 + NOSE_T)) < 0.3 and abs(at[1]) < LEAD_D and abs(at[2] - b["shelf"]) < 0.3:
            return "shelf top at the nose plate, 0.5 mm under the motor lead hole: a cove would narrow the hole; shelf carries < 0.1 kg"
        return None
    body, failed = fillet_inside(ctx, body, r=1.5, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]

    for k in ("aft", "hatch", "motor_mount"):
        ctx.rigid(k, Location())
    ctx.rigid("battery", Location((p.bat_x, 0, b["tray"])))
    ctx.rigid("xt60", Location(((b["xt"][0] + b["xt"][1]) / 2, b["xt"][2], b["tray"])))
    ctx.rigid("esc", Location(((b["esc"][0] + b["esc"][1]) / 2, b["esc"][2], b["shelf"])))
    ctx.rigid("fc", Location(((b["fc"][0] + b["fc"][1]) / 2, b["fc"][2], b["shelf"])))
    ctx.rigid("rx", Location(((b["rx"][0] + b["rx"][1]) / 2, b["rx"][2], b["shelf"])))
    if p.bat_x - bl / 2 < p.fuse_x0 + BOSS_L + CLEAR:
        ctx.notes.append(f"bat_x {p.bat_x} puts the pack into the nose insert bosses: it must be >= "
                         f"{p.fuse_x0 + BOSS_L + CLEAR + bl / 2:.1f}")
    return ctx.finish(body)
