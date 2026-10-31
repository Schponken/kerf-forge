"""Electrical system: the power tree from project.yaml `wiring:`, the current in every wire and item, the ratings it
must stay inside, hover/run time, connector access, and the wiring outputs (WIRING.md, wiring.svg, BOM rows).

Schema (docs/ARCHITECTURE.md "Electrical"):

    electrical:
      battery: battery                    # item id of the pack (catalog: cells, capacity_mah, c_rating[, c_burst])
      burst_s: 5                          # longest full-power burst, s (wire heating); default 5
      draw: {rx: {avg_a: 0.1, peak_a: 0.1, why: "..."}}   # only where the catalog has no current figure
      limits: {stack: {peak_a: 100, why: "ESC firmware current limit"}}   # a real, configured current cap
    wiring:
      - {id: main, from: battery, to: xt60, kind: power, v: 25.2, gauge: 12, color: red/black, length_mm: 90,
         route: [xt60_path, top_plate.xt60]}    # waypoints: item, item.joint (or keep-out) or [x, y, z] world mm

A power run is the +/- pair; its current is everything downstream of its `to` item (the tree is followed through the
`to` item's own outgoing power runs; a run at a lower voltage than the item's feed is a regulator output and is
referred back to the feed with the regulator efficiency). Item draw comes from the catalog: motors max_current_a
(peak) and, when the project has prop discs, their hover current; servos running_current_a / stall_current_a;
everything else current_a[/current_peak_a]. Connectors (catalog path '...connectors...') pass current through and are
rated by current_a (continuous) / current_peak_a (burst). Output-pin ratings: '<pin>_current_a' / '<pin>_burst_a'
or 'bec_<pin>_a'; a regulator (catalog output_v) without pin keys is rated by current_a for all its outputs.
"""
from __future__ import annotations

import math

import numpy as np

from . import catalog, geom

# --- physical constants (sources in docs/ENGINEERING.md section "Electrical") ---------------------------------------
CU_RHO_20 = 1.72e-8          # ohm*m, annealed copper at 20 C (CRC, via hyperphysics.gsu.edu Tables/rstiv)
CU_ALPHA = 0.00393           # 1/K, same table
CU_CV = 8920.0 * 385.0       # J/(m3 K): copper density 8.92 g/cm3 x specific heat 385 J/(kg K) (copper.org fact sheet)
WIRE_BURST_DT_K = 60.0       # allowed adiabatic rise in a burst: 40 C ambient -> 100 C, half of silicone's 200 C
AIR_RHO = 1.225              # kg/m3, ISA sea level
LIPO_V_NOM, LIPO_V_MAX = 3.7, 4.2
FM_DEFAULT = 0.5             # propeller figure of merit: Bauersfeld & Scaramuzza 2021 use 0.6 (0.5-0.7 typical);
#                              UIUC (Deters & Selig 2008) measured 0.38-0.61 for 2.5-5 in props -> 0.5, conservative
ETA_MOTOR_DEFAULT = 0.75     # motor efficiency at typical operating points (Bauersfeld & Scaramuzza 2021, arXiv 2109.04741)
USABLE_DEFAULT = 0.8         # LiPo 80 % rule (Flite Test, Beginner Series: Batteries and Safety)
COAX_KAPPA = 1.281           # induced-power interference factor, coaxial pair at equal thrust (momentum theory)
BEC_EFF_DEFAULT = 0.8        # switching regulator efficiency, conservative (no maker figure published for our BECs)


class ElectricalError(ValueError):
    pass


def ampacity(gauge) -> float:
    return float(catalog.get("wire.awg")["ampacity_a"][str(int(gauge))])


def wire_area_m2(gauge) -> float:
    d = float(catalog.get("wire.awg")["diameter_mm"][str(int(gauge))]) / 1000
    return math.pi * d * d / 4


