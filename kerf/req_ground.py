"""Steady uphill wheel-drive sizing from declared torque and terrain measurements.

Independent, equal-radius drives: sum each wheel's smaller motor/traction limit. This is a force budget,
not a contact simulation or proof of speed, starting, braking, stability, or electrical endurance.
Sources, assumptions and the input contract are in docs/ENGINEERING.md (Ground robots).
"""
from __future__ import annotations

import math

from .checks import item_mass_g
from .electrical import wiring_mass_g
from .requirements import G, REDESIGN_TIER, UNITS, _ev, check


def _number(value, params, name):
    try:
        if isinstance(value, bool):
            raise ValueError
        n = _ev(value, params)
        if not math.isfinite(n):
            raise ValueError
        return n
    except (ValueError, TypeError, OverflowError, NameError, SyntaxError, ZeroDivisionError):
        raise ValueError(f"wheel_drive: {name} must be a finite number or parameter expression") from None


@check("wheel_drive")
def wheel_drive(proj, asm, wheel_radius_mm, wheel_torque_nm, slope_deg, rolling_coeff, traction_mu,
                normal_load_fractions, torque_basis, terrain_basis, include=None, payload_g=0.0):
    """Sustained straight climb: F = mg(sin(slope) + Crr*cos(slope)), vs sum min(T/r, mu*N_i).

    normal_load_fractions: each independently driven wheel's share of total normal load at this slope/payload,
    including any load transfer; sum <= 1 (the remainder is on passive wheels). Torque is continuous wheel-side
    torque at the intended operating speed, after gearbox losses. Both bases must cite sources/measurements.
    include follows mass_max: explicit item masses only; otherwise all non-keepouts plus declared wiring.
    """
    p = proj.params
    r, torque, slope, crr, mu, payload = (
        _number(v, p, k) for k, v in (("wheel_radius_mm", wheel_radius_mm), ("wheel_torque_nm", wheel_torque_nm),
                                     ("slope_deg", slope_deg), ("rolling_coeff", rolling_coeff),
                                     ("traction_mu", traction_mu), ("payload_g", payload_g)))
    if r <= 0 or torque < 0 or crr < 0 or mu < 0 or payload < 0 or not 0 <= slope < 90:
        raise ValueError("wheel_drive: radius must be positive; torque, rolling_coeff, traction_mu and payload "
                         "nonnegative; uphill slope_deg must be in [0, 90)")
    if not isinstance(normal_load_fractions, (list, tuple)) or not normal_load_fractions:
        raise ValueError("wheel_drive: normal_load_fractions needs one share per driven wheel")
    fractions = [_number(v, p, "normal_load_fractions") for v in normal_load_fractions]
    if any(not 0 <= f <= 1 for f in fractions) or math.fsum(fractions) > 1:
        raise ValueError("wheel_drive: normal_load_fractions must be nonnegative and sum to at most 1")
    for name, basis in (("torque_basis", torque_basis), ("terrain_basis", terrain_basis)):
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError(f"wheel_drive: {name} needs a source/measurement rationale for the declared inputs")
    if include is not None and (not isinstance(include, (list, tuple)) or not include or
                                any(not isinstance(i, str) for i in include) or len(set(include)) != len(include)):
        raise ValueError("wheel_drive: include must be a nonempty list of unique item ids")
    ids = include if include is not None else [i for i, it in proj.items.items() if it.role != "keepout"]
    masses = []
    for i in ids:
        it = proj.items.get(i)
        if it is None or it.role == "keepout" or it.shape is None:
            raise ValueError(f"wheel_drive: {i!r} must be a built, mass-bearing item")
        m = _number(item_mass_g(it), {}, f"mass of {i}")
        if m <= 0:
            raise ValueError(f"wheel_drive: {i!r} has no positive modeled mass; add a sourced catalog weight or "
                             "mass_g, or fix its printed geometry/material")
        masses.append(m)
    if include is None:
        for w in proj.data.get("wiring") or []:
            if "length_mm" in w and _number(w["length_mm"], {}, "wire length_mm") < 0:
                raise ValueError("wheel_drive: wire length_mm must be nonnegative")
            if "conductors" in w:
                n = _number(w["conductors"], {}, "wire conductors")
                if n < 1 or not n.is_integer():
                    raise ValueError("wheel_drive: wire conductors must be a positive integer")
    wire_g = 0.0 if include is not None else _number(wiring_mass_g(proj), {}, "wiring mass")
    if wire_g < 0:
        raise ValueError("wheel_drive: wiring mass must be nonnegative; check wire lengths and conductors")
    mass_g = sum(masses) + wire_g + payload
    if not math.isfinite(mass_g) or mass_g <= 0:
        raise ValueError("wheel_drive: modeled total mass must be finite and positive")
    radius_m = r / 1000
    if radius_m == 0:
        raise ValueError("wheel_drive: wheel_radius_mm is too small to represent in metres")
    angle = math.radians(slope)
    weight = mass_g / 1000 * G
    normal = weight * math.cos(angle)
    grade = weight * math.sin(angle)
    rolling = crr * normal
    required = grade + rolling
    motor_per_wheel = torque / radius_m
    traction = [mu * normal * f for f in fractions]
    available = [min(motor_per_wheel, t) for t in traction]
    limit = sum(available)
    required_torque = required * radius_m
    if not all(math.isfinite(v) for v in (normal, grade, rolling, required, motor_per_wheel, limit,
                                         required_torque, *traction)):
        raise ValueError("wheel_drive: inputs produce non-finite forces or torque")
    motor_limited = [motor_per_wheel <= t for t in traction]
    limiting = "motor torque" if all(motor_limited) else "traction" if not any(motor_limited) else "mixed"
    return {"ok": required <= limit, "value": required, "limit": limit,
            "mass_g": mass_g, "grade_force_n": grade, "rolling_force_n": rolling,
            "motor_force_per_wheel_n": motor_per_wheel, "traction_per_wheel_n": traction,
            "available_per_wheel_n": available, "required_total_torque_nm": required_torque,
            "limiting": limiting,
            "detail": f"steady straight uphill force {required:.3g} N vs {limit:.3g} N ({limiting}); "
                      f"{mass_g:.3g} g at {slope:g} deg, total demanded wheel torque {required_torque:.3g} N*m. "
                      "Declared independent drives and wheel loads; no starting, braking, speed, tip-over or runtime proof. "
                      f"Torque basis: {torque_basis.strip()}; terrain/load basis: {terrain_basis.strip()}"}


UNITS["wheel_drive"] = ("N", "max")
REDESIGN_TIER["wheel_drive"] = 0
