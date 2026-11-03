"""Shared numbers for the hawk_wing swing-wing FPV plane, computed once from params + catalog so every part agrees
(DESIGN.md "Part contracts").

Frame (every part is modelled in it): X aft from the glove's leading edge at the centreline, Y to the right wing,
Z up; the wing's root chord plane is z = 0. Printed parts sit at their home placement (wings spread) with rigid joints
at the origin, except the moving ones: each outer panel (hub + two skin segments + aileron + skid) turns about its
sweep pivot, the ailerons / elevator / rudder about their hinge lines, the pinions with their servos.

Wing: ONE straight-tapered planform (wing_* params, MH 45, straight trailing edge). The fixed glove is its inner part
|y| <= pivot_y; each outer panel is the rest, from its root station y = pivot_y to the tip.

Sweep pivot (per side): a vertical 5 mm steel pin (rods.ss_rod_5, stocked 50 mm) at (pivot_x, +-pivot_y), pivot_back
mm ahead of the trailing edge at the panel root, so only the round "elbow" disc behind the pin turns in place and the
rest of the panel swings OUT and back. Stack along the pin, bottom to top:
  pod floor plate  POD_FLOOR_Z0..POD_FLOOR_Z1   pin pressed in (8 mm)
  0.5 gap
  hub boss          BOSS_Z0..BOSS_Z1             two 625 bearings pressed in its ends (28 mm apart, centre to centre)
  0.5 gap
  pivot cap         CAP_Z0..CAP_Z1               pin slip-fits its blind bore (8 mm): cap off -> panel lifts off
The sector gear (21 T, module 2) is a band on the hub boss below the wing (SECTOR_Z0..Z1), inside the pod; the 13 T
pinion on the MG996R's aluminium horn meshes it from straight AHEAD of the pin (pair convention: driven gear +X of
the pinion), so the servo lies along X in a slim nacelle (pod) under the glove's trailing-edge corner.
"""
import math

from kerf import aero

AIRFOIL = "mh45"              # near-zero Cm0 (-0.012): sweeping changes the trim only through the AC / CG shift
TAIL_AIRFOIL = "naca0009"
MAIN_TUBE = "rods.cf_tube_8x6"
REAR_TUBE = "rods.cf_tube_6x4"
BOOM_TUBE = "rods.cf_tube_8x6"
PIN = "rods.ss_rod_5"
BEARING = "bearings.625"
SWEEP_SERVO = "servos.MG996R"
SWEEP_HORN = "servo_horns.aluminum_25T"
SURF_SERVO = "servos.KST_X08_Plus"
MOTOR = "drone.motors.2806_5_1300kv_7in"
BATTERY = "drone.batteries.6S_1800"
TE_MIN = 1.2                  # printed trailing edge: three 0.4 mm lines (>= 1.2 mm walls print reliably)

GEAR_M, Z_PINION, Z_SECTOR, GEAR_W = 2.0, 13, 21, 10.0      # 21/13 = 1.615: 65 deg of sweep = 105 deg of the servo
PINION_W = 11.0               # pinion wider than the sector so the mesh keeps full width over the axial play
PIN_L = 50.0                  # stocked rods.ss_rod_5 length
GAP = 0.5                     # axial running clearance at each end of the boss (ENGINEERING s8)

# z stack on the pin axis (see the module docstring)
POD_FLOOR_Z0, POD_FLOOR_Z1 = -35.5, -27.5
BOSS_Z0, BOSS_Z1 = -27.0, 6.0
CAP_Z0, CAP_Z1 = 6.5, 14.5
BOSS_R = 11.0                 # 16 mm bearing outer race + 3 mm wall
SECTOR_Z0 = -16.0             # sector band SECTOR_Z0..+GEAR_W on the boss, inside the pod
PINION_Z0 = -16.5             # pinion bottom = the horn's outer face
POD_ROOF_Z = -3.0             # top of the pod's roof (just under the glove / panel lower skin)
HUB_DISC_Z0 = -2.0            # flat underside of the hub's elbow disc over the pod opening (1 mm above the roof)
DISC_R = 24.0                 # hub elbow disc radius round the pin; the glove notch and pod opening are DISC_R + 1 / + 0.5
SECTOR_MARGIN = 12.0          # deg of teeth past the meshing tooth at each end of the sweep (> 0.5 pitch of 17.1 deg)