def burst_rise_k(current_a: float, gauge, seconds: float) -> float:
    """Adiabatic temperature rise of a copper conductor carrying `current_a` for `seconds` (no heat lost: the
    conservative short-burst model). Resistivity is taken at 100 C (the end of the allowed rise)."""
    j = current_a / wire_area_m2(gauge)
    rho = CU_RHO_20 * (1 + CU_ALPHA * 80.0)
    return j * j * rho * seconds / CU_CV


def hover_power_w(mass_g: float, prop_d_mm: float, groups: list, fm=FM_DEFAULT, eta=ETA_MOTOR_DEFAULT) -> float:
    """Electrical hover power (W) from momentum theory. `groups` = number of rotors per coaxial group, e.g. [1,1,1,1]
    for a quad, [2] for a coax pair. Thrust is shared equally by all rotors; a coaxial pair pays COAX_KAPPA."""
    n = sum(groups)
    t = mass_g / 1000 * 9.80665 / n
    a = math.pi * (prop_d_mm / 2000) ** 2
    p_rotor = t ** 1.5 / math.sqrt(2 * AIR_RHO * a)
    kappa = {1: 1.0, 2: COAX_KAPPA}
    if any(g not in kappa for g in groups):
        raise ElectricalError(f"coaxial groups of {groups}: only single rotors and coaxial pairs are modelled")
    return sum(kappa[g] * g * p_rotor for g in groups) / (fm * eta)


# --- model -------------------------------------------------------------------------------------------------------------
def _ref(s: str):
    item, _, pin = str(s).partition(".")
    return item, pin


def _cat(proj, iid):
    it = proj.items[iid]
    path = it.spec.get("catalog")
    return (path or ""), (catalog.get(path) if path else {})


def _is_connector(path):
    return "connectors" in path.split(".")


def _rotors(proj):
    """Prop discs (keep-out proxy prop_disc): world centre, axis, diameter; grouped into coaxial sets."""
    discs = []
    for iid, it in proj.items.items():
        if it.role == "keepout" and it.spec.get("proxy") == "prop_disc" and it.shape is not None:
            d = float(it.spec["diameter"]) if "diameter" in it.spec else catalog.num(catalog.get(it.spec["catalog"]), "diameter_mm")
            loc = it.shape.location
            discs.append((iid, geom.world_point(loc, (0, 0, 0)), geom.world_dir(loc, (0, 0, 1)), d))
    groups, used = [], set()
    for i, (a, ca, za, _) in enumerate(discs):
        if a in used:
            continue
        g = [a]
        used.add(a)
        for b, cb, _, _ in discs[i + 1:]:
            v = cb - ca
            if b not in used and np.linalg.norm(v - np.dot(v, za) * za) < 1.0:
                g.append(b)
                used.add(b)
        groups.append(g)
    return discs, groups


def _silicone(key, gauge) -> float:
    """OD (mm) or g/m of one silicone conductor (catalog wire.silicone). Gauges finer than the table use its finest
    entry (an upper bound on both)."""
    t = catalog.get("wire.silicone")[key]
    g = int(gauge)
    if str(g) in t:
        return float(t[str(g)])
    finest = max(int(k) for k in t)
    if g > finest:
        return float(t[str(finest)])
    raise ElectricalError(f"AWG {g} is not in catalog wire.silicone.{key}")


def wire_mass_g(w) -> float:
    n = int(w.get("conductors") or (2 if w.get("kind", "power") == "power" else 1))
    return _silicone("g_per_m", w["gauge"]) * float(w["length_mm"]) / 1000 * n


def wiring_mass_g(proj) -> float:
    """Mass of every declared run (silicone wire g/m x cut length x conductors); 0 without `wiring:`."""
    return sum(wire_mass_g(w) for w in proj.data.get("wiring") or [] if not w.get("supplied"))   # supplied leads: in the item


def total_mass_g(proj) -> float:
    from .checks import item_mass_g
    return sum(item_mass_g(it) for it in proj.items.values() if it.role != "keepout" and it.shape is not None) + wiring_mass_g(proj)


