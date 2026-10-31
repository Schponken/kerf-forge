"""Shared geometry for the desk robot arm, computed once from params + catalog so every part agrees.

World frame at home (all joints 0): desk at z = 0, yaw axis = Z axis, arm stretched out along +X, horizontal.
Every link is a fork (two side plates): the servo hangs OUTSIDE plate A (+Y side), mounted top-first from behind
(iface.servo_mount top_through), its horn drives the child's plate A; the child's plate B turns on an M3 shoulder
screw through the parent's plate B (dual support, docs/ENGINEERING.md section 8). Link frames (upper arm, forearm,
gripper) sit on the horn face: X along the link, Y = world up at home, Z = world -Y (across the fork).
"""
from kerf import iface

HORN = "servo_horns.aluminum_25T"
SERVOS = {"yaw": "servos.MG996R", "sh": "servos.DS3225", "el": "servos.DS3218", "wr": "servos.MG996R", "gr": "servos.MG996R"}


def layout(p, cat):
    s = {k: iface.servo_dims(v) for k, v in SERVOS.items()}
    hub = iface.horn_dims(HORN)["hub_h"]
    t, gap = p.plate_t, p.side_gap

    def face(d):  # top-through mount: horn face beyond the face the tab tops press on (along servo +Z)
        return -d["tab_t"] + d["top"] + d["shaft_h"] + hub

    for k in ("sh", "el", "wr", "gr"):
        if s[k]["top"] - s[k]["tab_t"] <= t:
            raise ValueError(f"{SERVOS[k]} case top would not clear a {t} mm plate when mounted top-through")
    w_g = p.grip_w
    w_f = face(s["wr"]) + w_g + gap + t
    w_u = face(s["el"]) + w_f + gap + t
    cheek_in = (face(s["sh"]) + w_u + gap - t) / 2          # cheek inner faces at y = +-cheek_in (symmetric)
    cheek_out = cheek_in + t
    y_h_sh = cheek_out - face(s["sh"])                      # world y of the shoulder horn face (upper arm z = 0)

    # base / yaw stack (z up): servo hangs in the base, gear pair on top of its horn
    z_shelf = p.base_floor + 0.5 + s["yaw"]["tab_z"]        # yaw servo tab undersides rest here
    z_horn_yaw = z_shelf + s["yaw"]["top"] + s["yaw"]["shaft_h"] + hub
    z_gear0, z_gear1 = z_horn_yaw, z_horn_yaw + p.gear_w
    z_tt = z_gear0 - 0.6                                    # tower top = top face of the upper bearing
    b = iface.bearing_dims("bearings.6001")
    z_bhi = z_tt - b["B"]
    z_blo = p.brg_lo_z
    z_plat0 = z_gear1 + 0.5
    yaw_c = p.gear_m * (p.gear_z_tt + p.gear_z_yaw) / 2
    return {
        "w_g": w_g, "w_f": w_f, "w_u": w_u, "cheek_in": cheek_in, "cheek_out": cheek_out, "y_h_sh": y_h_sh,
        "face_sh": face(s["sh"]), "face_el": face(s["el"]), "face_wr": face(s["wr"]), "face_gr": face(s["gr"]),
        "z_shelf": z_shelf, "z_horn_yaw": z_horn_yaw, "z_gear0": z_gear0, "z_gear1": z_gear1, "z_tt": z_tt,
        "z_bhi": z_bhi, "z_blo": z_blo, "z_plat0": z_plat0, "z_plat1": z_plat0 + p.plat_t, "yaw_c": yaw_c,
        "brg_D": b["D"], "brg_d": b["d"], "brg_B": b["B"],
        "yaw_out_x": s["yaw"]["out_x"], "sh_out_x": s["sh"]["out_x"], "el_out_x": s["el"]["out_x"],
        "wr_out_x": s["wr"]["out_x"], "gr_out_x": s["gr"]["out_x"],
        "sh_tab_t": s["sh"]["tab_t"], "el_tab_t": s["el"]["tab_t"], "wr_tab_t": s["wr"]["tab_t"], "gr_tab_t": s["gr"]["tab_t"],
        "yaw_tab_t": s["yaw"]["tab_t"],
        "ds_L": s["sh"]["L"], "ds_W": s["sh"]["W"], "ds_span": s["sh"]["span"], "ds_hx": s["sh"]["hx"],
        "mg_hy": s["yaw"]["hy"], "mg_L": s["wr"]["L"], "mg_W": s["wr"]["W"], "mg_span": s["wr"]["span"], "mg_hx": s["wr"]["hx"],
        "mg_tab_z": s["wr"]["tab_z"], "mg_top": s["wr"]["top"], "ds_tab_z": s["sh"]["tab_z"], "ds_top": s["sh"]["top"],
        "yaw_stall_nmm": cat.num(cat.get(SERVOS["yaw"]), "stall_torque_kgcm") * 98.0665,
        "sh_stall_nmm": cat.num(cat.get(SERVOS["sh"]), "stall_torque_kgcm") * 98.0665,
        "el_stall_nmm": cat.num(cat.get(SERVOS["el"]), "stall_torque_kgcm") * 98.0665,
        "mg_stall_nmm": cat.num(cat.get(SERVOS["gr"]), "stall_torque_kgcm") * 98.0665,
    }
