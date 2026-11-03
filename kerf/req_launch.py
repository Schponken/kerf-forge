"""Elastic (bungee) launchers: exit speed, peak acceleration and the brake stop, from the elastic's sourced force curve.

`bungee_launch` integrates one strand's force-vs-elongation curve (catalog `force_curve`: [[elongation, N], ...],
elongation = stretched length / rest length - 1) over the power stroke, for `strands` strands of rest length `rest_mm`
that shorten from `start_mm` (cocked) to `end_mm` (where the sled meets the brake and the payload flies off):

  W = n * integral F(L / L0 - 1) dL           work the strands give back (1:1, sled travel = strand shortening)
  E = eta * W - m g s (sin a + mu cos a)      eta = the elastic's hysteresis / dynamic efficiency (catalog or arg)
  v = sqrt(2 E / (m + n m_strand / 3))        a strand fixed at one end moves on average at 1/3 of its KE share
  peak = (eta * n F(start) - m g (sin a + mu cos a)) / m_eff   (in g; eta also scales the force: the rate-dependent
                                                               loss is what the drop from static to dynamic pull is)

m = payload + the moving items (sled, wheels, cradle). An anchor with numbered notches moves both lengths by
`notch_pitch_mm` per notch above 1, so `notch` and `strands` are the launch setting printed on a drone's cradle; the
result carries the whole setting table (exit speed per strands x notch for this payload).

`brake` (optional): the sled (without the payload, which has left) is stopped by `strands` elastic cords crossing its
path between two posts `half_gap_mm` either side of it (a V as it is pushed in): pushed in by d, the cord's length
between its anchors (`free_mm`, the crossing included) grows by 2 (sqrt(w^2 + d^2) - w) and pushes back with
2 n T d / sqrt(w^2 + d^2); `rest_mm` (default free_mm) is the cord's unstretched length when it is tied in pre-stretched. The launch elastic keeps pulling (its force at end_mm - d). The stop distance must be at
most `max_stop_mm`; the peak force and deceleration go into the result for the strength checks of the sled bumper and
the brake posts.
"""
from __future__ import annotations

import math

from . import catalog
from .checks import item_mass_g
from .requirements import UNITS, G, _ev, check

UNITS["bungee_launch"] = ("m/s", "min")
STEPS = 400


def curve_entry(path: str, curve: str = "force_curve") -> dict:
    """The catalog elastic with `curve` (e.g. force_curve_premium, the stiff end of the sourced spread) as its force_curve."""
    e = catalog.get(path)
    if curve not in e:
        raise ValueError(f"{path} has no '{curve}' (a list of [elongation, N per strand] points with a source)")
    return {**e, "force_curve": e[curve]}


def force_n(entry: dict, path: str, e: float) -> float:
    """One strand's pull at elongation e (fraction), linear between the catalog points; 0 when slack."""
    pts = sorted((float(a), float(b)) for a, b in entry["force_curve"])
    if e <= 0:
        return 0.0
    if e > pts[-1][0] + 1e-9:
        raise ValueError(f"{path}: elongation {e * 100:.0f} % is beyond its measured force curve "
                         f"(max {pts[-1][0] * 100:.0f} %); shorten the stroke or lengthen the strands")
    prev = (0.0, 0.0)
    for a, b in pts:
        if e <= a:
            return prev[1] + (b - prev[1]) * (e - prev[0]) / (a - prev[0]) if a > prev[0] else b
        prev = (a, b)
    return pts[-1][1]


def work_j(entry, path, n, L0, L1, L2) -> float:
    """Work (J) n strands of rest length L0 give back shortening from L2 to L1 (mm)."""
    h = (L2 - L1) / STEPS
    tot = sum(force_n(entry, path, (L1 + (i + 0.5) * h) / L0 - 1) for i in range(STEPS))
    return n * tot * h / 1000.0


def launch(entry, path, strands, rest_mm, start_mm, end_mm, mass_kg, angle_deg=0.0, rolling_mu=0.0,
           efficiency=None) -> dict:
    """Exit speed (m/s), peak acceleration (g) and the energy figures for one setting."""
    if end_mm >= start_mm:
        raise ValueError(f"start_mm {start_mm:g} must exceed end_mm {end_mm:g} (the strands shorten as the sled runs)")
    eta = float(efficiency if efficiency is not None else entry.get("efficiency", 1.0))
    s = (start_mm - end_mm) / 1000.0
    a = math.radians(angle_deg)
    drag = mass_kg * G * (math.sin(a) + rolling_mu * math.cos(a))
    m_strand = float(entry.get("mass_per_m_g", 0.0)) * rest_mm / 1e6
    m_eff = mass_kg + strands * m_strand / 3.0
    W = work_j(entry, path, strands, rest_mm, end_mm, start_mm)
    E = eta * W - drag * s
    v = math.sqrt(2 * E / m_eff) if E > 0 else 0.0
    f0 = strands * force_n(entry, path, start_mm / rest_mm - 1)
    return {"v": v, "work_j": W, "eta": eta, "stroke_m": s, "m_eff": m_eff, "peak_g": (eta * f0 - drag) / m_eff / G,
            "pull_n": f0, "end_pull_n": strands * force_n(entry, path, end_mm / rest_mm - 1),
            "e_start": start_mm / rest_mm - 1, "e_end": end_mm / rest_mm - 1}


