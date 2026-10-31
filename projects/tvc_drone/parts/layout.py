"""Shared gimbal/mast geometry for tvc_drone, from params + catalog, so every part agrees.
World frame = ring_low's frame = the gimbal centre at home: the roll axis is world X, the pitch axis world Y, both
through the origin, and the thrust line is the Z axis."""
from kerf import iface

SERVO = "servos.MG90S"
HORN = "servo_horns.aluminum_micro_21T"
MOTOR = "drone.motors.2207_1855kv_6s"


def layout(p, cat):
    s = iface.servo_dims(SERVO)
    h = iface.horn_dims(HORN)
    k = s["top"] + s["shaft_h"] + (h["hub_h"] or h["t"])     # tab underside -> horn face, along the servo output
    m = cat.get(MOTOR)
    motor_h = cat.num(m, "body_h")
    roll_face = p.ring_r_out + p.lug_out                      # roll horn face (outer ring +X lug outer face)
    return {
        "servo_k": k, "servo_out_x": s["out_x"], "servo_L": s["L"], "servo_W": s["W"], "servo_span": s["span"],
        "servo_tab_t": s["tab_t"], "servo_tab_z": s["tab_z"], "servo_top": s["top"], "servo_hx": s["hx"],
        "horn_od": h["od"], "horn_bc": h["bc"],
        "roll_face": roll_face,                               # x of the roll horn face
        "roll_tab_x": roll_face + k,                          # x of the roll servo's tab underside (yoke plate face)
        "pitch_tab_y": p.ring_r_in,                           # y of the pitch servo's tab underside (ring pad face)
        "pitch_face": p.ring_r_in - k,                        # y of the pitch horn face (hub +Y lug)
        "motor_h": motor_h, "motor_bell_r": cat.num(m, "bell_d") / 2,
        "rod_z0": p.ring_low_z + 2.0,                         # rod bottom end (2 mm floor under the bore)
        "ring_top_z": p.ring_low_z + 2.0 + p.rod_len,         # rod top end; ring_top's cap sits on it
        "leg_angles": [30.0, 150.0, 270.0],
        "rod_angles": [90.0, 210.0, 330.0],
    }
