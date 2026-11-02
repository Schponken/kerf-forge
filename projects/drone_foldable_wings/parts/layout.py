"""Shared numbers for the hawk-fold drone, computed once from params + catalog so every part agrees (DESIGN.md).

Frame (every part is modelled in it): X aft from the wing root leading edge at the centreline, Y to the right wing,
Z up; the wing's root chord plane is z = 0. Printed parts sit at their home placement with rigid joints at the
origin, except the moving ones: each wing half (hub + two skin segments + aileron) turns about its sweep pivot, the
ailerons, elevator and rudder about their hinge lines, the pinions with their servos.

Sweep pivot: a vertical 4 mm stainless pin at (pivot_x, +-pivot_y), just ahead of the root trailing-edge corner, so
the whole panel swings OUT and back (the root never crosses the centreline). The pin is pressed into the pivot deck
(lower plate, inside the aft fuselage) and the spine (upper plate, above the wing root) and turns freely in the
hub's boss between them; stack: deck | 0.5 gap | boss | 0.5 gap | spine arm = the 50 mm stocked pin.
"""
import math

from kerf import aero

AIRFOIL = "mh45"              # near-zero Cm0: sweeping the wing changes the trim only through the AC / CG shift
TAIL_AIRFOIL = "naca0009"
MAIN_TUBE = "rods.cf_tube_8x6"
REAR_TUBE = "rods.cf_tube_6x4"
BOOM_TUBE = "rods.cf_tube_8x6"
PIN = "rods.ss_rod_4"
SWEEP_SERVO = "servos.MG996R"   # MG90S was too weak: back-driven at partial sweep under g (DESIGN.md)
SWEEP_HORN = "servo_horns.aluminum_25T"
SURF_SERVO = "servos.KST_X08_Plus"
MOTOR = "drone.motors.2806_5_1300kv_7in"
BATTERY = "drone.batteries.4S_1500"
TE_MIN = 1.0                  # printed trailing edge: two perimeters + margin

GEAR_M, Z_PINION, Z_SECTOR, GEAR_W = 2.0, 13, 21, 10.0     # 1.615:1 servo -> wing: 70 deg fold = 113 deg of the 120 deg standard travel
PIN_L = 50.0                  # stocked 4 mm rod length (catalog rods.ss_rod_4 lengths)
PLATE_T = 6.0                 # deck and spine arm thickness at the pin
GAP = 0.5                     # axial running clearance each end of the boss (ENGINEERING s8)
BOSS_TOP = 13.0               # boss top face z (above the root trailing edge, under the spine arm)
BOSS_R = 10.0                 # boss outer radius (4.35 free bore + 7.8 wall)


def planform(p):
    return aero.Planform(span=p.wing_span, root_chord=p.wing_root_chord, tip_chord=p.wing_tip_chord,
                         sweep_le_deg=p.wing_sweep_le_deg, twist_tip_deg=p.wing_twist_tip_deg, root_airfoil=AIRFOIL,
                         te_min=TE_MIN)


def tail_planform(p):
    return aero.Planform(span=p.htail_span, root_chord=p.htail_root_chord, tip_chord=p.htail_tip_chord,
                         sweep_le_deg=p.htail_sweep_le_deg, root_airfoil=TAIL_AIRFOIL, x_le0=p.htail_x_le0,
                         z0=p.htail_z0, te_min=0.8)


