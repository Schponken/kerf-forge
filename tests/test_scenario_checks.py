"""Synthetic scenario contracts: hand-calculated quantities, never real plant demand or hardware certification."""
import copy

import pytest
from build123d import Align, Axis, Box, Location

from kerf import assembly, electrical, project, proxies, requirements
from kerf.ctx import Ctx
from kerf.req_scenario import reservoir_capacity, sensor_coverage


def _water(tmp_path):
    region = project.Item("water", "keepout", {}, Box(100, 100, 200))
    return project.Project("Synthetic water volume", tmp_path, {}, {}, {"water": region})


def test_reservoir_volume_units_reserve_and_demand_by_hand(tmp_path):
    proj = _water(tmp_path)
    # 100 × 100 × 200 mm = 2 L; 90% usable minus 200 mL reserve = 1600 mL = 16 days at 100 mL/day.
    r = reservoir_capacity(proj, None, "water", daily_ml=100, days=14, usable_fraction=0.9, reserve_ml=200)
    assert r["ok"] and r["capacity_ml"] == pytest.approx(2000)
    assert r["available_ml"] == pytest.approx(1600) and r["value"] == pytest.approx(16)
    assert r["needed_capacity_ml"] == pytest.approx(1600 / 0.9)
    assert "Does not prove" in r["detail"]
    fail = reservoir_capacity(proj, None, "water", daily_ml=125, days=14, usable_fraction=0.9, reserve_ml=200)
    assert not fail["ok"] and fail["value"] == pytest.approx(12.8)
    empty = reservoir_capacity(proj, None, "water", daily_ml=100, days=14, usable_fraction=0.9, reserve_ml=2000)
    assert not empty["ok"] and empty["value"] == 0


@pytest.mark.parametrize("change", [
    {"daily_ml": 0}, {"daily_ml": -1}, {"daily_ml": float("nan")}, {"days": float("inf")},
    {"days": True}, {"usable_fraction": 0}, {"usable_fraction": 1.01}, {"reserve_ml": -1},
    {"daily_ml": 1e308, "days": 1e308},
    {"daily_ml": 1e-308},
])
def test_reservoir_rejects_invalid_scenario_numbers(tmp_path, change):
    kw = dict(volume="water", daily_ml=100, days=14, usable_fraction=0.9, reserve_ml=200) | change
    with pytest.raises(ValueError):
        reservoir_capacity(_water(tmp_path), None, **kw)


def test_reservoir_requires_actual_internal_region_not_tank_material(tmp_path):
    proj = _water(tmp_path)
    proj.items["water"].role = "printed"
    with pytest.raises(ValueError, match="keep-out region"):
        reservoir_capacity(proj, None, "water", 100, 14, 0.9)
    proj.items["water"].role = "keepout"
    proj.items["water"].shape = None
    with pytest.raises(ValueError, match="valid solid"):
        reservoir_capacity(proj, None, "water", 100, 14, 0.9)


def _sensor(tmp_path, z=100):
    ctx = Ctx("base", {})
    ctx.linear("slide", Axis((0, 0, 0), (0, 0, 1)), range=(0, 200))
    ctx.rigid("region", Location((0, 0, z)))
    base = ctx.finish(Box(2, 2, 2))
    view_spec = {"proxy": "view_cone", "length": 200, "aperture": [2, 2], "hfov_deg": 90, "vfov_deg": 90}
    target_spec = {"proxy": "box", "size": [20, 20, 20]}
    items = {"base": project.Item("base", "printed", {}, base),
             "view": project.Item("view", "keepout", view_spec, proxies.build(Ctx("view", {}), view_spec)),
             "target": project.Item("target", "keepout", target_spec, proxies.build(Ctx("target", {}), target_spec))}
    data = {"assembly": {"root": "base", "joints": [
        {"parent": "base.slide", "child": "view.bottom", "name": "slide", "range": [0, 200]},
        {"parent": "base.region", "child": "target.bottom"}]}}
    proj = project.Project("Synthetic sensing region", tmp_path, data, {}, items)
    asm = assembly.plan(proj)
    assembly.solve(asm)
    return proj, asm


def test_coverage_uses_placed_solids_and_restores_pose(tmp_path):
    proj, asm = _sensor(tmp_path)
    home = proj.items["view"].shape.location
    r = sensor_coverage(proj, asm, "view", "target")
    assert r["ok"] and r["value"] == pytest.approx(100)
    assert "does not prove unobstructed visibility" in r["detail"]
    moved = sensor_coverage(proj, asm, "view", "target", pose={"slide": 200})
    assert not moved["ok"] and moved["value"] == 0
    assert proj.items["view"].shape.location == home


def test_coverage_boundary_partial_outside_and_near_miss(tmp_path):
    proj, asm = _sensor(tmp_path, z=190)
    # The 20 mm target extends from z=190 to 210; exactly half lies before the z=200 frustum end.
    partial = sensor_coverage(proj, asm, "view", "target", min_fraction=0.5)
    assert partial["ok"] and partial["value"] == pytest.approx(50)
    assert not sensor_coverage(proj, asm, "view", "target")["ok"]
    proj, asm = _sensor(tmp_path, z=200.001)
    assert sensor_coverage(proj, asm, "view", "target")["value"] == 0
    proj, asm = _sensor(tmp_path, z=180.001)
    near = sensor_coverage(proj, asm, "view", "target")
    assert not near["ok"] and 99.99 < near["value"] < 100  # Never round a small uncovered sliver into a pass.