def planform(p):
    return aero.Planform(span=p.wing_span, root_chord=p.wing_root_chord, tip_chord=p.wing_tip_chord,
                         sweep_le_deg=p.wing_sweep_le_deg, twist_tip_deg=p.wing_twist_tip_deg, root_airfoil=AIRFOIL,
                         te_min=TE_MIN)


def tail_planform(p):
    return aero.Planform(span=p.htail_span, root_chord=p.htail_root_chord, tip_chord=p.htail_tip_chord,
                         sweep_le_deg=p.htail_sweep_le_deg, root_airfoil=TAIL_AIRFOIL, x_le0=p.htail_x_le0,
                         z0=p.htail_z0, te_min=1.2)


def layout(p, cat):
    pf = planform(p)
    g = pf.geometry()
    out = {"wing_airfoil": AIRFOIL, "wing_x_le0": 0.0, "wing_z0": 0.0, "wing_te_min": TE_MIN, "semi": p.wing_span / 2,
           "htail_airfoil": TAIL_AIRFOIL, "mac": g["mac_mm"], "area_dm2": g["area_dm2"]}
    x_te = pf.x_le(p.pivot_y) + pf.chord(p.pivot_y)
    out["pivot_x"] = x_te - p.pivot_back
    cd = GEAR_M * (Z_PINION + Z_SECTOR) / 2
    out.update({"gear_cd": cd, "pinion_x": out["pivot_x"] - cd, "sector_ro": GEAR_M * (Z_SECTOR + 2) / 2,
                "pinion_ro": GEAR_M * (Z_PINION + 2) / 2})
    # spar tubes: straight, through the thickness centre at the same chord fraction at both ends; inner ends in the
    # hub's sockets, run out through both skin segments
    for k, frac, y1 in (("main", p.spar_main_frac, p.spar_main_y1), ("rear", p.spar_rear_frac, p.spar_rear_y1)):
        a, b = aero.spar_line(pf, frac, frac, p.spar_y0, y1)
        out.update({f"{k}_x0": float(a[0]), f"{k}_z0": float(a[2]), f"{k}_x1": float(b[0]), f"{k}_z1": float(b[2])})
        out[f"{k}_len"] = math.dist((a[0], p.spar_y0, a[2]), (b[0], y1, b[2]))
    out["main_od"] = cat.num(cat.get(MAIN_TUBE), "od", "od_mm")
    out["rear_od"] = cat.num(cat.get(REAR_TUBE), "od", "od_mm")
    out["boom_od"] = cat.num(cat.get(BOOM_TUBE), "od", "od_mm")
    out["boom_len"] = p.boom_x1 - p.boom_x0
    tg = tail_planform(p).geometry()
    out["htail_x_ac"] = tg["x_np_mm"]
    out["htail_area_dm2"] = tg["area_dm2"]
    import importlib.util, pathlib
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location("hawk_wiring", pathlib.Path(__file__).with_name("wiring.py"))
    wiring = importlib.util.module_from_spec(spec); spec.loader.exec_module(wiring)
    out.update(wiring.route_params(SimpleNamespace(**{**vars(p), **out})))
    return out


def tube_line(p, which, side):
    """(start, end) world points of a spar tube on one side (+1 right, -1 left), home pose."""
    y1 = p.spar_main_y1 if which == "main" else p.spar_rear_y1
    return ((getattr(p, f"{which}_x0"), side * p.spar_y0, getattr(p, f"{which}_z0")),
            (getattr(p, f"{which}_x1"), side * y1, getattr(p, f"{which}_z1")))


def tube_loc(p, which, side):
    from build123d import Location, Plane
    a, b = tube_line(p, which, side)
    d = tuple(bb - aa for aa, bb in zip(a, b))
    return Location(Plane(origin=a, x_dir=(1, 0, 0) if abs(d[0]) < 0.9 * math.hypot(*d) else (0, 0, 1), z_dir=d))


def pivot_xy(p, side):
    return (p.pivot_x, side * p.pivot_y)


def pivot_axis(p, side):
    """Sweep pivot axis for side +1 right / -1 left: origin on the pod floor plate's top face, direction chosen so a
    POSITIVE joint angle sweeps the panel aft (right: clockwise seen from above)."""
    from build123d import Axis
    return Axis((p.pivot_x, side * p.pivot_y, POD_FLOOR_Z1), (0, 0, -side))


def pin_loc(p, side, z):
    """Pin-axis frame at height z, +Z up (iface.pin_hole / bearing_seat loc on a face at z)."""
    from build123d import Location
    return Location((p.pivot_x, side * p.pivot_y, z))


