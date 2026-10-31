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
    from .electrical import wiring_mass_g
    m = sum(item_mass_g(proj.items[i]) for i in ids) + (0.0 if include else wiring_mass_g(proj))   # all-up incl. wires
    return {"ok": m <= max_g, "value": round(m, 1), "limit": max_g, "detail": "estimated assembled mass (g)" + ("" if include else ", incl. declared wiring")}


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
def thrust_to_weight(proj, asm, min_ratio, thrust_g_total=None, test_v=None, pack_v=None, motors=None, factor=1.0,
                     output_limit=1.0):
    """Static thrust / all-up mass. Motor thrust tables are measured at one supply voltage (`test_v`); prop thrust goes
    with speed squared and speed with voltage, so a thrust from a 24 V table flown on a 22.2 V pack is scaled by
    (pack_v / test_v)^2. Give both to check at the pack's nominal (or loaded) voltage.
    Or give `motors: [item, ...]`: thrust = sum of each motor's catalog thrust_g_max x factor (coax / installation loss)
    x output_limit^2 (a throttle cap), at the catalog thrust_test_v; pack_v defaults to the electrical battery's
    nominal voltage (cells x 3.7 V)."""
    from .electrical import wiring_mass_g
    if motors:
        if thrust_g_total is not None:
            raise ValueError("thrust_to_weight: give thrust_g_total or motors, not both")
        tvs = set()
        thrust_g_total = 0.0
        for mid in motors:
            e = catalog.get(proj.items[mid].spec["catalog"])
            thrust_g_total += float(e["thrust_g_max"]) * float(factor) * float(output_limit) ** 2
            tvs.add(float(e.get("thrust_test_v") or 0) or None)
        if len(tvs) != 1 or None in tvs:
            raise ValueError("thrust_to_weight: every motor needs a catalog thrust_test_v (and the same one)")
        test_v = tvs.pop()
        if pack_v is None:
            bat = (proj.data.get("electrical") or {}).get("battery")
            cells = catalog.get(proj.items[bat].spec["catalog"]).get("cells") if bat in proj.items else None
            if not cells:
                raise ValueError("thrust_to_weight: give pack_v (no electrical battery with cells)")
            pack_v = round(3.7 * float(cells), 2)
        thrust_g_total = round(thrust_g_total, 1)
    if thrust_g_total is None:
        raise ValueError("thrust_to_weight: give thrust_g_total or motors")
    if (test_v is None) != (pack_v is None):
        raise ValueError("thrust_to_weight: give both test_v and pack_v (or neither)")
    k = (float(pack_v) / float(test_v)) ** 2 if test_v else 1.0
    t = thrust_g_total * k
    m = sum(item_mass_g(it) for it in proj.items.values() if it.role != "keepout") + wiring_mass_g(proj)
    r = t / m if m else 0.0
    volt = f" ({thrust_g_total} g at {test_v} V x ({pack_v}/{test_v})^2 = {t:.0f} g at {pack_v} V)" if test_v else ""
    return {"ok": r >= min_ratio, "value": round(r, 2), "limit": min_ratio,
            "detail": f"{t:.0f} g thrust / {m:.0f} g all-up mass{volt}"}


def _ev(v, params):
    """Numbers in yaml may be expressions over params/layout values, e.g. "pivot_h + 10"."""
    if isinstance(v, (int, float)):
        return float(v)
    from .project import _MATH
    return float(eval(str(v), {"__builtins__": {}}, {**_MATH, **params}))


def _region(item, spec, params=None):
    """Vectorised predicate (x, y, z arrays in the part frame) for a yaml region:
    {box: [[x0,y0,z0],[x1,y1,z1]]} | {sites: group, radius: r} | {near_joint: label, radius: r} |
    {cylinder: {at: [x,y,z] | joint label, dir: [dx,dy,dz], r: radius, tol: 0.3, span: [s0, s1]}} (faces whose
    distance from the axis is r +/- tol, e.g. a bore or a shaft seat; span limits the axial extent from `at`) |
    {any: [region, region, ...]} (the union, e.g. fixed at both pivots of a part)."""
    shape = item.shape
    if "any" in spec:                       # union of regions, e.g. a part held at two pivots
        preds = [_region(item, sub, params) for sub in spec["any"]]
        return lambda x, y, z: np.logical_or.reduce([f(x, y, z) for f in preds])
    if "cylinder" in spec:
        c = spec["cylinder"]
        o, d = _axis(item, c, params or {})
        rr, tol = _ev(c["r"], params or {}), _ev(c.get("tol", 0.3), params or {})
        s0, s1 = [_ev(v, params or {}) for v in c.get("span", [-1e9, 1e9])]

        def cyl(x, y, z):
            r = np.stack([x - o[0], y - o[1], z - o[2]], axis=-1)
            a = r @ d
            rad = np.linalg.norm(r - a[..., None] * d, axis=-1)
            return (np.abs(rad - rr) <= tol) & (a >= s0) & (a <= s1)
        return cyl
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


