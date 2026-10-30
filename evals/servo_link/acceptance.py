from evals.common import base_checks, need_joint, need_req, screws_touching


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    need_joint(rep, "swing", fails, covers=(-90, 90))
    fs = rep.get("assembly", {}).get("fasteners", [])
    if len(fs) < 12:
        fails.append(f"expected >= 12 aligned screws, found {len(fs)}")
    for a, b in (("base", "bracket"), ("bracket", "servo"), ("arm", "horn")):
        if not any({f["male"], f["female"]} == {a, b} for f in fs):
            fails.append(f"no screws join {a} and {b}")
    r = need_req(rep, "arm_torque", "static_torque", fails)
    return fails
