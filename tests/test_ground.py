"""Synthetic steady-climb force budgets; no measured rover, tire coefficient or motor rating is claimed."""
import math
from types import SimpleNamespace as NS

import pytest
from build123d import Box

from kerf import advice, assembly as A, project as P, requirements as R
from kerf.req_ground import wheel_drive


BASE = dict(wheel_radius_mm=100, wheel_torque_nm=5, slope_deg=30, rolling_coeff=0.02, traction_mu=0.8,
            normal_load_fractions=[0.5, 0.5], torque_basis="Synthetic independent drives, continuous at test speed",
            terrain_basis="Synthetic surface and equal normal loads at the stated slope")


def _proj(mass_g=10000):
    return NS(params={}, data={}, items={"body": NS(role="purchased", shape=Box(1, 1, 1), spec={"mass_g": mass_g})})


def _run(proj=None, **kw):
    return wheel_drive(proj or _proj(), None, **(BASE | kw))


def test_grade_rolling_torque_and_traction_by_hand():
    r = _run()
    # 10 kg: N = 98.0665*cos30, grade = 49.03325; rolling = .02*N.
    assert r["grade_force_n"] == pytest.approx(49.03325)
    assert r["rolling_force_n"] == pytest.approx(1.698561604)
    assert r["value"] == pytest.approx(50.731811604)
    assert r["traction_per_wheel_n"] == pytest.approx([33.971232084, 33.971232084])
    assert r["motor_force_per_wheel_n"] == 50  # 5 N*m / 0.1 m; no mm/m error
    assert r["limit"] == pytest.approx(67.942464168)
    assert r["required_total_torque_nm"] == pytest.approx(5.0731811604)
    assert r["limiting"] == "traction" and r["ok"]
    assert "no starting, braking, speed, tip-over or runtime proof" in r["detail"]


def test_motor_torque_can_limit_a_grippy_surface():
    r = _run(wheel_torque_nm=2)
    assert r["limit"] == 40 and not r["ok"] and r["limiting"] == "motor torque"
    assert "continuous" in advice.advise(r | {"check": "wheel_drive"}, BASE)[0]
    assert _run(wheel_radius_mm=50, wheel_torque_nm=2)["ok"]


def test_asymmetric_wheel_loads_cannot_borrow_unused_motor_torque():
    # At level, rolling demand 39.2266 N. Naive min(sum motor=50, sum traction=98.0665) falsely passes.
    r = _run(slope_deg=0, rolling_coeff=0.4, traction_mu=1, wheel_torque_nm=2.5,
             normal_load_fractions=[0.1, 0.9])
    assert r["available_per_wheel_n"] == pytest.approx([9.80665, 25])
    assert r["limit"] == pytest.approx(34.80665)
    assert r["limit"] < r["value"]
    assert not r["ok"] and r["limiting"] == "mixed"
    tip = advice.advise(r | {"check": "wheel_drive"}, BASE)[0]
    assert "more continuous torque" in tip and "wheel loads" in tip
    assert _run(slope_deg=0, rolling_coeff=0.4, traction_mu=1, wheel_torque_nm=3,
                normal_load_fractions=[0.1, 0.9])["ok"]  # the heavily loaded wheel can supply more force


def test_unloaded_wheel_and_passive_wheel_fraction():
    r = _run(normal_load_fractions=[0, 0.4])
    assert r["available_per_wheel_n"][0] == 0
    assert r["limit"] == pytest.approx(27.176985667) and not r["ok"]
    assert "extra motor torque alone" in advice.advise(r | {"check": "wheel_drive"}, BASE)[0]
    assert _run(traction_mu=0)["limit"] == 0 and not _run(traction_mu=0)["ok"]
    assert _run(normal_load_fractions=[0, 0])["limit"] == 0


def test_exact_boundary_and_just_beyond_it_use_unrounded_forces():
    r = _run(slope_deg=0, rolling_coeff=0.1, traction_mu=0.1, normal_load_fractions=[1])
    assert r["value"] == r["limit"] and r["ok"]
    assert not _run(slope_deg=0, rolling_coeff=0.1000000001, traction_mu=0.1,
                    normal_load_fractions=[1])["ok"]
    # An ideal rolling body can coast without force. This does not claim it can start.
    assert _run(slope_deg=0, rolling_coeff=0, wheel_torque_nm=0, traction_mu=0)["ok"]


def test_mass_wiring_payload_and_explicit_include():
    p = _proj()
    p.items["extra"] = NS(role="purchased", shape=Box(1, 1, 1), spec={"mass_g": 500})
    p.items["space"] = NS(role="keepout", shape=Box(1, 1, 1), spec={})
    p.data["wiring"] = [{"length_mm": 1000, "gauge": 22, "conductors": 2}]
    # Existing catalog: AWG22 silicone wire 5 g/m/conductor, plus 250 g explicit payload.
    assert _run(p, payload_g=250)["mass_g"] == 10760
    assert _run(p, include=["body"], payload_g=250)["mass_g"] == 10250
    p.data["wiring"][0]["supplied"] = "extra"
    assert _run(p)["mass_g"] == 10500  # supplied lead already counted in purchased mass


