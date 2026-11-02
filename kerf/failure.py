"""Know how it breaks (docs/VISION.md section 2): a per-part failure table and the `weak_link` requirement.

`table(proj, asm, rep)` -> report.json `failure_modes`, one row per printed part:
- how it fails: its most used strength case (FEA / impact / stop / cantilever: value over limit, the higher of stress
  and deflection use), where (the peak location the case reports) and the failure kind from the print direction
  (a part judged across its layers splits between layers; along the layers it bends or cracks);
- what it takes with it: the bought parts mounted on it (its assembly subtree up to the next printed part) and their
  price;
- repair: the screws to undo and redo (fasteners through the part) and the reprint, at least the time the printer's
  maximum flow needs for its mass (kerf/printpkg.py), plus the filament cost.
`weak_link` proves a designed failure order: under one event, the cheap part's strength case is used more than the
expensive part's (normalised to the same applied force), so the cheap part breaks first.
"""
from __future__ import annotations

import re

import numpy as np

from .requirements import UNITS, check

STRENGTH = ("fea_static", "impact_fea", "stop_impact", "cantilever_stress")


def _use(row: dict, spec: dict) -> tuple[float, str]:
    """(use, what) of one strength row: stress / allowed, or deflection / its limit when that is higher."""
    use, what = 0.0, "stress"
    if isinstance(row.get("value"), (int, float)) and isinstance(row.get("limit"), (int, float)) and row["limit"]:
        use = row["value"] / row["limit"]
    lim = spec.get("max_disp_mm")
    if lim and isinstance(row.get("max_disp_mm"), (int, float)):
        d = row["max_disp_mm"] / float(lim)
        if d > use:
            use, what = d, "deflection"
    return use, what


def _how(spec: dict, what: str) -> str:
    if what == "deflection":
        return "bends too far (deflection limit) before it breaks"
    d = spec.get("direction", "xy")
    if d == "z":
        return "splits between print layers (the load pulls across them)"
    if d == "auto":
        return "cracks partly across its print layers"
    return "bends and cracks along its print layers"


def _mounted(proj, asm, part) -> list[str]:
    """Bought items carried by `part`: its assembly subtree, stopping at the next printed part."""
    out, stack = [], list(asm.children.get(part, []))
    while stack:
        n = stack.pop()
        it = proj.items.get(n)
        if it is None or it.role == "printed":
            continue
        if it.spec.get("catalog"):
            out.append(n)
        stack.extend(asm.children.get(n, []))
    for kid, it in proj.items.items():          # keep-outs that ride on a mounted item (props on motors) and are bought
        if it.role == "keepout" and it.spec.get("catalog") and it.spec.get("owner") in out and kid not in out:
            out.append(kid)
    return sorted(out)


def _price(prices: dict, key: str) -> float | None:
    e = prices.get(key)
    if not e:
        return None
    return float(e["pack_usd"]) / float(e.get("pack_qty") or 1)


def table(proj, asm, rep: dict) -> list[dict]:
    from . import printpkg
    from .ship import load_prices
    prices = load_prices()
    specs = {q.get("id", q.get("check")): q for q in proj.data.get("requirements") or []}
    rows = {r["id"]: r for r in rep.get("requirements") or [] if r.get("check") in STRENGTH and not r.get("skipped")}
    fast = (rep.get("assembly") or {}).get("fasteners") or []
    out = []
    for pid, it in proj.printed.items():
        pr = (rep.get("parts") or {}).get(pid) or {}
        mat = it.spec.get("material", "PETG")
        mass = float(pr.get("mass_est_g") or 0)
        f = _price(prices, f"material:{mat}")
        cost = round(f * mass, 2) if f is not None else None
        prof = printpkg.profile(mat)
        try:
            from . import catalog
            dens = float(catalog.get(f"materials.{mat}")["density"])
        except Exception:  # noqa: BLE001
            dens = 1.25
        reprint_min = round(mass / dens * 1000.0 / prof["max_flow"] / 60.0, 1)
        best = None
        for rid, r in rows.items():
            sp = specs.get(rid, {})
            if sp.get("part") != pid:
                continue
            use, what = _use(r, sp)
            if best is None or use > best[0]:
                best = (use, what, rid, r, sp)
        mounted = _mounted(proj, asm, pid)
        mcost = [(m, _price(prices, proj.items[m].spec["catalog"])) for m in mounted]
        n_screws = sum(1 for x in fast if pid in (x.get("male"), x.get("female")))
        row = {"part": pid, "material": mat, "filament_usd": cost, "reprint_min_at_least": reprint_min,
               "screws_to_undo": n_screws,
               "takes_with_it": [{"item": m, "usd": None if c is None else round(c, 2)} for m, c in mcost],
               "takes_with_it_usd": round(sum(c for _, c in mcost if c is not None), 2)}
        if best:
            use, what, rid, r, sp = best
            at = re.search(r"peak [\d.]+ MPa at (\[[^\]]*\])", r.get("detail", ""))
            row.update(fails_in=rid, use=round(use, 2), how=_how(sp, what), at=at.group(1) if at else None)
        else:
            row.update(fails_in=None, use=None, how="no strength case: not load-bearing (or not checked)", at=None)
        out.append(row)
    out.sort(key=lambda r: -(r["use"] or 0))
    return out


