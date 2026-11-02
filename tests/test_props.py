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


def test_thrust_comes_from_the_fitted_prop():
    """A motor's thrust depends on its prop: thrust_by_prop[prop of the disc it owns]; an untested prop is an error."""
    from kerf import requirements as R
    motor = S(spec={"catalog": "drone.motors.2806_5_1300kv_7in"}, role="purchased")
    e = catalog.get("drone.motors.2806_5_1300kv_7in")
    for prop, want in (("drone.props.7in", 2058), ("drone.props.hq_7x4x3", 2319)):
        proj = S(items={"m": motor, "p": S(role="keepout", spec={"proxy": "prop_disc", "catalog": prop, "owner": "m"})})
        assert R._motor_thrust_g(proj, "m", e, []) == want
    proj = S(items={"m": motor, "p": S(role="keepout", spec={"proxy": "prop_disc", "catalog": "drone.props.5_1in", "owner": "m"})})
    with pytest.raises(ValueError, match="thrust_by_prop"):
        R._motor_thrust_g(proj, "m", e, [])


def test_prop_ground_clearance(monkeypatch):
    from build123d import Box, Cylinder, Pos, Rot
    from kerf import requirements as R
    monkeypatch.setattr(R.A, "solve", lambda asm, pose=None: None)
    body = S(role="purchased", shape=Pos(0, 0, 0) * Box(100, 40, 40), spec={})        # belly at z -20
    disc = lambda zc: S(role="keepout", spec={"proxy": "prop_disc"}, shape=Pos(60, 0, zc) * Rot(0, 90, 0) * Cylinder(50, 8))
    r = R.prop_ground(S(items={"b": body, "p": disc(0)}), None, min_mm=5)
    assert not r["ok"] and r["value"] == pytest.approx(-30, abs=0.01)                 # tip at -50, belly at -20
    r = R.prop_ground(S(items={"b": body, "p": disc(40)}), None, min_mm=5)
    assert r["ok"] and r["value"] == pytest.approx(10, abs=0.01)