def analyse(proj, fm=None, eta=None) -> dict:
    """Currents, ratings and lengths for the whole electrical system. Raises ElectricalError on a malformed tree."""
    data = proj.data
    el = data.get("electrical") or {}
    wires = data.get("wiring") or []
    if not wires:
        raise ElectricalError("project.yaml has no `wiring:` section")
    bat = el.get("battery") or el.get("supply")
    if bat not in proj.items:
        raise ElectricalError(f"electrical.battery / electrical.supply '{bat}' is not an item")
    bpath, bcat = _cat(proj, bat)
    mains = "cells" not in bcat and "output_v" in bcat      # a wall adapter / bench supply: no run time
    if mains:
        cells, v_bat = 0, float(bcat["output_v"])
    else:
        for k in ("cells", "capacity_mah", "c_rating"):
            if k not in bcat:
                raise ElectricalError(f"battery catalog entry {bpath} has no '{k}' (a mains supply needs output_v + current_a)")
        cells = int(bcat["cells"])
        v_bat = cells * LIPO_V_MAX
    draw_over = el.get("draw") or {}
    limits = el.get("limits") or {}
    for d in (draw_over, limits):
        for k, v in d.items():
            if k not in proj.items:
                raise ElectricalError(f"electrical override for unknown item '{k}'")
            if not (v or {}).get("why"):
                raise ElectricalError(f"electrical override for '{k}' needs a 'why'")
    bec_eff = float(el.get("bec_eff", BEC_EFF_DEFAULT))
    burst_s = float(el.get("burst_s", 5.0))

    ws = []
    for i, w in enumerate(wires):
        wid = w.get("id", f"w{i + 1}")
        for k in ("from", "to", "gauge", "length_mm"):
            if k not in w:
                raise ElectricalError(f"wiring '{wid}' needs '{k}'")
        (fi, fp), (ti, tp) = _ref(w["from"]), _ref(w["to"])
        for x in (fi, ti):
            if x not in proj.items:
                raise ElectricalError(f"wiring '{wid}': unknown item '{x}'")
        kind = w.get("kind", "power")
        if kind not in ("power", "signal"):
            raise ElectricalError(f"wiring '{wid}': kind must be power or signal")
        if kind == "power" and "v" not in w:
            raise ElectricalError(f"wiring '{wid}': a power run needs its voltage 'v'")
        if str(int(w["gauge"])) not in catalog.get("wire.awg")["ampacity_a"]:
            raise ElectricalError(f"wiring '{wid}': AWG {w['gauge']} is not in catalog wire.awg")
        ws.append({**w, "id": wid, "fi": fi, "fp": fp, "ti": ti, "tp": tp, "kind": kind})
    power = [w for w in ws if w["kind"] == "power"]
    feed = {}
    for w in power:
        if w["ti"] in feed:
            raise ElectricalError(f"item '{w['ti']}' is fed by two power runs ({feed[w['ti']]['id']}, {w['id']})")
        feed[w["ti"]] = w
    if bat in feed:
        raise ElectricalError("the battery cannot be fed by a power run")

    discs, groups = _rotors(proj)
    mass = total_mass_g(proj)
    hover = None
    motors = [i for i in proj.items if "max_current_a" in _cat(proj, i)[1] and proj.items[i].role == "purchased"]
    if discs and mains:
        raise ElectricalError("prop discs on a mains supply (tethered flight) are not modelled; use a battery")
    if discs:
        dset = {d[3] for d in discs}
        if len(dset) > 1:
            raise ElectricalError(f"prop discs of different diameters {sorted(dset)} are not modelled")
        p = hover_power_w(mass, discs[0][3], [len(g) for g in groups], fm or el.get("fm", FM_DEFAULT),
                          eta or el.get("eta", ETA_MOTOR_DEFAULT))
        hover = {"mass_g": round(mass, 1), "rotors": len(discs), "coax_groups": [g for g in groups if len(g) > 1],
                 "prop_d_mm": discs[0][3], "power_w": round(p, 1), "v_nom": cells * LIPO_V_NOM}
        if not motors:
            raise ElectricalError("prop discs but no motor (catalog max_current_a) in the power tree")

    def own(i):
        """(avg_a, peak_a, source) the item itself draws at its feed voltage."""
        if i in draw_over:
            o = draw_over[i]
            return float(o["avg_a"]), float(o.get("peak_a", o["avg_a"])), f"electrical.draw: {o['why']}"
        path, e = _cat(proj, i)
        if i == bat or _is_connector(path) or "output_v" in e:
            return 0.0, 0.0, "pass-through"
        if "max_current_a" in e:
            pk = float(e["max_current_a"])
            if hover:
                v = feed[i]["v"] if i in feed else v_bat
                return hover["power_w"] / len(motors) / hover["v_nom"] * (v_bat / v), pk, "hover (momentum theory) / catalog max_current_a"
            return pk, pk, "catalog max_current_a (no props: run at max)"
        if "stall_current_a" in e:
            return float(e.get("running_current_a", e["stall_current_a"])), float(e["stall_current_a"]), "catalog running/stall current"
        if "current_a" in e:
            return float(e["current_a"]), float(e.get("current_peak_a", e["current_a"])), "catalog current_a"
        if any(w["fi"] == i for w in power):
            return 0.0, 0.0, "distributor (no own draw in catalog)"
        raise ElectricalError(f"no current figure for '{i}' ({path or 'no catalog'}): add it to the catalog with a source, "
                              f"or electrical.draw with a why")

    memo, stack = {}, set()

    def through(i):
        """(avg, peak) drawn at item i's input, including everything downstream."""
        if i in memo:
            return memo[i]
        if i in stack:
            raise ElectricalError(f"power wiring loops back through '{i}'")
        stack.add(i)
        a, p, _ = own(i)
        vin = feed[i]["v"] if i in feed else v_bat
        for w in power:
            if w["fi"] != i:
                continue
            ca, cp = through(w["ti"])
            w["avg_a"], w["peak_a"] = ca, cp
            if float(w["v"]) < 0.9 * vin:                 # regulator output: refer back to the input side
                k = float(w["v"]) / (vin * bec_eff)
                ca, cp = ca * k, cp * k
            a, p = a + ca, p + cp
        if i in limits:
            p = min(p, float(limits[i]["peak_a"]))
        stack.discard(i)
        memo[i] = (a, p)
        return a, p

    tot_avg, tot_peak = through(bat)
    for w in power:
        if "avg_a" not in w:
            raise ElectricalError(f"wiring '{w['id']}' is not connected to the battery's power tree")
    for w in ws:
        if w["kind"] == "signal":
            w["avg_a"], w["peak_a"] = 0.0, 0.0
    for w in ws:
        _route(proj, w)

    rows = []

    def row(what, kind, value, limit, note=""):
        rows.append({"what": what, "kind": kind, "value": round(value, 3), "limit": round(limit, 3),
                     "ok": value <= limit + 1e-9, "note": note})

    ah = 0.0 if mains else float(bcat["capacity_mah"]) / 1000
    if mains:
        row(f"supply {bat}", "avg A vs rated", tot_avg, float(bcat["current_a"]), bpath)
        row(f"supply {bat}", "peak A vs peak rating", tot_peak, float(bcat.get("current_peak_a", bcat["current_a"])), bpath)
    else:
        row(f"battery {bat}", "avg A vs C rating", tot_avg, ah * float(bcat["c_rating"]), f"{bcat['capacity_mah']} mAh x {bcat['c_rating']}C")
        row(f"battery {bat}", "peak A vs burst C", tot_peak, ah * float(bcat.get("c_burst", bcat["c_rating"])),
            f"{bcat['capacity_mah']} mAh x {bcat.get('c_burst', bcat['c_rating'])}C")
    for w in power:
        row(f"wire {w['id']} AWG {w['gauge']}", "avg A vs chassis ampacity", w["avg_a"], ampacity(w["gauge"]), "catalog wire.awg")
        row(f"wire {w['id']} AWG {w['gauge']}", f"burst rise K ({w['peak_a']:.1f} A, {burst_s:g} s)",
            burst_rise_k(w["peak_a"], w["gauge"], burst_s), WIRE_BURST_DT_K, "adiabatic copper heating")
    for i in proj.items:
        path, e = _cat(proj, i)
        if _is_connector(path) and i in feed:
            a, p = memo.get(i, (0, 0))
            row(f"connector {i}", "avg A vs rated", a, float(e["current_a"]), path)
            row(f"connector {i}", "peak A vs peak rating", p, float(e.get("current_peak_a", e["current_a"])), path)
    # output pins and regulators
    outs = {}
    for w in power:
        outs.setdefault((w["fi"], w["fp"]), []).append(w)
    for (i, pin), group in outs.items():
        path, e = _cat(proj, i)
        cont = burst = None
        if pin:
            cont = e.get(f"{pin}_current_a", e.get(f"bec_{pin}_a"))
            burst = e.get(f"{pin}_burst_a", e.get(f"{pin}_current_peak_a"))
        if cont is None and "output_v" in e:
            cont, burst = e.get("current_a"), e.get("current_peak_a")
        if cont is None:
            continue
        per_run = pin and f"{pin}_current_a" in e        # e.g. one ESC channel per motor run
        runs = group if per_run else [None]
        for w in runs:
            sel = [w] if w else group
            a = sum(x["avg_a"] for x in sel)
            p = sum(x["peak_a"] for x in sel)
            name = f"{i}.{pin or 'out'}" + (f" -> {w['ti']}" if w else "")
            row(name, "avg A vs rated", a, float(cont), path)
            row(name, "peak A vs burst rating", p, float(burst if burst is not None else cont), path)
    # voltage compatibility
    for w in power:
        _, e = _cat(proj, w["ti"])
        lo = e.get("voltage_min", e.get("input_v_min"))
        hi = e.get("voltage_max", e.get("input_v_max"))
        if w["fi"] == bat and abs(float(w["v"]) - v_bat) > 0.05:
            rows.append({"what": f"wire {w['id']}", "kind": "voltage", "value": w["v"], "limit": v_bat, "ok": False,
                         "note": f"runs from the source carry its full voltage {v_bat:g} V"})
        if lo is not None and hi is not None:
            ok = float(lo) - 1e-9 <= float(w["v"]) <= float(hi) + 1e-9
            rows.append({"what": f"{w['ti']} input", "kind": "voltage", "value": w["v"], "limit": [lo, hi], "ok": ok, "note": ""})

    usable = float(el.get("usable", USABLE_DEFAULT))
    return {"battery": bat, "mains": mains, "cells": cells, "v_bat": v_bat, "capacity_ah": ah, "usable": usable, "burst_s": burst_s,
            "avg_a": round(tot_avg, 3), "peak_a": round(tot_peak, 3), "hover": hover,
            "minutes": round(ah * usable / tot_avg * 60, 2) if tot_avg > 0 and not mains else None,
            "loads": {i: dict(zip(("avg_a", "peak_a", "source"), own(i))) for i in memo},
            "wires": [{k: w.get(k) for k in ("id", "from", "to", "kind", "v", "gauge", "color", "conductors", "length_mm", "avg_a",
                                             "peak_a", "routed_mm", "cut_min_mm", "points", "supplied", "note")} for w in ws],
            "ratings": rows}


