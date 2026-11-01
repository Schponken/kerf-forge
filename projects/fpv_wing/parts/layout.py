"""Shared numbers for the 1 m flying wing, computed once from params + catalog so every part agrees.

Frame: X aft from the wing's leading edge at the centreline, Y to the right wing, Z up; the chord plane at the
centreline is z = 0. Every part is modelled in this frame (they are bolted / glued in place, rigid joints at the origin)
except the elevons, which turn about their hinge line.
"""
import math

from kerf import aero

AIRFOIL = "mh45"
MAIN_TUBE = "rods.cf_tube_8x6"      # bending spar (strength data: catalog, REFERENCES.md)
REAR_TUBE = "rods.cf_tube_6x4"
MOTOR = "drone.motors.2806_5_1300kv_7in"
SERVO = "servos.KST_X08_Plus"
SERVO_X = 200.0          # servo tab-plane centre x: between the spars at its station (DESIGN.md)
SERVO_Y = 228.0          # |y| of the servo's tab plane; the output points inboard, the arm sits at |y| ~217
LEAD_ROOT_X = 130.0      # where the servo lead's channel meets the root face (between the root bolts and the rear spar)


TE_MIN = 1.0                           # printed trailing edge: two perimeters of a 0.4 mm nozzle plus margin


def layout(p, cat):
    pf = planform(p)
    g = pf.geometry()
    semi = p.wing_span / 2
    out = {"wing_airfoil": AIRFOIL, "wing_x_le0": 0.0, "wing_z0": 0.0, "wing_te_min": TE_MIN, "semi": semi,
           "mac": g["mac_mm"], "x_np": g["x_np_mm"], "area_dm2": g["area_dm2"]}
    # spar tubes: straight from just off the centreline (left and right tubes don't meet) to their outer ends,
    # through the section's thickness centre at the same chord fraction at both ends
    for k, frac, y1 in (("main", p.spar_main_frac, p.spar_main_y1), ("rear", p.spar_rear_frac, p.spar_rear_y1)):
        a, b = aero.spar_line(pf, frac, frac, p.spar_y0, y1)
        out.update({f"{k}_x0": a[0], f"{k}_z0": a[2], f"{k}_x1": b[0], f"{k}_z1": b[2]})
    out["main_od"] = cat.num(cat.get(MAIN_TUBE), "od", "od_mm")
    out["rear_od"] = cat.num(cat.get(REAR_TUBE), "od", "od_mm")
    out["main_len"] = math.dist((out["main_x0"], p.spar_y0, out["main_z0"]), (out["main_x1"], p.spar_main_y1, out["main_z1"]))
    out["rear_len"] = math.dist((out["rear_x0"], p.spar_y0, out["rear_z0"]), (out["rear_x1"], p.spar_rear_y1, out["rear_z1"]))
    out["x_te_root"] = p.wing_root_chord
    # wing-root bolts sit half-way through the root section's thickness at their chord stations
    for k, x in (("1", p.root_bolt_x1), ("2", p.root_bolt_x2)):
        out[f"root_bolt_z{k}"] = aero.spar_point(pf, p.pod_hw, x / pf.chord(p.pod_hw))[2]
    out["cg_target_x"] = g["x_np_mm"] - 0.10 * g["mac_mm"]
    # elevon servo: lies flat in the inner segment (8 mm across the thickness), output shaft spanwise and inboard;
    # tab plane at |y| SERVO_Y, centred on the thickness centre at SERVO_X
    out["servo_x"], out["servo_y"] = SERVO_X, SERVO_Y
    out["servo_z"] = aero.spar_point(pf, SERVO_Y, (SERVO_X - pf.x_le(SERVO_Y)) / pf.chord(SERVO_Y))[2]
    sd = _servo_dims(cat)
    out["servo_out_y"] = SERVO_Y - (sd["top"] + sd["shaft_h"])       # |y| of the spline tip (arm just outboard of it)
    out["horn_y"] = out["servo_out_y"] + 1.5
    out["servo_out_x"] = SERVO_X + sd["out_x"]
    # servo lead channel: pocket (inboard end) to the root face, diagonally between the two spars
    ys = SERVO_Y - 12
    a = aero.spar_point(pf, ys, (SERVO_X - 8 - pf.x_le(ys)) / pf.chord(ys))
    b = aero.spar_point(pf, p.pod_hw, (LEAD_ROOT_X - pf.x_le(p.pod_hw)) / pf.chord(p.pod_hw))
    out.update({"lead_x0": float(a[0]), "lead_y0": ys, "lead_z0": float(a[2]), "lead_x1": float(b[0]), "lead_z1": float(b[2])})
    return out


def _servo_dims(cat):
    from kerf import iface
    return iface.servo_dims(SERVO)


def servo_location(p, side):
    """Servo proxy 'tabs' joint in the wing: proxy X = world X (output end aft), proxy Z (output) = inboard."""
    from build123d import Location, Plane
    return Location(Plane(origin=(p.servo_x, side * p.servo_y, p.servo_z), x_dir=(1, 0, 0), z_dir=(0, -side, 0)))


def lead_line(p, side):
    """Servo lead channel (pocket end, root end), world points."""
    return ((p.lead_x0, side * p.lead_y0, p.lead_z0), (p.lead_x1, side * (p.pod_hw - 3.0), p.lead_z1))


def planform(p):
    return aero.Planform(span=p.wing_span, root_chord=p.wing_root_chord, tip_chord=p.wing_tip_chord,
                         sweep_le_deg=p.wing_sweep_le_deg, twist_tip_deg=p.wing_twist_tip_deg, root_airfoil=AIRFOIL,
                         te_min=TE_MIN)


def tube_line(p, which, side):
    """(start, end) world points of a spar tube on one side (+1 right, -1 left)."""
    y1 = p.spar_main_y1 if which == "main" else p.spar_rear_y1
    a = (getattr(p, f"{which}_x0"), side * p.spar_y0, getattr(p, f"{which}_z0"))
    b = (getattr(p, f"{which}_x1"), side * y1, getattr(p, f"{which}_z1"))
    return a, b
