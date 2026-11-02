"""Design for life (docs/VISION.md section 2): what a part does after the first day.

- `flex_strain`  a part that flexes on purpose (snap-fit hook, living hinge): bending strain at the root
  (snap, straight cantilever: e = 1.5 t y / L^2; hinge bent through angle a over length L: e = t a / (2 L)) against the
  permissible strain of a single snap: 70 % of the yield strain for unreinforced (amorphous) plastics, 50 % of the
  strain at break for reinforced ones (Machine Design, "Fundamentals of Annular Snap-Fit Joints"); half that for a
  beam printed across its layers (Fictiv, "How to Design Snap Fit Components"). The yield strain is estimated as
  tensile strength / modulus (linear up to yield: lower than the real yield strain, so on the safe side). A part that
  flexes again and again (cycles > 1) needs a fatigue strain from the catalog; without one it fails rather than guess.
- `creep_limit` a constant load (a shelf, a hanging arm at rest, a clamp): the named strength case's peak stress
  (von Mises p99.9) at most the lowest creep-rupture stress the catalog documents for the material, divided by sf
  (default 3: the documented ruptures happen within hours, far short of a service life). No creep data: it fails.
- `screw_locking` screws in something that vibrates (motors with props, or a use-story `vibration` hazard) must not
  back out: every fastener group with a metal thread (nut, heat-set insert, threaded part) needs a declared locking
  method (nyloc / threadlocker / lock washer / safety wire); screws cut into plastic (tap) hold by their own thread.
"""
from __future__ import annotations

import math

from . import catalog
from .requirements import UNITS, _ev, _strength, check

SNAP_YIELD_SHARE = 0.70      # amorphous plastics, single brief snap: share of the yield strain
SNAP_BREAK_SHARE = 0.50      # reinforced plastics: share of the strain at break
ACROSS_LAYERS = 0.50         # beam printed along Z: halve the permissible strain
LOCKS = ("nyloc", "threadlocker", "lock washer", "safety wire")


def allowable_strain_pct(material: str, across_layers: bool = False) -> tuple[float, str]:
    m = catalog.get(f"materials.{material}")
    if m.get("reinforced"):
        brk = m.get("elongation_break_z_pct" if across_layers else "elongation_break_xy_pct")
        if brk is None:
            raise ValueError(f"materials.{material} is reinforced but has no elongation at break in the catalog")
        a, how = SNAP_BREAK_SHARE * float(brk), f"50 % of its {brk} % strain at break"
    else:
        E = catalog.num(m, "youngs_modulus_mpa")
        ys = _strength(material, "xy") / E * 100
        a, how = SNAP_YIELD_SHARE * ys, f"70 % of its ~{ys:.1f} % yield strain (strength / modulus)"
    if across_layers:
        a, how = a * ACROSS_LAYERS, how + ", halved across the layers"
    return a, how


@check("flex_strain")
def flex_strain(proj, asm, part, kind, t_mm, L_mm, deflection_mm=None, angle_deg=None, cycles=1, across_layers=False):
    """Root strain of a snap hook (kind snap: deflection_mm) or living hinge (kind hinge: angle_deg) vs permissible."""
    p = proj.params or {}
    t, L = _ev(t_mm, p), _ev(L_mm, p)
    if kind == "snap":
        e = 1.5 * t * _ev(deflection_mm, p) / (L * L) * 100
        how_e = f"1.5 t y / L^2 = 1.5 x {t:g} x {_ev(deflection_mm, p):g} / {L:g}^2"
    elif kind == "hinge":
        e = t * math.radians(_ev(angle_deg, p)) / (2 * L) * 100
        how_e = f"t a / 2L = {t:g} x {math.radians(_ev(angle_deg, p)):.2f} rad / (2 x {L:g})"
    else:
        raise ValueError("flex_strain kind: snap or hinge")
    mat = proj.items[part].spec.get("material", "PETG")
    if int(cycles) > 1:
        fat = catalog.get(f"materials.{mat}").get("fatigue_strain_pct")
        if fat is None:
            return {"ok": False, "value": round(e, 2), "limit": None,
                    "detail": f"{part} flexes {cycles} times but the catalog has no fatigue strain for {mat}: use a "
                              f"material with sourced fatigue data (or a pin hinge), or add the data with its source"}
        a, how = float(fat) * (ACROSS_LAYERS if across_layers else 1.0), f"fatigue strain {fat} %"
    else:
        a, how = allowable_strain_pct(mat, across_layers)
    return {"ok": e <= a, "value": round(e, 2), "limit": round(a, 2),
            "detail": f"{part} {kind}: root strain {how_e} = {e:.2f} % vs {a:.2f} % permissible for {mat} ({how})"}


