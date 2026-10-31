"""Audit engine minors ENG-7..ENG-20 (AUDIT.md): one test per fix."""
import json

import pytest
from build123d import Box, Location, Pos

from kerf import assembly as A, checks, electrical as E, export, hole_axes, iface, pins, project as P, requirements
from kerf.ctx import Ctx
from kerf.req_gears import lewis_stress, lewis_y
from test_engine import _write_project


class _It:
    def __init__(self, shape, spec):
        self.id, self.shape, self.spec = "p", shape, spec


def _plate_with_hole(teardrop, pin=False):
    c = Ctx("p", {}, {"spec": {"print_rot": [90, 0, 0]}})
    plate = Box(30, 30, 6)
    loc = Location((0, 0, 3))             # hole axis = part Z; with print_rot [90,0,0] it lies along the bed
    td = iface.print_up_deg(c, loc) if teardrop else None
    if pin:
        plate -= iface.pin_hole(c, "M3", loc, "g", depth=6, fit="free", teardrop=td)
    else:
        plate -= iface.bolt_pattern(c, "g", "M3", [(0, 0)], loc, "clearance", 6, teardrop=td)
    return _It(c.finish(plate), {"print_rot": [90, 0, 0]})


def test_eng7_horizontal_round_holes_flagged():
    p, w = hole_axes.check(_plate_with_hole(False, pin=True))
    assert p and "pin hole" in p[0]
    p, w = hole_axes.check(_plate_with_hole(True, pin=True))
    assert not p and not w
    p, w = hole_axes.check(_plate_with_hole(False))
    assert not p and w and "clearance" in w[0]
    p, w = hole_axes.check(_plate_with_hole(True))
    assert not p and not w


def test_eng9_bed_contact():
    flat = Pos(0, 0, 1) * Box(60, 40, 2)                         # big face down
    on_edge = Pos(0, 0, 30) * Box(60, 2, 60)                      # standing on a 2 mm edge: 120 mm2 vs 3600 mm2
    assert checks.bed_contact("a", flat) == []
    w = checks.bed_contact("b", on_edge)
    assert w and "sits on the bed" in w[0]


def test_eng13_short_dowel_warned():
    assert pins.PIN_SPAN_SLACK == 1.0


def test_eng16_lock_advice():
    assert "TIP" in pins.lock_advice(["heatset"]) and "brass" in pins.lock_advice(["heatset"])
    t = pins.lock_advice(["tap"])
    assert "no threadlocker" in t and "nylon-patch" in t


def test_eng15_bom_extra_keys_and_duplicates():
    class Pr:
        data = {"bom_extra": [{"item": "M2 x 8 screw", "qty": 4, "type": "hardware"},
                              {"item": "Glue", "qty": 1, "spce": "typo"}, {"qty": 3}]}
    p, w = export.bom_extra_check(Pr, [{"screw": "M2", "length_mm": 5}])
    assert any("unknown key" in x and "spce" in x for x in p) and any("needs an 'item'" in x for x in p)
    assert w and "M2" in w[0] and "duplicate" in w[0]


def test_eng14_horn_centre_screw_rows():
    class It:
        def __init__(self, cat, q=1):
            self.role, self.spec = "purchased", {"catalog": cat, "qty": q}

    class Pr:
        items = {"a": It("servo_horns.aluminum_25T"), "b": It("servo_horns.aluminum_25T"), "c": It("servos.MG996R")}
    rows = export.horn_screw_rows(Pr)
    assert rows == [{"type": "fastener", "item": "M3 horn centre screw", "qty": 2, "spec": "",
                     "note": rows[0]["note"]}]


def test_eng17_throttle_estimate_gets_margin():
    assert E._limit_peak({"peak_a": 20, "why": "x"}) == 20
    assert E._limit_peak({"peak_a": 20, "why": "x", "kind": "throttle_estimate"}) == pytest.approx(23.0)
    with pytest.raises(E.ElectricalError):
        E._limit_peak({"peak_a": 20, "why": "x", "kind": "guess"})


def test_eng12_wire_colour_required(tmp_path):
    from test_electrical import _servos
    proj, asm = _servos(tmp_path, 1)
    proj.data["wiring"][0].pop("color", None)
    with pytest.raises(E.ElectricalError, match="color"):
        E.analyse(proj)
    proj.data["wiring"][0]["supplied"] = "psu"                   # a supplied lead may leave it out
    E.analyse(proj)


def test_eng18_review_status_flags_stale_out(tmp_path, monkeypatch):
    from kerf import cli
    d = _write_project(tmp_path / "proj", """
        name: t
        params: {}
        parts: {a: {file: parts/a.py, material: PETG}}
        assembly: {root: a, joints: []}
        """, {"a": "from build123d import *\ndef build(ctx):\n    return ctx.finish(Box(10, 10, 10))\n"})
    fp = P.load(str(d)).fingerprint()
    (d / "review.json").write_text(json.dumps({"verdict": "PASS", "fingerprint": fp}))
    r = cli.review_status(str(d))
    assert r["ok"] and r["out_stale"] and "not built" in r["why"]
    (d / "out").mkdir()
    (d / "out" / "report.json").write_text(json.dumps({"fingerprint": "old"}))
    assert "run kerf build" in cli.review_status(str(d))["why"]
    (d / "out" / "report.json").write_text(json.dumps({"fingerprint": fp}))
    r = cli.review_status(str(d))
    assert r["ok"] and not r["out_stale"]


def test_eng20_lewis():
    # Shigley Table 14-2 values and the robot_arm yaw pair: 922 N*mm on the 36 T (m 1.5, b 8): Ft = 34.1 N,
    # Y(24 T) = 0.337 -> 8.44 MPa
    assert lewis_y(24) == pytest.approx(0.337) and lewis_y(36) == pytest.approx((0.371 + 0.384) / 2)
    assert lewis_stress(1.5, 36, 24, 8, 922) == pytest.approx(922 / 27 / (8 * 1.5 * 0.337), rel=1e-6)
    with pytest.raises(ValueError):
        lewis_y(10)
    assert "gear_bending" in requirements.REGISTRY


def test_eng8_11_fea_hygiene_warnings(tmp_path):
    from kerf.pipeline import _fea_hygiene
    d = _write_project(tmp_path / "f", """
        name: t
        params: {}
        parts: {a: {file: parts/a.py, material: PETG}}
        assembly: {root: a, joints: []}
        requirements:
          - id: f1
            check: fea_static
            part: a
            fixed: {box: [[-5, -5, -0.1], [5, 5, 0.1]]}
            loads:
              - {cylinder: {at: [0, 0, 0], dir: [0, 0, 1], r: 2, span: [0, 10]}, force_n: [1, 0, 0]}
        """, {"a": "from build123d import *\nfrom kerf import iface\ndef build(ctx):\n"
                   "    s = Box(40, 40, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))\n"
                   "    s -= iface.bolt_pattern(ctx, 'g', 'M3', [(15, 15)], Location((0, 0, 10)), 'clearance', 10)\n"
                   "    return ctx.finish(s)\n"})
    proj = P.build(P.load(str(d)))
    w = " | ".join(_fea_hygiene(proj))
    assert "no load_axis" in w and "use bearing_n" in w and "fixed box(es) hold none" in w
