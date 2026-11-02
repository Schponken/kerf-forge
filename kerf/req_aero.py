"""Fixed-wing requirement checks (flying wings first): static margin, wing loading, stall speed, spar bending.

The wing is the project's planform, read from params with a prefix (default `wing_`: wing_span, wing_root_chord,
wing_tip_chord, wing_sweep_le_deg, wing_dihedral_deg, wing_twist_tip_deg, wing_x_le0, wing_z0, wing_airfoil) - the
same numbers the wing parts are built from (kerf/aero.py Planform.from_params), so the checks judge the real wing.
Formulas and their sources: docs/ENGINEERING.md "Fixed wing".
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np

from . import aero, catalog
from .req_balance import assembly_cg
from .requirements import UNITS, check, item_mass_g


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


# ---------------------------------------------------------------- conventional aircraft, pivoting (folding) wings
def _home_to_pose(proj, asm, items, pose):
    """{item: Location T} carrying each item from its home placement to its placement at `pose` (planform points
    are in the home frame, so T applied to them follows a wing half that pivots or folds)."""
    from build123d import Location
    if not items:
        return {}
    from . import assembly as A
    A.solve(asm)
    home = {i: Location(proj.items[i].shape.location) for i in items}
    A.solve(asm, pose or {})
    return {i: proj.items[i].shape.location * home[i].inverse() for i in items}


def _half_strips(pf, y0, y1, side, n, T=None, frac=0.5):
    """Spanwise strips of one wing half (|y| from y0 to y1, side +1 right / -1 left), moved by T: per strip the four
    planform corners (XY), the quarter-chord and `frac`-chord points at mid-strip, its true area (mm2)."""
    from .geom import world_point
    mv = (lambda q: world_point(T, q)) if T is not None else (lambda q: np.asarray(q, float))
    ys = np.linspace(y0, y1, n + 1)
    out = []
    for a, b in zip(ys[:-1], ys[1:]):
        m = (a + b) / 2
        pt = lambda y, f: mv((pf.x_le(y) + f * pf.chord(y), side * y, pf.z_le(y)))
        out.append({"corners": np.array([pt(a, 0), pt(b, 0), pt(b, 1), pt(a, 1)]), "qc": pt(m, 0.25), "fc": pt(m, frac),
                    "mid": pt(m, 0.5), "area": pf.chord(m) * (b - a), "root": pt(a, frac), "tip": pt(b, frac)})
    return out


def _proj_area(c) -> float:
    x, y = c[:, 0], c[:, 1]
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 2


def _thick_frac(pf) -> float:
    try:
        return float(aero.airfoil_data(pf.root_airfoil).get("thickness_x_pct", 30.0)) / 100
    except ValueError:
        return 0.30                                    # NACA 4-digit sections are thickest at 30 % chord


def wing_at_pose(proj, asm, wing="wing_", halves=None, root_y=0.0, pose=None, strips=40):
    """Projected wing at a pose: area (mm2), span (mm), aspect ratio, sweep of the thickest-point line (deg, area
    weighted over the halves), aerodynamic centre x (area-weighted quarter-chord points: strip theory) and the moved
    strips. `halves`: {right: item, left: item} carrying |y| >= root_y; the centre strip |y| < root_y stays put."""
    pf = _pf(proj, wing)
    frac = _thick_frac(pf)
    T = _home_to_pose(proj, asm, list((halves or {}).values()), pose)
    parts = []
    for side, key in ((1, "right"), (-1, "left")):
        it = (halves or {}).get(key)
        if root_y > 0:
            parts.append(("centre", _half_strips(pf, 0.0, root_y, side, max(2, strips // 10), None, frac)))
        parts.append((key, _half_strips(pf, root_y, pf.semi, side, strips, T.get(it) if it else None, frac)))
    allc = np.vstack([s["corners"] for _, ss in parts for s in ss])
    span = float(allc[:, 1].max() - allc[:, 1].min())
    S = sum(_proj_area(s["corners"]) for _, ss in parts for s in ss)
    x_ac = sum(_proj_area(s["corners"]) * s["qc"][0] for _, ss in parts for s in ss) / S
    sw, wsum = 0.0, 0.0
    for key, ss in parts:
        if key == "centre":
            continue
        v = ss[-1]["tip"] - ss[0]["root"]
        a = sum(_proj_area(s["corners"]) for s in ss)
        sw += a * math.degrees(math.atan2(v[0], abs(v[1]))); wsum += a
    return {"area_mm2": S, "span_mm": span, "aspect": span ** 2 / S, "sweep_deg": sw / wsum, "x_ac_mm": x_ac,
            "thick_frac": frac, "parts": parts, "pf": pf}


@check("static_margin_tail")
def static_margin_tail(proj, asm, min=0.05, max=0.25, wing="wing_", tail="htail_", halves=None, root_y=0.0, pose=None,
                       eta_t=0.9, eta=0.95, downwash=None, fuselage=None, strips=40):
    """Static margin of a wing + horizontal-tail aircraft, (x_NP - x_CG) / MAC of the spread (home) wing, at the home
    pose or at `pose` (e.g. wings swept back).
    Wing: the `wing` planform, projected at the pose (`halves` {right: item, left: item} move |y| >= root_y with those
    items); lift slope a_w = aero.lift_slope(A, sweep of the thickest-point line) (Raymer eq. 12.6), aerodynamic centre
    = area-weighted quarter-chord points (strip theory). Tail: the `tail` planform (its own x_le0), a_t likewise, AC at
    its quarter MAC, efficiency eta_t (0.9). Downwash d(eps)/d(alpha) = 2 a_w / (pi A_w) (elliptic loading, far field;
    Raymer sec. 16.3) unless `downwash` is given. Neutral point = (a_w S_w x_w + eta_t a_t S_t (1 - deps) x_t) /
    (a_w S_w + eta_t a_t S_t (1 - deps)), moved forward by an optional fuselage term (Raymer eq. 16.25: Cm_alpha_fus =
    K_fus W_f^2 L_f / (c S_w) per deg; `fuselage: {length_mm, width_mm, k_fus}`, K_fus from Raymer fig. 16.14).
    CG = the assembled CG of every item and wire at the pose."""
    from . import assembly as A
    from .requirements import _ev
    root_y = _ev(root_y, proj.params or {})            # a number or an expression over params / layout ("pivot_y")
    w = wing_at_pose(proj, asm, wing, halves, root_y, pose, strips)
    cg, M = assembly_cg(proj)
    if halves:
        A.solve(asm)
    ref = w["pf"].geometry()
    mac = ref["mac_mm"]
    a_w = aero.lift_slope(w["aspect"], w["sweep_deg"], eta)
    tp = _pf(proj, tail)
    tg = tp.geometry()
    t_sweep = math.degrees(math.atan(math.tan(math.radians(tp.sweep_le_deg))
                                     - _thick_frac(tp) * 2 * (tp.root_chord - tp.tip_chord) / tp.span))
    a_t = aero.lift_slope(tg["aspect_ratio"], t_sweep, eta)
    deps = float(downwash) if downwash is not None else 2 * a_w / (math.pi * w["aspect"])
    deps = float(np.clip(deps, 0.0, 0.95))            # (min / max are the limits here)
    Sw, St = w["area_mm2"], tg["area_mm2"]
    kt = eta_t * a_t * St * (1 - deps)
    x_np = (a_w * Sw * w["x_ac_mm"] + kt * tg["x_np_mm"]) / (a_w * Sw + kt)
    cla = a_w + kt / Sw
    fus_txt = ""
    if fuselage:
        cma_f = float(fuselage["k_fus"]) * float(fuselage["width_mm"]) ** 2 * float(fuselage["length_mm"]) / (mac * Sw) * 180 / math.pi
        dx = cma_f / cla * mac
        x_np -= dx
        fus_txt = f"; fuselage Cm_alpha +{cma_f:.3f}/rad moves it {dx:.1f} mm forward"
    sm = (x_np - float(cg[0])) / mac
    vh = St * (tg["x_np_mm"] - float(cg[0])) / (Sw * mac)
    return {"ok": min - 1e-9 <= sm <= max + 1e-9, "value": round(sm, 4), "limit": [min, max], "bound": "range",
            "unit": "x MAC", "pose": pose or {}, "cg_x_mm": round(float(cg[0]), 1), "np_x_mm": round(x_np, 1),
            "wing_ac_x_mm": round(w["x_ac_mm"], 1), "tail_ac_x_mm": round(tg["x_np_mm"], 1),
            "wing": {"area_dm2": round(Sw / 1e4, 2), "span_mm": round(w["span_mm"], 1), "aspect": round(w["aspect"], 2),
                     "sweep_deg": round(w["sweep_deg"], 1), "lift_slope_per_rad": round(a_w, 3)},
            "tail": {"area_dm2": round(St / 1e4, 2), "lift_slope_per_rad": round(a_t, 3), "volume": round(vh, 3)},
            "downwash": round(deps, 3), "cl_alpha_per_rad": round(cla, 3),
            "detail": f"{'pose ' + str(pose) if pose else 'home'}: wing {Sw / 1e4:.2f} dm², span {w['span_mm']:.0f} mm, "
                      f"A {w['aspect']:.2f}, sweep {w['sweep_deg']:.1f}°, a_w {a_w:.2f}/rad, AC x {w['x_ac_mm']:.1f}; tail "
                      f"{St / 1e4:.2f} dm², a_t {a_t:.2f}/rad, AC x {tg['x_np_mm']:.1f}, V_h {vh:.2f}; deps/dalpha "
                      f"{deps:.2f}{fus_txt}; NP x {x_np:.1f}, CG x {float(cg[0]):.1f} ({M:.0f} g): margin {sm * 100:.1f} % "
                      f"of the {mac:.1f} mm MAC"}


@check("fold_hinge_moment")
def fold_hinge_moment(proj, asm, joint, item, side, speed_kmh, cd, cl=0.0, actuator=None, stall_kgcm=None, ratio=1.0,
                      max_fraction=0.5, wing="wing_", root_y=0.0, samples=13, strips=40, extra_nmm=0.0):
    """Aerodynamic moment about a wing sweep / fold joint: every strip of the moving half (`item`, |y| root_y..tip on
    `side`) carries drag q cd dA along the flight direction (+x, at its mid-chord) and lift q cl dA (+z, at its quarter
    chord), q = rho V^2 / 2 at `speed_kmh` (sea level); the moment about the joint axis, worst over `samples` angles of
    the joint range, against the actuator's stall torque (catalog, or `stall_kgcm`) x `ratio` (gear reduction from the
    actuator to the joint) x `max_fraction`. `cd` is the force coefficient along the flight direction: drag (+), or the
    net chordwise force cd cos(a) - cl sin(a), which turns FORWARD (-) at high lift (leading-edge suction).
    `extra_nmm` adds a moment the air load does not cover, e.g. pivot friction mu x 2 (root moment / support spacing)
    x pin radius (state the arithmetic in the requirement's why)."""
    from . import assembly as A
    from .requirements import _axis_world, _ev
    root_y = _ev(root_y, proj.params or {})
    e = next((e for e in asm.edges if e.name == joint), None)
    if e is None or e.kind != "revolute":
        raise ValueError(f"fold_hinge_moment: '{joint}' is not a revolute joint")
    if stall_kgcm is None:
        ent = catalog.get(proj.items[actuator].spec["catalog"])
        stall_kgcm = catalog.num(ent, "stall_torque_kgcm", "stall_torque_kg_cm", "stall_torque")
    sgn = {"right": 1, "left": -1}.get(side, side)
    pf = _pf(proj, wing)
    v = float(speed_kmh) / 3.6
    q = 0.5 * aero.RHO * v * v * 1e-6                    # N per mm2
    worst, at = 0.0, None
    for ang in np.linspace(e.range[0], e.range[1], int(samples)):
        T = _home_to_pose(proj, asm, [item], {joint: float(ang)})[item]
        o, d = _axis_world(proj, e)
        tau = 0.0
        for s in _half_strips(pf, root_y, pf.semi, int(sgn), strips, T):
            tau += float(np.dot(np.cross(s["mid"] - o, (q * cd * s["area"], 0.0, 0.0)), d))
            tau += float(np.dot(np.cross(s["qc"] - o, (0.0, 0.0, q * cl * s["area"])), d))
        if abs(tau) >= worst:
            worst, at = abs(tau), float(ang)
    A.solve(asm)
    worst += float(extra_nmm)
    kgcm = worst / 98.0665
    lim = float(stall_kgcm) * float(ratio) * float(max_fraction)
    return {"ok": kgcm <= lim + 1e-9, "value": round(kgcm, 3), "limit": round(lim, 3), "bound": "max", "unit": "kg·cm",
            "at_deg": at, "servo_kgcm": round(kgcm / float(ratio), 3),
            "detail": f"{speed_kmh:g} km/h (q {q * 1e6:.0f} Pa), cd {cd:g}, cl {cl:g} on the {pf.semi - root_y:.0f} mm half: "
                      f"{kgcm:.2f} kg·cm about {joint} at {at:g}°, {kgcm / float(ratio):.2f} kg·cm at the actuator vs stall "
                      f"{float(stall_kgcm):g} x ratio {float(ratio):g} x {max_fraction:g}"}


UNITS.update({"static_margin": ("x MAC", "range"), "wing_loading": ("g/dm²", "max"), "stall_speed": ("km/h", "max"),
              "spar_bending": ("x allowable", "max"), "static_margin_tail": ("x MAC", "range"),
              "fold_hinge_moment": ("kg·cm", "max")})