def layout(p, cat):
    pf = planform(p)
    g = pf.geometry()
    semi = p.wing_span / 2
    out = {"wing_airfoil": AIRFOIL, "wing_x_le0": 0.0, "wing_z0": 0.0, "wing_te_min": TE_MIN, "semi": semi,
           "htail_airfoil": TAIL_AIRFOIL, "mac": g["mac_mm"], "area_dm2": g["area_dm2"]}
    # pivot: pivot_back mm ahead of the root trailing edge at the panel root station
    x_te = pf.x_le(p.pivot_y) + pf.chord(p.pivot_y)
    out["pivot_x"] = x_te - p.pivot_back
    out["boss_z1"] = BOSS_TOP
    out["boss_z0"] = BOSS_TOP - (PIN_L - 2 * PLATE_T - 2 * GAP)
    out["spine_arm_z0"] = BOSS_TOP + GAP
    out["deck_z1"] = out["boss_z0"] - GAP
    out["deck_z0"] = out["deck_z1"] - PLATE_T
    out["boss_r"] = BOSS_R
    # gears: sector on the boss, pinion on the servo horn straight ahead of the pivot
    cd = GEAR_M * (Z_PINION + Z_SECTOR) / 2
    out.update({"gear_cd": cd, "pinion_x": out["pivot_x"] - cd, "sector_z0": SECTOR_Z0, "sector_z1": SECTOR_Z0 + GEAR_W,
                "sector_ro": GEAR_M * (Z_SECTOR + 2) / 2, "pinion_ro": GEAR_M * (Z_PINION + 2) / 2})
    # spar tubes: straight, through the section's thickness centre at the same chord fraction at both ends; they
    # start inside the hub (bonded in its sockets) and run out through both skin segments
    for k, frac, y1 in (("main", p.spar_main_frac, p.spar_main_y1), ("rear", p.spar_rear_frac, p.spar_rear_y1)):
        a, b = aero.spar_line(pf, frac, frac, p.spar_y0, y1)
        out.update({f"{k}_x0": float(a[0]), f"{k}_z0": float(a[2]), f"{k}_x1": float(b[0]), f"{k}_z1": float(b[2])})
        out[f"{k}_len"] = math.dist((a[0], p.spar_y0, a[2]), (b[0], y1, b[2]))
    out["main_od"] = cat.num(cat.get(MAIN_TUBE), "od", "od_mm")
    out["rear_od"] = cat.num(cat.get(REAR_TUBE), "od", "od_mm")
    out["boom_od"] = cat.num(cat.get(BOOM_TUBE), "od", "od_mm")
    out["boom_len"] = p.boom_x1 - p.boom_x0
    # tail: neutral point of the horizontal tail alone (its quarter MAC) for the DESIGN.md tail-volume figure
    tg = tail_planform(p).geometry()
    out["htail_x_ac"] = tg["x_np_mm"]
    out["htail_area_dm2"] = tg["area_dm2"]
    return out


def tube_line(p, which, side):
    """(start, end) world points of a spar tube on one side (+1 right, -1 left), home pose."""
    y1 = p.spar_main_y1 if which == "main" else p.spar_rear_y1
    return ((getattr(p, f"{which}_x0"), side * p.spar_y0, getattr(p, f"{which}_z0")),
            (getattr(p, f"{which}_x1"), side * y1, getattr(p, f"{which}_z1")))


def pivot(p, side):
    """Pivot axis point on the deck's top face (x, y, z), side +1 right / -1 left; the axis is +Z."""
    return (p.pivot_x, side * p.pivot_y, p.deck_z1)


# ---------------------------------------------------------------- joint frames shared by parent and child parts
PINION_Z0 = -24.0             # pinion bottom = horn face (the horn's outer face carries the pinion)
PINION_W = 11.0               # pinion is wider than the sector so the mesh keeps full width over the backlash
SECTOR_Z0 = -23.5             # sector band z0..z0+GEAR_W on the hub boss (top 1.5 mm under the spine cover)


def pivot_axis(p, side):
    """Sweep pivot axis (pin axis) for side +1 right / -1 left: origin on the deck top, direction chosen so a
    POSITIVE joint angle sweeps the panel aft (right: clockwise seen from above)."""
    from build123d import Axis
    return Axis((p.pivot_x, side * p.pivot_y, p.deck_z1), (0, 0, -side))


def horn_face_above_tabs(cat_servo=SWEEP_SERVO, horn=SWEEP_HORN):
    """Height of the horn's outer face above the servo's tab underside (servo top + spline + horn hub above it)."""
    from kerf import iface
    d, h = iface.servo_dims(cat_servo), iface.horn_dims(horn)
    return d["top"] + d["shaft_h"] - h["engage"] + max(h["hub_total"] - h["t"], 0.0) + h["t"]


def sweep_servo_loc(p, side):
    """Servo proxy 'tabs' frame (tab underside centre): output vertical (+Z), output end aft (+X) on the pinion axis."""
    from build123d import Location, Plane
    from kerf import iface
    d = iface.servo_dims(SWEEP_SERVO)
    z = PINION_Z0 - horn_face_above_tabs()
    return Location(Plane(origin=(p.pinion_x - d["out_x"], side * p.pivot_y, z), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))


