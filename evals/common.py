"""Helpers for eval acceptance scripts. Each evals/<id>/acceptance.py defines accept(rep, proj_dir) -> list[str]
of failures (empty = pass). Acceptance files are the grader: never edit them to make a project pass."""
import math


def req(rep, rid):
    return next((r for r in rep.get("requirements", []) if r["id"] == rid), None)


def need_req(rep, rid, check, fails, **must):
    r = req(rep, rid)
    if r is None:
        fails.append(f"requirement id '{rid}' ({check}) is missing from project.yaml")
        return None
    allowed = check if isinstance(check, (tuple, list)) else (check,)
    if r["check"] not in allowed:
        fails.append(f"requirement '{rid}' must use check {' or '.join(allowed)}, uses '{r['check']}'")
    if not r["ok"]:
        fails.append(f"requirement '{rid}' fails: {r['detail']} = {r['value']} (limit {r['limit']})")
    return r


def joint(rep, name):
    return next((j for j in rep.get("assembly", {}).get("joints", []) if j["name"] == name), None)


def need_joint(rep, name, fails, covers=None, kind="revolute"):
    j = joint(rep, name)
    if j is None:
        fails.append(f"joint '{name}' missing")
        return None
    if j["kind"] != kind:
        fails.append(f"joint '{name}' must be {kind}, is {j['kind']}")
    if covers and not (j["range"][0] <= covers[0] and j["range"][1] >= covers[1]):
        fails.append(f"joint '{name}' range {j['range']} must cover {list(covers)}")
    sw = next((s for s in rep.get("assembly", {}).get("sweeps", []) if s["joint"] == name), None)
    if sw is None:
        fails.append(f"joint '{name}' was not swept")
    elif not sw["clear"]:
        fails.append(f"joint '{name}' collides during its sweep: {sw['collisions'][:1]}")
    return j


def screws_touching(rep, item):
    return [f for f in rep.get("assembly", {}).get("fasteners", []) if item in (f["male"], f["female"])]


def dist(a, b):
    return math.dist(a, b)


def base_checks(rep, fails):
    if not rep.get("ok"):
        fails.append(f"kerf build is not passing: {rep.get('problems', [])[:4]}")
    for pid, p in rep.get("parts", {}).items():
        if not p.get("fits"):
            fails.append(f"part {pid} does not fit the printer")


# Electrical roles every flying project must contain; matched against each purchased item's catalog path or id.
FLIGHT_ELECTRONICS = {
    "flight controller": ("stack", "fc", "flight_controller"),
    "ESC": ("stack", "esc"),
    "receiver": ("receiver", "rx"),
    "battery": ("battery",),
    "battery strap": ("strap",),
    "power connector": ("xt60", "xt30", "connector"),
}


def complete_electronics(rep, proj_dir, fails, roles, min_flight_min):
    """Graded 'complete electronics' rules shared by the drone evals (brief section added 2026-10-30)."""
    from pathlib import Path
    import yaml
    items = rep.get("assembly", {}).get("positions", {})
    data = yaml.safe_load(open(Path(proj_dir) / "project.yaml")) or {}
    purchased = {k: str((v or {}).get("catalog", "")) + " " + k
                 for k, v in (data.get("purchased") or data.get("items") or {}).items()
                 if isinstance(v, dict)}
    blob = " ".join(purchased.values()).lower() + " " + " ".join(items).lower()
    for role, keys in roles.items():
        if not any(k in blob for k in keys):
            fails.append(f"electronics: no {role} in the project")
    if not data.get("wiring"):
        fails.append("project.yaml has no `wiring:` section")
    else:
        for i, w in enumerate(data["wiring"]):
            if not isinstance(w, dict) or not w.get("gauge") or not w.get("length_mm"):
                fails.append(f"wiring[{i}] needs gauge and length_mm")
    need_req(rep, "power", "power_budget", fails)
    r = need_req(rep, "flight_time", "flight_time", fails)
    if r and (r.get("value") is None or r["value"] < min_flight_min):
        fails.append(f"flight_time must report >= {min_flight_min} min at hover")
    out = Path(proj_dir) / "out"
    for f in ("WIRING.md", "wiring.svg"):
        if not (out / f).exists():
            fails.append(f"out/{f} missing")
