"""Electrical system: power tree currents, ratings, hover time and connector access against hand calculations."""
import math

import pytest

from kerf import assembly as A, electrical as E, project as P, requirements, wiring_out as WO
from test_engine import _write_project

# A 3" quad reduced to its electrical parts. Masses are fixed with mass_g so the hover numbers are hand-checkable:
# 164 + 5 + 16.8 + 4 x 9.1 + 2.2 = 224.4 g of parts, plus the declared wiring (catalog wire.silicone g/m x cut length
# x conductors): lead + main 2 x (2 x 0.2 m x 28 g/m) = 22.4, phases 4 x 2 x 0.2 x 8 = 12.8, rx5v 2 x 0.1 x 4 = 0.8
# (28 AWG uses the 24 AWG figure), crsf 0.1 x 4 = 0.4 -> 36.4 g; all-up 260.8 g.
YAML = """
name: Elec test
params: {{}}
parts: {{}}
purchased:
  battery: {{catalog: drone.batteries.4S_1500, proxy: box, mass_g: 164,
            joints: {{m1: [60, 60, 40], m2: [-60, 60, 40], m3: [-60, -60, 40], m4: [60, -60, 40], xt: [{xt_x}, 0, 0],
                      st: [0, 0, 60], rxj: [0, 30, 60]}}}}
  xt60: {{catalog: drone.connectors.XT60, proxy: box, mass_g: 5}}
  stack: {{catalog: drone.stacks.fc_20, proxy: box, size: [30, 30, 10], mass_g: 16.8}}
  rx: {{catalog: electronics.receivers.elrs_nano, proxy: box, mass_g: 2.2}}
  m1: {{catalog: drone.motors.1404_3800kv_3in, proxy: box, size: [20, 20, 15], mass_g: 9.1}}
  m2: {{catalog: drone.motors.1404_3800kv_3in, proxy: box, size: [20, 20, 15], mass_g: 9.1}}
  m3: {{catalog: drone.motors.1404_3800kv_3in, proxy: box, size: [20, 20, 15], mass_g: 9.1}}
  m4: {{catalog: drone.motors.1404_3800kv_3in, proxy: box, size: [20, 20, 15], mass_g: 9.1}}
keepouts:
  p1: {{catalog: drone.props.3in, proxy: prop_disc, h: 5}}
  p2: {{catalog: drone.props.3in, proxy: prop_disc, h: 5}}
  p3: {{catalog: drone.props.3in, proxy: prop_disc, h: 5}}
  p4: {{catalog: drone.props.3in, proxy: prop_disc, h: 5}}
assembly:
  root: battery
  joints:
    - {{parent: battery.m1, child: m1.bottom}}
    - {{parent: battery.m2, child: m2.bottom}}
    - {{parent: battery.m3, child: m3.bottom}}
    - {{parent: battery.m4, child: m4.bottom}}
    - {{parent: m1.top, child: p1.hub}}
    - {{parent: m2.top, child: p2.hub}}
    - {{parent: m3.top, child: p3.hub}}
    - {{parent: m4.top, child: p4.hub}}
    - {{parent: battery.xt, child: xt60.bottom}}
    - {{parent: battery.st, child: stack.bottom}}
    - {{parent: battery.rxj, child: rx.bottom}}
electrical:
  battery: battery
{extra}
wiring:
  - {{id: lead, from: battery, to: xt60, v: 16.8, gauge: 14, color: red/black, length_mm: {lead_len}}}
  - {{id: main, from: xt60, to: stack, v: 16.8, gauge: 14, color: red/black, length_mm: 200}}
  - {{id: ph1, from: stack.esc, to: m1, v: 16.8, gauge: 20, length_mm: 200}}
  - {{id: ph2, from: stack.esc, to: m2, v: 16.8, gauge: 20, length_mm: 200}}
  - {{id: ph3, from: stack.esc, to: m3, v: 16.8, gauge: 20, length_mm: 200}}
  - {{id: ph4, from: stack.esc, to: m4, v: 16.8, gauge: 20, length_mm: 200}}
  - {{id: rx5v, from: stack.5v, to: rx, v: 5.0, gauge: 28, length_mm: 100}}
  - {{id: crsf, from: stack, to: rx, kind: signal, gauge: 28, length_mm: 100}}
requirements:
  - {{id: power, check: power_budget}}
  - {{id: flight_time, check: flight_time, min_min: 3}}
  - {{id: plug, check: connector_access, item: xt60, direction: [1, 0, 0], length_mm: 30}}
"""


