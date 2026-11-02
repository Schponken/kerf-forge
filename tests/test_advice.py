"""Specific advice (kerf/advice.py): each failed requirement gets what to change and by how much, from its own numbers;
overlaps and joint collisions carry their own fix; the plain cards use it instead of one blanket sentence."""
from types import SimpleNamespace as NS

from build123d import Box, Pos

from kerf import advice, explain


def test_stress_advice_sizes_the_section_and_names_stronger_materials():
    proj = NS(items={"arm": NS(spec={"material": "PLA", "infill": 0.3})})
    tips = advice.advise({"check": "fea_static", "ok": False, "value": 18.0, "limit": 12.5}, {"part": "arm", "direction": "xy"}, proj)
    assert "1.44x" in tips[0] and "20 % thicker" in tips[0] and "44 % wider" in tips[0]   # sqrt(1.44) = 1.2
    alt = next(t for t in tips if t.startswith("Or print it"))          # needs >= 39 x 1.44 = 56 MPa: PETG (48) is not enough
    assert "PA6-CF (102 MPa vs 39)" in alt and "PETG (" not in alt


def test_frequency_servo_tip_balance_and_flight_time_advice():
    nf = advice.advise({"check": "natural_freq", "ok": False, "value": 186.0, "limit": [170.0, 510.0]}, {"separation": 0.2}, None)
    assert "204 Hz" in nf[0] and "20 % more stiffness" in nf[0]                            # (204 / 186)^2 = 1.20
    sv = advice.advise({"check": "static_torque", "ok": False, "value": 6.0}, {"max_fraction": 0.5}, None)
    assert "12.0 kg·cm" in sv[0] and "DS3218" in sv[1] and "MG996R" not in sv[1]
    tip = advice.advise({"check": "tip_over", "ok": False, "value": 10.0, "limit": 15.0}, {}, None)
    assert "widen the footprint 52 %" in tip[0]                                            # tan15 / tan10 = 1.52
    sm = advice.advise({"check": "static_margin", "ok": False, "value": 0.02, "limit": [0.05, 0.15]}, {}, None)
    assert "too far back" in sm[0] and "battery forward" in sm[0]
    ft = advice.advise({"check": "flight_time", "ok": False, "value": 10.0, "limit": 12}, {}, None)
    assert "20 % more battery" in ft[0]
    assert advice.advise({"check": "mass_max", "ok": True, "value": 1, "limit": 2}, {}, None) == []


def test_cards_use_the_advice_and_the_problems_own_fix():
    card = explain.explain_requirement({"id": "t", "check": "thrust_to_weight", "ok": False, "value": 5.4, "limit": 6, "bound": "min",
                                        "unit": ":1", "advice": ["Cut 10 % weight.", "Weight is cheaper."]})
    assert card["fix"] == "Cut 10 % weight." and card["fixes"] == ["Weight is cheaper."]
    c = explain.explain("lid and battery overlap by 290.8 mm3 in the assembled position — fix: battery can't change shape, so cut a pocket", ["lid"])
    assert c["title"] == "Two parts are in the same space" and c["fix"].startswith("Battery can't change shape") and "overlap (290.8" in c["why"]
    k = explain.explain("hub (group 'm'): no 2.5 mm hex key can reach the head (straight hits ['deck'], ball-end at 25 deg also blocked)", ["hub"])
    assert "['deck']" in k["fix"] and "key_access" in k["fix"]


def test_overlap_names_the_part_to_cut_and_by_how_much():
    lid = NS(role="printed", shape=Box(40, 40, 10))                      # z -5..5
    bat = NS(role="purchased", shape=Pos(0, 0, 9) * Box(20, 20, 10))    # z 4..14: 1 mm deep into the lid's top
    proj = NS(items={"lid": lid, "battery": bat})
    t = advice.overlap(proj, "lid", "battery")
    assert t.startswith("battery can't change shape, so cut a pocket 1.3 mm deep into lid") and "along -Z" in t


def test_sweep_collision_says_where_to_stop_or_make_room():
    s = {"joint": "fold", "kind": "revolute", "range": [0, 80], "samples": 9,
         "collisions": [{"a": "wing", "b": "hub", "volume_mm3": 3, "at": 70.0}, {"a": "wing", "b": "hub", "volume_mm3": 9, "at": 80.0}]}
    proj = NS(items={"wing": NS(role="printed"), "hub": NS(role="printed")})
    t = advice.sweep(s, proj)
    assert "from 70 to 80°" in t and "end the range at about 65°" in t and "wing or hub" in t


def test_wiring_errors_get_their_own_fix_not_see_the_details():
    for m, words in [("circuit: wiring names unknown item 'esc2'", "esc2"),
                     ("circuit: pdb terminal BAT+ takes 2 wire(s) but 3 land on it", "splice"),
                     ("circuit ERC: output connected to output on net TX1: fc.TX1 and gps.TX - two outputs", "TX of one to RX"),
                     ("circuit ERC: Unconnected pin gps.VCC is not wired (wire it, or ...)", "optional"),
                     ("circuit ERC: Insufficient drive current on net N5 for pin rx.VCC", "supply output"),
                     ("circuit: something odd", "wiring:")]:
        c = explain.explain(m)
        assert words in c["fix"] and c["fix"] != "See the details.", (m, c)
