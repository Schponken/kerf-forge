from evals.common import base_checks, need_joint, need_req


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    import yaml
    y = yaml.safe_load((proj_dir / "project.yaml").read_text())
    if y.get("supports") != "avoid":
        fails.append("project.yaml must set supports: avoid")
    for p in ("base", "proximal", "middle", "distal"):
        if p not in rep.get("parts", {}):
            fails.append(f"printed part '{p}' missing")
    for j, cov in (("mcp", (0, 80)), ("pip", (0, 80)), ("dip", (0, 70))):
        need_joint(rep, j, fails, covers=cov)
    s = next((s for s in rep.get("assembly", {}).get("sweeps", []) if s["joint"] == "curl"), None)
    if s is None or not s["clear"] or s["samples"] < 4:
        fails.append("coupled sweep 'curl' (>= 4 poses) missing or colliding")
    if len(rep.get("assembly", {}).get("fasteners", [])) < 3:
        fails.append("each of the 3 joints needs an aligned pin or screw (fastener check)")
    for rid, lo, hi in (("len_proximal", 40, 48), ("len_middle", 22, 28), ("len_distal", 18, 24)):
        r = need_req(rep, rid, "distance", fails)
        if r and r["value"] is not None and not lo <= r["value"] <= hi:
            fails.append(f"{rid} = {r['value']} mm, must be {lo}-{hi}")
    need_req(rep, "proximal_fea", "fea_static", fails)
    for rid in ("flexor_open", "extensor_open"):
        need_req(rep, rid, "channel_clear", fails)
    return fails
