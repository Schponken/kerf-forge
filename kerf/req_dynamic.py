"""Simulate it moving (docs/VISION.md section 2): dynamic load cases as requirement checks, each from one linear FEA
solve of the part's own stiffness.

One `fea_static` solve under a reference load set gives the stresses per newton and the load set's compliance
C = (f . u) / |F|^2 (mm/N; f . u is the external work the solver reports), i.e. the part's stiffness k = 1/C where the
load acts. Linear elasticity then scales everything:

- `impact_fea`  drop / crash: the moving mass m meets the part as a spring k. Drop from h (energy m g (h + d) = 1/2 k
  d^2): F = m g + sqrt((m g)^2 + 2 k m g h); crash at v (1/2 m v^2 = 1/2 k d^2): F = v sqrt(k m). Contact time of the
  half-sine pulse t = pi sqrt(m / k). Only the part deforms (floor and the rest rigid), so F is an upper estimate.
- `stop_impact` a joint driven into its hard stop at speed w: the moving inertia I about the joint (every item beyond
  it, from its solid's inertia and its mass) meets the stop's rotational stiffness k_t = k r^2: torque w sqrt(k_t I),
  plus the actuator's stall torque pushing on, as stop force F = M / r (r = the stop load's lever about the axis).
- `natural_freq` first bending frequency of a part carrying a mass (a motor on an arm, a camera on a mast):
  f = 1/(2 pi) sqrt(k / (m + 33/140 m_part)) (Rayleigh, cantilever with a tip mass), compared with the excitation:
  a rotor's rotation and blade-pass rates (KV x pack voltage no-load, at hover thrust by thrust ~ rpm^2) or a stated
  frequency; ok when f clears the excitation by the stated ratio (above) or band (separation).
Each check reports the scaled stress against the material strength / sf exactly as fea_static does.
"""
from __future__ import annotations

import math

import numpy as np

from . import assembly as A, catalog, geom
from .requirements import G, UNITS, _axis_world, _ev, check, fea_static

RAYLEIGH_BEAM = 33.0 / 140.0      # cantilever: share of the beam's own mass that acts at the tip (Rayleigh)


def _solve(proj, asm, part, fixed, loads, sf, direction, case, mesh_size=None):
    r = fea_static(proj, asm, part, fixed, loads, sf=sf, direction=direction, case=case, mesh_size=mesh_size)
    F0 = float(np.linalg.norm(r["applied_force_n"]))
    if F0 <= 0 or not r.get("work_nmm"):
        raise ValueError(f"{part}: the reference loads apply no net force (give force_n loads in the impact direction)")
    k = F0 * F0 / r["work_nmm"]                     # N/mm
    return r, F0, k


def _scaled(r, s, F, what):
    """fea_static's result with stresses scaled by s (linear elasticity), its plots and stress field too."""
    out = {k: v for k, v in r.items() if not k.startswith("_")}
    allow = r["limit"]
    val = r["value"] * s
    disp = r["max_disp_mm"] * s
    out.update(value=round(val, 2), max_disp_mm=round(disp, 3), applied_force_n=[round(x * s, 2) for x in r["applied_force_n"]])
    if "_field" in r and r["_field"].get("field") is not None:
        fld = dict(r["_field"]["field"])
        fld["vm"] = fld["vm"] * s
        out["_field"] = {**r["_field"], "field": fld, "disp_use": None}
    if "_viz" in r:
        v = dict(r["_viz"])
        v.update(vm=v["vm"] * s, p999=v["p999"] * s, peak=v["peak"] * s, title=f"{r['_field']['part'] if '_field' in r else ''}: "
                 f"{what}, von Mises (MPa), limit {allow:.1f}")
        out["_viz"] = v
    sf_note = r["detail"].split("FEA ")[0] if not r["detail"].startswith("FEA ") else ""
    out["ok"] = val <= allow and not sf_note
    return out, val, disp


