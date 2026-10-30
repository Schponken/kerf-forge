"""Shared geometry for the servo test rig, computed once from params + catalog so base and bracket agree."""
from kerf import iface


def layout(p, cat):
    s = iface.servo_dims("servos.MG996R")
    hx = s["span"] / 2 + 6.0                         # foot screws just outside the servo tabs: hex key reaches them
    g_x = hx + 6.0 + p.gusset_t / 2                  # gusset centre line, outboard of the screws
    wall_w = 2 * (g_x + p.gusset_t / 2)
    wall_h = p.pivot_h + s["W"] / 2 + 8.0
    y0 = -(p.wall_t + p.foot_d) / 2                  # bracket origin (wall back face) in base coordinates
    return {
        "foot_hx": hx, "foot_y1": p.wall_t + 9.0, "foot_y2": p.wall_t + p.foot_d - 9.0,
        "gusset_x": g_x, "wall_w": wall_w, "wall_h": wall_h, "bracket_y0": y0,
        "servo_tab_z": s["tab_z"], "servo_tab_t": s["tab_t"], "servo_W": s["W"], "servo_out_x": s["out_x"],
        "servo_hx": s["hx"], "servo_stall_nmm": cat.num(cat.get("servos.MG996R"), "stall_torque_kgcm", "stall_torque_kg_cm") * 98.0665,
    }
