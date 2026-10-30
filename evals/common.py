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
