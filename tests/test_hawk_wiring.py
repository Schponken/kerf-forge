"""Hawk electrical contract: no CAD build, and known engineering failures stay visible."""
from pathlib import Path

import numpy as np
import pytest
import yaml

from kerf import catalog, electrical as E, project as P, req_electrical as R
from kerf.requirements import _ev

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def hawk():
    proj = P.load(str(ROOT / "projects/hawk_wing"))
    proj.params.update(P.shared_layout(proj))
    return proj


@pytest.fixture
def currents_only(hawk, monkeypatch):
    # Electrical ratings are independent of CAD routing. The flight lead checks the actual assembled routes.
    monkeypatch.setattr(E, "_point", lambda *args, **kwargs: np.zeros(3))
    monkeypatch.setattr(E, "total_mass_g", lambda proj: 1800.0)
    return hawk


def test_complete_power_tree_and_separate_servo_becs(currents_only):
    model = E.analyse(currents_only)
    loads = {"motor", "fc", "esc", "receiver", "gps", "camera", "vtx", "xt60",
             "sweep_servo_r", "sweep_servo_l", "ail_servo_r", "ail_servo_l", "elev_servo", "rud_servo"}
    assert loads == set(model["loads"]) - {"battery"}
    rated = {r["what"]: r for r in model["ratings"] if r["kind"] == "peak A vs burst rating"}
    assert rated["esc.5v"]["value"] == 5.0 and rated["esc.5v"]["limit"] == 7.0
    assert rated["fc.vx"]["value"] == 3.6 and rated["fc.vx"]["limit"] == 7.0
    assert rated["fc.4v5"]["value"] == 1.1 and rated["fc.4v5"]["limit"] == 2.0
    wires = {w["to"]: w for w in model["wires"] if w["kind"] == "power"}
    assert all(wires[s]["from"] == "esc.5v" and wires[s]["v"] == 5 for s in ("sweep_servo_r", "sweep_servo_l"))
    assert all(wires[s]["from"] == "fc.vx" and wires[s]["v"] == 6 for s in ("ail_servo_r", "ail_servo_l", "elev_servo", "rud_servo"))
    assert all(wires[s]["from"] == "fc.4v5" and wires[s]["v"] == 5 for s in ("receiver", "gps", "camera", "vtx"))
    pins = [w["pin"] for w in model["wires"] if w.get("pin")]
    assert set(pins) == {"S1", "S3", "S4", "S5", "S6", "S7", "S8"} and len(pins) == len(set(pins))


def test_stock_motor_lead_failure_is_not_disguised(currents_only):
    model = E.analyse(currents_only)
    assert not currents_only.data["electrical"].get("limits")
    assert currents_only.data["electrical"]["burst_s"] == 10
    phase = next(w for w in model["wires"] if w["id"] == "phases")
    assert phase["gauge"] == 18 and phase["length_mm"] == 365 and phase["conductors"] == 3
    failures = [r for r in model["ratings"] if not r["ok"] and not r.get("soft")]
    assert len(failures) == 1 and failures[0]["what"] == "wire phases AWG 18"
    assert failures[0]["value"] == pytest.approx(227.054, abs=0.001)
    assert failures[0]["limit"] == 60
    power = R.power_budget(currents_only, None)
    assert not power["ok"] and "wire phases AWG 18" in power["detail"]


def test_endurance_target_and_true_estimate_stay_visible(currents_only):
    req = next(r for r in currents_only.data["requirements"] if r["id"] == "flight_time")
    assert req["min_min"] == 20 and not req.get("advisory")
    result = R.flight_time(currents_only, None, req["min_min"])
    assert not result["ok"] and result["limit"] == 20
    assert result["value"] == pytest.approx(18.15, abs=0.01)
    assert E.wiring_mass_g(currents_only) == pytest.approx(109.72)


def test_route_expressions_and_moving_panel_references(hawk):
    wires = hawk.data["wiring"]
    assert len(wires) == 25 and len({w["id"] for w in wires}) == len(wires)
    for wire in wires:
        for point in wire.get("route", []):
            values = point["at"] if isinstance(point, dict) else point
            assert len(values) == 3
            assert all(np.isfinite(_ev(value, hawk.params)) for value in values)
    for side in ("r", "l"):
        run = next(w for w in wires if w["id"] == f"ail_{side}_pwr")
        moving = [p["item"] for p in run["route"] if isinstance(p, dict)]
        assert moving == [f"hub_{side}"] * 4 + [f"wing_{side}2"] * 20
    # The tail exits sideways before following the boom externally, avoiding the transverse clamp screw.
    assert [hawk.params[f"wire_elev_3_{a}"] for a in "xyz"] == [190, 35, -38]
    assert hawk.params["wire_elev_5_z"] == hawk.params["boom_z"] - 8


def test_route_helper_tracks_actual_electronics_and_transport_params(hawk):
    before = dict(hawk.params)
    # These are real exposed tuning variables, not hard-coded coordinates from the old 150 mm pivot layout.
    changed = P.load(str(ROOT / "projects/hawk_wing"))
    changed.params.update(pivot_y=132, hub_y1=177, spar_y0=138, fuse_x1=290, bat_x=-65)
    after = {**changed.params, **P.shared_layout(changed)}
    assert after["wire_sweep_r_6_y"] == 102  # shared glove entry = pivot_y - 30
    assert after["wire_elev_4_x"] == 298  # external route clears the actual fuselage end
    assert after["wire_ail_hub_r_3_y"] == 178  # hub channel root = hub_y1 + 1
    assert after["wire_ail_hub_r_0_y"] != before["wire_ail_hub_r_0_y"]


def test_detachable_servo_connector_bom_has_real_catalog_parts(hawk):
    connector = catalog.get("electronics.connectors.crimp_pin_male_pololu1931")
    assert connector["source"] == "https://www.pololu.com/product/1931"
    assert connector["wire_awg_min"] == 28 and connector["wire_awg_max"] == 22 and connector["pitch"] == 2.54
    assert "current_a" not in connector and "weight_g" not in connector  # not published by the manufacturer
    rows = {r["price_key"]: r for r in hawk.data["bom_extra"]}
    assert rows["electronics.connectors.crimp_pin_male_pololu1931"]["qty"] == 18
    assert rows["electronics.connectors.servo_housing_1x3_pololu1902"]["qty"] == 6