def _story_hazard(proj, kind):
    for h in ((proj.data.get("use_story") or {}).get("goes_wrong") or []):
        if h.get("hazard") == kind and h.get("survive", True) is not False:
            return h
    raise ValueError(f"use_story has no surviving '{kind}' hazard: give height_m / speed_m_s here")


@check("impact_fea")
def impact_fea(proj, asm, part, fixed, loads, hazard=None, height_m=None, speed_m_s=None, mass_kg=None, mass_g=None,
               sf=3.0, direction="xy", mesh_size=None):
    """Drop or crash into `part`: the loads give where and in which direction it is hit (their sizes only set the
    pattern). Speed from height_m (drop), speed_m_s (crash) or the use story's hazard; mass = mass_kg / mass_g, the
    story hazard's mass_kg, or the whole assembly. Value: the scaled von Mises p99.9 (MPa) vs strength / sf."""
    from .usestory import _mass_kg
    h = _story_hazard(proj, hazard) if hazard and height_m is None and speed_m_s is None else {}
    height_m = height_m if height_m is not None else h.get("height_m")
    speed_m_s = speed_m_s if speed_m_s is not None else h.get("speed_m_s")
    if height_m is None and speed_m_s is None:
        raise ValueError("impact_fea needs height_m (drop), speed_m_s (crash) or hazard: drop|crash from the use story")
    m = float(mass_kg if mass_kg is not None else (mass_g / 1000 if mass_g is not None else h.get("mass_kg") or _mass_kg(proj)))
    case = "drop" if height_m is not None else "crash"
    r, F0, k = _solve(proj, asm, part, fixed, loads, sf, direction, case, mesh_size)
    kSI = k * 1000.0                                # N/m
    if height_m is not None:
        W = m * G
        F = W + math.sqrt(W * W + 2 * kSI * W * float(height_m))
        v = math.sqrt(2 * G * float(height_m))
        how = f"drop {float(height_m):g} m ({v:.2f} m/s)"
    else:
        v = float(speed_m_s)
        F = v * math.sqrt(kSI * m)
        how = f"crash at {v:g} m/s"
    t_ms = math.pi * math.sqrt(m / kSI) * 1000
    out, val, disp = _scaled(r, F / F0, F, how)
    out["impact"] = {"force_n": round(F, 1), "stiffness_n_mm": k, "contact_ms": round(t_ms, 2), "mass_kg": round(m, 3)}
    out["detail"] = (f"{how}, {m:.3f} kg into {part} (stiffness {k:.0f} N/mm where it is hit): peak force {F:.0f} N over a "
                     f"{t_ms:.2f} ms half-sine contact, {disp:.2f} mm deflection; von Mises p99.9 {val:.1f} MPa vs "
                     f"{r['limit']} allowed (strength / SF {sf})")
    return out


def _inertia_kgm2(proj, ids, o, d) -> float:
    """Moment of inertia (kg*m^2) of items about the axis through o along unit d (each item uniform over its solid,
    scaled to its statics mass; parallel-axis theorem from its centre of mass)."""
    from build123d import CenterOf
    from .checks import item_mass_g
    I = 0.0
    for i in ids:
        it = proj.items[i]
        if it.shape is None or it.role == "keepout":
            continue
        m = item_mass_g(it) / 1000.0
        vol = geom.volume(it.shape)
        if m <= 0 or vol <= 0:
            continue
        J = np.array(it.shape.matrix_of_inertia, dtype=float) / vol          # mm^2 per unit mass, about its CG
        c = it.shape.center(CenterOf.MASS)
        c = np.array([c.X, c.Y, c.Z]) - o
        r_perp2 = float(c @ c - (c @ d) ** 2)
        I += m * (float(d @ J @ d) + r_perp2) * 1e-6
    return I


