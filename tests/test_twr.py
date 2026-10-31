"""thrust_to_weight with voltage derating, against a hand calculation."""
import types

import pytest

from kerf import requirements


@pytest.fixture
def proj(monkeypatch):
    monkeypatch.setattr(requirements, "item_mass_g", lambda it: 500.0)
    return types.SimpleNamespace(items={"a": types.SimpleNamespace(role="part")}, data={})


def test_plain_ratio(proj):
    r = requirements.REGISTRY["thrust_to_weight"](proj, None, thrust_g_total=1000, min_ratio=2.0)
    assert r["ok"] and r["value"] == 2.0


def test_voltage_derate(proj):
    # 1000 g measured at 24 V, flown at 22.2 V: 1000 x (22.2/24)^2 = 855.6 g -> 1.71 on 500 g
    r = requirements.REGISTRY["thrust_to_weight"](proj, None, thrust_g_total=1000, min_ratio=2.0, test_v=24, pack_v=22.2)
    assert r["value"] == pytest.approx(1.71, abs=0.005) and not r["ok"]
    with pytest.raises(ValueError):
        requirements.REGISTRY["thrust_to_weight"](proj, None, thrust_g_total=1000, min_ratio=2.0, test_v=24)


def test_thrust_from_catalog_motors(proj):
    # 2 x XING2 2207 (1685 g at 24.0 V) x 0.78 coax x 0.85^2 cap = 1899 g at 24 V; 6S nominal 22.2 V:
    # 1899 x (22.2/24)^2 = 1625 g on 500 g -> 3.25
    S = types.SimpleNamespace
    proj.items.update({"m1": S(role="purchased", spec={"catalog": "drone.motors.2207_1855kv_6s"}),
                       "m2": S(role="purchased", spec={"catalog": "drone.motors.2207_1855kv_6s"}),
                       "bat": S(role="purchased", spec={"catalog": "drone.batteries.6S_1100"})})
    proj.data["electrical"] = {"battery": "bat"}
    r = requirements.REGISTRY["thrust_to_weight"](proj, None, min_ratio=2.0, motors=["m1", "m2"], factor=0.78,
                                                     output_limit=0.85)
    m = 500.0 * 4                                   # the fixture prices every item at 500 g
    assert r["value"] == pytest.approx(2 * 1685 * 0.78 * 0.85 ** 2 * (22.2 / 24) ** 2 / m, abs=0.005)
    assert "at 24.0 V" in r["detail"] and "22.2 V" in r["detail"]
