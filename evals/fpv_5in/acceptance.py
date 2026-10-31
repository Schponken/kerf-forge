import itertools
from evals.common import FLIGHT_ELECTRONICS, complete_electronics, base_checks, dist, need_joint, need_req, screws_touching


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    pos = rep.get("assembly", {}).get("positions", {})
    motors = [f"motor_{i}" for i in range(1, 5)]
    for m in motors + ["stack", "camera", "battery", "xt60"] + [f"prop_{i}" for i in range(1, 5)]:
        if m not in pos:
            fails.append(f"item '{m}' missing")
    if fails:
        return fails
    for m in motors:
        n = len([f for f in screws_touching(rep, m) if f["screw"] == "M3"])
        if n < 4:
            fails.append(f"{m} is held by {n} aligned M3 screws, need 4")
    if len([f for f in screws_touching(rep, "stack") if f["screw"] == "M3"]) < 4:
        fails.append("stack needs 4 aligned M3 screws")
    diag = max(dist(pos[a][:2], pos[b][:2]) for a, b in itertools.combinations(motors, 2))
    if not 200 <= diag <= 240:
        fails.append(f"motor-to-motor diagonal {diag:.1f} mm, must be 200-240")
    r = need_req(rep, "prop_gap", "prop_clearance", fails)
    if r and (r.get("value") is None or r["value"] < 3):
        fails.append("prop_gap must report a minimum clearance >= 3 mm")
    need_joint(rep, "cam_tilt", fails, covers=(0, 30))
    r = need_req(rep, "twr", "thrust_to_weight", fails)
    if r and r["limit"] < 6:
        fails.append("twr limit must be >= 6")
    need_req(rep, "arm_strength", "fea_static", fails)
    r = need_req(rep, "frame_mass", "mass_max", fails)
    if r and r["limit"] > 250:
        fails.append("frame_mass limit must be <= 250 g")
    complete_electronics(rep, proj_dir, fails, {**FLIGHT_ELECTRONICS, "video TX": ("vtx",), "camera": ("camera",)}, 3)
    return fails