def _proj(tmp_path, extra="", lead_len=200, xt_x=0):
    d = _write_project(tmp_path / "elec", YAML.format(extra=extra, lead_len=lead_len, xt_x=xt_x), {})
    proj = P.build(P.load(str(d)))
    for i, it in proj.items.items():
        assert it.error is None, (i, it.error)
    asm = A.plan(proj)
    A.solve(asm)
    return proj, asm


def test_hover_power_by_hand():
    # 1 kg on 4 x 10 in (254 mm) props: T = 2.4517 N per rotor, A = pi 0.127^2 = 0.050671 m2,
    # P_ideal = T^1.5 / sqrt(2 rho A) = 3.8389 / 0.35233 = 10.896 W per rotor; x4 / (0.5 x 0.75) = 116.2 W
    assert E.hover_power_w(1000, 254, [1, 1, 1, 1]) == pytest.approx(116.2, abs=0.1)
    # the same thrust on one coaxial pair of the same props: 2 rotors at 4.9033 N, x 1.281
    t = 1 * 9.80665 / 2
    p = 1.281 * 2 * t ** 1.5 / math.sqrt(2 * 1.225 * math.pi * 0.127 ** 2) / 0.375
    assert E.hover_power_w(1000, 254, [2]) == pytest.approx(p, rel=1e-9)
    # T^1.5 = 10.858 -> 30.817 W per rotor, x 2 x 1.281 / 0.375 = 210.5 W (81 % more than the quad: half the disc area)
    assert E.hover_power_w(1000, 254, [2]) == pytest.approx(210.5, abs=0.1)


def test_burst_rise_by_hand():
    # 14 AWG (1.62814 mm): A = 2.0819 mm2; 63.7 A -> J = 3.0597e7 A/m2; rho(100 C) = 1.72e-8 x 1.3144 = 2.2608e-8;
    # dT/dt = J^2 rho / (8920 x 385) = 6.163 K/s -> 30.8 K in 5 s
    assert E.burst_rise_k(63.7, 14, 5) == pytest.approx(30.8, abs=0.1)


def test_quad_currents_and_flight_time(tmp_path):
    proj, asm = _proj(tmp_path)
    m = E.analyse(proj)
    # hover: 260.8 g on 4 x 76.49 mm props: T = 0.6394 N/rotor, T^1.5 / sqrt(2 rho A) = 0.51127 / 0.10611 = 4.818 W,
    # x 4 / 0.375 = 51.4 W electrical (see test_hover_power_by_hand for the method)
    assert m["hover"]["mass_g"] == pytest.approx(260.8, abs=0.01)
    assert m["hover"]["power_w"] == pytest.approx(51.4, abs=0.1)
    # battery avg = 51.40 W / 14.8 V (4S nominal) + FC 0.3 A + RX 0.1 A x 5 V / (16.8 V x 0.8) = 3.473 + 0.3 + 0.0372
    assert m["avg_a"] == pytest.approx(3.810, abs=0.003)
    # peak = 4 x 15.84 (catalog max) + 0.3 + 0.0372 = 63.70 A
    assert m["peak_a"] == pytest.approx(63.70, abs=0.01)
    # 1.5 Ah x 0.8 / 3.810 A = 18.9 min
    assert m["minutes"] == pytest.approx(18.9, abs=0.05)
    rows = {(r["what"], r["kind"]): r for r in m["ratings"]}
    # the XT60's 60 A burst rating (1 minute, Holybro) is exceeded by the 63.7 A punch-out; the 30 A continuous one is not
    assert not rows[("connector xt60", "peak A vs peak rating")]["ok"]
    assert rows[("connector xt60", "avg A vs rated")]["ok"]
    assert rows[("stack.5v", "avg A vs rated")]["limit"] == 2.0          # SpeedyBee 5 V pad budget
    assert rows[("stack.esc -> m1", "peak A vs burst rating")]["limit"] == 45  # per-channel ESC burst
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert not r["power"]["ok"] and "connector xt60" in r["power"]["detail"]
    assert r["flight_time"]["ok"] and r["flight_time"]["value"] == pytest.approx(18.9, abs=0.05)