def _axis(item, spec, params):
    """(origin, unit dir) in the part frame from {at: [x,y,z] | joint label, dir: [..]}; a joint label without `dir`
    uses that joint's axis (revolute) or its local Z."""
    at = spec["at"]
    if isinstance(at, str):
        j = next((j for j in item.shape.kerf_joints if j.label == at), None)
        if j is None:
            raise ValueError(f"{item.id} has no joint '{at}'")
        if j.loc is not None:
            o, d = geom.world_point(j.loc, (0, 0, 0)), geom.world_dir(j.loc, (0, 0, 1))
        else:
            p, q = j.axis.position, j.axis.direction
            o, d = np.array([p.X, p.Y, p.Z]), np.array([q.X, q.Y, q.Z])
    else:
        o, d = np.array([_ev(v, params) for v in at]), None
    if "dir" in spec:
        d = np.array([_ev(v, params) for v in spec["dir"]])
    if d is None:
        raise ValueError(f"axis {spec} needs dir")
    return o, d / np.linalg.norm(d)


def _fea_load(item, spec, params):
    """One yaml load -> fea load dict: region keys plus force_n | pressure_mpa | torque_nmm + axis | bearing_n."""
    ld = {"pred": _region(item, spec, params)}
    vec = lambda k: tuple(_ev(v, params) for v in spec[k])  # noqa: E731
    if "force_n" in spec:
        ld["force"] = vec("force_n")
    elif "pressure_mpa" in spec:
        ld["pressure"] = _ev(spec["pressure_mpa"], params)
    elif "torque_nmm" in spec:
        if "axis" not in spec:
            raise ValueError("a torque_nmm load needs axis: {at: [x,y,z] | joint label, dir: [..]}")
        o, d = _axis(item, spec["axis"], params)
        ld.update(torque=_ev(spec["torque_nmm"], params), axis_at=o, axis_dir=d)
    elif "bearing_n" in spec:
        ld["bearing"] = vec("bearing_n")
    else:
        raise ValueError(f"load needs force_n, pressure_mpa, torque_nmm or bearing_n: {spec}")
    return ld


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
def _across_share(item) -> float:
    """Largest cos^2 (share across layers) of the part's declared load_axis in its print orientation; 0 without one."""
    from build123d import Rot
    from .checks import _axis_vec
    la = item.spec.get("load_axis")
    if la is None:
        return 0.0
    axes = [la] if isinstance(la, str) or (isinstance(la, (list, tuple)) and la and isinstance(la[0], (int, float))) else la
    rot = Rot(*item.spec.get("print_rot", [0, 0, 0]))
    return max(float(geom.world_dir(rot, tuple(_axis_vec(a)))[2]) ** 2 for a in axes)


def _pin_lever_load(proj, asm, item, spec):
    """Single-shear pivots (ENG-5): a bearing load on a pin bore of this part is really applied by the OTHER parts of
    the pin group, at their bands along the pin. When those bands' centroid is off this part's bands' centroid along
    the axis, the pin also bends this part's bore by M = (c_other - c_this) x F. Returns (extra torque load, note) or
    None (no matching pin, balanced double shear, or `single_shear: false` on the load)."""
    if "bearing_n" not in spec or "cylinder" not in spec or spec.get("single_shear") is False or asm is None:
        return None
    from . import pins as PN
    o, d = _axis(item, spec["cylinder"], proj.params or {})
    F = np.array([_ev(v, proj.params) for v in spec["bearing_n"]], dtype=float)
    inv = item.shape.location.inverse()
    for g, members in PN._collect(asm).items():
        mine, other = [], []
        for iid, s, p_w, u_w in members:
            p = geom.world_point(inv, p_w)
            u = geom.world_dir(inv, u_w)
            c = p - u * s.depth / 2                       # band centre (the hole runs `depth` into -Z of its site)
            (mine if iid == item.id else other).append((c, u))
        if not mine or not other:
            continue
        u0 = mine[0][1]
        if abs(abs(float(np.dot(u0, d))) - 1) > 1e-3 or np.linalg.norm(np.cross(mine[0][0] - o, d)) > 0.3:
            continue                                      # not this load's bore
        ct = np.mean([c for c, _ in mine], axis=0)
        co = np.mean([c for c, _ in other], axis=0)
        lever = float(np.dot(co - ct, d)) * d
        M = np.cross(lever, F)
        m = float(np.linalg.norm(M))
        if m < 1.0:
            return None
        ld = {"pred": _region(item, spec, proj.params), "torque": m, "axis_at": ct, "axis_dir": M / m}
        return ld, (f"pin '{g}' is single-shear here: the load enters {np.linalg.norm(lever):.1f} mm along the pin "
                    f"from this part's band, so a {m:.0f} N mm moment was added on the bore")
    return None


