from evals.common import base_checks, need_joint, need_req


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    need_joint(rep, "elevon_l", fails, covers=(-20, 20))
    need_joint(rep, "elevon_r", fails, covers=(-20, 20))
    for rid, chk in (("static_margin", "static_margin"), ("wing_loading", "wing_loading"), ("stall_speed", "stall_speed"),
                     ("spar_bending", "spar_bending"), ("twr", "thrust_to_weight"), ("flight_time", "flight_time"),
                     ("prop_clear", "prop_clearance"), ("span", "size_max"), ("auw", "mass_max")):
        need_req(rep, rid, chk, fails)
    reqs = {r["id"]: r for r in rep.get("requirements", [])}
    sm = reqs.get("static_margin", {})
    if sm and not (0.05 <= (sm.get("value") or 0) <= 0.15):
        fails.append(f"static margin {sm.get('value')} outside 5-15 % MAC")
    st = reqs.get("stall_speed", {})
    if st and (st.get("value") or 99) > 55:
        fails.append(f"stall speed {st.get('value')} km/h > 55")
    sb = reqs.get("spar_bending", {})
    if sb and float((sb.get("load_factor") or 0)) < 6:
        fails.append("spar_bending must be checked at >= 6 g")
    pur = rep.get("purchased", {})
    cats = " ".join(str(v.get("catalog", "")) for v in pur.values())
    for need in ("servos.", "batter", "motor", "prop", "tube"):
        if need not in cats:
            fails.append(f"no catalog {need} part")
    wings = [p for p, v in rep.get("parts", {}).items() if v.get("airfoil")]
    if len(wings) < 4:
        fails.append("fewer than 4 wing segments with a catalog airfoil")
    return fails
