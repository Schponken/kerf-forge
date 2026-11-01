"""Shared geometry for the parallel gripper, computed once from params + catalog so every part agrees.

Gripper frame G (same as projects/robot_arm's gripper, so the parts drop onto that arm's wrist): origin on the wrist
axis at the wrist horn face, X forward along the gripper, Y up at home, Z across the wrist fork (world -Y).
The wrist fork is the arm's: plate A (z 0..plate_t) bolts to the wrist horn, plate B (z grip_w-plate_t..grip_w)
turns on an M3 pivot screw in a heat-set insert; fork width grip_w = robot_arm's (its forearm width is derived from it).

Drive: the grip servo (MG996R) lies inline between the fork plates, case top through the bulkhead (tab tops on the
bulkhead's back face x = x_bulk), output axis along +X at (y = 0, z = z_c), so the tool point sits on the wrist line.
A printed pinion on its aluminium horn drives two racks: the top rack belongs to jaw_r (+Z side), the bottom rack to
jaw_l (-Z side); turning the servo +a deg moves both jaws OUT by a * mm_per_deg (rack and pinion, kerf.drives).
Each jaw is a carriage on two steel guide rods along Z (in front of the pinion) plus a finger forward to the pad.
Jaw frame J: X forward, Y toward the jaw's own rack, Z = the jaw's opening direction; origin at closed (grip 0) on the
pad face plane, on the pinion axis line (y = 0), at x = x_c0 (carriage back face). jaw_r: J = G axes; jaw_l: J = G
rotated 180 deg about X.

Stand frame S (world, Z up, bench at z = 0): the bench stand reproduces the robot_arm forearm's wrist end. Its
"forearm frame" F = Location((0, 0, stand_h), (90, 0, 0)): X along the forearm toward the gripper, Y up, Z across
(world -Y), wrist axis on F's Z axis; plate A outer face at F z = 0 (wrist servo tab tops, top-through), plate B outer
face at F z = w_f. The gripper's horn face is at F z = face (horn face above plate A's outer face).
"""
import math

from kerf import iface

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"


def layout(p, cat):
    s = iface.servo_dims(SERVO)
    h = iface.horn_dims(HORN)
    # top-through mount: horn face beyond the face the tab tops press on (robot_arm layout.face)
    face = -s["tab_t"] + s["top"] + s["shaft_h"] + h["hub_h"]
    if s["top"] - s["tab_t"] <= p.bulk_t:
        raise ValueError(f"{SERVO} case top would not clear a {p.bulk_t} mm bulkhead when mounted top-through")
    W, t = p.grip_w, p.plate_t
    z_c = W / 2
    w_f = face + W + p.side_gap + t                    # forearm / stand fork outer width (robot_arm w_f)
    y_s = -s["out_x"]                                   # grip servo body centre: output axis on y = 0
    x_case0 = p.x_bulk - s["tab_t"] - s["tab_z"]       # servo case bottom (toward the wrist)
    x_horn = p.x_bulk + face                            # pinion back face sits on the horn face
    r_p = p.gear_m * p.pinion_z / 2
    mm_per_deg = r_p * math.pi / 180
    s_max = mm_per_deg * p.grip_max                     # each jaw's travel, closed -> open
    x_p0, x_p1 = x_horn, x_horn + p.gear_b             # pinion + rack slab
    x_c0 = x_p1 + p.slab_gap                            # carriage slab (rods)
    x_c1 = x_c0 + p.carr_x
    x_rod = (x_c0 + x_c1) / 2
    z_in = p.gap0 / 2                                   # pad face / carriage inner face from z_c, closed
    z_stop = z_in + s_max + p.carr_len + p.stop_gap     # cheek inner faces from z_c (open-end hard stop)
    pitch = math.pi * p.gear_m
    # rack teeth (jaw frame, along J z = toward the centre is -z... see jaw.py): must cover the mesh point from
    # closed (z_c) to open (z_c + s_max past the pad plane) with 1.5 pitches either side; odd count (kerf.drives)
    rack_n = int(math.ceil((s_max + 3 * pitch) / pitch)) | 1
    x_tip = x_c1 + p.finger_len
    return {
        "face": face, "z_c": z_c, "w_f": w_f, "y_s": y_s, "x_case0": x_case0, "x_horn": x_horn,
        "r_p": r_p, "mm_per_deg": mm_per_deg, "s_max": s_max, "x_p0": x_p0, "x_p1": x_p1,
        "x_c0": x_c0, "x_c1": x_c1, "x_rod": x_rod, "z_in": z_in, "z_stop": z_stop, "rack_n": rack_n,
        "pitch": pitch, "x_tip": x_tip, "x_tcp": x_tip - p.pad_len / 2,
        "mg_L": s["L"], "mg_W": s["W"], "mg_span": s["span"], "mg_hx": s["hx"], "mg_hy": s["hy"],
        "mg_tab_t": s["tab_t"], "mg_tab_z": s["tab_z"], "mg_top": s["top"], "mg_out_x": s["out_x"],
        "horn_bc": h["bc"], "horn_od": h["od"],
        "mg_stall_nmm": cat.num(cat.get(SERVO), "stall_torque_kgcm") * 98.0665,
        # grip force per jaw with the servo at stall, both jaws on the object (torque splits over two meshes)
        "grip_stall_n": cat.num(cat.get(SERVO), "stall_torque_kgcm") * 98.0665 / (2 * r_p),
    }
