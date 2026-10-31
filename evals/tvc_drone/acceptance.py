from evals.common import FLIGHT_ELECTRONICS, complete_electronics, base_checks, need_joint, need_req


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    pos = rep.get("assembly", {}).get("positions", {})
    for m in ("motor_top", "motor_bottom", "prop_top", "prop_bottom", "servo_pitch", "servo_roll", "battery"):
        if m not in pos:
            fails.append(f"item '{m}' missing")
    if len([k for k in pos if k.startswith("rod_")]) < 3:
        fails.append("need >= 3 carbon rods named rod_*")
    if len([k for k in rep.get("parts", {}) if k.startswith("leg_")]) < 3:
        fails.append("need >= 3 printed legs named leg_*")
    need_joint(rep, "gimbal_pitch", fails, covers=(-15, 15))
    need_joint(rep, "gimbal_roll", fails, covers=(-15, 15))
    s = next((s for s in rep.get("assembly", {}).get("sweeps", []) if s["joint"] == "gimbal_corners"), None)
    if s is None:
        fails.append("coupled sweep 'gimbal_corners' missing")
    elif not s["clear"] or s["samples"] < 4:
        fails.append(f"gimbal_corners must have >= 4 poses and be clear: {s.get('collisions', [])[:1]}")
    r = need_req(rep, "twr", "thrust_to_weight", fails)
    if r and r["limit"] < 1.8:
        fails.append("twr limit must be >= 1.8")
    need_req(rep, "cg_axis", "cg", fails)
    need_req(rep, "gimbal_fea", "fea_static", fails)
    r = need_req(rep, "stand", "tip_over", fails)
    if r and r["limit"] is not None and r["limit"] < 15:
        fails.append("stand limit must be >= 15 degrees")
    complete_electronics(rep, proj_dir, fails, FLIGHT_ELECTRONICS, 2)
    return fails