SF_MIN = {"static": 2.0, "across_layers": 3.0, "crash": 3.0, "landing": 3.0}   # docs/ENGINEERING.md section 3


@check("fea_static")
def fea_static(proj, asm, part, fixed, loads, sf=2.0, direction="xy", max_disp_mm=None, mesh_size=None, case="static"):
    """Finite-element check of one printed part under named load cases (part frame, N).
    Passes when 99.9th-percentile von Mises <= strength(direction) / sf and deflection <= max_disp_mm.
    direction: xy | z | auto (auto blends xy and z strength by the part's load_axis share across layers, cos^2 rule).
    case: static | crash | landing. sf must meet ENGINEERING.md section 3: 2.0 static along the layers, 3.0 across
    the layers (direction z, or auto with > 25 % across) and 3.0 for crash / landing cases; a lower sf fails."""
    from . import fea
    from .checks import LAYER_WARN_NZ2
    it = proj.items[part]
    mat = it.spec.get("material", "PETG")
    if case not in ("static", "crash", "landing"):
        raise ValueError(f"fea_static case '{case}': use static, crash or landing")
    if direction not in ("xy", "z", "auto"):
        raise ValueError(f"fea_static direction '{direction}': use xy, z or auto")
    nz2 = 1.0 if direction == "z" else (_across_share(it) if direction == "auto" else 0.0)
    if direction == "auto" and it.spec.get("load_axis") is None:
        raise ValueError(f"fea_static on {part}: direction auto needs the part's load_axis (or say xy / z)")
    need = max(SF_MIN[case], SF_MIN["across_layers"] if nz2 > LAYER_WARN_NZ2 else SF_MIN["static"])
    m = catalog.get(f"materials.{mat}")
    E = catalog.num(m, "youngs_modulus_mpa", "tensile_modulus_mpa", "youngs_modulus", "E_mpa")
    nu = catalog.num(m, "poisson", "poissons_ratio", default=0.38)
    shape = it.shape.located(__import__("build123d").Location())
    fl, shear_notes = [], []
    for l in loads:
        fl.append(_fea_load(it, l, proj.params))
        extra = _pin_lever_load(proj, asm, it, l)
        if extra is not None:
            fl.append(extra[0])
            shear_notes.append(extra[1])
    res = fea.static(shape, E, nu, _region(it, fixed, proj.params), fl, size=mesh_size)
    xy, z = _strength(mat, "xy"), _strength(mat, "z")
    strength = xy - (xy - z) * nz2
    allow = strength / sf
    sf_ok = sf >= need - 1e-9
    ok = sf_ok and res["max_vm_mpa"] <= allow and (max_disp_mm is None or res["max_disp_mm"] <= max_disp_mm)
    sf_msg = "" if sf_ok else (f"SF {sf} is below the ENGINEERING.md section 3 minimum {need} for this case "
                               f"({case}, {nz2 * 100:.0f} % across layers): raise sf; ")
    return {"ok": ok, "value": round(res["max_vm_mpa"], 2), "limit": round(allow, 2), "sf_min": need,
            "applied_force_n": res["applied_force_n"], "applied_moment_nmm": res["applied_moment_nmm"],
            "max_disp_mm": round(res["max_disp_mm"], 3), "max_disp_at": res.get("max_disp_at"),
            "_viz": {**res["_viz"], "allow": allow, "title": f"{part}: von Mises (MPa), limit {allow:.1f}",
                     "p999": res["max_vm_mpa"], "peak": res["max_vm_peak_mpa"]},
            "detail": sf_msg + "".join(n + "; " for n in shear_notes) + f"FEA {part}: von Mises p99.9 (MPa) vs {mat} {direction} strength / SF {sf}; "
                      f"peak {res['max_vm_peak_mpa']:.2f} MPa at {res.get('max_vm_peak_at')}, deflection {res['max_disp_mm']:.3f} mm"
                      + (f" (limit {max_disp_mm})" if max_disp_mm else "") + f" at {res.get('max_disp_at')}, {res['elements']} elements"}