def gears():
    """(pinion, sector gear) from kerf.drives.spur_pair at the origin, z 0..width: the pinion goes on the horn at
    (pinion_x, +-pivot_y, PINION_Z0) and the sector gear's centre on the pivot axis (+X of the pinion, the pair's own
    convention) at SECTOR_Z0, so the teeth are phased to mesh at home."""
    from kerf import drives
    g1, g2, _ = drives.spur_pair(GEAR_M, Z_PINION, Z_SECTOR, PINION_W)
    _, s2, _ = drives.spur_pair(GEAR_M, Z_PINION, Z_SECTOR, GEAR_W)
    return g1, s2


def boom_loc(p):
    """Boom rod 'end_a' frame: front end of the tube on the boom axis, +Z aft."""
    from build123d import Location, Plane
    return Location(Plane(origin=(p.boom_x0, 0, p.boom_z), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))


def tube_loc(p, which, side):
    from build123d import Location, Plane
    a, b = tube_line(p, which, side)
    d = tuple(bb - aa for aa, bb in zip(a, b))
    return Location(Plane(origin=a, x_dir=(1, 0, 0) if abs(d[0]) < 0.9 * math.hypot(*d) else (0, 0, 1), z_dir=d))


# ---------------------------------------------------------------- fuselage outline (both fuselage parts loft these)
def fuse_stations(p):
    """Outer fuselage sections, front to back: (x, half width, z bottom, z top, corner radius). Rounded rectangles,
    lofted straight between stations. fwd_fuse uses x <= fuse_joint_x, aft_fuse x >= fuse_joint_x; the joint section
    is shared, so the two parts meet flush."""
    hw, hw2, zb, zt = p.fuse_hw, p.fuse_hw_wing, p.fuse_bottom, p.fuse_top
    zc = p.boom_z
    return [(p.fuse_x0, 22.0, p.motor_z - 22.0, p.motor_z + 22.0, 10.0),
            (p.fuse_x0 + 45.0, hw, zb, zt, 12.0),
            (p.fuse_joint_x, hw, zb, zt, 12.0),
            (140.0, hw2, zb, zt, 12.0),
            (218.0, hw2, zb, zt, 12.0),
            (p.fuse_x1, 10.0, zc - 10.0, zc + 10.0, 9.0)]


def fuse_section(p, x):
    """Interpolated (half width, z bottom, z top, corner radius) of the outer fuselage at x."""
    st = fuse_stations(p)
    for a, b in zip(st[:-1], st[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(a[i] + t * (b[i] - a[i]) for i in range(1, 5))
    raise ValueError(f"x {x} outside the fuselage ({st[0][0]}..{st[-1][0]})")


def section_face(p, x):
    """build123d Face of the outer section at x (in the plane x = const)."""
    from build123d import Plane, RectangleRounded, Location
    hw, zb, zt, r = fuse_section(p, x)
    return Plane.YZ.offset(x) * RectangleRounded(2 * hw, zt - zb, min(r, hw - 0.1, (zt - zb) / 2 - 0.1)).moved(
        Location((0, (zb + zt) / 2)))


JOINT_BOLTS = [(-22.0, -20.0), (22.0, -20.0), (-22.0, -64.0), (22.0, -64.0)]   # (y, z) of the fuselage-joint M3s


def lead_root(p, side):
    """Aileron servo lead channel point on the hub / inner-segment interface face (y = hub_y1): 150 mm aft of the
    leading edge plane, at the section's thickness centre there. The wing segments bring the lead here; the hub
    carries it on to its exit under the boss (lead_exit)."""
    pf = planform(p)
    y = p.hub_y1
    return aero.spar_point(pf, y, (150.0 - pf.x_le(y)) / pf.chord(y)) * (1, side, 1)


def lead_exit(p, side):
    """Where the aileron lead leaves the hub's underside, beside the boss (12 mm ahead of the pivot), straight down
    into the fuselage through the spine cover's boss hole (13 mm radius)."""
    return (p.pivot_x - 12.0, side * p.pivot_y, -3.0)