SLACK = 1.15


def _point(proj, ref, endpoint=False):
    """World point of a route reference. An endpoint pin (`stack.5v`) that is not a joint of the item is just an
    electrical pin name: the item's bounding-box centre stands in for it."""
    if isinstance(ref, (list, tuple)):
        return np.asarray(ref, float)
    if isinstance(ref, dict):                       # {item, at: [x, y, z] | joint}: a tie point that moves with the item
        it = proj.items.get(ref.get("item"))
        if it is None or it.shape is None:
            raise ElectricalError(f"route point {ref}: unknown item")
        at = ref.get("at", [0, 0, 0])
        if isinstance(at, str):
            return geom.world_point(it.shape.joints[at].location, (0, 0, 0))
        return geom.world_point(it.shape.location, at)
    item, pin = _ref(ref)
    if item not in proj.items or proj.items[item].shape is None:
        raise ElectricalError(f"route point '{ref}': unknown item")
    sh = proj.items[item].shape
    if pin and pin in sh.joints:
        return geom.world_point(sh.joints[pin].location, (0, 0, 0))
    if pin and not endpoint:
        raise ElectricalError(f"route point '{ref}': {item} has no joint '{pin}' (has {sorted(sh.joints)})")
    lo, hi = geom.bbox(sh)
    return (lo + hi) / 2