def section_props(shape, origin, normal):
    """Cut `shape` with the plane (origin, normal). Returns area (mm2), centroid, unit normal n, two in-plane unit
    axes e1, e2, the 2x2 second-moment tensor S about the centroid in (e1, e2) (mm4), and boundary sample points."""
    from build123d import Compound, Plane
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    n = np.asarray(normal, float)
    n /= np.linalg.norm(n)
    faces = shape.intersect(Plane(origin=tuple(origin), z_dir=tuple(n)))
    faces = [f for f in (faces.faces() if faces is not None else []) if f.area > 1e-9]
    if not faces:
        raise ValueError(f"section plane at {list(origin)} normal {n.tolist()} does not cut the part")
    c = Compound(faces)
    g = GProp_GProps()
    BRepGProp.SurfaceProperties_s(c.wrapped, g)
    area = g.Mass()
    cg = g.CentreOfMass()
    cen = np.array([cg.X(), cg.Y(), cg.Z()])
    mi = g.MatrixOfInertia()      # J = integral(|r|^2 I - r r^T) dA about the centroid
    J = np.array([[mi.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
    S3 = np.trace(J) / 2 * np.eye(3) - J   # integral(r r^T) dA
    e1 = np.cross(n, [1.0, 0, 0] if abs(n[0]) < 0.9 else [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    E = np.stack([e1, e2])
    pts = np.array([[p.X, p.Y, p.Z] for e in c.edges() for p in (e.position_at(t) for t in np.linspace(0, 1, 17))])
    return {"area": area, "centroid": cen, "n": n, "e1": e1, "e2": e2, "S": E @ S3 @ E.T, "pts": pts,
            "faces": len(faces)}


def _point(item, at, params):
    """A load point in the part frame: a joint label on the part or an [x, y, z] list (expressions allowed)."""
    if isinstance(at, str):
        j = next((j for j in item.shape.kerf_joints if j.label == at), None)
        if j is None:
            raise ValueError(f"{item.id} has no joint '{at}'")
        loc = j.loc if j.loc is not None else __import__("build123d").Location(j.axis.position)
        return geom.world_point(loc, (0, 0, 0))
    return np.array([_ev(v, params) for v in at])


def _layer_strength(item, normal, direction):
    """Strength for normal stress along `normal` (part frame). direction 'xy'/'z' forces one; 'auto' uses the part's
    print_rot: stress along build Z is across layers. In between, blend by cos^2 of the angle to build Z."""
    mat = item.spec.get("material", "PETG")
    if direction in ("xy", "z"):
        return _strength(mat, direction), direction
    from build123d import Rot
    nz = abs(float(geom.world_dir(Rot(*item.spec.get("print_rot", [0, 0, 0])), normal)[2]))
    xy, z = _strength(mat, "xy"), _strength(mat, "z")
    return xy - (xy - z) * nz ** 2, f"auto ({nz ** 2 * 100:.0f}% across layers)"


@check("cantilever_stress")
def cantilever_stress(proj, asm, part, section, loads, sf=2.0, direction="auto", kt=1.0, load_case=""):
    """Hand-calc (beam theory) bending + axial stress at one cross-section of a printed part.
    section: {name, at: [x,y,z], normal: [nx,ny,nz]} in the part frame, normal pointing toward the loaded (free) end.
    loads: [{at: joint label | [x,y,z], force_n: [fx,fy,fz]}] on the free side. Stress = kt * max |N/A + bending|
    over the section outline (unsymmetric bending formula, so any section shape works). Torsion and shear are
    reported, not included: this is for sizing; fea_static is the proof (docs/ENGINEERING.md section 3)."""
    it = proj.items[part]
    p = proj.params
    shape = it.shape.located(__import__("build123d").Location())
    sec = section_props(shape, [_ev(v, p) for v in section["at"]], [_ev(v, p) for v in section["normal"]])
    c, n = sec["centroid"], sec["n"]
    F, M = np.zeros(3), np.zeros(3)
    for ld in loads:
        q = _point(it, ld["at"], p)
        f = np.array([_ev(v, p) for v in ld["force_n"]])
        if np.dot(q - c, n) <= 0:
            raise ValueError(f"load at {np.round(q, 1).tolist()} is not on the free side of section "
                             f"'{section.get('name', '')}' (normal must point toward the loads)")
        F += f
        M += np.cross(q - c, f)
    m1, m2 = float(M @ sec["e1"]), float(M @ sec["e2"])
    # stress sigma = k1*a + k2*b over in-plane coords (a, b); its moment about the centroid must equal M.
    (Saa, Sab), (_, Sbb) = sec["S"]
    k1, k2 = np.linalg.solve([[Sab, Sbb], [-Saa, -Sab]], [m1, m2])
    r = sec["pts"] - c
    sig = float(F @ n) / sec["area"] + k1 * (r @ sec["e1"]) + k2 * (r @ sec["e2"])
    smax = kt * float(np.max(np.abs(sig)))
    strength, how = _layer_strength(it, n, direction)
    allow = strength / sf
    name = section.get("name", "section")
    return {"ok": smax <= allow, "value": round(smax, 2), "limit": round(allow, 2),
            "detail": f"beam theory at {part} '{name}'{' / ' + load_case if load_case else ''}: max normal stress "
                      f"(MPa) vs {it.spec.get('material', 'PETG')} {how} strength {strength:.1f} / SF {sf}"
                      f"{f' x Kt {kt}' if kt != 1 else ''}; bending {np.hypot(m1, m2):.0f} N*mm, axial {F @ n:.1f} N, "
                      f"torsion {M @ n:.0f} N*mm (not included), area {sec['area']:.1f} mm2"}


def _support_polygon(shapes, tol):
    """Ground contact: mesh vertices within `tol` of the lowest point; returns (ground z, convex hull XY Nx2 CCW)."""
    from scipy.spatial import ConvexHull
    V = np.vstack([geom.mesh(s, tol=0.1, ang=0.3)[0] for s in shapes])
    z0 = float(V[:, 2].min())
    P = V[V[:, 2] <= z0 + tol][:, :2]
    try:
        h = ConvexHull(P)
    except Exception:  # noqa: BLE001  (fewer than 3 non-collinear contacts: a point or a line can't stand)
        return z0, None
    return z0, P[h.vertices]


@check("tip_over")
def tip_over(proj, asm, min_deg, support=None, poses=None, payload_g=0.0, payload_at=None, tol=0.5):
    """Static tip-over angle on a flat floor: the smallest tilt (deg) about any edge of the support polygon that
    brings the assembled CG over that edge, atan(distance CG-to-edge / CG height). Worst over `poses`.
    support: item ids that touch the floor (default: whatever is lowest). payload_g at a joint adds to the CG.
    Negative = the CG is already outside the footprint (falls over by itself)."""
    ids = [i for i, it in proj.items.items() if it.role != "keepout" and it.shape is not None]
    worst, worst_pose, worst_h = np.inf, None, None
    for pose in poses or [{}]:
        A.solve(asm, pose)
        cg, _ = req_balance.assembly_cg(proj, payload_g=payload_g, payload_at=payload_at)
        z0, hull = _support_polygon([proj.items[i].shape for i in (support or ids)], tol)
        h = cg[2] - z0
        if hull is None:
            ang = -90.0
        else:
            d = np.inf
            for a, b in zip(hull, np.roll(hull, -1, axis=0)):   # CCW hull: inside is left of each edge
                e = b - a
                d = min(d, float((e[0] * (cg[1] - a[1]) - e[1] * (cg[0] - a[0])) / np.linalg.norm(e)))
            ang = float(np.degrees(np.arctan2(d, h)))
        if ang < worst:
            worst, worst_pose, worst_h = ang, pose, h
    A.solve(asm)
    return {"ok": worst >= min_deg, "value": round(worst, 1), "limit": min_deg,
            "detail": f"static tip-over angle (deg) at pose {worst_pose}: CG {worst_h:.1f} mm above the floor"
                      + (f", incl. {payload_g} g at {payload_at}" if payload_g else "")}


def _tube(points, d):
    """Solid swept by a ball of diameter d along a polyline (cylinders per segment + balls at the corners)."""
    from build123d import Plane, Solid, Vector
    r = d / 2
    out = None
    for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
        v = b - a
        L = float(np.linalg.norm(v))
        if L < 1e-9:
            continue
        seg = Solid.make_cylinder(r, L, Plane(origin=Vector(*a), z_dir=Vector(*(v / L))))
        out = seg if out is None else out + seg
        if 0 < i:
            out += Solid.make_sphere(r).moved(__import__("build123d").Location(Vector(*a)))
    if out is None:
        raise ValueError("channel path needs at least two distinct points")
    return out


@check("channel_clear")
def channel_clear(proj, asm, path, diameter, poses=None, ignore=None, tol_frac=1e-5):
    """A declared internal channel (tendon, wire, air) is open end to end for `diameter` mm.
    path: waypoints, each {item: id, at: [x, y, z] | joint_label} in that item's frame, so the path follows the parts
    as joints move. poses: list of {joint: value} to check besides home. ignore: items the channel may pass through
    (e.g. the tendon proxy itself). value = the largest diameter that passes at every pose (bisection to 0.01 mm,
    searched up to 2 x diameter, reported to 0.01 mm); the check fails when that is below `diameter`."""
    params = proj.params
    skip = set(ignore or [])
    ids = [i for i, it in proj.items.items() if it.shape is not None and it.role != "keepout" and i not in skip]

    def world_path():
        pts = []
        for w in path:
            it = proj.items[w["item"]]
            p = _point(it, w["at"], params)
            pts.append(geom.world_point(it.shape.location, p))
        return pts

    def blocked(pts, d):
        tube = _tube(pts, d)
        tol = max(1e-7, tol_frac * tube.volume)   # relative, so a thin probe still counts a real obstruction
        hits = {}
        for i in ids:
            v = geom.overlap(proj.items[i].shape, tube)
            if v > tol:
                hits[i] = round(v, 3)
        return hits

    worst_d, worst_hits, worst_pose = 2 * float(diameter), {}, None
    for pose in [{}] + list(poses or []):
        A.solve(asm, pose)
        pts = world_path()
        hits = blocked(pts, diameter)
        if hits and not worst_hits:
            worst_hits, worst_pose = hits, pose
        lo, hi = 0.0, worst_d
        if not blocked(pts, hi):
            continue
        while hi - lo > 0.002:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if not blocked(pts, mid) else (lo, mid)
        worst_d = min(worst_d, lo)
    A.solve(asm)
    ok = worst_d >= float(diameter) - 0.002
    where = f"; blocked by {worst_hits} (mm3) at pose {worst_pose or 'home'}" if worst_hits else ""
    return {"ok": ok, "value": round(worst_d, 2), "limit": float(diameter),
            "detail": f"largest diameter open along the {len(path)}-point channel over {1 + len(poses or [])} pose(s) (mm){where}"}


SAMPLE_MM = 1.0


def _surface_points(shape) -> np.ndarray:
    """Points on a shape's surface (its own frame, Location()), no two neighbours more than SAMPLE_MM apart."""
    import trimesh
    from build123d import Location
    v, f = geom.mesh(shape.located(Location()), tol=0.05, ang=0.2)
    v, _ = trimesh.remesh.subdivide_to_size(v, f, max_edge=SAMPLE_MM, max_iter=20)
    return v


def _matrix(loc):
    tr = loc.wrapped.Transformation()
    return (np.array([[tr.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)]),
            np.array([tr.Value(i, 4) for i in (1, 2, 3)]))


def _disc_gap(disc, other, cache) -> float:
    """Upper bound (<= SAMPLE_MM high) on the gap between a prop-disc keep-out (a cylinder, frame at its bottom
    centre) and any item: the other item's sampled surface measured against the exact cylinder."""
    from build123d import Location
    if ("disc", disc.id) not in cache:
        lo, hi = geom.bbox(disc.shape.located(Location()))
        cache[("disc", disc.id)] = ((hi[0] - lo[0]) / 2, hi[2] - lo[2])
    if ("pts", other.id) not in cache:
        cache[("pts", other.id)] = _surface_points(other.shape)
    R, h = cache[("disc", disc.id)]
    Ro, to = _matrix(other.shape.location)
    Rd, td = _matrix(disc.shape.location)
    q = (cache[("pts", other.id)] @ Ro.T + to - td) @ Rd          # world -> disc frame (Rd is orthonormal)
    rho = np.hypot(q[:, 0], q[:, 1])
    dz = np.maximum(0.0, np.abs(q[:, 2] - h / 2) - h / 2)
    return float(np.min(np.hypot(np.maximum(0.0, rho - R), dz)))


@check("prop_clearance")
def prop_clearance(proj, asm, min_mm, min_between_mm=None, props=None, ignore=None, joints=None, samples=9,
                   poses=None):
    """Smallest gap from each prop disc (keep-out, proxy prop_disc) to every other prop disc (tip to tip) and to
    every other item, at home, while each moving joint sweeps its range (default: all of them) and at any extra
    coupled `poses`. Skipped: the disc's owner (its motor), allow_overlap partners and `ignore` items."""
    items = proj.items
    props = props or [i for i, it in items.items() if it.role == "keepout" and it.spec.get("proxy") == "prop_disc"]
    if not props:
        raise ValueError("no prop discs (keepouts with proxy: prop_disc) in the project")
    allowed = A._allowed(asm)
    skip = set(ignore or [])
    others = [i for i, it in items.items() if it.shape is not None and it.role != "keepout" and i not in skip]
    pairs = []
    for k, p in enumerate(props):
        pairs += [(p, q, min_between_mm if min_between_mm is not None else min_mm) for q in props[k + 1:]]
        pairs += [(p, o, min_mm) for o in others
                  if o != items[p].spec.get("owner") and frozenset((p, o)) not in allowed]
    all_pose = [{}] + list(poses or [])
    for e in asm.movable:
        if joints is None or e.name in joints:
            all_pose += [{e.name: float(v)} for v in np.linspace(e.range[0], e.range[1], samples)]
    # Exact B-rep distances cost seconds per pair on big parts, so each pose is screened with sampled surfaces
    # (points <= SAMPLE_MM apart, measured against the disc's exact cylinder: an upper bound, never more than
    # SAMPLE_MM too large), and only pairs that could still be the worst get the exact OCC distance.
    clouds = {}
    worst = None  # (margin, gap, a, b, pose, lim)
    for pose in all_pose:
        A.solve(asm, pose)
        cand = []
        for a, b, lim in pairs:
            approx = _disc_gap(items[a], items[b], clouds)
            cand.append((approx - lim, a, b, lim))
        for m_up, a, b, lim in sorted(cand):
            if worst is not None and m_up - SAMPLE_MM >= worst[0]:
                break
            g = float(items[a].shape.distance_to(items[b].shape))
            if worst is None or g - lim < worst[0]:
                worst = (g - lim, g, a, b, pose, lim)
    A.solve(asm)
    if worst is None:
        return {"ok": True, "value": None, "limit": min_mm, "detail": "nothing to check against"}
    _, g, a, b, pose, lim = worst
    return {"ok": worst[0] >= 0, "value": round(g, 2), "limit": lim,
            "detail": f"tightest prop gap (mm): {a} to {b} at pose {pose or 'home'} "
                      f"({len(props)} discs, {len(all_pose)} poses)"}


SLOW = {"fea_static"}


def run_all(proj, asm, quick: bool = False) -> list:
    out = []
    for req in proj.data.get("requirements") or []:
        kw = {k: v for k, v in req.items() if k not in ("check", "why", "id")}
        name = req["check"]
        rid = req.get("id", name)
        if quick and name in SLOW:
            out.append({"id": rid, "check": name, "why": req.get("why", ""), "ok": True, "skipped": True,
                        "value": None, "limit": None, "detail": "skipped in --quick (runs in full check/build/verify)"})
            continue
        try:
            if name not in REGISTRY:
                raise ValueError(f"unknown check '{name}' (have {sorted(REGISTRY)})")
            r = REGISTRY[name](proj, asm, **kw)
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "value": None, "limit": None, "detail": f"check failed to run: {type(e).__name__}: {e}"}
        out.append({"id": rid, "check": name, "why": req.get("why", ""), **r})
    return out


from . import req_balance  # noqa: E402,F401  (registers the balance checks: cg)
from . import req_electrical  # noqa: E402,F401  (power_budget, flight_time, run_time, connector_access)
from . import req_stops  # noqa: E402,F401  (hard_stop)