def test_current_limit_and_overrides_need_a_why(tmp_path):
    proj, asm = _proj(tmp_path, extra="  limits: {stack: {peak_a: 55, why: 'ESC current limit set to 55 A'}}")
    m = E.analyse(proj)
    assert m["peak_a"] == pytest.approx(55, abs=1e-6)
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert r["power"]["ok"], r["power"]["detail"]
    # the cap is an instruction to the builder: WIRING.md and the assembly steps say to set it (review: a cap that
    # only lives in project.yaml lets someone fly uncapped)
    md = WO.wiring_md(proj, m)
    assert "## Configure before the first power-up" in md and "ESC current limit set to 55 A" in md
    assert any("Configure before the first power-up" in x and "55 A" in x for x in WO.steps(m))
    # a cap on one motor shows in the Loads table as that motor's peak (catalog 15.84 A -> 10 A)
    proj, asm = _proj(tmp_path, extra="  limits: {m1: {peak_a: 10, why: 'output limit'}}")
    m = E.analyse(proj)
    assert m["loads"]["m1"]["peak_a"] == 10 and "capped: output limit" in m["loads"]["m1"]["source"]
    assert m["peak_a"] == pytest.approx(63.70 - 5.84, abs=0.01)
    proj, asm = _proj(tmp_path, extra="  limits: {stack: {peak_a: 55}}")
    with pytest.raises(E.ElectricalError, match="why"):
        E.analyse(proj)


def test_routed_length_needs_slack(tmp_path):
    # the XT60 sits on the battery's bottom centre: both box centres are 15.5 - 8.0 mm apart in z (battery 28 mm
    # tall, centre 14; XT60 16 mm tall, centre 8) -> routed 6.0 mm, cut length >= 6.9 mm
    proj, asm = _proj(tmp_path, lead_len=6.5)
    m = E.analyse(proj)
    w = next(w for w in m["wires"] if w["id"] == "lead")
    assert w["routed_mm"] == pytest.approx(6.0, abs=0.01)
    assert E.length_problems(m) and "lead" in E.length_problems(m)[0]
    proj, asm = _proj(tmp_path, lead_len=7)
    assert not [p for p in E.length_problems(E.analyse(proj)) if "'lead'" in p]


def test_connector_access(tmp_path):
    # XT60 21.3 mm long on the battery's bottom centre: its +X face is inside the battery footprint (80 mm long)
    # -> a plug along +X runs into the battery. Moved to x = 60 its face is at 70.65, past the battery end at 40.
    proj, asm = _proj(tmp_path)
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert not r["plug"]["ok"] and "battery" in str(r["plug"]["value"])
    proj, asm = _proj(tmp_path, xt_x=60)
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert r["plug"]["ok"], r["plug"]


def test_input_voltage_range(tmp_path):
    # the receiver takes 5.0 V only (catalog voltage_min = voltage_max = 5); feeding it from the 9 V pad fails
    proj, asm = _proj(tmp_path)
    proj.data["wiring"][6] = {**proj.data["wiring"][6], "v": 9.0}
    rows = [r for r in E.analyse(proj)["ratings"] if r["kind"] == "voltage"]
    assert rows and not rows[0]["ok"] and rows[0]["what"] == "rx input"


