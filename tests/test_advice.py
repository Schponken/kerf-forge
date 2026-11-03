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
    assert "213 Hz" in nf[0] and "31 % more stiffness" in nf[0]                            # (213 / 186)^2 = 1.31
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


def _frequency_gate(monkeypatch, frequency, excitations, **settings):
    """Exercise the real frequency check without meshing or solving; 1 kg makes k set f_n exactly."""
    import math
    from kerf import req_dynamic
    monkeypatch.setattr(req_dynamic, "_solve", lambda *a, **kw: ({}, 1, (2 * math.pi * frequency) ** 2 / 1000))
    monkeypatch.setattr(req_dynamic, "rotor_hz", lambda *a, **kw: excitations)
    monkeypatch.setattr("kerf.checks.item_mass_g", lambda item: 0)
    return req_dynamic.natural_freq(NS(items={"arm": NS()}), None, part="arm", fixed={}, loads=[],
                                    carried_g=1000, excitation={"motor": "motor"}, **settings)


def test_resonance_advice_targets_clear_every_actual_excitation(monkeypatch):
    import re
    for fn, excitations, sep in [(185, [200.2, 600.5], .2), (186, [170, 510], .2),
                                  (200, [170, 200, 230], .2), (200, [230, 170, 200], .2),
                                  (100, [100], .95)]:
        row = _frequency_gate(monkeypatch, fn, excitations, separation=sep)
        assert not row["ok"]
        tips = advice.advise({"check": "natural_freq", **row}, {"separation": sep})
        targets = [float(v) for v in re.findall(r"to at (?:least|most) ([\d.]+) Hz", " ".join(tips))]
        assert len(targets) == 2
        for target in targets:
            assert _frequency_gate(monkeypatch, target, excitations, separation=sep)["ok"], (target, tips)
        if fn == 185:
            assert targets == [251, 166]        # nearest safe integer targets: 200.2/.8 and 200.2/1.2
        if fn == 200:
            assert targets == [288, 141]        # clear the overlapping bands of all three excitations


def test_resonance_boundaries_preserve_real_gate_strictness(monkeypatch):
    # The check includes equality; advice rounds outward instead of rounding a boundary into the unsafe band.
    assert _frequency_gate(monkeypatch, 256, [192], separation=.25)["ok"]  # exactly representable equality
    assert _frequency_gate(monkeypatch, 256, [320], separation=.25)["ok"]
    assert _frequency_gate(monkeypatch, 250 + 1e-6, [200], separation=.2)["ok"]
    assert not _frequency_gate(monkeypatch, 250 - 1e-6, [200], separation=.2)["ok"]
    low = 200 / 1.2
    assert _frequency_gate(monkeypatch, low - 1e-6, [200], separation=.2)["ok"]
    assert not _frequency_gate(monkeypatch, low + 1e-6, [200], separation=.2)["ok"]
    tips = advice.advise({"check": "natural_freq", "value": 200, "limit": [200]}, {"separation": .2})
    assert "at least 251 Hz" in tips[0] and "at most 166 Hz" in tips[1]


def test_frequency_ratio_advice_uses_highest_excitation_and_branch_precedence(monkeypatch):
    row = _frequency_gate(monkeypatch, 186, [170, 510], min_ratio=1.5, separation=.2)
    assert not row["ok"]
    tips = advice.advise({"check": "natural_freq", **row}, {"min_ratio": 1.5, "separation": .2})
    assert "at least 766 Hz" in tips[0] and not any("at most" in t for t in tips)
    assert _frequency_gate(monkeypatch, 766, [170, 510], min_ratio=1.5, separation=.2)["ok"]
    assert not _frequency_gate(monkeypatch, 765 - 1e-6, [170, 510], min_ratio=1.5)["ok"]
    assert _frequency_gate(monkeypatch, 765, [170, 510], min_ratio=1.5)["ok"]


def test_resonance_large_separation_has_only_a_lower_solution(monkeypatch):
    for sep, target in [(1, 49), (2, 33)]:
        row = _frequency_gate(monkeypatch, 100, [100], separation=sep)
        tips = advice.advise({"check": "natural_freq", **row}, {"separation": sep})
        assert len(tips) == 1 and f"at most {target} Hz" in tips[0]
        assert _frequency_gate(monkeypatch, target, [100], separation=sep)["ok"]


def test_resonance_advice_rejects_invalid_numbers_and_respects_zero():
    row = {"check": "natural_freq", "value": 100, "limit": [100]}
    for settings in [{"separation": 0}, {"separation": -1}, {"separation": float("nan")},
                     {"separation": float("inf")}, {"min_ratio": 0}]:
        assert advice.advise(row, settings) == []
    for bad in [0, -1, float("nan"), float("inf")]:
        assert advice.advise({**row, "value": bad}, {"separation": .2}) == []
    assert advice.advise({**row, "limit": [float("nan")]}, {"separation": .2}) == []
    assert advice.advise({**row, "limit": [0]}, {"separation": 2}) == []  # no positive frequency can clear it
