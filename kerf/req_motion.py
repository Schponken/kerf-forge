"""Requirements proven by simulating the assembly in MuJoCo (kerf/sim.py): a grip that holds under shaking, a move
that finishes in time on the servos' real torque and speed, and the force of a drop fed to the part's FEA."""
from __future__ import annotations

import math

import numpy as np

from . import assembly as A, catalog, geom, sim
from .requirements import check


def _mu(value) -> tuple[float, str]:
    """(static friction coefficient, where it came from): a number stated in project.yaml, or a catalog key
    'friction.<pair>' (its `mu_static`, sourced)."""
    if isinstance(value, (int, float)):
        return float(value), "stated in project.yaml"
    e = catalog.get(value if str(value).startswith("friction.") else f"friction.{value}")
    return float(catalog.num(e, "mu_static")), f"catalog {value}"


@check("grip_hold")
def grip_hold(proj, asm, joint, pads, mass_g, friction, width_mm, size_mm=None, pad_t_mm=(6.0, 6.0),
              pad_mm=(8.0, 6.0), pose=None, torque_fraction=0.5, shake_g=1.0, shake_hz=2.0, max_slip_mm=1.0,
              actuator=None):
    """An object of mass_g / width_mm, friction (number or catalog 'friction.<pair>') at both jaw pads, squeezed by
    the servo on `joint` at torque_fraction of its stall torque, the arm locked at `pose`, shaken at shake_g (1 g)
    along three axes on top of gravity. value = the worst slip of the object across the jaws (mm)."""
    mu, src = _mu(friction)
    M = sim.load(proj, asm, actuators={joint: actuator} if actuator else None, refs=list(pads))
    r = sim.grip(M, joint, list(pads), float(mass_g), mu, float(width_mm), size_mm, tuple(pad_t_mm), tuple(pad_mm),
                 pose, float(torque_fraction), float(shake_g), float(shake_hz))
    worst = max(r["slip_mm"].values())
    return {"ok": worst <= max_slip_mm, "value": round(worst, 3), "limit": float(max_slip_mm),
            "detail": f"{mass_g:g} g, {width_mm:g} mm object, mu {mu:g} ({src}); '{joint}' servo at {torque_fraction:g} x stall "
                      f"squeezes {r['squeeze_n']} N ({r['lever_mm']} mm lever at {r['grip_deg']} deg); slip (mm) under "
                      f"{shake_g:g} g shake + gravity: {r['slip_mm']}; by hand it lets go above {r['hand_slip_mass_g']} g "
                      f"(2 mu N = m (1 + {shake_g:g}) g)"}


@check("joint_speed")
def joint_speed(proj, asm, end, max_s, start=None, payload_g=0.0, payload_at=None, band_deg=sim.BAND_DEG):
    """Command every servo from pose `start` (default home) to `end`; the servos have the catalog stall torque and
    no-load speed. value = the time (s) after which every driven joint stays within band_deg of its target
    (None = never: the servo torque cannot get it there or hold it)."""
    M = sim.load(proj, asm, refs=[payload_at] if payload_at else ())
    if not M.servos:
        raise ValueError("joint_speed: no joint is driven by a catalog servo")
    r = sim.move(M, start or {}, end, float(max_s), float(payload_g), payload_at, float(band_deg))
    t = r["time_s"]
    lim = {j: f"{M.servos[j]['stall_nm']:.2f} N*m, {math.degrees(M.servos[j]['w0']):.0f} deg/s" for j in M.servos}
    return {"ok": t is not None and t <= max_s, "value": t, "limit": float(max_s),
            "detail": f"{start or {}} -> {end} with {payload_g:g} g at {payload_at}; peak torque / stall {r['peak_fraction']}; "
                      f"final error (deg) {r['final_error_deg']}; servos (stall, no-load speed): {lim}"
                      + ("" if t is not None else f"; NOT reached within {r['sim_s']} s")}


def _hit_world(M, mj, d, ref):
    link, p = M.local(ref)
    b = mj.body(link)
    return d.xpos[b.id] + d.xmat[b.id].reshape(3, 3) @ p


def _rot_down(down):
    """Rotation taking unit vector `down` onto -Z (the assembly falls in that orientation)."""
    a = np.asarray(down, float) / np.linalg.norm(down)
    b = np.array([0.0, 0.0, -1.0])
    v, c = np.cross(a, b), float(np.dot(a, b))
    if c < -0.999999:
        return np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