def test_outputs_written(tmp_path):
    from kerf import pipeline
    _proj(tmp_path)
    rep = pipeline.run(str(tmp_path / "elec"), sweeps=False, do_export=True)
    out = tmp_path / "elec" / "out"
    for f in ("WIRING.md", "wiring.svg", "ASSEMBLY.md", "bom.csv"):
        assert (out / f).exists(), f
    assert "## Electrical" in (out / "ASSEMBLY.md").read_text() and "Step 1" in (out / "ASSEMBLY.md").read_text()
    assert "hover time" in (out / "WIRING.md").read_text() and "<svg" in (out / "wiring.svg").read_text()
    wires = [r for r in rep["bom"] if r["type"] == "wire"]
    # power runs are pairs: lead 2 x 200 + main 2 x 200 = 800 mm of AWG 14 red/black -> 0.8 m
    assert any(r["item"].startswith("AWG 14") and r["qty"] == 0.8 for r in wires)
    assert not [p for p in rep["problems"] if "ship" in p or "electrical" in p]
    assert any("heat-shrink" in r["item"] for r in wires)
    assert all(r["link"] for r in rep["bom"] if r["type"] == "purchased")
    assert rep["electrical"]["minutes"] > 15


def test_wire_rows_carry_price_keys():
    rows = WO.bom_rows({"wires": [{"kind": "power", "gauge": 14, "length_mm": 120, "color": None},
                                  {"kind": "power", "gauge": 20, "length_mm": 100, "conductors": 3},
                                  {"kind": "signal", "gauge": 28, "length_mm": 55}]})
    wire = {r["item"]: r for r in rows if "metres" in r["item"]}
    # 2 x 120 = 240 mm -> 0.3 m; 3 x 100 = 300 mm -> 0.3 m; 55 mm -> 0.1 m
    assert [w["qty"] for w in wire.values()] == [0.3, 0.3, 0.1]
    assert {w["price_key"] for w in wire.values()} == {"wire:AWG14", "wire:AWG20", "wire:AWG28"}
    shrink = [r for r in rows if "heat-shrink" in r["item"]]
    assert sum(r["qty"] for r in shrink) == 2 * 2 + 2 * 3 + 2 * 1     # one piece per conductor end


SERVO_YAML = """
name: Servo psu test
params: {{}}
parts: {{}}
purchased:
  psu: {{catalog: electronics.supplies.meanwell_gst60a05, proxy: box, joints: {{{joints}}}}}
{servos}
assembly:
  root: psu
  joints:
{tree}
electrical:
  supply: psu
wiring:
{wires}
requirements:
  - {{id: power, check: power_budget}}
  - {{id: rt, check: run_time, min_min: 10}}
"""


def _servos(tmp_path, n):
    servos = "\n".join(f"  s{k}: {{catalog: servos.MG996R, proxy: box, size: [40, 20, 37]}}" for k in range(n))
    joints = ", ".join(f"j{k}: [{k * 50}, 0, 40]" for k in range(n))
    tree = "\n".join(f"    - {{parent: psu.j{k}, child: s{k}.bottom}}" for k in range(n))
    wires = "\n".join(f"  - {{id: w{k}, from: psu, to: s{k}, v: 5.0, gauge: 20, length_mm: 400}}" for k in range(n))
    d = _write_project(tmp_path / f"psu{n}", SERVO_YAML.format(servos=servos, joints=joints, tree=tree, wires=wires), {})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    return proj, asm


def test_mains_supply_servos(tmp_path):
    # MG996R datasheet: 0.9 A running, 2.5 A stall (6 V). Two servos on the 5 V 6 A adapter: 1.8 A avg, 5.0 A peak -> ok
    proj, asm = _servos(tmp_path, 2)
    m = E.analyse(proj)
    assert m["mains"] and m["avg_a"] == pytest.approx(1.8) and m["peak_a"] == pytest.approx(5.0)
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert r["power"]["ok"], r["power"]["detail"]
    assert not r["rt"]["ok"] and "mains" in r["rt"]["detail"]          # no capacity -> no run time claim
    # three servos can stall together: 7.5 A > 6 A rated
    proj, asm = _servos(tmp_path, 3)
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert not r["power"]["ok"] and "supply psu peak" in r["power"]["detail"]


