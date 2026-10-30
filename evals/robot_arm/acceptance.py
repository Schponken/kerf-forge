from evals.common import base_checks, need_joint, need_req


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    for name, cov in (("base_yaw", (-90, 90)), ("shoulder", (-60, 60)), ("elbow", (-60, 60)), ("wrist", (-75, 75)), ("grip", None)):
        need_joint(rep, name, fails, covers=cov)
    if not any(k.endswith(".tcp") for k in rep.get("assembly", {}).get("joint_origins", {})):
        fails.append("no rigid joint labelled 'tcp'")
    pur = rep.get("purchased", {})
    if not any(str(v.get("catalog", "")).startswith("bearings.") for v in pur.values()):
        fails.append("no catalog bearing in the assembly (base yaw must run on a bearing)")
    if not any(str(v.get("catalog", "")).startswith("servos.") for v in pur.values()):
        fails.append("no catalog servos")
    for rid in ("torque_shoulder", "torque_elbow", "torque_wrist"):
        r = need_req(rep, rid, "static_torque", fails)
    reqs = {r["id"]: r for r in rep.get("requirements", [])}
    import yaml
    y = yaml.safe_load((proj_dir / "project.yaml").read_text())
    for r in y.get("requirements", []):
        if r.get("id", "").startswith("torque_"):
            if float(r.get("payload_g", 0)) < 150:
                fails.append(f"{r['id']}: payload_g must be >= 150")
            if float(r.get("max_fraction", 0.5)) > 0.5:
                fails.append(f"{r['id']}: max_fraction must be <= 0.5")
            if not r.get("payload_at", "").endswith(".tcp"):
                fails.append(f"{r['id']}: payload_at must be the tcp")
    r = need_req(rep, "reach", "distance", fails)
    if r and r["value"] is not None and not 230 <= r["value"] <= 300:
        fails.append(f"reach {r['value']} mm must be 230-300")
    need_req(rep, "upper_arm_fea", "fea_static", fails)
    r = need_req(rep, "grip_open", "distance", fails)
    if r and r["value"] is not None and r["value"] < 40:
        fails.append(f"grip opening {r['value']} mm < 40")
    return fails