def stop(brake: dict, v: float, mass_kg: float, launch_entry, launch_path, strands, rest_mm, end_mm, params) -> dict:
    """Stop distance (mm), peak force (N) and deceleration (g) of the sled hitting a V cord brake at speed v."""
    path = brake["elastic"]
    be = curve_entry(path, brake.get("curve", "force_curve"))
    n = _ev(brake.get("strands", 1), params)
    w, L = _ev(brake["half_gap_mm"], params), _ev(brake["free_mm"], params)
    Lr = _ev(brake.get("rest_mm", L), params)      # cord rest length < free_mm: tied in pre-stretched
    ke, d, h, peak = 0.5 * mass_kg * v * v, 0.0, 0.5, 0.0
    while ke > 0:
        hyp = math.hypot(w, d)
        f_brake = 2 * n * force_n(be, path, (L + 2 * (hyp - w)) / Lr - 1) * d / hyp
        f_pull = strands * force_n(launch_entry, launch_path, max(end_mm - d, 0) / rest_mm - 1)
        peak = max(peak, f_brake)
        ke -= (f_brake - f_pull) * h / 1000.0
        d += h
        if d > 5000:
            raise ValueError("the brake never stops the sled (cord too weak against the launch elastic's pull)")
    return {"stop_mm": d, "peak_n": peak, "peak_g": peak / mass_kg / G, "ke_j": 0.5 * mass_kg * v * v}


@check("bungee_launch")
def bungee_launch(proj, asm, elastic, strands, rest_mm, start_mm, end_mm, payload_g=0.0, moving=(), moving_g=None,
                  angle_deg=0.0, rolling_mu=0.0, efficiency=None, notch=1, notches=1, notch_pitch_mm=0.0,
                  max_strands=None, min_speed_m_s=None, max_speed_m_s=None, max_g=None, brake=None,
                  curve="force_curve"):
    """Exit speed of a payload from an elastic launcher at its setting (strands x notch) vs [min, max] speed and the
    peak acceleration vs max_g; optional brake stop distance vs brake.max_stop_mm. `curve` picks the catalog force
    curve (the soft end of a sourced spread to prove the speed, the stiff end for peak g, forces and the brake)."""
    p = proj.params or {}
    ev = lambda x: _ev(x, p)  # noqa: E731
    entry = curve_entry(elastic, curve)
    sled_g = ev(moving_g) if moving_g is not None else sum(item_mass_g(proj.items[i]) for i in moving)
    m = (sled_g + ev(payload_g)) / 1000.0
    n, L0, k = int(ev(strands)), ev(rest_mm), ev(notch_pitch_mm)
    shift = lambda nn: (nn - 1) * k  # noqa: E731
    nt = int(ev(notch))
    kw = dict(angle_deg=ev(angle_deg), rolling_mu=ev(rolling_mu), efficiency=efficiency)
    r = launch(entry, elastic, n, L0, ev(start_mm) + shift(nt), ev(end_mm) + shift(nt), m, **kw)
    table = {}
    for ns in range(1, int(ev(max_strands if max_strands is not None else strands)) + 1):
        for nn in range(1, int(ev(notches)) + 1):
            try:
                table[f"{ns}x{nn}"] = round(launch(entry, elastic, ns, L0, ev(start_mm) + shift(nn),
                                                   ev(end_mm) + shift(nn), m, **kw)["v"], 2)
            except ValueError:
                table[f"{ns}x{nn}"] = None        # beyond the measured curve: not a usable setting
    lo = ev(min_speed_m_s) if min_speed_m_s is not None else None
    hi = ev(max_speed_m_s) if max_speed_m_s is not None else None
    ok = (lo is None or r["v"] >= lo) and (hi is None or r["v"] <= hi)
    notes = [f"{n} x {elastic.split('.')[-1]} (rest {L0:g} mm) from {r['e_start'] * 100:.0f} % to {r['e_end'] * 100:.0f} % "
             f"stretch over {r['stroke_m'] * 1000:.0f} mm: {r['work_j']:.0f} J x efficiency {r['eta']:.2f}; "
             f"{m * 1000:.0f} g moving ({ev(payload_g):.0f} g payload) at {ev(angle_deg):g} deg -> {r['v']:.2f} m/s"]
    if lo is not None or hi is not None:
        notes.append(f"wanted {lo if lo is not None else '-'}..{hi if hi is not None else '-'} m/s")
    mg = ev(max_g) if max_g is not None else None
    notes.append(f"peak {r['peak_g']:.1f} g at release ({r['pull_n']:.0f} N pull)" + (f" vs max {mg:g} g" if mg else ""))
    if mg is not None and r["peak_g"] > mg:
        ok = False
    out = {"value": round(r["v"], 2), "limit": lo if lo is not None else hi, "peak_g": round(r["peak_g"], 2),
           "curve": curve, "pull_n": round(r["pull_n"], 1), "end_pull_n": round(r["end_pull_n"], 1), "work_j": round(r["work_j"], 1), "table": table}
    if brake:
        sled = sled_g / 1000.0
        b = stop(brake, r["v"], sled, entry, elastic, n, L0, ev(end_mm) + shift(nt), p)
        mx = ev(brake["max_stop_mm"])
        notes.append(f"brake: {sled * 1000:.0f} g sled at {r['v']:.1f} m/s ({b['ke_j']:.0f} J) stops in {b['stop_mm']:.0f} mm "
                     f"(max {mx:g}), peak {b['peak_n']:.0f} N = {b['peak_g']:.0f} g on the sled")
        ok = ok and b["stop_mm"] <= mx
        out.update(brake_stop_mm=round(b["stop_mm"], 1), brake_peak_n=round(b["peak_n"], 1), brake_peak_g=round(b["peak_g"], 1))
    return {"ok": ok, **out, "detail": "; ".join(notes)}
