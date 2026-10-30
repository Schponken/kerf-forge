from evals.common import base_checks, need_joint, need_req


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    need_joint(rep, "pan", fails, covers=(-80, 80))
    need_joint(rep, "tilt", fails, covers=(-30, 60))
    pur = rep.get("purchased", {})
    if not any(str(v.get("catalog", "")).startswith("servos.") for v in pur.values()):
        fails.append("no catalog servos")
    need_req(rep, "torque_tilt", "static_torque", fails)
    if not (proj_dir.parent.parent / "evals" / "pan_tilt" / "BLIND_RUN.md").exists():
        fails.append("evals/pan_tilt/BLIND_RUN.md (blind subagent run record) missing")
    return fails