def sector_deg(p):
    """Hub angles (deg, right side, CCW from +X seen from above) the sector's teeth must cover: the pinion meshes at
    hub angle 180 spread and 180 + fold_max folded (the hub turns clockwise as it folds). Left side: mirror (-angle)."""
    return 180.0 - SECTOR_MARGIN, 180.0 + p.fold_max + SECTOR_MARGIN


def horn_face_above_tabs(cat_servo=SWEEP_SERVO, horn=SWEEP_HORN):
    """Height of the horn's outer face above the servo's tab underside (servo top + spline + horn hub above it)."""
    from kerf import iface
    d, h = iface.servo_dims(cat_servo), iface.horn_dims(horn)
    return d["top"] + d["shaft_h"] - h["engage"] + max(h["hub_total"] - h["t"], 0.0) + h["t"]


def sweep_servo_loc(p, side):
    """Servo proxy 'tabs' frame (tab underside centre): output vertical (+Z) on the pinion axis, output end aft (+X),
    so the body lies along X ahead of the pin under the glove."""
    from build123d import Location, Plane
    from kerf import iface
    d = iface.servo_dims(SWEEP_SERVO)
    z = PINION_Z0 - horn_face_above_tabs()
    return Location(Plane(origin=(p.pinion_x - d["out_x"], side * p.pivot_y, z), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))


def gears():
    """(pinion, sector gear) from kerf.drives.spur_pair at the origin, z 0..width: the pinion goes on the horn at
    (pinion_x, +-pivot_y, PINION_Z0) and the sector gear's centre on the pivot axis (+X of the pinion, the pair's own
    convention) at SECTOR_Z0, so the teeth are phased to mesh at home on both sides."""
    from kerf import drives
    g1, _, _ = drives.spur_pair(GEAR_M, Z_PINION, Z_SECTOR, PINION_W)
    _, s2, _ = drives.spur_pair(GEAR_M, Z_PINION, Z_SECTOR, GEAR_W)
    return g1, s2


def boom_loc(p):
    """Boom rod 'end_a' frame: front end of the tube on the boom axis, +Z aft."""
    from build123d import Location, Plane
    return Location(Plane(origin=(p.boom_x0, 0, p.boom_z), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))


# ---------------------------------------------------------------- fuselage outline (fuselage + nose loft these)
def fuse_stations(p):
    """Outer fuselage sections, front to back: (x, half width, z bottom, z top, corner radius), rounded rectangles
    lofted straight between stations. The top under the glove (x 0..glove TE) is cut away by the glove's lower
    surface (saddle); the hatch is the top ahead of the glove; the tail end wraps the boom socket."""
    hw, zb, zt = p.fuse_hw, p.fuse_bottom, p.fuse_top
    return [(p.nose_x0, 20.0, p.motor_z - 20.0, p.motor_z + 20.0, 9.0),
            (p.nose_x1, hw - 2.0, zb + 6.0, zt, 12.0),
            (-60.0, hw, zb, zt, 12.0),
            (60.0, hw, zb, zt - 4.0, 12.0),
            (200.0, hw - 6.0, zb + 12.0, -2.0, 11.0),
            (p.fuse_x1, 9.0, p.boom_z - 9.0, p.boom_z + 9.0, 8.0)]


