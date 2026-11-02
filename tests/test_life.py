"""Design for life (kerf/req_life.py): snap / hinge strain, creep under a lasting load, screws that vibrate loose."""
import math
from types import SimpleNamespace as NS

import pytest

from kerf import req_life as L
from kerf.requirements import REGISTRY


def _p(mat="PETG", data=None, items=None):
    its = {"hook": NS(role="printed", spec={"material": mat}, shape=None), **(items or {})}
    return NS(items=its, params={"t": 2.0}, data=data or {})


def test_snap_and_hinge_strain_against_the_permissible_strain():
    # PETG (catalog): 48 MPa / 1460 MPa = 3.29 % linear yield strain -> 70 % = 2.30 % permissible for one snap
    a, how = L.allowable_strain_pct("PETG")
    assert a == pytest.approx(0.7 * 48 / 1460 * 100, rel=1e-6) and "yield" in how
    r = REGISTRY["flex_strain"](_p(), None, part="hook", kind="snap", t_mm="t", L_mm=20, deflection_mm=1.0)
    assert r["value"] == pytest.approx(1.5 * 2 * 1.0 / 400 * 100, abs=0.01) and r["ok"]          # 0.75 %
    r = REGISTRY["flex_strain"](_p(), None, part="hook", kind="snap", t_mm=2, L_mm=8, deflection_mm=1.5)
    assert not r["ok"]                                                                             # 7.0 %
    across = REGISTRY["flex_strain"](_p(), None, part="hook", kind="snap", t_mm=2, L_mm=20, deflection_mm=1.0, across_layers=True)
    assert across["limit"] == pytest.approx(a / 2, abs=0.01)
    # reinforced: 50 % of the 10.4 % strain at break (CF-PETG X-Y)
    assert L.allowable_strain_pct("CF-PETG")[0] == pytest.approx(5.2)
    h = REGISTRY["flex_strain"](_p(), None, part="hook", kind="hinge", t_mm=0.5, L_mm=3, angle_deg=90)
    assert h["value"] == pytest.approx(0.5 * math.pi / 2 / 6 * 100, abs=0.01) and not h["ok"]     # 13 %: PETG is no hinge
    rep = REGISTRY["flex_strain"](_p(), None, part="hook", kind="snap", t_mm=2, L_mm=20, deflection_mm=1.0, cycles=1000)
    assert not rep["ok"] and "no fatigue strain" in rep["detail"]                                 # never guessed


def test_creep_uses_the_documented_rupture_stress(monkeypatch):
    from kerf import failure
    monkeypatch.setattr(failure, "_row", lambda proj, asm, rid: ({"part": "hook"}, {"value": 4.0}, 0.0, 1.0))
    r = REGISTRY["creep_limit"](_p("PLA"), None, case="shelf")
    assert r["ok"] and r["limit"] == pytest.approx(5.0)            # PLA ruptured at 15 MPa within ~1.2 h: / SF 3
    r = REGISTRY["creep_limit"](_p("PETG"), None, case="shelf")
    assert not r["ok"] and "no creep-rupture data" in r["detail"]


def test_screw_locking_only_where_it_vibrates(monkeypatch):
    from kerf import assembly as A
    fast = [{"group": "motor_1", "receiver": "threaded"}, {"group": "arm_1", "receiver": "nut_trap"},
            {"group": "vtx", "receiver": "tap"}]
    monkeypatch.setattr(A, "fasteners", lambda asm: (fast, []))
    quiet = REGISTRY["screw_locking"](_p(), None)
    assert quiet["ok"] and "nothing" in quiet["detail"]
    drone = _p(items={"m": NS(role="purchased", spec={"catalog": "drone.motors.2207_1855kv_6s"}, shape=None)})
    r = REGISTRY["screw_locking"](drone, None, locking={"motor_1": "threadlocker"})
    assert not r["ok"] and "arm_1" in r["detail"] and "vtx" not in r["detail"]       # screws into plastic hold
    assert REGISTRY["screw_locking"](drone, None, locking={"motor_1": "threadlocker", "arm_1": "nyloc"})["ok"]
    assert not REGISTRY["screw_locking"](drone, None, locking={"motor_1": "glue", "arm_1": "nyloc"})["ok"]
