"""bungee_launch: exit speed, peak g and the V-cord brake stop against hand calculations (linear test strand)."""
import math
from types import SimpleNamespace

import pytest

from kerf import req_launch as RL
from kerf.requirements import G

LIN = {"force_curve": [[1.0, 100.0], [3.0, 300.0]], "efficiency": 1.0, "mass_per_m_g": 0.0}   # 100 N per 100 % stretch


@pytest.fixture
def cat(monkeypatch):
    monkeypatch.setattr(RL.catalog, "get", lambda path: {"test.lin": LIN}[path])
    LIN["force_curve_stiff"] = [[1.0, 200.0], [3.0, 600.0]]                     # twice as stiff


def _run(**kw):
    proj = SimpleNamespace(params={"strands_set": 1}, items={})
    base = dict(elastic="test.lin", strands="strands_set", rest_mm=1000, start_mm=2000, end_mm=1000, moving_g=1000)
    return RL.bungee_launch(proj, None, **{**base, **kw})


def test_flat_rail_energy_to_speed(cat):
    # W = 100 N x 1 m / 2 = 50 J -> 1 kg at sqrt(2 x 50 / 1) = 10 m/s; peak 100 N / 1 kg = 10.2 g
    r = _run(min_speed_m_s=9.9)
    assert r["ok"] and r["value"] == pytest.approx(10.0, abs=0.01)
    assert r["peak_g"] == pytest.approx(100 / G, abs=0.01) and r["work_j"] == pytest.approx(50.0, abs=0.05)


def test_slope_friction_efficiency_and_max_g(cat):
    # 30 deg ramp, mu 0.05: drag = 9.80665 (0.5 + 0.05 cos30) N over 1 m; eta 0.8 on 50 J
    drag = G * (0.5 + 0.05 * math.cos(math.radians(30)))
    r = _run(angle_deg=30, rolling_mu=0.05, efficiency=0.8, max_g=5)
    assert r["value"] == pytest.approx(math.sqrt(2 * (40 - drag)), abs=0.01)
    assert not r["ok"] and r["peak_g"] == pytest.approx((80 - drag) / G, abs=0.01)   # 7.3 g > 5 g


def test_strand_mass_notches_and_table(cat):
    # 2 strands, notch 3 moves both lengths +100 mm: e from 1.1 to 0.1 -> W = 2 x 100 x (1.1^2 - 0.1^2) / 2 x 1 m = 120 J
    LIN["mass_per_m_g"] = 300.0              # 0.3 kg per strand -> m_eff = 1 + 2 x 0.3 / 3 = 1.2 kg
    try:
        r = _run(strands=2, notch=3, notches=3, notch_pitch_mm=50, max_strands=2)
    finally:
        LIN["mass_per_m_g"] = 0.0
    assert r["value"] == pytest.approx(math.sqrt(2 * 120 / 1.2), abs=0.02)
    assert r["table"]["2x3"] == pytest.approx(r["value"], abs=0.01) and r["table"]["1x1"] < r["table"]["2x1"]


def test_beyond_curve_refused(cat):
    with pytest.raises(ValueError, match="beyond its measured force curve"):
        _run(start_mm=4500)


def test_v_cord_brake_stop_distance(cat):
    # cord linear 100 N per 100 %: stored energy = n 100 D^2 / (2 L); no launch pull left (end = rest length)
    # 0.5 kg sled at 10 m/s = 25 J -> D = sqrt(2 L KE / (100 n)), d = sqrt((w + D/2)^2 - w^2)
    L, w, n = 400.0, 30.0, 2
    r = _run(moving_g=500, payload_g=500, brake={"elastic": "test.lin", "strands": n, "half_gap_mm": w, "free_mm": L,
                                                 "max_stop_mm": 300})
    v = r["value"]                                      # 1 kg launched: 10 m/s; the 0.5 kg sled alone is braked
    ke = 0.5 * 0.5 * v * v * 1000                      # N mm
    D = math.sqrt(2 * L * ke / (100 * n))
    d = math.sqrt((w + D / 2) ** 2 - w * w)
    assert r["brake_stop_mm"] == pytest.approx(d, abs=1.0) and r["ok"]
    assert r["brake_peak_n"] == pytest.approx(2 * n * 100 * D / L * d / math.hypot(w, d), rel=0.01)


def test_named_curve_doubles_the_energy(cat):
    # the stiff curve is 2x the force at every stretch: 2 x 50 J -> sqrt(200) m/s; a missing curve is refused
    r = _run(curve="force_curve_stiff")
    assert r["value"] == pytest.approx(math.sqrt(200), abs=0.01) and r["curve"] == "force_curve_stiff"
    with pytest.raises(ValueError, match="has no 'nope'"):
        _run(curve="nope")


def test_prestretched_brake_stops_sooner(cat):
    b = {"elastic": "test.lin", "strands": 2, "half_gap_mm": 30, "free_mm": 400, "max_stop_mm": 300}
    loose = _run(moving_g=500, payload_g=500, brake=b)["brake_stop_mm"]
    tight = _run(moving_g=500, payload_g=500, brake={**b, "rest_mm": 200})["brake_stop_mm"]
    assert tight < loose
