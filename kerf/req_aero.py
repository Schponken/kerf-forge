"""Fixed-wing requirement checks (flying wings first): static margin, wing loading, stall speed, spar bending.

The wing is the project's planform, read from params with a prefix (default `wing_`: wing_span, wing_root_chord,
wing_tip_chord, wing_sweep_le_deg, wing_dihedral_deg, wing_twist_tip_deg, wing_x_le0, wing_z0, wing_airfoil) - the
same numbers the wing parts are built from (kerf/aero.py Planform.from_params), so the checks judge the real wing.
Formulas and their sources: docs/ENGINEERING.md "Fixed wing".
"""
from __future__ import annotations

import math
from types import SimpleNamespace

from . import aero, catalog
from .req_balance import assembly_cg
from .requirements import check, item_mass_g


def _pf(proj, wing: str = "wing_") -> aero.Planform:
    p = SimpleNamespace(**proj.params)
    if not hasattr(p, wing + "span"):
        raise ValueError(f"no wing planform: params need {wing}span, {wing}root_chord, {wing}tip_chord (and sweep, "
                         f"twist, x_le0, airfoil) - see kerf/aero.py Planform.from_params")
    return aero.Planform.from_params(p, wing)


def _mass(proj) -> float:
    from .electrical import wiring_mass_g
    return sum(item_mass_g(it) for it in proj.items.values() if it.role != "keepout") + wiring_mass_g(proj)


@check("static_margin")
def static_margin(proj, asm, min=0.05, max=0.15, wing="wing_"):
    """(neutral point x - CG x) / MAC. Neutral point of a tailless wing = its aerodynamic centre, the quarter-chord
    point of the mean aerodynamic chord. CG = the assembled CG of every item and wire at the home pose."""
    pf = _pf(proj, wing)
    g = pf.geometry()
    cg, M = assembly_cg(proj)
    sm = (g["x_np_mm"] - float(cg[0])) / g["mac_mm"]
    return {"ok": min - 1e-9 <= sm <= max + 1e-9, "value": round(sm, 4), "limit": [min, max], "bound": "range",
            "unit": "x MAC", "cg_x_mm": round(float(cg[0]), 1), "np_x_mm": round(g["x_np_mm"], 1), "mac_mm": round(g["mac_mm"], 1),
            "detail": f"neutral point x {g['x_np_mm']:.1f} mm (quarter of the {g['mac_mm']:.1f} mm MAC at y {g['y_mac_mm']:.1f}, "
                      f"its LE at x {g['x_le_mac_mm']:.1f}), CG x {float(cg[0]):.1f} mm for {M:.0f} g: margin "
                      f"{sm * 100:.1f} % MAC (CG {'ahead of' if sm > 0 else 'behind'} the NP)"}


@check("wing_loading")
def wing_loading(proj, asm, max_g_dm2, wing="wing_"):
    """All-up mass / wing area (the whole trapezoid, centre section included)."""
    pf = _pf(proj, wing)
    S = pf.geometry()["area_dm2"]
    m = _mass(proj)
    v = m / S
    return {"ok": v <= max_g_dm2, "value": round(v, 1), "limit": max_g_dm2, "bound": "max", "unit": "g/dm²",
            "detail": f"{m:.0f} g / {S:.2f} dm² wing area"}


@check("stall_speed")
def stall_speed(proj, asm, max_kmh, cl_max=None, airfoil=None, re=None, wing="wing_"):
    """Level-flight stall speed sqrt(2 W / (rho S CLmax)) at sea level. CLmax of the wing = 0.9 x the airfoil's 2D
    clmax x cos(quarter-chord sweep) (Raymer, Aircraft Design: A Conceptual Approach, eq. 12.15) from
    catalog/airfoils/airfoils.json at the highest listed Reynolds number not above `re` (default: the lowest listed,
    the conservative one), unless `cl_max` (the wing's) is given."""
    pf = _pf(proj, wing)
    g = pf.geometry()
    how = "given"
    if cl_max is None:
        af = airfoil or pf.root_airfoil
        cl2, at = aero.clmax_2d(af, re)
        cl_max = 0.9 * cl2 * math.cos(math.radians(g["sweep_c4_deg"]))
        how = f"0.9 x {af} clmax {cl2:g} (Re {at:,.0f}) x cos({g['sweep_c4_deg']:.1f} deg quarter-chord sweep)"
    m = _mass(proj)
    v = aero.stall_speed_kmh(m, g["area_mm2"] / 1e6, cl_max)
    return {"ok": v <= max_kmh, "value": round(v, 1), "limit": max_kmh, "bound": "max", "unit": "km/h",
            "cl_max": round(cl_max, 3),
            "detail": f"{m:.0f} g, {g['area_dm2']:.2f} dm², CLmax {cl_max:.3f} ({how}), sea level"}


@check("spar_bending")
def spar_bending(proj, asm, tubes, y_root, load_factor=6.0, sf=1.5, wing="wing_"):
    """Bending stress in a wing half's spar tube(s) at span station `y_root` (where they leave the centre section)
    with the all-up mass at `load_factor` g on an elliptical lift distribution. `tubes`: catalog paths of the tubes in
    ONE half; they share the moment by bending stiffness E I. Limit = the tube's flexural (else tensile) strength / sf."""
    pf = _pf(proj, wing)
    m = _mass(proj)
    M = aero.root_moment_nmm(m, float(load_factor), pf.semi, float(y_root))
    rows = []
    for path in tubes:
        e = catalog.get(path)
        D = catalog.num(e, "od_mm", "outer_d_mm", "od")
        d = catalog.num(e, "id_mm", "inner_d_mm", "id", default=0.0)
        E = catalog.num(e, "modulus_gpa", "flexural_modulus_gpa", "youngs_modulus_gpa", default=None)
        S = catalog.num(e, "flexural_strength_mpa", "tensile_strength_mpa", "strength_mpa")
        I = math.pi / 64 * (D ** 4 - d ** 4)
        rows.append({"path": path, "D": D, "d": d, "E": E or 1.0, "S": S, "I": I})
    EI = sum(r["E"] * r["I"] for r in rows)
    worst, txt = 0.0, []
    for r in rows:
        Mi = M * r["E"] * r["I"] / EI
        sig = Mi * (r["D"] / 2) / r["I"]
        use = sig / (r["S"] / sf)
        worst = max(worst, use)
        txt.append(f"{r['path'].split('.')[-1]} {r['D']:g}x{r['d']:g} mm: {sig:.0f} MPa of {r['S']:g}/{sf:g}")
    return {"ok": worst <= 1.0, "value": round(worst, 4), "limit": 1.0, "bound": "max", "unit": "x allowable",
            "load_factor": float(load_factor), "moment_nmm": round(M),
            "detail": f"{m:.0f} g at {load_factor:g} g, elliptical lift: {M / 1000:.2f} N m at y {y_root:g} mm; " + "; ".join(txt)}
