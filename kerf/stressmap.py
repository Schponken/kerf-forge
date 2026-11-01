"""Where a part's material works and where it idles, from the FEA stress fields of all its load cases.

fea_static only proves pass/fail. This turns the per-element field (kerf/fea.py `_field`) into design feedback:
utilisation (stress / allowable, worst case over every load case, element by element), how much of the volume
idles below COLD of the allowable, and the coarse zones where material should go (hot) or could come out (cold).
A part whose strength checks never use more than OVERBUILT of the allowable, and whose stiffness checks never use more
than half of their deflection limit, is overbuilt: pipeline.py reports it so the designer removes material there or
says in DESIGN.md why it must stay (fit, print, stiffness not checked by FEA).
"""
from __future__ import annotations

import numpy as np

COLD = 0.15        # element below this fraction of the allowable stress = idle material
OVERBUILT = 0.25   # a part's worst case under this = overbuilt, unless stiffness governs
GRID = 6           # zones per longest side


def summarize(cases: list[dict]) -> dict:
    """cases: [{"field": fea `_field`, "allow": MPa, "disp_use": max_disp / limit or None}] for ONE part."""
    usable = [c for c in cases if c.get("field") is not None and c.get("allow")]
    if not usable:
        return {}
    n = {len(c["field"]["vm"]) for c in usable}
    if len(n) == 1:      # same mesh for every case (same part, same mesh size): combine element by element
        f0 = usable[0]["field"]
        util = np.max([c["field"]["vm"] / c["allow"] for c in usable], axis=0)
        cent, vol = f0["c"], f0["vol"]
    else:                # different meshes: judge on the most-used case alone (conservative)
        best = max(usable, key=lambda c: float(np.percentile(c["field"]["vm"], 99.9)) / c["allow"])
        util, cent, vol = best["field"]["vm"] / best["allow"], best["field"]["c"], best["field"]["vol"]
    peak = float(np.percentile(util, 99.9))
    cold_pct = float(vol[util < COLD].sum() / vol.sum() * 100)
    lo, hi = cent.min(axis=0), cent.max(axis=0)
    cell = max(float((hi - lo).max()) / GRID, 1e-6)
    key = np.floor((cent - lo) / cell).astype(int)
    zones: dict[tuple, list] = {}
    for i, k in enumerate(map(tuple, key)):
        zones.setdefault(k, []).append(i)
    rows = []
    for k, idx in zones.items():
        idx = np.asarray(idx)
        v = float(vol[idx].sum())
        rows.append({"at": (lo + (np.asarray(k) + 0.5) * cell).round(1).tolist(), "vol_mm3": round(v, 1),
                     "use": round(float((util[idx] * vol[idx]).sum() / v), 3), "peak": round(float(util[idx].max()), 3)})
    total = float(vol.sum())
    # most removable first: idle volume, weighted by how idle it is
    cold = sorted((r for r in rows if r["use"] < COLD and r["vol_mm3"] > 0.02 * total),
                  key=lambda r: -r["vol_mm3"] * (1 - r["use"] / COLD))[:3]
    hot = sorted(rows, key=lambda r: -r["peak"])[:3]
    disp = [c["disp_use"] for c in cases if c.get("disp_use") is not None]
    stiff = max(disp) if disp else None
    return {"utilisation": round(peak, 3), "cold_volume_pct": round(cold_pct, 1), "cold_zones": cold, "hot_zones": hot,
            "deflection_use": None if stiff is None else round(stiff, 3),
            "overbuilt": peak < OVERBUILT and (stiff is None or stiff < 0.5)}


def advice(part: str, s: dict) -> str | None:
    """One warning line for an overbuilt part (None when the part's material is used)."""
    if not s or not s.get("overbuilt"):
        return None
    where = "; ".join(f"around {z['at']} ({z['vol_mm3']:.0f} mm3 at {z['use'] * 100:.0f} %)" for z in s["cold_zones"]) or "throughout"
    return (f"{part}: overbuilt: every strength check uses at most {s['utilisation'] * 100:.0f} % of the allowable stress and "
            f"{s['cold_volume_pct']:.0f} % of the volume works below {COLD * 100:.0f} %; idle material {where}. Remove or "
            "reshape it (pockets, thinner walls, ribs along the load path), or say in DESIGN.md why it must stay "
            "(fit, print, stiffness the FEA cases don't load)")