@check("stop_impact")
def stop_impact(proj, asm, joint, part, fixed, loads, speed_dps=None, actuator=None, sf=3.0, direction="xy", mesh_size=None):
    """A joint runs into its hard stop at full speed. `part` carries the stop (loads = the stop contact and the force
    direction on it, part frame); speed_dps or the actuator's catalog speed (60 / speed_s_per_60 deg/s); inertia of
    everything beyond the joint about its axis; stall torque of the actuator keeps pushing. Value: scaled von Mises."""
    e = next((x for x in asm.edges if x.name == joint), None)
    if e is None or e.kind != "revolute":
        raise ValueError(f"stop_impact needs a revolute joint, not '{joint}'")
    servo = None
    if actuator:
        servo = catalog.get(proj.items[actuator].spec["catalog"])
    if speed_dps is None:
        if servo is None or not servo.get("speed_s_per_60"):
            raise ValueError("stop_impact needs speed_dps or an actuator with speed_s_per_60 in the catalog")
        speed_dps = 60.0 / float(servo["speed_s_per_60"])
    A.solve(asm)
    o, d = _axis_world(proj, e)
    d = d / np.linalg.norm(d)
    beyond = asm.subtree(e.child)
    I = _inertia_kgm2(proj, beyond, o, d)
    r, F0, k = _solve(proj, asm, part, fixed, loads, sf, direction, "crash", mesh_size)
    # the stop load's lever about the joint axis, in the part's own frame (the FEA frame): from its force and moment
    oP, dP = _to_part(proj, part, o), _to_part_dir(proj, part, d)
    Fv, Mv = np.array(r["applied_force_n"]), np.array(r["applied_moment_nmm"])
    M_axis = float(dP @ (Mv - np.cross(oP, Fv)))
    lever = abs(M_axis) / F0
    if lever < 1.0:
        raise ValueError(f"the stop load on {part} acts within 1 mm of the '{joint}' axis: give its contact face")
    w = math.radians(float(speed_dps))
    kt = k * 1000.0 * (lever / 1000.0) ** 2        # N*m/rad
    M_hit = w * math.sqrt(kt * I)
    M_stall = float(servo["stall_torque_kgcm"]) * G / 100.0 if servo else 0.0
    M = M_hit + M_stall
    F = M / (lever / 1000.0)
    out, val, disp = _scaled(r, F / F0, F, f"'{joint}' into its stop at {speed_dps:.0f} deg/s")
    out["impact"] = {"torque_nm": round(M, 4), "impact_torque_nm": M_hit, "inertia_kgm2": I, "force_n": round(F, 1),
                     "lever_mm": round(lever, 2), "stiffness_n_mm": k}
    out["detail"] = (f"'{joint}' hits its stop at {speed_dps:.0f} deg/s: inertia {I * 1e6:.0f} kg*mm^2 beyond it, stop "
                     f"stiffness {kt:.1f} N*m/rad at {lever:.1f} mm -> {M_hit:.3f} N*m impact"
                     + (f" + {M_stall:.3f} N*m stall" if M_stall else "") + f" = {F:.0f} N on the stop; von Mises p99.9 "
                     f"{val:.1f} MPa vs {r['limit']} allowed (strength / SF {sf})")
    return out


def _to_part(proj, part, p):
    """World point -> the part's own frame (where fea_static meshes and loads it)."""
    return np.asarray(geom.world_point(proj.items[part].shape.location.inverse(), tuple(float(x) for x in p)), float)


def _to_part_dir(proj, part, d):
    a = _to_part(proj, part, (0, 0, 0))
    b = _to_part(proj, part, d)
    v = b - a
    return v / np.linalg.norm(v)