def _route(proj, w):
    pts = [_point(proj, w["from"], True)] + [_point(proj, r) for r in (w.get("route") or [])] + [_point(proj, w["to"], True)]
    L = float(sum(np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])))
    w["routed_mm"] = round(L, 1)
    w["cut_min_mm"] = round(L * SLACK, 1)
    w["points"] = [np.round(p, 1).tolist() for p in pts]


def length_problems(model) -> list:
    return [f"wiring '{w['id']}': length_mm {w['length_mm']} is shorter than the routed length {w['routed_mm']} mm "
            f"+ 15 % slack = {w['cut_min_mm']} mm" for w in model["wires"] if float(w["length_mm"]) < w["cut_min_mm"]]


def route_check(proj, asm, model) -> tuple[list, list]:
    """Every run at home and at both ends of every moving joint: (a) its routed length + 15 % must fit the cut length
    (runs that cross a moving joint need the slack the worst pose asks for); (b) a tube of the wire's outer diameter
    along the route must not pass through any item other than the two it connects, nor through a spinning prop disc.
    Returns (per-run results, problems)."""
    from . import assembly as A
    from .requirements import _tube
    poses = [("home", {})] + [(f"{e.name}={v:g}", {e.name: v}) for e in asm.movable for v in e.range]
    poses += [(f"{s.get('name')}#{k}", p) for s in proj.data["assembly"].get("sweeps") or [] for k, p in enumerate(s.get("poses") or [])]
    wires = {w["id"]: w for w in model["wires"]}
    res = {i: {"id": i, "max_routed_mm": 0.0, "worst_pose": "home", "hits": []} for i in wires}
    try:
        for name, pose in poses:
            A.solve(asm, pose)
            for i, w in wires.items():
                spec = _spec(proj, i)
                pts = [_point(proj, spec["from"], True)] + [_point(proj, r) for r in (spec.get("route") or [])] + \
                      [_point(proj, spec["to"], True)]
                L = float(sum(np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])))
                r = res[i]
                if L > r["max_routed_mm"]:
                    r["max_routed_mm"], r["worst_pose"] = round(L, 1), name
                tube = _tube(pts, _silicone("od_mm", spec["gauge"]))
                skip = {_ref(spec["from"])[0], _ref(spec["to"])[0]}
                for j, it in proj.items.items():
                    if j in skip or it.shape is None:
                        continue
                    if it.role == "keepout" and it.spec.get("proxy") != "prop_disc":
                        continue
                    v = geom.overlap(tube, it.shape)
                    if v > geom.OVERLAP_TOL_MM3 and (j, name) not in {(h[0], h[1]) for h in r["hits"]}:
                        r["hits"].append((j, name, round(v, 1)))
    finally:
        A.solve(asm)
    problems = []
    for i, r in res.items():
        need = round(r["max_routed_mm"] * SLACK, 1)
        r["cut_min_mm"] = need
        if float(wires[i]["length_mm"]) < need:
            problems.append(f"wiring '{i}': length_mm {wires[i]['length_mm']} < {need} mm (routed {r['max_routed_mm']} mm "
                            f"at {r['worst_pose']} + 15 %)")
        for j, pose, v in r["hits"][:3]:
            problems.append(f"wiring '{i}' runs through {j} at {pose} ({v} mm3): route it round, through a hole, or "
                            f"along a channel")
    return list(res.values()), problems


def _spec(proj, wid):
    for k, w in enumerate(proj.data.get("wiring") or []):
        if w.get("id", f"w{k + 1}") == wid:
            return w
    raise ElectricalError(f"wiring '{wid}' not found")