def fuse_section(p, x):
    """Interpolated (half width, z bottom, z top, corner radius) of the outer fuselage at x."""
    st = fuse_stations(p)
    for a, b in zip(st[:-1], st[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(a[i] + t * (b[i] - a[i]) for i in range(1, 5))
    raise ValueError(f"x {x} outside the fuselage ({st[0][0]}..{st[-1][0]})")


def section_face(p, x):
    """build123d Face of the outer fuselage section at x (in the plane x = const)."""
    from build123d import Plane, RectangleRounded, Location
    hw, zb, zt, r = fuse_section(p, x)
    return Plane.YZ.offset(x) * RectangleRounded(2 * hw, zt - zb, min(r, hw - 0.1, (zt - zb) / 2 - 0.1)).moved(
        Location((0, (zb + zt) / 2)))


# ---------------------------------------------------------------- items carried by the fuselage / glove / nose
BAY_FLOOR_Z = -66.0           # battery bay floor top (fuselage bottom -70 + 4 mm floor); pad 3 mm on it
SHELF_TOP = -25.0             # electronics shelf top over the pack (pack top -29, strap 1.8 under the shelf)
VTX_X = 205.0                 # VTX on the fuselage floor under the glove's trailing edge; antenna up through the glove
GPS_X = 120.0                 # GPS in the glove's centre pocket (46 % chord: 21 mm deep there)
LEAD_ROOT_X = 190.0           # aileron lead on the hub / wing_x1 face, aft of the rear spar
CAM_TILT = 10.0               # camera tilted up (deg): the view clears the motor bell


def item_locs(p):
    """{joint label: Location} of the box-proxy items the fuselage carries (proxy frame: bottom centre, +Z up)."""
    from build123d import Location
    b = p.bat_x
    hw = p.fuse_hw
    return {"pad": Location((b, 0, BAY_FLOOR_Z)),
            "battery": Location((b, 0, BAY_FLOOR_Z + 3.0)),
            "strap": Location((b, 0, BAY_FLOOR_Z + 3.0 + 34.0)),
            "xt60": Location((b - 43.5 - 14.0, 0, BAY_FLOOR_Z)),
            "esc": Location((b + 5.0, 15.0, SHELF_TOP)),
            "fc": Location((b - 12.0, -16.0, SHELF_TOP)),
            "rx": Location((b + 24.0, -16.0, SHELF_TOP)),
            "vtx": Location((VTX_X, 0, p.fuse_bottom + 15.0)),
            "vtx_ant": Location((VTX_X, 0, p.fuse_bottom + 23.0))}


def camera_locs(p):
    """(camera box 'bottom' frame, view-cone 'bottom' frame at the lens front looking forward, tilted up CAM_TILT)."""
    from build123d import Location, Plane
    cx, cz = p.nose_x0 + 13.0, 3.0
    t = math.radians(CAM_TILT)
    return (Location((cx, 0, cz)),
            Location(Plane(origin=(cx - 9.5, 0, cz + 9.5), x_dir=(0, 1, 0), z_dir=(-math.cos(t), 0, math.sin(t)))))


def gps_loc(p):
    from build123d import Location
    return Location((GPS_X, 0, 2.5))


def lead_root(p, side):
    """Aileron lead channel point on the hub / inner-segment interface face (y = hub_y1): x 190, 15 mm aft of the rear
    spar, on the section's thickness centre (10 mm deep there): the wing segments bring the lead here, the hub carries
    it on to the pivot cap."""
    pf = planform(p)
    y = p.hub_y1
    return aero.spar_point(pf, y, (LEAD_ROOT_X - pf.x_le(y)) / pf.chord(y)) * (1, side, 1)


# ---------------------------------------------------------------- shared fastener / keep-out positions (DESIGN.md)
NOTCH_R = DISC_R + 1.0        # glove trailing-edge corner cut round each pin (the hub's elbow disc turns in it)
POD_OPEN_R = DISC_R + 0.5     # pod roof opening round each pin: the 21 T sector (r 23) passes through it when the
                              # panel is lifted off / put on
CAP_SCREWS = [(-12.0, -31.0), (12.0, -31.0)]    # (dx, dy) from the pin, RIGHT side (left: dy -> -dy): 2 x M3 from
                              # the cap's top, through the glove, into heat-set inserts in the pod roof (group cap_r/l)
POD_SCREWS = [(162.0, -20.0), (195.0, -24.0)]   # (x, dy from pivot_y), RIGHT side: 2 x M3 from below through the
                              # pod's front flange into heat-set inserts in the glove's lower skin (group pod_r/l)
GLOVE_SCREWS = [(30.0, 24.0), (30.0, -24.0), (200.0, 18.0), (200.0, -18.0)]   # (x, y): 4 x M3 from the glove top
                              # (counterbored) into heat-set inserts in the fuselage's saddle rim (group glove)
POD_PAD_Z = POD_ROOF_Z        # glove underside is flat at this z over each pod's footprint (the pod bolts to it)
LEAD_EXIT_D = (-14.0, 3.0)    # (dx, dy) from the pin, right side: aileron lead leaves the hub's top here (r 14.3),
                              # up into the hollow cap where its plug meets the glove-side extension


def cap_screw_xy(p, side):
    return [(p.pivot_x + dx, side * (p.pivot_y + dy)) for dx, dy in CAP_SCREWS]


def pod_screw_xy(p, side):
    return [(x, side * (p.pivot_y + dy)) for x, dy in POD_SCREWS]
