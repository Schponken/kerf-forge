"""A prop is modelled as its swept disc (keep-out) but is a bought, flying part: its mass rides on its motor and it
is listed as purchased (BOM + report)."""
from types import SimpleNamespace as S

import pytest

from kerf import catalog, checks, project as P


def test_prop_mass_rides_on_its_motor():
    motor = P.Item("motor", "purchased", {"catalog": "drone.motors.2806_5_1300kv_7in"})
    prop = P.Item("prop", "keepout", {"catalog": "drone.props.7in", "proxy": "prop_disc", "owner": "motor"})
    proj = S(items={"motor": motor, "prop": prop})
    P.carry_props(proj)
    w = catalog.num(catalog.get("drone.props.7in"), "weight_g")
    assert motor.carried_g == pytest.approx(w)
    assert checks.item_mass_g(motor) == pytest.approx(catalog.num(catalog.get("drone.motors.2806_5_1300kv_7in"), "weight_g") + w)
    P.carry_props(proj)                                   # rebuilding does not add it twice
    assert motor.carried_g == pytest.approx(w)
