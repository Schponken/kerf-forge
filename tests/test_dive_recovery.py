"""Recovery analysis against independent force/kinematic calculations; no CAD or FEA."""
from types import SimpleNamespace

import pytest
from kerf import aero, req_aero, requirements


@pytest.fixture
def plane(monkeypatch):
    proj = SimpleNamespace(params={}, items={})
    geometry = {'sweep_c4_deg': 0.0, 'area_mm2': 200000.0}
    monkeypatch.setattr(req_aero, '_pf', lambda *a: SimpleNamespace(root_airfoil='test', geometry=lambda: geometry))
    monkeypatch.setattr(req_aero, '_mass', lambda p: 2000.0)
    monkeypatch.setattr(aero, 'clmax_2d', lambda *a: (1.0 / .9, 200000))
    return proj


def test_eas_load_and_pullout_radius_against_force_balance(plane):
    r = req_aero.dive_recovery(plane, None, 100, 80, 2, structural_limit_g=6)
    q = .5 * 1.225 * (80 / 3.6) ** 2
    assert r['ok']
    assert r['lift_capacity_g'] == pytest.approx(q * .2 / (2 * 9.80665), abs=.001)
    assert r['feasible_kinematic_radius_m'] == pytest.approx((80 / 3.6) ** 2 / 9.80665, abs=.01)
    assert r['dive_q_pa'] / (.5 * 1.225 * (150 / 3.6) ** 2) == pytest.approx(4/9, abs=1e-5)


def test_altitude_keeps_eas_load_but_increases_tas_and_radius(plane):
    low = req_aero.dive_recovery(plane, None, 100, 80, 2, structural_limit_g=6)
    high = req_aero.dive_recovery(plane, None, 100, 80, 2, structural_limit_g=6, altitude_m=3000)
    assert high['lift_capacity_g'] == low['lift_capacity_g']
    assert high['dive_q_pa'] == low['dive_q_pa']
    assert high['density_kg_m3'] == pytest.approx(.909, abs=.003)
    assert high['reopen_tas_kmh'] > low['reopen_tas_kmh']
    assert high['conditional_radius_m'] / low['conditional_radius_m'] == pytest.approx(1.225 / high['density_kg_m3'], abs=.001)


def test_unknown_structure_never_passes_or_reports_available_radius(plane):
    r = req_aero.dive_recovery(plane, None, 100, 80, 2)
    assert not r['ok'] and r['status'] == 'unproven' and r['value'] is None
    assert r['lift_capacity_g'] > 2
    assert r['feasible_kinematic_radius_m'] is None
    assert r['evidence']['deployment'] == r['evidence']['flutter'] == 'unproven'
    assert 'dive_recovery' in requirements.STRENGTH_CHECKS
    assert requirements.redesign_tier({'check': 'dive_recovery'}) == 0


def test_lift_and_structural_limits_fail_independently(plane):
    lift = req_aero.dive_recovery(plane, None, 100, 80, 4, structural_limit_g=6)
    assert not lift['ok'] and lift['required_recovery_eas_kmh'] > 80
    structure = req_aero.dive_recovery(plane, None, 100, 80, 2, structural_limit_g=1.5)
    assert not structure['ok'] and structure['evidence']['structure'] == 'exceeded'


@pytest.mark.parametrize('override', [dict(dive_eas_kmh=float('nan')), dict(recovery_g=True),
    dict(recovery_g=1), dict(reopen_eas_kmh=110), dict(altitude_m=-1), dict(altitude_m=12000),
    dict(structural_limit_g=float('inf'))])
def test_invalid_envelopes_rejected(plane, override):
    args = dict(dive_eas_kmh=100, reopen_eas_kmh=80, recovery_g=2, structural_limit_g=6)
    args.update(override)
    with pytest.raises(ValueError):
        req_aero.dive_recovery(plane, None, **args)
