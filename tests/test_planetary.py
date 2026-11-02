"""Planetary sets (kerf/drives.planetary + req_gears.planetary_bending): tooth-count rules, meshing without
interference, ratio, and the Lewis check on the most loaded planet."""
import math
from types import SimpleNamespace as NS

import pytest

from kerf import drives
from kerf.req_gears import lewis_y, planetary_bending


def test_rules_catch_the_three_ways_a_set_cannot_be_built():
    assert drives.planetary_rules(12, 18, 48, 3, 1.5) == []
    assert "z_sun + 2 z_planet" in drives.planetary_rules(12, 18, 50, 3, 1.5)[0]
    assert "not whole" in drives.planetary_rules(12, 18, 48, 7, 1.5)[0]                # 60 / 7
    assert any("tips are" in b for b in drives.planetary_rules(12, 18, 48, 5, 1.5))      # 5 planets of 30 mm tip dia crowd


def test_set_meshes_without_interference_at_the_right_ratio():
    sun, planets, ring, info = drives.planetary(1.5, 12, 18, 48, 3, 8)
    assert info.ratio == pytest.approx(5.0) and info.center == pytest.approx(22.5)
    assert [round(math.hypot(*p), 4) for p in info.planet_xy] == [22.5] * 3
    assert all((sun & p).volume < 1e-6 and (ring & p).volume < 1e-6 for p in planets)
    assert info.ring_od == pytest.approx(48 * 1.5 + 2 * 2.5 * 1.5 + 0.0, abs=1.0)      # rim 2.5 modules outside the root


def test_most_loaded_planet_lewis_stress():
    proj = NS(params={})
    r = planetary_bending(proj, None, module=1.5, z_sun=12, z_planet=18, z_ring=48, n_planets=3, width=8,
                          torque_nmm=1000, material="PETG", sf=3)
    Ft = 1000 / 9.0 / 3 * 2.25                                   # T / r_sun / n x K_gamma (75 % on one planet)
    assert r["value"] == pytest.approx(Ft / (8 * 1.5 * lewis_y(12)), rel=1e-3) and r["limit"] == pytest.approx(16.0)
    assert r["ok"] == (r["value"] <= 16.0)
    bad = planetary_bending(proj, None, module=1.5, z_sun=12, z_planet=18, z_ring=48, n_planets=7, width=8, torque_nmm=10)
    assert not bad["ok"] and "not whole" in bad["detail"]


def test_worm_numbers_and_printable_worm():
    ws = drives.worm_numbers(1.5, 1, 30, 12.0, 0.27)
    lam = math.atan(1.5 / 12.0)
    assert ws.ratio == 30 and ws.lead_deg == pytest.approx(math.degrees(lam))
    pn = math.radians(20)
    assert ws.efficiency == pytest.approx((math.cos(pn) - 0.27 * math.tan(lam)) / (math.cos(pn) + 0.27 / math.tan(lam)))
    assert ws.self_locking                                         # tan 7.1 deg = 0.125 < 0.27
    assert not drives.worm_numbers(1.5, 4, 30, 12.0, 0.27).self_locking   # 4 starts: lead 26.6 deg
    w = drives.worm(1.5, 1, 12.0, 20.0, bore=3.0)
    bb = w.bounding_box().size
    assert w.is_valid and bb.Z == pytest.approx(20.0, abs=1e-3) and bb.X == pytest.approx(12.0 + 2 * 1.5, abs=0.1)
    from kerf.req_gears import worm_drive
    r = worm_drive(NS(params={}), None, module=1.5, starts=1, z_wheel=30, worm_d=12, width=8, torque_out_nmm=2000,
                   must_self_lock=True)
    assert r["self_locking"] and r["value"] == pytest.approx(2000 / 22.5 / (8 * 1.5 * lewis_y(30)), rel=1e-3)
