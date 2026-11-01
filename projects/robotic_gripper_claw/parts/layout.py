"""Shared geometry for the robotic gripper claw, computed once from params + catalog so every part agrees.

The claw replaces the desk robot arm's gripper + finger (projects/robot_arm) on the arm's wrist, so its wrist end is
the old gripper's: plate A on the wrist servo's 25T horn, plate B on an M3 pivot screw into a heat-set insert, GRIP_W
across. Those numbers are the arm's (robot_arm project.yaml params + robot_arm/parts/layout.py formulas);
tests/test_claw_fits_arm.py fails if the arm changes and this file does not.

Frames
- Claw frame (palm, cover): the old gripper's. Origin on the wrist axis at the wrist horn face; X forward along the
  claw, Y up at the arm's home pose, Z across the wrist fork (horn face z = 0, pivot face z = GRIP_W). The palm
  underside is y = 0; the grip servo hangs below it and its horn face is at y = face.
- Stand frame (wrist_stand, the bench stand that replicates the forearm's wrist end): the arm's forearm frame moved
  to the wrist axis: X along the forearm toward the claw, Y = the forearm's up, Z across with the wrist servo's tab
  tops pressing on plate A's outer face z = 0 (servo below, z < 0). The stand stands on the desk with Z up.
  At wrist = 0 the claw frame is the stand frame moved by (0, 0, face).
"""
import math

from kerf import iface

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"
# the arm's wrist fork (robot_arm/project.yaml params; guarded by tests/test_claw_fits_arm.py)
ARM = {"plate_t": 7.0, "side_gap": 1.5, "grip_w": 35.0, "link_h": 34.0}
FA_WEB_BACK = 9.0          # robot_arm forearm.py: rear web centre = servo body rear end - 9 mm
FA_WEB_T = 4.0             # robot_arm forearm.py: web thickness
FA_TAB_MARGIN = 5.0        # robot_arm forearm.py: plate A runs 5 mm past the servo's front tab


def layout(p, cat):
    s = iface.servo_dims(SERVO)
    h = iface.horn_dims(HORN)
    t, gap, W, r = ARM["plate_t"], ARM["side_gap"], ARM["grip_w"], ARM["link_h"] / 2
    face = -s["tab_t"] + s["top"] + s["shaft_h"] + h["hub_h"]   # horn face above the face the tab tops press on
    w_f = face + W + gap + t                                     # forearm fork: plate A outer face to plate B outer face

    # gear pair (1:1), axes vertical (claw Y), symmetric about the fork mid-plane z = W / 2
    c = p.gear_m * p.gear_z                                      # standard centre distance m (z + z) / 2
    z_d, z_i = W / 2 - c / 2, W / 2 + c / 2                      # drive (on the grip horn) and idler axes
    r_tip = p.gear_m * (p.gear_z / 2 + 1)
    y_g0 = face                                                  # gear bottom = grip horn face
    y_g1 = y_g0 + p.gear_w
    y_c0 = y_g1 + 0.5                                            # cover underside: 0.5 mm over the gear tops
    y_c1 = y_c0 + p.cover_t

    # grip servo: output end toward the wrist, so the body sits forward under the fingers and the lead leaves backward
    x_sc = p.x_g + s["out_x"]                                    # servo body centre (claw X)
    # pads: contact point at the closed pose, relative to each gear axis (drive finger; the idler mirrors it in z)
    dz_pad = (W / 2 - p.pad_gap / 2) - z_d                       # inward offset from the gear axis to the pad face
    L_pad = math.hypot(p.finger_len, dz_pad)
    a_pad = math.degrees(math.atan2(dz_pad, p.finger_len))

    def gap_at(th):        # pad-to-pad gap when each finger has turned th degrees open
        return W - 2 * z_d - 2 * L_pad * math.sin(math.radians(a_pad - th))

    stall = cat.num(cat.get(SERVO), "stall_torque_kgcm") * 98.0665
    return {
        "W": W, "plate_t": t, "side_gap": gap, "r_w": r, "face": face, "w_f": w_f,
        "gear_c": c, "z_d": z_d, "z_i": z_i, "r_tip": r_tip, "y_g0": y_g0, "y_g1": y_g1, "y_c0": y_c0, "y_c1": y_c1,
        "x_sc": x_sc, "out_x": s["out_x"], "mg_L": s["L"], "mg_W": s["W"], "mg_span": s["span"], "mg_hx": s["hx"],
        "mg_hy": s["hy"], "mg_tab_t": s["tab_t"], "mg_tab_z": s["tab_z"], "mg_top": s["top"],
        "dz_pad": dz_pad, "L_pad": L_pad, "a_pad": a_pad, "gap_open": gap_at(p.grip_open),
        "x_tcp": p.x_g + p.finger_len, "z_tcp": W / 2, "y_pad": y_g0 + p.gear_w / 2,   # pad centre height = gear mid-plane
        "stall_nmm": stall,
        # the arm's forearm around the wrist axis (stand frame), robot_arm/parts/forearm.py
        "fa_a_front": s["span"] / 2 + FA_TAB_MARGIN - s["out_x"],              # plate A runs this far past the wrist axis
        "fa_web_x": -s["out_x"] - s["L"] / 2 - FA_WEB_BACK, "fa_web_t": FA_WEB_T,  # rear web centre (behind the axis)
        "fa_servo_x": -s["out_x"],                                               # wrist servo body centre
    }
