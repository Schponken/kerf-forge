"""Electrical requirement checks (registered into requirements.REGISTRY): power_budget, flight_time / run_time,
connector_access. The model itself lives in kerf/electrical.py."""
from __future__ import annotations

import numpy as np
from build123d import Box, Location

from . import assembly as A, electrical as E, geom
from .requirements import check


@check("power_budget")
def power_budget(proj, asm, fm=None, eta=None):
    """Every rated element (battery C, BEC/ESC outputs, connectors, wire ampacity and burst heating, input voltage
    ranges) holds at average and at peak current."""
    m = E.analyse(proj, fm=fm, eta=eta)
    bad = [r for r in m["ratings"] if not r["ok"]]
    util = [r["value"] / r["limit"] for r in m["ratings"] if r["kind"] != "voltage" and r["limit"]]
    worst = max(util) if util else 0.0
    detail = (f"worst load / rating over {len(m['ratings'])} rated elements (battery avg {m['avg_a']} A, peak "
              f"{m['peak_a']} A)")
    if bad:
        detail += "; over: " + "; ".join(f"{r['what']} {r['kind']} {r['value']} > {r['limit']}" for r in bad[:6])
    return {"ok": not bad, "value": round(worst, 3), "limit": 1.0, "detail": detail, "rows": m["ratings"]}


def _time(proj, min_min, fm, eta, label):
    m = E.analyse(proj, fm=fm, eta=eta)
    t = m["minutes"]
    h = m["hover"]
    how = (f"hover: {h['power_w']} W for {h['mass_g']} g on {h['rotors']} x {h['prop_d_mm']:g} mm props" if h
           else "average draw of every load")
    return {"ok": t is not None and t >= min_min, "value": t, "limit": min_min,
            "detail": f"{label} (min): {m['capacity_ah'] * 1000:g} mAh x {m['usable']:g} usable / {m['avg_a']} A ({how})"}


@check("flight_time")
def flight_time(proj, asm, min_min, fm=None, eta=None):
    """Hover time from usable capacity and the momentum-theory hover current plus every other load's average."""
    return _time(proj, min_min, fm, eta, "hover flight time")


@check("run_time")
def run_time(proj, asm, min_min, fm=None, eta=None):
    """Run time from usable capacity and every load's average current (robots, gadgets)."""
    return _time(proj, min_min, fm, eta, "run time")


def _probe(item, direction, length, size=None, at=None, gap=0.5):
    """Box (item frame) leaving the item's face along an axis direction: the plug/cable/hand that must get in."""
    d = np.asarray(direction, float)
    ax = int(np.argmax(np.abs(d)))
    if np.count_nonzero(np.abs(d) > 1e-9) != 1:
        raise ValueError(f"connector_access direction {direction} must be along one item axis")
    sgn = 1.0 if d[ax] > 0 else -1.0
    local = item.shape.moved(item.shape.location.inverse())
    lo, hi = geom.bbox(local)
    c = (lo + hi) / 2 if at is None else np.asarray(at, float)
    ext = list(hi - lo)
    others = [k for k in range(3) if k != ax]
    if size is not None:
        for k, s in zip(others, size):
            ext[k] = float(s)
    face = (hi[ax] if sgn > 0 else lo[ax]) if at is None else c[ax]
    dims = [0.0, 0.0, 0.0]
    for k in others:
        dims[k] = ext[k]
    dims[ax] = float(length)
    centre = c.copy()
    centre[ax] = face + sgn * (gap + length / 2)
    return Location(tuple(centre)) * Box(*dims), dims


@check("connector_access")
def connector_access(proj, asm, item, direction, length_mm=30.0, size=None, at=None, ignore=None, pose=None):
    """A plug, cable or finger can reach the item: a box with the item's cross-section (or `size` [a, b] across the
    direction, `at` a local start point) leaving its face along `direction` (item frame) for `length_mm` hits nothing
    of the assembled device (keep-outs and `ignore` items excepted)."""
    A.solve(asm, pose or {})
    try:
        it = proj.items[item]
        box, dims = _probe(it, direction, length_mm, size, at)
        probe = it.shape.location * box
        skip = {item, *(ignore or [])}
        hits = []
        for i, o in proj.items.items():
            if i in skip or o.role == "keepout" or o.shape is None:
                continue
            v = geom.overlap(probe, o.shape)
            if v > geom.OVERLAP_TOL_MM3:
                hits.append(f"{i} ({v:.0f} mm3)")
    finally:
        A.solve(asm)
    return {"ok": not hits, "value": hits or "clear", "limit": f"{length_mm} mm free along {list(direction)}",
            "detail": f"access to {item}: probe {[round(x, 1) for x in dims]} mm" + (f" blocked by {hits}" if hits else "")}