def rotor_hz(proj, motor, throttle="hover", blades=None, prop=None):
    """(rotation Hz, blade-pass Hz) of a motor's rotor: no-load speed KV x pack voltage at full, and at hover the
    speed where its thrust carries 1/n of the all-up weight (thrust ~ rpm^2 from the catalog's max thrust)."""
    from .usestory import _mass_kg
    it = proj.items[motor]
    mc = catalog.get(it.spec["catalog"])
    kv = mc.get("kv")
    if not kv:
        raise ValueError(f"{motor}: catalog entry has no kv")
    v = float(mc.get("thrust_test_v") or 0)
    pack = (proj.data.get("electrical") or {}).get("battery")
    if pack:
        b = catalog.get(proj.items[pack].spec["catalog"])
        v = 3.7 * float(b["cells"])                 # nominal cell voltage
    rpm_full = float(kv) * v
    if throttle == "hover":
        n = sum(1 for i in proj.items.values() if i.spec.get("catalog") == it.spec["catalog"])
        w_g = _mass_kg(proj) * 1000 / max(n, 1)
        rpm = rpm_full * math.sqrt(min(1.0, w_g / float(mc["thrust_g_max"])))
    elif throttle == "max":
        rpm = rpm_full
    else:
        rpm = rpm_full * float(throttle)
    if blades is None and prop:
        blades = catalog.get(proj.items[prop].spec["catalog"]).get("blades")
    return rpm / 60.0, rpm / 60.0 * float(blades or 1)


@check("natural_freq")
def natural_freq(proj, asm, part, fixed, loads, carried_g=None, carried=None, excitation=None, min_ratio=None,
                 separation=None, mesh_size=None, direction="xy"):
    """First natural frequency of `part` carrying a mass where `loads` act (their direction = the vibration
    direction): carried_g, or the statics masses of the `carried` items, plus 33/140 of the part's own mass.
    excitation: {hz: f} | {motor: id, throttle: hover | max | 0..1, blades: n | prop: id}. Pass rule (state one):
    min_ratio (f_n >= ratio x the highest excitation) or separation (every excitation at least that fraction away)."""
    from .checks import item_mass_g
    r, F0, k = _solve(proj, asm, part, fixed, loads, 2.0, direction, "static", mesh_size)
    m_c = (float(carried_g) if carried_g is not None else sum(item_mass_g(proj.items[i]) for i in carried or [])) / 1000
    m_p = item_mass_g(proj.items[part]) / 1000
    m = m_c + RAYLEIGH_BEAM * m_p
    fn = math.sqrt(k * 1000.0 / m) / (2 * math.pi)
    ex = []
    if excitation:
        if "hz" in excitation:
            ex = [float(_ev(excitation["hz"], proj.params))]
        else:
            ex = list(rotor_hz(proj, excitation["motor"], excitation.get("throttle", "hover"),
                               excitation.get("blades"), excitation.get("prop")))
    if min_ratio is None and separation is None and ex:
        raise ValueError("natural_freq needs min_ratio or separation (say how far from the excitation it must be)")
    worst = None
    if ex and min_ratio is not None:
        worst = fn / max(ex)
        ok = worst >= float(min_ratio)
        rule = f"f_n / highest excitation = {worst:.2f} (min {min_ratio})"
    elif ex:
        worst = min(abs(e - fn) / fn for e in ex)
        ok = worst >= float(separation)
        rule = f"nearest excitation {worst * 100:.0f} % away (min {float(separation) * 100:.0f} %)"
    else:
        ok, rule = True, "no excitation stated"
    return {"ok": ok, "value": round(fn, 1), "limit": [round(e, 1) for e in ex], "stiffness_n_mm": k, "mass_kg": m,
            "detail": f"{part}: stiffness {k:.1f} N/mm where the mass sits, {m_c * 1000:.1f} g carried + 33/140 of its own "
                      f"{m_p * 1000:.1f} g -> f_n {fn:.0f} Hz; excitation {', '.join(f'{e:.0f} Hz' for e in ex) or '-'}; {rule}"}


UNITS.update({"impact_fea": ("MPa", "max"), "stop_impact": ("MPa", "max"), "natural_freq": ("Hz", "vs excitation")})