def lines(rows: list[dict]) -> list[str]:
    """Markdown table for ASSEMBLY.md / the review pack."""
    if not rows:
        return []
    L = ["| part | breaks first in | use of its limit | how | takes with it | repair |", "|---|---|---|---|---|---|"]
    for r in rows:
        takes = ", ".join(t["item"] for t in r["takes_with_it"]) or "-"
        if r["takes_with_it_usd"]:
            takes += f" (${r['takes_with_it_usd']:.2f} if they break too)"
        rep = f"undo {r['screws_to_undo']} screws, reprint (>= {r['reprint_min_at_least']:g} min" + (
            f", ${r['filament_usd']:.2f} filament)" if r["filament_usd"] is not None else ")")
        L.append(f"| {r['part']} | {r['fails_in'] or '-'} | {'-' if r['use'] is None else f'{r['use']:.0%}'} | {r['how']} | {takes} | {rep} |")
    return L


# ---- weak_link ----

def _row(proj, asm, rid):
    from .requirements import REGISTRY
    spec = next((q for q in proj.data.get("requirements") or [] if q.get("id") == rid), None)
    if spec is None:
        raise ValueError(f"weak_link: no requirement '{rid}'")
    if spec.get("check") not in STRENGTH:
        raise ValueError(f"weak_link: '{rid}' is a {spec.get('check')}, not a strength case")
    kw = {k: v for k, v in spec.items() if k not in ("check", "why", "id")}
    r = REGISTRY[spec["check"]](proj, asm, **kw)
    use, _ = _use(r, {})                     # breaking order: stress use only (a deflection limit is not a break)
    F = float(np.linalg.norm(r.get("applied_force_n") or [0.0]))
    return spec, r, use, F


@check("weak_link")
def weak_link(proj, asm, cheap, expensive, min_ratio=1.0):
    """The cheap part breaks first: under the same event, the cheap part's strength case `cheap` (a requirement id)
    uses more of its limit than every case in `expensive` (ids of cases on the parts that must survive, each loaded
    by the same event, e.g. the arm's crash reaction on the body). Uses are compared at the same applied force (each
    expensive case is scaled to the cheap case's force; linear elasticity). Value: the cheap use / the highest other."""
    sc, rc, uc, Fc = _row(proj, asm, cheap)
    worst, rows = 0.0, []
    for rid in [expensive] if isinstance(expensive, str) else expensive:
        se, re_, ue, Fe = _row(proj, asm, rid)
        ue_n = ue * (Fc / Fe) if Fe > 0 and Fc > 0 else ue
        rows.append(f"{rid} ({se['part']}) {ue_n:.0%}")
        worst = max(worst, ue_n)
    ratio = uc / worst if worst > 0 else float("inf")
    ok = ratio >= float(min_ratio)
    return {"ok": ok, "value": round(ratio, 2), "limit": float(min_ratio),
            "detail": f"under one event {sc['part']} ({cheap}) uses {uc:.0%} of its limit vs " + ", ".join(rows)
                      + (f": {sc['part']} breaks first" if ok else f": {sc['part']} is NOT the weak link; make it the "
                         f"weakest part on that load path (or strengthen the others)")}


UNITS.update({"weak_link": ("× the strongest other", "min")})