def test_supplied_lead_is_not_bought_or_cut():
    """A run that comes with an item (an adapter's DC cord, a pack's own lead) is checked like any wire but adds no
    wire or heat-shrink to the BOM and its step says to plug it in, not to cut and solder."""
    wires = [{"id": "cord", "from": "psu", "to": "jack", "kind": "power", "gauge": 24, "length_mm": 1000, "color": None,
              "supplied": "psu", "points": []},
             {"id": "pwr", "from": "jack", "to": "servo", "kind": "power", "gauge": 22, "length_mm": 250, "color": "red/black",
              "points": []}]
    rows = WO.bom_rows({"wires": wires})
    assert [r["item"] for r in rows if "metres" in r["item"]] == ["AWG 22 silicone stranded wire (red/black), metres"]
    assert sum(r["qty"] for r in rows if "heat-shrink" in r["item"]) == 4
    st = WO.steps({"wires": wires, "mains": True})
    assert st[0].startswith("**cord** is the lead that comes with psu") and "Cut 2 x 250 mm" in st[1]
    assert "adapter" in st[-1]


ROUTE_BASE = """
from build123d import *
def build(ctx):
    s = Box(20, 20, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.revolute("pivot", Axis((0, 0, 10), (0, 1, 0)), range=(-90, 90))
    ctx.rigid("blk", Location((0, 40, 0)))
    return ctx.finish(s)
"""
ROUTE_YAML = """
name: Route test
params: {L: 60}
parts:
  base: {file: parts/base.py, material: PETG}
  arm: {file: parts/arm.py, material: PETG}
purchased:
  blk: {proxy: box, size: [10, 10, 10], mass_g: 1}
assembly:
  root: base
  joints:
    - {parent: base.pivot, child: arm.hub, name: swing, range: [-90, 90]}
    - {parent: base.blk, child: blk.bottom}
wiring:
  - {id: hinge, from: base, to: arm, kind: signal, gauge: 24, length_mm: 100, route: [{item: arm, at: [60, 0, 10]}]}
  - {id: thru, from: base, to: arm, kind: signal, gauge: 24, length_mm: 500, route: [[0, 40, 5]]}
"""


def test_route_check_slack_and_collisions(tmp_path):
    from test_engine import HINGE_ARM
    d = _write_project(tmp_path / "route", ROUTE_YAML, {"base": ROUTE_BASE, "arm": HINGE_ARM})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    model = {"wires": [{"id": "hinge", "length_mm": 100}, {"id": "thru", "length_mm": 500}]}
    res, problems = E.route_check(proj, asm, model)
    r = {x["id"]: x for x in res}
    # The revolute frame stands the arm up at home (arm local x -> world +z, local z -> world +y, pivot (0,0,10)):
    # base centre (0,0,5) -> tie point (local 60,0,10) = (0,12,70) -> arm bbox centre (local 30,0,2) = (0,2,40):
    # sqrt(12^2 + 65^2) + sqrt(10^2 + 30^2) = 66.10 + 31.62 = 97.72 mm. Swung 90 deg the tie point is at (+-60,12,10):
    # 61.39 + 31.62 = 93.0 mm. Worst = home, 97.7 -> cut >= 112.4 mm, so the 100 mm run is short.
    assert r["hinge"]["max_routed_mm"] == pytest.approx(97.7, abs=0.05) and r["hinge"]["worst_pose"] == "home"
    assert any("'hinge'" in p and "112.4" in p for p in problems)
    # the second run goes straight through the purchased block; the first never touches it
    assert any("'thru' runs through blk" in p for p in problems)
    assert not any("'hinge' runs through" in p for p in problems)


def test_supplied_lead_is_not_bought_or_weighed():
    w = {"id": "lead", "from": "battery", "to": "xt60", "kind": "power", "gauge": 12, "length_mm": 100,
         "supplied": True, "points": [[0, 0, 0], [0, 0, 1]]}
    assert WO.bom_rows({"wires": [w]}) == []
    assert "nothing to cut" in WO.steps({"wires": [w]})[0]

    class _P:
        data = {"wiring": [w, {**w, "supplied": False}]}
    assert E.wiring_mass_g(_P()) == pytest.approx(2 * 0.1 * 43)     # only the second: 2 x 0.1 m x 43 g/m (AWG 12)


