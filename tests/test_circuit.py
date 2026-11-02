"""kerf/circuit.py: project.yaml wiring -> pin-level KiCad netlist -> SKiDL ERC (+ KiCad / vendor 3D models in proxies)."""
import copy
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from kerf import catalog, circuit, geom, project as P, proxies
from kerf.ctx import Ctx

needs_kicad = pytest.mark.skipif(circuit.symbol_dir() is None, reason="KiCad symbol libraries not installed (./setup.sh)")


def _proj(name, edit=None):
    proj = P.load(name)
    proj.data = copy.deepcopy(proj.data)
    if edit:
        edit(proj.data)
    return proj


def _run(data, rid):
    return next(w for w in data["wiring"] if w.get("id") == rid)


# --- the pin tables --------------------------------------------------------------------------------------------------
@needs_kicad
def test_every_pin_table_is_sourced_and_its_ports_name_real_pins():
    for key, e in circuit.load_pins().items():
        assert e.get("source"), key
        if e.get("symbol"):
            lib, _, nm = e["symbol"].partition(":")
            pins = circuit.symbol_pins(circuit.kicad_symbol(lib, nm))
            assert set(e.get("types") or {}) <= {p[1] for p in pins}, key
            assert not e.get("types") or e.get("types_why"), f"{key}: type overrides need types_why"
        else:
            pins = [tuple(p) for p in e["pins"]]
            assert len({p[0] for p in pins}) == len(pins), f"{key}: duplicate pin numbers"
        names = {p[1] for p in pins}
        for side in ("in", "out"):
            for port, v in ((e.get("ports") or {}).get(side) or {}).items():
                for lst in (v.values() if isinstance(v, dict) else [v]):
                    assert set(lst) <= names, f"{key} {side}.{port}: {set(lst) - names}"
        assert all(t in circuit.TYPES for t in (e.get("types") or {}).values()), key
        if e.get("optional"):
            assert e["optional"].get("why"), key


def test_table_lookup_takes_the_longest_prefix():
    t = {"servos": {"x": 1}, "servos.MG996R": {"x": 2}}
    assert circuit.table_for("servos.MG996R", t)[0] == "servos.MG996R"
    assert circuit.table_for("servos.DS3218", t)[0] == "servos"
    assert circuit.table_for("servosX.a", t) == (None, None)


@needs_kicad
def test_kicad_symbol_extraction_follows_extends():
    blocks = circuit.kicad_symbol("MCU_Module", "Arduino_Nano_v3.x")
    assert len(blocks) == 2 and '(symbol "Arduino_Nano_v2.x"' in blocks[0]
    pins = {nm: t for _, nm, t in circuit.symbol_pins(blocks)}
    assert pins["+5V"] == "power_out" and pins["VIN"] == "power_in" and pins["A4"] == "bidirectional"


# --- the two showcase projects pass ------------------------------------------------------------------------------------
@needs_kicad
@pytest.mark.parametrize("name,nets", [("robot_arm", 13), ("fpv_5in", 20)])
def test_project_circuit_passes_erc(name, nets):
    r = circuit.check(_proj(name))
    assert r["ran"] and r["problems"] == [], r["problems"]
    assert r["nets"] == nets and r["coverage"]["missing"] == []


@needs_kicad
def test_robot_arm_nets_are_the_real_ones():
    m = circuit.model(_proj("robot_arm"))
    by = {n: set(v) for n, v in m["nets"].items()}
    gnd = next(v for v in by.values() if ("psu", "4") in v)
    assert ("psu", "5") in gnd and ("driver", "1") in gnd and ("nano", "4") in gnd and ("yaw_servo", "3") in gnd  # one ground
    assert {("driver", "11"), ("sh_servo", "1")} in [v for v in by.values()]            # ch1 -> shoulder PWM
    assert ("driver", "6") not in {x for v in by.values() for x in v} and ("driver", "6") in m["nc"]   # V+ unused, flagged


# --- wiring errors the ERC must catch ------------------------------------------------------------------------------------
@needs_kicad
def test_erc_catches_two_outputs_on_one_net():
    """CRSF wired TX to TX (not crossed): the FC's T2 and the receiver's TX both drive one wire."""
    r = circuit.check(_proj("fpv_5in", lambda d: _run(d, "crsf").update(pins={"from": ["T2", "R2"], "to": ["TX", "RX"]})))
    assert r["ran"]
    assert any("output connected to output" in p and "T2" in p and "TX" in p for p in r["problems"]), r["problems"]


@needs_kicad
def test_erc_catches_a_power_input_with_no_source():
    """The yaw bus loses its feed from the supply: the yaw servo's + is a power input on a net nothing drives."""
    r = circuit.check(_proj("robot_arm", lambda d: d.__setitem__("wiring", [w for w in d["wiring"] if w["id"] != "psu_yaw"])))
    assert r["ran"]
    assert any("power input on a net that nothing supplies" in p and "yaw_servo" in p for p in r["problems"]), r["problems"]


@needs_kicad
def test_erc_catches_an_unconnected_pin():
    """The receiver's 5 V feed is left out: its power pin is not wired."""
    r = circuit.check(_proj("fpv_5in", lambda d: d.__setitem__("wiring", [w for w in d["wiring"] if w["id"] != "rx_5v"])))
    assert r["ran"]
    assert any("Unconnected pin" in p and "5V" in p and "receiver" in p for p in r["problems"]), r["problems"]


@needs_kicad
def test_conductor_count_must_match_the_pins():
    r = circuit.check(_proj("fpv_5in", lambda d: _run(d, "crsf").pop("conductors")))
    assert any("crsf' declares 1 conductor(s) but lands on 2 pins" in p for p in r["problems"]), r["problems"]