@check("drop_impact")
def drop_impact(proj, asm, part, at, height_mm, radius_mm, subtree=None, pose=None, down=(0, 0, -1), floor=None,
                payload_g=0.0, payload_at=None, fea=None, max_force_n=None):
    """Everything downstream of joint `subtree` (the whole assembly when omitted) held rigid at `pose` and dropped
    height_mm onto a hard floor, landing on point `at` (item.label) of `part` with `down` (assembly frame) pointing at
    the floor. Contact: Hertz (the part's catalog E and Poisson, radius_mm = the radius of the surface that hits; floor
    rigid or a catalog material) in series with the part's own stiffness at that point (FEA under 1 N, when `fea` is
    given), undamped. value = peak contact force (N). With `fea: {fixed, direction, sf, max_disp_mm, mesh_size,
    radius}` that force goes to fea_static (case crash) at the hit point and limit = the largest force the part takes
    (the FEA is linear); otherwise limit = max_force_n."""
    from .requirements import fea_static
    if fea is None and max_force_n is None:
        raise ValueError("drop_impact: give fea (the part's FEA set-up) or max_force_n")
    pose = pose or {}
    refs = [at] + ([payload_at] if payload_at else [])
    M = sim.load(proj, asm, refs=refs)
    pay = None
    m0, c0, I0, (mj, d) = sim.subtree_inertia(M, pose, subtree)
    if payload_g and payload_at:
        pay = (payload_g / 1000.0, _hit_world(M, mj, d, payload_at))
        m0, c0, I0, (mj, d) = sim.subtree_inertia(M, pose, subtree, pay)
    hit = _hit_world(M, mj, d, at)
    R = _rot_down(down)
    rel, I = R @ (hit - c0), R @ I0 @ R.T
    mat = proj.items[part].spec.get("material", "PETG")
    me = catalog.get(f"materials.{mat}")
    E, nu = catalog.num(me, "youngs_modulus_mpa"), catalog.num(me, "poisson", default=0.38)
    fE, fnu = (None, 0.3)
    if floor and floor != "rigid":
        fe = catalog.get(f"materials.{floor}")
        fE, fnu = catalog.num(fe, "youngs_modulus_mpa"), catalog.num(fe, "poisson", default=0.3)
    K = sim.hertz_k(E, nu, float(radius_mm), fE, fnu)
    # the force on the part, in the part's own frame (fea loads are in the part frame)
    A.solve(asm, pose)
    try:
        f_dir = geom.world_dir(proj.items[part].shape.location.inverse(), -np.asarray(down, float))
    finally:
        A.solve(asm)
    ks, unit = None, None
    label = at.split(".", 1)[1]
    if fea:
        spec = dict(fea)
        rad = spec.pop("radius", 5.0)
        kw = {k: spec[k] for k in ("direction", "sf", "max_disp_mm", "mesh_size") if k in spec}
        unit = fea_static(proj, asm, part, spec["fixed"], [{"near_joint": label, "radius": rad, "force_n": f_dir.tolist()}],
                          case="crash", **kw)
        ks = 1000.0 / unit["max_disp_mm"] if unit["max_disp_mm"] > 0 else None      # N/m
    r = sim.drop_body(m0, I, rel, float(height_mm) / 1000.0, K, ks)
    F = r["peak_n"]
    head = (f"{m0 * 1000:.0f} g ({'all' if subtree is None else 'beyond ' + subtree}{f' + {payload_g:g} g payload' if pay else ''}) "
            f"dropped {height_mm:g} mm onto {at} ({mat} R {radius_mm:g} mm on a {'rigid floor' if fE is None else floor}); "
            f"{r['v_mps']:.2f} m/s; contact {r['contact_s'] * 1000:.2f} ms; "
            f"structure {'rigid' if ks is None else f'{ks / 1000:.1f} N/mm (FEA, 1 N at the hit point)'}; "
            f"Hertz alone would give {sim.hertz_peak(K, m0, r['v_mps']):.0f} N for a centred hit")
    if not fea:
        return {"ok": F <= max_force_n, "value": round(F, 1), "limit": float(max_force_n), "detail": head}
    res = fea_static(proj, asm, part, fea["fixed"], [{"near_joint": label, "radius": fea.get("radius", 5.0),
                                                       "force_n": (F * f_dir).tolist()}], case="crash", **kw)
    take = F * res["limit"] / res["value"] if res["value"] > 0 else float("inf")
    ok = bool(res["ok"]) and (max_force_n is None or F <= max_force_n)
    return {"ok": ok, "value": round(F, 1), "limit": round(take, 1),
            "fea": {k: res[k] for k in ("value", "limit", "max_disp_mm", "max_disp_at")},
            "_viz": res.get("_viz"), "_field": res.get("_field"),
            "detail": head + f"; fea_static (crash) with {F:.0f} N: {res['detail']}"}