def test_existing_catalog_and_printed_mass_models_are_used():
    p = _proj()
    p.items["body"].spec = {"catalog": "boards.pca9685_adafruit"}
    assert _run(p)["mass_g"] == 9  # existing catalog weight, not proxy box volume
    p.items["body"] = NS(role="printed", shape=Box(10, 10, 10), spec={"material": "PLA", "infill": 1})
    assert _run(p)["mass_g"] == pytest.approx(1.24)


@pytest.mark.parametrize("change", [
    {"wheel_radius_mm": 0}, {"wheel_radius_mm": -1}, {"wheel_radius_mm": 5e-324},
    {"wheel_torque_nm": -1}, {"wheel_torque_nm": math.inf}, {"traction_mu": math.nan},
    {"traction_mu": -1}, {"rolling_coeff": -1}, {"payload_g": -1},
    {"slope_deg": -1}, {"slope_deg": 90}, {"slope_deg": 100}, {"slope_deg": True},
    {"wheel_radius_mm": "missing_param"}, {"normal_load_fractions": []}, {"normal_load_fractions": "0.5,0.5"},
    {"normal_load_fractions": [-0.1, 0.5]}, {"normal_load_fractions": [0.6, 0.5]},
    {"normal_load_fractions": [math.inf]}, {"normal_load_fractions": [False]},
    {"torque_basis": " "}, {"terrain_basis": None}, {"torque_basis": 1},
    {"include": []}, {"include": "body"}, {"include": ["body", "body"]}, {"include": ["missing"]},
    {"wheel_torque_nm": 1e308, "wheel_radius_mm": 1e-308},
])
def test_invalid_inputs_are_refused(change):
    with pytest.raises(ValueError, match="wheel_drive"):
        _run(**change)


@pytest.mark.parametrize("mass", [0, -1, math.nan, math.inf])
def test_invalid_or_unknown_component_mass_cannot_pass(mass):
    with pytest.raises(ValueError, match="mass"):
        _run(_proj(mass))
    p = _proj()
    p.items["body"].spec = {"catalog": "not_a_catalog_entry"}
    with pytest.raises(ValueError, match="sourced catalog weight"):
        _run(p)


def test_missing_shape_and_keepout_in_include_are_errors():
    p = _proj()
    p.items["body"].shape = None
    with pytest.raises(ValueError, match="built, mass-bearing"):
        _run(p)
    p.items["body"].role = "keepout"
    with pytest.raises(ValueError, match="built, mass-bearing"):
        _run(p, include=["body"])


def test_invalid_wire_mass_cannot_cancel_out_good_mass():
    p = _proj()
    p.data["wiring"] = [{"length_mm": -10, "gauge": 22}, {"length_mm": 1000, "gauge": 22}]
    with pytest.raises(ValueError, match="wire length"):
        _run(p)
    p.data["wiring"][0] = {"length_mm": 10, "gauge": 22, "conductors": 0.5}
    with pytest.raises(ValueError, match="conductors"):
        _run(p)


def test_yaml_registration_expressions_units_advice_and_existing_tip_over(tmp_path):
    import yaml
    d = tmp_path / "synthetic_rover_budget"
    (d / "parts").mkdir(parents=True)
    (d / "parts/body.py").write_text("from build123d import Box\ndef build(ctx):\n    return ctx.finish(Box(100, 60, 20))\n")
    req = {"id": "climb", "check": "wheel_drive", **BASE, "wheel_radius_mm": "diameter / 2", "wheel_torque_nm": 0}
    (d / "project.yaml").write_text(yaml.safe_dump({"name": "Synthetic budget only", "params": {"diameter": 200},
        "parts": {"body": {"file": "parts/body.py", "material": "PLA", "infill": 1}},
        "assembly": {"root": "body", "joints": []},
        "requirements": [req, {"id": "balance", "check": "tip_over", "min_deg": 35}]}))
    p = P.build(P.load(str(d)))
    rows = R.run_all(p, A.plan(p))
    r = next(r for r in rows if r["id"] == "climb")
    assert not r["ok"] and r["unit"] == "N" and r["bound"] == "max"
    assert r["mass_g"] == pytest.approx(148.8)
    assert r["advice"] and R.redesign_tier(req) == 0
    assert next(r for r in rows if r["id"] == "balance")["ok"]  # old all-directions support check, unchanged
    req["normal_load_fractions"] = [2]
    bad = R._run_one(p, A.plan(p), req, False)
    assert not bad["ok"] and bad["value"] is None and "sum to at most 1" in bad["detail"]
