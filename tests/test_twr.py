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