@needs_kicad
def test_terminal_capacity():
    def add(d):
        w = copy.deepcopy(_run(d, "pwr_sh"))
        d["wiring"].append(w | {"id": "pwr_extra", "to": "yaw_servo"})
    r = circuit.check(_proj("robot_arm", add))
    assert any("bus_arm terminal + takes 5 wire(s) but 6 land on it" in p for p in r["problems"]), r["problems"]


@needs_kicad
def test_unknown_pin_and_port_are_reported():
    r = circuit.check(_proj("robot_arm", lambda d: _run(d, "i2c").update(pins={"from": ["+5V", "GND", "A4", "SDA"], "to": ["VCC", "GND", "SDA", "SCL"]})))
    assert any("nano has no pin 'SDA'" in p for p in r["problems"]), r["problems"]


@needs_kicad
def test_missing_pin_table_skips_erc_with_a_warning():
    tables = {k: v for k, v in circuit.load_pins().items() if k != "electronics.receivers.elrs_nano"}
    m = circuit.model(_proj("fpv_5in"), tables)
    assert m["missing"] == ["receiver (electronics.receivers.elrs_nano)"]


# --- outputs: netlist, KiCad schematic, SVG/PDF ----------------------------------------------------------------------------
def _tiny():
    """A 4-item circuit (battery -> XT60 -> stack -> camera video) for the slow output test."""
    items = {"battery": "drone.batteries.6S_1300", "xt60": "drone.connectors.XT60", "stack": "drone.stacks.fc_30_5",
             "camera": "drone.cameras.micro_19mm"}
    wiring = [{"id": "lead", "from": "battery", "to": "xt60", "v": 25.2},
              {"id": "main", "from": "xt60", "to": "stack", "v": 25.2},
              {"id": "cam_9v", "from": "stack.9v", "to": "camera", "v": 9},
              {"id": "video", "from": "camera", "to": "stack", "kind": "signal", "pins": {"from": ["VIDEO"], "to": ["CAM"]}}]
    return SimpleNamespace(items={k: SimpleNamespace(spec={"catalog": v}) for k, v in items.items()},
                           data={"wiring": wiring}, dir=Path("tiny"), name="tiny")


@needs_kicad
def test_outputs_netlist_schematic_svg_pdf(tmp_path):
    proj = _tiny()
    r = circuit.check(proj)
    assert r["ran"] and r["problems"] == [], r["problems"]
    w = circuit.write(proj, tmp_path, r)
    assert w["errors"] == [], w["errors"]
    net = (tmp_path / "kicad" / "tiny.net").read_text()
    assert re.search(r"\(net\s+\(code", net) and '(ref "battery")' in net and '(ref "camera")' in net
    sch = (tmp_path / "kicad" / "tiny.kicad_sch").read_text()
    assert sch.startswith("(kicad_sch") and "Battery" in sch
    assert (tmp_path / "schematic.svg").read_text().lstrip().startswith("<svg")
    assert (tmp_path / "schematic.pdf").read_bytes()[:5] == b"%PDF-"
    assert "no ERC errors" in (tmp_path / "kicad" / "erc.txt").read_text()


# --- 3D models: KiCad XT60, Adafruit PCA9685 -------------------------------------------------------------------------------
XT60 = {"catalog": "drone.connectors.XT60", "proxy": "step", "base": "box", "model": "kicad/AMASS_XT60-M_1x02_P7.2mm_Vertical.step",
        "model_rot": [0, -90, 0], "model_pos": [5.75, 0, 4.35]}
PCA = {"catalog": "boards.pca9685_adafruit", "proxy": "step", "base": "board", "model": "adafruit_815_pca9685.step",
       "model_pos": [-29.21, -6.223, 0], "groups": {"holes": "driver"}}


def _build(spec):
    return proxies.build(Ctx("x", {}, {"spec": spec}), spec)


def test_kicad_xt60_model_matches_the_catalog():
    s = _build(XT60)
    bb = s.bounding_box()
    assert (bb.size.X, bb.size.Y) == pytest.approx((20.5, 8.1), abs=0.01)
    assert catalog.get("drone.connectors.XT60")["length"] == 20.5
    assert len(s.solids()) == 3                    # KiCad's model untouched: body + 2 contacts
    v, f = geom.mesh(s)                            # one contact cone face OCC cannot triangulate: the rest still meshes
    assert len(f) > 500 and v[:, 0].min() == pytest.approx(-10.25, abs=0.05)
    with pytest.raises(ValueError, match="X m"):   # 1 mm along the connector: refused (and the old 21.3 mm length was too)
        _build(XT60 | {"model_pos": [6.75, 0, 4.35]})


def test_adafruit_pca9685_model_matches_catalog_holes_and_underside():
    s = _build(PCA)
    bb = s.bounding_box()
    assert bb.min.Z == pytest.approx(-2.01, abs=0.01)      # solder tails under the board are real now
    assert len(s.kerf_sites) == 4
    ref = proxies.build(Ctx("y", {}, {}), {"catalog": "boards.pca9685_adafruit", "proxy": "board"})
    assert ref.bounding_box().min.Z == pytest.approx(-2.0, abs=0.02)   # the plain proxy carries the underside too


def test_model_sources_are_recorded():
    import hashlib
    root = Path(__file__).resolve().parent.parent / "catalog" / "models"
    for f, src in ((root / "kicad" / "AMASS_XT60-M_1x02_P7.2mm_Vertical.step", root / "kicad" / "SOURCES.md"),
                   (root / "adafruit_815_pca9685.step", root / "SOURCES.md")):
        assert hashlib.sha256(f.read_bytes()).hexdigest() in src.read_text(), f.name
