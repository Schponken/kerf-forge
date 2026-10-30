"""Engineering requirement checks named in project.yaml under `requirements:`.

Each check gets (proj, asm, **kwargs from yaml) and returns dict(ok, value, limit, detail).
Add new checks with @check("name"). Keep them physics-based and documented in docs/ENGINEERING.md.
"""
from __future__ import annotations

import numpy as np
from build123d import CenterOf

from . import assembly as A, catalog, geom
from .checks import item_mass_g

G = 9.80665
REGISTRY = {}


def check(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def _joint_world(proj, ref):
    item, label = ref.split(".", 1)
    j = proj.items[item].shape.joints[label]
    loc = j.location
    return np.array([loc.position.X, loc.position.Y, loc.position.Z]), loc


def _com(item):
    c = item.shape.center(CenterOf.MASS)
    return np.array([c.X, c.Y, c.Z])


def _axis_world(proj, e):
    """World origin and unit direction of a revolute/linear joint edge."""
    pj = proj.items[e.parent].shape.joints[e.pjoint]
    loc = pj.location
    o = geom.world_point(loc, (0, 0, 0))
    d = geom.world_dir(loc, (0, 0, 1))
    return o, d


@check("mass_max")
def mass_max(proj, asm, max_g, include=None):
    ids = include or [i for i, it in proj.items.items() if it.role != "keepout"]
    m = sum(item_mass_g(proj.items[i]) for i in ids)
    return {"ok": m <= max_g, "value": round(m, 1), "limit": max_g, "detail": "estimated assembled mass (g)"}


@check("size_max")
def size_max(proj, asm, max_mm):
    shapes = [it.shape for it in proj.items.values() if it.role != "keepout" and it.shape is not None]
    lo = np.min([geom.bbox(s)[0] for s in shapes], axis=0)
    hi = np.max([geom.bbox(s)[1] for s in shapes], axis=0)
    size = (hi - lo).tolist()
    return {"ok": all(a <= b for a, b in zip(size, max_mm)), "value": [round(x, 1) for x in size], "limit": max_mm,
            "detail": "assembled bounding box at home pose (mm)"}


@check("distance")
def distance(proj, asm, a, b, min_mm=None, max_mm=None, pose=None):
    """Distance between two joint origins (e.g. shoulder axis to gripper tip = reach)."""
    A.solve(asm, pose or {})
    pa, _ = _joint_world(proj, a)
    pb, _ = _joint_world(proj, b)
    d = float(np.linalg.norm(pa - pb))
    A.solve(asm)
    ok = (min_mm is None or d >= min_mm) and (max_mm is None or d <= max_mm)
    return {"ok": ok, "value": round(d, 1), "limit": [min_mm, max_mm], "detail": f"|{a} - {b}| (mm)"}


@check("clearance_min")
def clearance_min(proj, asm, a, b, min_mm, joints=None, samples=9):
    """Smallest gap between two items, at home and while the listed joints sweep."""
    poses = [{}]
    for name in joints or []:
        e = next(e for e in asm.edges if e.name == name)
        poses += [{name: float(v)} for v in np.linspace(e.range[0], e.range[1], samples)]
    worst = np.inf
    for pose in poses:
        A.solve(asm, pose)
        worst = min(worst, proj.items[a].shape.distance_to(proj.items[b].shape))
    A.solve(asm)
    return {"ok": worst >= min_mm, "value": round(float(worst), 2), "limit": min_mm, "detail": f"min gap {a} to {b} (mm)"}


@check("static_torque")
def static_torque(proj, asm, joint, actuator=None, stall_kgcm=None, max_fraction=0.5, payload_g=0.0,
                  payload_at=None, poses=None):
    """Worst gravity torque on a revolute joint from everything downstream of it plus a payload,
    compared with the actuator's stall torque. max_fraction 0.5 = never ask more than half of stall."""
    e = next((e for e in asm.edges if e.name == joint), None)
    if e is None or e.kind != "revolute":
        raise ValueError(f"static_torque: '{joint}' is not a revolute joint")
    if stall_kgcm is None:
        ent = catalog.get(proj.items[actuator].spec["catalog"])
        stall_kgcm = catalog.num(ent, "stall_torque_kgcm", "stall_torque_kg_cm", "stall_torque")
    downstream = [i for i in asm.subtree(e.child) if proj.items[i].role != "keepout"]
    if poses is None:
        poses = [{joint: float(v)} for v in np.linspace(e.range[0], e.range[1], 13)]
    worst, worst_pose = 0.0, None
    for pose in poses:
        A.solve(asm, pose)
        o, d = _axis_world(proj, e)
        tau = 0.0
        for i in downstream:
            m = item_mass_g(proj.items[i]) / 1000
            r = _com(proj.items[i]) - o
            tau += float(np.dot(np.cross(r, np.array([0, 0, -m * G])), d))
        if payload_g and payload_at:
            p, _ = _joint_world(proj, payload_at)
            tau += float(np.dot(np.cross(p - o, np.array([0, 0, -payload_g / 1000 * G])), d))
        if abs(tau) > abs(worst):
            worst, worst_pose = tau, pose
    A.solve(asm)
    need_kgcm = abs(worst) / G / 10  # worst is N*mm (mass kg x g x lever mm) -> kg*cm
    return {"ok": need_kgcm <= max_fraction * stall_kgcm, "value": round(need_kgcm, 2),
            "limit": round(max_fraction * stall_kgcm, 2),
            "detail": f"worst gravity torque on {joint} (kg*cm) at {worst_pose}; stall {stall_kgcm} kg*cm x {max_fraction}"}


@check("thrust_to_weight")
def thrust_to_weight(proj, asm, thrust_g_total, min_ratio):
    m = sum(item_mass_g(it) for it in proj.items.values() if it.role != "keepout")
    r = thrust_g_total / m if m else 0.0
    return {"ok": r >= min_ratio, "value": round(r, 2), "limit": min_ratio,
            "detail": f"{thrust_g_total} g thrust / {m:.0f} g all-up mass"}


def _ev(v, params):
    """Numbers in yaml may be expressions over params/layout values, e.g. "pivot_h + 10"."""
    if isinstance(v, (int, float)):
        return float(v)
    from .project import _MATH
    return float(eval(str(v), {"__builtins__": {}}, {**_MATH, **params}))


def _region(item, spec, params=None):
    """Vectorised predicate (x, y, z arrays in the part frame) for a yaml region:
    {box: [[x0,y0,z0],[x1,y1,z1]]} | {sites: group, radius: r} | {near_joint: label, radius: r}."""
    shape = item.shape
    if "box" in spec:
        (x0, y0, z0), (x1, y1, z1) = [[_ev(v, params or {}) for v in c] for c in spec["box"]]
        return lambda x, y, z: (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1) & (z >= z0) & (z <= z1)
    if "sites" in spec:
        pts = [geom.world_point(s.loc, (0, 0, 0)) for s in shape.kerf_sites if s.group == spec["sites"]]
    elif "near_joint" in spec:
        j = next((j for j in shape.kerf_joints if j.label == spec["near_joint"]), None)
        if j is None:
            raise ValueError(f"{item.id} has no joint '{spec['near_joint']}'")
        loc = j.loc if j.loc is not None else __import__("build123d").Location(j.axis.position)
        pts = [geom.world_point(loc, (0, 0, 0))]
    else:
        raise ValueError(f"region needs box, sites or near_joint: {spec}")
    if not pts:
        raise ValueError(f"region {spec} matched no points on {item.id}")
    P = np.array(pts)
    r = _ev(spec.get("radius", 5.0), params or {})

    def pred(x, y, z):
        d = np.min(np.linalg.norm(np.stack([x, y, z], axis=-1)[..., None, :] - P, axis=-1), axis=-1)
        return d <= r
    return pred


def _strength(material, direction):
    from .checks import density  # noqa: F401  (materials live in the catalog)
    try:
        m = catalog.get(f"materials.{material}")
    except Exception as e:
        raise ValueError(f"materials.{material} not in catalog: {e}")
    xy = catalog.num(m, "tensile_strength_xy_mpa", "tensile_strength_mpa", "tensile_strength_xy", "tensile_strength")
    if direction == "z":
        return catalog.num(m, "tensile_strength_z_mpa", "tensile_strength_z", default=xy * 0.5)
    return xy


@check("fea_static")
def fea_static(proj, asm, part, fixed, loads, sf=2.0, direction="xy", max_disp_mm=None, mesh_size=None):
    """Finite-element check of one printed part under named load cases (part frame, N).
    Passes when 99.9th-percentile von Mises <= strength(direction) / sf and deflection <= max_disp_mm."""
    from . import fea
    it = proj.items[part]
    mat = it.spec.get("material", "PETG")
    m = catalog.get(f"materials.{mat}")
    E = catalog.num(m, "youngs_modulus_mpa", "tensile_modulus_mpa", "youngs_modulus", "E_mpa")
    nu = catalog.num(m, "poisson", "poissons_ratio", default=0.38)
    shape = it.shape.located(__import__("build123d").Location())
    res = fea.static(shape, E, nu, _region(it, fixed, proj.params),
                     [(_region(it, l, proj.params), tuple(_ev(v, proj.params) for v in l["force_n"])) for l in loads],
                     size=mesh_size)
    allow = _strength(mat, direction) / sf
    ok = res["max_vm_mpa"] <= allow and (max_disp_mm is None or res["max_disp_mm"] <= max_disp_mm)
    return {"ok": ok, "value": round(res["max_vm_mpa"], 2), "limit": round(allow, 2),
            "detail": f"FEA {part}: von Mises p99.9 (MPa) vs {mat} {direction} strength / SF {sf}; "
                      f"peak {res['max_vm_peak_mpa']:.2f} MPa, deflection {res['max_disp_mm']:.3f} mm"
                      + (f" (limit {max_disp_mm})" if max_disp_mm else "") + f", {res['elements']} elements"}


def run_all(proj, asm) -> list:
    out = []
    for req in proj.data.get("requirements") or []:
        kw = {k: v for k, v in req.items() if k not in ("check", "why", "id")}
        name = req["check"]
        rid = req.get("id", name)
        try:
            if name not in REGISTRY:
                raise ValueError(f"unknown check '{name}' (have {sorted(REGISTRY)})")
            r = REGISTRY[name](proj, asm, **kw)
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "value": None, "limit": None, "detail": f"check failed to run: {type(e).__name__}: {e}"}
        out.append({"id": rid, "check": name, "why": req.get("why", ""), **r})
    return out
