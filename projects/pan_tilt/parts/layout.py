"""Shared geometry for the pan-tilt head, computed once from params + catalog so base, yoke and bracket agree.

Frames (all mm, Z up at home pose, camera looking along +X):
- base:    origin at the centre of the tripod-nut axis on the bottom face. The pan axis is at x = pan_x.
- yoke:    origin on the pan axis at the pan-horn face (the yoke plate's underside), axes = world at home.
- bracket: origin on the tilt axis, midway between the two arms; X forward (camera), Z up at tilt = 0.
"""
from kerf import iface

SERVO = "servos.SG90"
HORN = "servo_horns.aluminum_micro_21T"
CAM = "boards.rpi_camera_module_3"


def layout(p, cat):
    s = iface.servo_dims(SERVO)
    h = iface.horn_dims(HORN)
    cam = cat.get(CAM)
    nut = cat.get("tripod_nut_1_4_20")
    stall_nmm = cat.num(cat.get(SERVO), "stall_torque_kgcm") * 98.0665

    # ---- base: servo body hangs in a pocket above the tripod-screw tip zone
    tab_z = p.servo_floor_z + s["tab_z"]                 # tab underside = base top (deck) height
    out_h = s["top"] + s["shaft_h"]                       # tab underside -> spline top
    pan_x = s["out_x"]                                    # pan axis sits out_x ahead of the servo body centre
    base_l = s["span"] + 2 * p.base_margin                # tabs fully supported
    base_w = s["W"] + 2 * p.base_side

    # ---- yoke (frame: pan horn face). tilt servo on the +Y wall, mounted from outside (top_through)
    horn_face_z = tab_z + out_h + h["hub_h"]              # world z of the pan horn face = yoke origin
    arm_y_in = p.cam_gap / 2                              # bracket arm inner faces at +-arm_y_in
    horn_y = arm_y_in + p.arm_t                           # tilt horn face (+Y arm outer face)
    # top_through: tab TOPS on the wall's outer face; output is (top + shaft_h - tab_t) inward from that face
    wall_out = horn_y + h["hub_h"] + (s["top"] + s["shaft_h"] - s["tab_t"])
    wall_in = wall_out - p.wall_t
    tilt_body_z = p.tilt_h - s["out_x"]                    # tilt servo body centre (output end up)
    knuckle_y = -horn_y + p.knuckle_len                   # -Y knuckle inner end (bracket frame y)
    pin_wall_in = -(horn_y + p.pivot_gap)                 # -Y wall inner face (yoke frame)
    pin_wall_out = pin_wall_in - p.wall_t

    # ---- camera on the bracket: lens centre on the tilt axis
    lens_y = cat.num(cam["lens_offset"], "y")
    rear = cat.num(cam, "rear_clearance")
    standoff = rear + 0.3
    cam_seat_x = p.cam_plate_x + p.cam_plate_t + standoff  # board underside (PCB back face)
    cam_t = cat.num(cam, "thickness")
    lens_front_x = cam_seat_x + cam_t + cat.num(cam, "component_height")
    board_w = cat.num(cam, "width")                         # 23.862 along the board's y (world Z)
    board_l = cat.num(cam, "length")                        # 25.0 along the board's x (world Y)

    return {
        "servo_L": s["L"], "servo_W": s["W"], "servo_span": s["span"], "servo_hx": s["hx"], "servo_tab_t": s["tab_t"],
        "servo_tab_z": s["tab_z"], "servo_top": s["top"], "servo_out_x": s["out_x"], "servo_stall_nmm": stall_nmm,
        "tab_z": tab_z, "out_h": out_h, "pan_x": pan_x, "base_l": base_l, "base_w": base_w,
        "nut_af": cat.num(nut, "across_flats"), "nut_h": cat.num(nut, "thickness"),
        "horn_face_z": horn_face_z, "horn_od": h["od"], "horn_bc": h["bc"], "horn_hub_h": h["hub_h"],
        "arm_y_in": arm_y_in, "horn_y": horn_y, "wall_out": wall_out, "wall_in": wall_in, "tilt_body_z": tilt_body_z,
        "knuckle_y": knuckle_y, "pin_wall_in": pin_wall_in, "pin_wall_out": pin_wall_out,
        "lens_y": lens_y, "standoff": standoff, "cam_seat_x": cam_seat_x, "lens_front_x": lens_front_x,
        "board_w": board_w, "board_l": board_l, "cam_zc": -lens_y,
        "hfov": cat.num(cam, "hfov_deg"), "vfov": cat.num(cam, "vfov_deg"),
    }