def test_voltage_drop_by_hand(tmp_path):
    """One MG996R on 400 mm of AWG 20 from the 5 V adapter. Hand calc: AWG 20 d 0.8128 mm -> A = 5.1887e-7 m2;
    copper 1.72e-8 ohm m at 20 C, alpha 0.00393. Loop (2 x 0.4 m) at 40 C: 0.8 x 1.8552e-8 / 5.1887e-7 = 0.02860 ohm
    -> 0.9 A running drops 0.02574 V (servo sees 4.974 V); at 100 C (2.2608e-8): 0.03486 ohm x 2.5 A stall = 0.0871 V."""
    assert E.loop_ohm(20, 400) == pytest.approx(0.02860, rel=2e-3)
    proj, asm = _servos(tmp_path, 1)
    rows = {r["kind"]: r for r in E.analyse(proj)["ratings"] if r["kind"].startswith("voltage after")}
    avg = rows["voltage after IR drop (avg, 1 run(s))"]
    peak = rows["voltage after IR drop (peak, 1 run(s))"]
    assert avg["value"] == pytest.approx(5 - 0.02574, abs=1e-3) and avg["ok"] and avg["limit"] == 4.8
    assert peak["value"] == pytest.approx(5 - 0.0871, abs=1e-3) and peak["soft"]


def test_voltage_drop_sag_is_reported_not_failed(tmp_path):
    """Thin, long wire: the average drop below the servo's 4.8 V fails power_budget; a sag only at peak is reported."""
    proj, asm = _servos(tmp_path, 1)
    proj.data["wiring"][0].update(gauge=26, length_mm=1500)
    # AWG 26: A = 1.2810e-7; 3 m loop. 40 C: 0.4345 ohm x 0.9 A = 0.391 V -> 4.609 V < 4.8 -> fail
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert not r["power"]["ok"] and "voltage after IR drop (avg" in r["power"]["detail"]
    proj.data["wiring"][0].update(gauge=22, length_mm=1500)
    # AWG 22, 3 m loop: 40 C 0.1703 ohm x 0.9 = 0.153 V (ok); 100 C 0.2075 ohm x 2.5 A = 0.519 V -> 4.48 V sag
    r = {x["id"]: x for x in requirements.run_all(proj, asm)}
    assert r["power"]["ok"] and "brief sag at peak" in r["power"]["detail"]


def test_steps_pick_the_verb_per_end():
    wires = [{"id": "p", "from": "jack", "to": "servo", "kind": "power", "gauge": 22, "length_mm": 250, "color": "red/black",
              "points": [], "terms": {"from": "screw", "to": "header"}},
             {"id": "g", "from": "nano", "to": "jack", "kind": "signal", "gauge": 26, "length_mm": 110, "color": "black",
              "points": [], "terms": {"from": "plug", "to": "screw"}}]
    st = WO.steps({"wires": wires, "mains": True})
    assert "clamp under jack's screw terminal, solder to the pin header servo's plug pushes onto; heat-shrink" in st[0]
    assert "plug into nano, clamp under jack's screw terminal." in st[1] and "heat-shrink" not in st[1]
    rows = WO.bom_rows({"wires": wires})
    assert sum(r["qty"] for r in rows if "heat-shrink" in r["item"]) == 2          # only the 2 header ends are soldered


def test_feed_at_the_minimum_is_reported_not_failed(tmp_path):
    """A run at exactly the load's minimum voltage (catalog min = nominal) leaves no headroom to judge a drop."""
    proj, asm = _servos(tmp_path, 1)
    proj.data["wiring"][0]["v"] = 4.8                     # MG996R voltage_min 4.8
    rows = [r for r in E.analyse(proj)["ratings"] if r["kind"].startswith("voltage after")]
    assert rows and all(r["soft"] and not r["ok"] for r in rows)
