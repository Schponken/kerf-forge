"""The catalog is the source of truth for every mating dimension. These tests check that it is complete, sourced and
self-consistent, and that every purchased-part proxy built from it has the catalog's own outside dimensions."""
import pytest

from kerf import catalog, iface
from kerf.ctx import Ctx
from kerf import proxies

CAT = catalog.load()


def entries(cat):
    return [(cat_name, k) for cat_name, v in CAT.items() if isinstance(v, dict) and cat_name == cat
            for k in v if not k.startswith("_")]


def test_every_entry_is_sourced():
    missing = catalog.unsourced()
    assert not missing, f"entries without a source: {missing[:10]}"


@pytest.mark.parametrize("size", ["M2", "M2.5", "M3", "M4", "M5"])
def test_screw_specs_consistent(size):
    sp = iface.screw_spec(size)
    d = sp["d"]
    assert d < sp["clearance"] < d + 1.0
    assert 0.6 * d < sp["tap"] < d
    assert sp["head_d"] > sp["clearance"] and sp["nut_af"] > d
    if sp.get("insert_hole"):
        assert d < sp["insert_hole"] < 2.0 * d + 0.5
        assert sp["insert_len"] >= d


@pytest.mark.parametrize("key", [k for _, k in entries("servos")])
def test_servo_proxy_matches_catalog(key):
    d = iface.servo_dims(f"servos.{key}")
    assert d["span"] > d["L"] > d["W"] > 0
    assert d["hx"] < d["span"] and d["hx"] > d["L"]          # holes are on the tabs, outside the body
    assert 0 < d["tab_z"] < d["H"]
    assert 0 < d["out_x"] < d["L"] / 2
    s = proxies.build(Ctx(key, {}), {"catalog": f"servos.{key}", "proxy": "servo"})
    bb = s.bounding_box()
    e = catalog.get(f"servos.{key}")
    boss = catalog.num(e, "cable_boss_protrusion", default=0.0)
    reach_out = max(d["span"] / 2, d["L"] / 2 + boss)     # the cable boss can stick out past the tabs on one end
    assert bb.size.X == pytest.approx(d["span"] / 2 + reach_out, abs=0.01)
    assert bb.size.Z == pytest.approx(d["H"] + d["shaft_h"], abs=0.01)


@pytest.mark.parametrize("key", [k for _, k in entries("servo_horns")])
def test_horn_proxy(key):
    h = iface.horn_dims(f"servo_horns.{key}")
    assert h["bc"] < h["od"] and h["n"] >= 2
    s = proxies.build(Ctx(key, {}), {"catalog": f"servo_horns.{key}", "proxy": "horn"})
    assert s.bounding_box().size.X == pytest.approx(h["od"], abs=0.01)


@pytest.mark.parametrize("key", [k for _, k in entries("bearings")])
def test_bearing_proxy(key):
    b = iface.bearing_dims(f"bearings.{key}")
    assert b["D"] > b["d"] > 0 and b["B"] > 0
    s = proxies.build(Ctx(key, {}), {"catalog": f"bearings.{key}", "proxy": "bearing"})
    bb = s.bounding_box()
    assert bb.size.X == pytest.approx(b["D"], abs=0.01) and bb.size.Z == pytest.approx(b["B"], abs=0.01)


@pytest.mark.parametrize("key", [k for _, k in entries("steppers")])
def test_stepper_proxy(key):
    s = proxies.build(Ctx(key, {}), {"catalog": f"steppers.{key}", "proxy": "stepper"})
    e = catalog.get(f"steppers.{key}")
    assert s.bounding_box().size.X == pytest.approx(catalog.num(e, "face"), abs=0.01)


@pytest.mark.parametrize("key", [k for _, k in entries("rods")])
def test_rod_proxy(key):
    s = proxies.build(Ctx(key, {}), {"catalog": f"rods.{key}", "proxy": "rod", "length": 100})
    e = catalog.get(f"rods.{key}")
    assert s.bounding_box().size.X == pytest.approx(catalog.num(e, "od"), abs=0.01)


@pytest.mark.parametrize("key", [k for _, k in entries("boards")])
def test_board_proxy(key):
    e = catalog.get(f"boards.{key}")
    s = proxies.build(Ctx(key, {}), {"catalog": f"boards.{key}", "proxy": "board", "groups": {"holes": "g"}})
    # envelope = PCB length plus any catalogued connector overhang on the +X edge
    assert s.bounding_box().size.X == pytest.approx(catalog.num(e, "length") + catalog.num(e, "usb_overhang", default=0), abs=0.01)
    for (x, y) in e.get("holes") or []:
        assert abs(x) < catalog.num(e, "length") / 2 and abs(y) < catalog.num(e, "width") / 2


@pytest.mark.parametrize("key", list((CAT.get("drone", {}).get("motors") or {}).keys()))
def test_motor_proxy(key):
    s = proxies.build(Ctx(key, {}), {"catalog": f"drone.motors.{key}", "proxy": "motor", "groups": {"mount": "m"}})
    e = catalog.get(f"drone.motors.{key}")
    assert s.bounding_box().size.X == pytest.approx(catalog.num(e, "bell_d"), abs=0.01)
    assert len(s.kerf_sites) == 4


@pytest.mark.parametrize("key", list((CAT.get("drone", {}).get("props") or {}).keys()))
def test_prop_disc(key):
    s = proxies.build(Ctx(key, {}), {"catalog": f"drone.props.{key}", "proxy": "prop_disc"})
    e = catalog.get(f"drone.props.{key}")
    assert s.bounding_box().size.X == pytest.approx(catalog.num(e, "diameter_mm"), abs=0.01)


@pytest.mark.parametrize("key", list((CAT.get("materials") or {}).keys()))
def test_materials_have_mechanics(key):
    m = catalog.get(f"materials.{key}")
    assert 0.9 < catalog.num(m, "density") < 1.6
    assert catalog.num(m, "tensile_strength_xy_mpa") > 5
    assert catalog.num(m, "youngs_modulus_mpa") > 5   # TPU 95A is genuinely ~10 MPa


@pytest.mark.parametrize("key", list((CAT.get("drone", {}).get("stacks") or {}).keys()))
def test_stack_proxy(key):
    s = proxies.build(Ctx(key, {}), {"catalog": f"drone.stacks.{key}", "proxy": "stack", "groups": {"holes": "h"}})
    assert len(s.kerf_sites) == 4


@pytest.mark.parametrize("key", list((CAT.get("drone", {}).get("batteries") or {}).keys()))
def test_battery_box(key):
    s = proxies.build(Ctx(key, {}), {"catalog": f"drone.batteries.{key}", "proxy": "box"})
    e = catalog.get(f"drone.batteries.{key}")
    assert s.bounding_box().size.X == pytest.approx(catalog.num(e, "length"), abs=0.01)