@pytest.mark.parametrize("fraction", [0, -1, 1.01, float("nan"), float("inf"), True])
def test_coverage_rejects_invalid_fraction(tmp_path, fraction):
    proj, asm = _sensor(tmp_path)
    with pytest.raises(ValueError, match="min_fraction"):
        sensor_coverage(proj, asm, "view", "target", fraction)


def test_coverage_requires_declared_view_cone_and_distinct_target(tmp_path):
    proj, asm = _sensor(tmp_path)
    with pytest.raises(ValueError, match="view_cone"):
        sensor_coverage(proj, asm, "target", "view")
    with pytest.raises(ValueError, match="distinct"):
        sensor_coverage(proj, asm, "view", "view")


@pytest.mark.parametrize("pose", [{"typo": 20}, {"slide": -1}, {"slide": 201}, {"slide": float("nan")}, {"slide": True}, [20]])
def test_coverage_never_silently_uses_home_for_invalid_pose(tmp_path, pose):
    proj, asm = _sensor(tmp_path)
    with pytest.raises(ValueError, match="pose"):
        sensor_coverage(proj, asm, "view", "target", pose=pose)


@pytest.mark.parametrize("on,expected", [(0, 0.1), (15, 0.325), (60, 1.0)])
def test_duty_average_keeps_peak_independent(on, expected):
    avg, peak = electrical.duty_current(active_a=1, idle_a=0.1, on_s=on, period_s=60, peak_a=2)
    assert avg == pytest.approx(expected) and peak == 2


@pytest.mark.parametrize("change", [
    {"active_a": -1}, {"idle_a": float("nan")}, {"period_s": 0}, {"period_s": float("inf")},
    {"on_s": -1}, {"on_s": 61}, {"peak_a": 0.5}, {"active_a": True}, {"on_s": "15"},
])
def test_duty_rejects_invalid_or_reversed_cycle(change):
    args = dict(active_a=1, idle_a=0.1, on_s=15, period_s=60, peak_a=2) | change
    with pytest.raises(electrical.ElectricalError):
        electrical.duty_current(**args)


def test_runtime_reuses_full_power_tree_and_retains_peak_ratings(tmp_path):
    from test_electrical import _proj

    proj, asm = _proj(tmp_path)
    before = electrical.analyse(proj)
    proj.data["electrical"]["draw"] = {f"m{i}": {"duty": {"active_a": 1, "idle_a": 0.1, "on_s": 15, "period_s": 60},
                                               "peak_a": 15.84, "why": "Synthetic duty test, not a plant-watering design"}
                                       for i in range(1, 5)}
    m = electrical.analyse(proj)
    # Four loads at 0.325 A plus FC 0.3 A and receiver referred through 5 V regulator (80% efficiency).
    expected_avg = 4 * 0.325 + 0.3 + 0.1 * 5 / (16.8 * 0.8)
    assert m["avg_a"] == pytest.approx(expected_avg, abs=0.0005)  # report rounds to mA
    assert m["peak_a"] == before["peak_a"]
    assert "15/60 s on" in m["loads"]["m1"]["source"]
    proj.data["requirements"] = [{"id": "trip", "check": "run_time", "min_min": 40}]
    result = requirements.run_all(proj, asm)[0]
    assert result["ok"] and result["value"] == pytest.approx(1.5 * 0.8 / expected_avg * 60, abs=0.05)
    proj.data["requirements"][0]["min_min"] = 48
    assert not requirements.run_all(proj, asm)[0]["ok"]
    # Contradictory average or missing peak cannot silently pick a lower power budget.
    good = copy.deepcopy(proj.data["electrical"]["draw"]["m1"])
    for invalid in [good | {"avg_a": 0}, {k: v for k, v in good.items() if k != "peak_a"}]:
        proj.data["electrical"]["draw"]["m1"] = invalid
        with pytest.raises(electrical.ElectricalError, match="explicit peak_a"):
            electrical.analyse(proj)
    for duty in [{k: v for k, v in good["duty"].items() if k != "on_s"},
                 good["duty"] | {"on_ms": 15000}, good["duty"] | {"peak_a": 2}]:
        proj.data["electrical"]["draw"]["m1"] = good | {"duty": duty}
        with pytest.raises(electrical.ElectricalError, match="exactly active_a"):
            electrical.analyse(proj)


def test_registry_reports_units_failures_and_specific_advice(tmp_path):
    proj = _water(tmp_path)
    proj.data["requirements"] = [{"id": "trip_water", "check": "reservoir_capacity", "volume": "water",
                                  "daily_ml": 125, "days": 14, "usable_fraction": 0.9, "reserve_ml": 200}]
    result = requirements.run_all(proj, None)[0]
    assert not result["ok"] and result["unit"] == "days" and result["bound"] == "min"
    assert "2166.67 mL" in result["advice"][0]
    proj.data["requirements"][0]["daily_ml"] = float("nan")
    invalid = requirements.run_all(proj, None)[0]
    assert not invalid["ok"] and invalid["value"] is None and "finite" in invalid["detail"]