@check("creep_limit")
def creep_limit(proj, asm, case, sf=3.0):
    """The strength case `case` (a requirement id) is a constant load: its stress must stay under the material's
    documented creep-rupture stress / sf."""
    from .failure import _row
    spec, r, _, _ = _row(proj, asm, case)
    mat = proj.items[spec["part"]].spec.get("material", "PETG")
    pts = catalog.get(f"materials.{mat}").get("creep_rupture") or []
    if not pts:
        return {"ok": False, "value": r.get("value"), "limit": None,
                "detail": f"{case} is a constant load but the catalog has no creep-rupture data for {mat}: add a sourced "
                          f"creep point (stress, hours) before trusting it under a lasting load"}
    low = min(pts, key=lambda q: q["stress_mpa"])
    allow = float(low["stress_mpa"]) / float(sf)
    v = float(r["value"])
    return {"ok": v <= allow, "value": round(v, 2), "limit": round(allow, 2),
            "detail": f"{case}: von Mises p99.9 {v:.2f} MPa under a lasting load vs {mat} creep rupture at "
                      f"{low['stress_mpa']} MPa within {low['hours']} h ({low.get('temp_c', '?')} °C) / SF {sf}"}


def vibrating(proj) -> str | None:
    """Why the project vibrates (motors driving props, or a use-story vibration hazard), or None."""
    for it in proj.items.values():
        if str(it.spec.get("catalog", "")).startswith("drone.motors."):
            return "motors with props"
    for h in ((proj.data.get("use_story") or {}).get("goes_wrong") or []):
        if h.get("hazard") == "other" and "vibrat" in str(h.get("what", "")).lower():
            return h.get("what")
    return None


@check("screw_locking")
def screw_locking(proj, asm, locking=None):
    """`locking`: {fastener group: nyloc | threadlocker | lock washer | safety wire}. Every group screwed into a metal
    thread (nut trap, heat-set insert, threaded bought part) on a vibrating project must name one."""
    from . import assembly as A
    why = vibrating(proj)
    if not why:
        return {"ok": True, "value": 0, "limit": 0, "detail": "nothing in this project vibrates (no motors driving props)"}
    locking = locking or {}
    bad = [f"{g}: '{m}'" for g, m in locking.items() if m not in LOCKS]
    fast, _ = A.fasteners(asm)
    need = sorted({f["group"] for f in fast if f.get("receiver") in ("nut_trap", "heatset", "threaded", "nut")})
    missing = [g for g in need if g not in locking]
    ok = not missing and not bad
    return {"ok": ok, "value": len(missing), "limit": 0,
            "detail": (f"vibration from {why}: " + (f"no locking for {', '.join(missing)} (say nyloc / threadlocker / "
                       f"lock washer per group)" if missing else f"{len(need)} metal-thread groups locked")
                       + (f"; unknown methods {bad} (use {', '.join(LOCKS)})" if bad else ""))}


UNITS.update({"flex_strain": ("% strain", "max"), "creep_limit": ("MPa", "max"), "screw_locking": ("groups unlocked", "max")})
