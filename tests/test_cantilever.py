"""cantilever_stress must match textbook beam formulas (sigma = M c / I, N / A)."""
import math

import pytest

from kerf import assembly as A, project as P, requirements
from test_engine import _write_project

BAR = """
from build123d import *
def build(ctx):
    s = Box(100, 10, 20, align=(Align.MIN, Align.CENTER, Align.CENTER))   # x = length, 10 wide (y), 20 tall (z)
    ctx.rigid("root", Location((0, 0, 0)))
    ctx.rigid("tip", Location((100, 0, 0)))
    return ctx.finish(s)
"""
TUBE = """
from build123d import *
def build(ctx):
    s = Cylinder(10, 100, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Cylinder(8, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("root", Location((0, 0, 0)))
    return ctx.finish(s)
"""


def _run(tmp_path, req: str, rot="[0, 0, 0]", part=BAR):
    y = f"""
name: Beam test
params: {{L: 100}}
parts:
  bar: {{file: parts/bar.py, material: PETG, print_rot: {rot}}}
assembly:
  root: bar
  joints: []
requirements:
  - {req}
"""
    d = _write_project(tmp_path / "beam", y, {"bar": part})
    proj = P.build(P.load(str(d)))
    assert proj.items["bar"].error is None, proj.items["bar"].error
    return requirements.run_all(proj, A.plan(proj))[0]


SEC = "section: {name: root, at: [20, 0, 0], normal: [1, 0, 0]}"


def test_tip_load_strong_axis(tmp_path):
    r = _run(tmp_path, "{check: cantilever_stress, part: bar, " + SEC + ", loads: [{at: tip, force_n: [0, 0, -10]}], sf: 2}")
    M, I, c = 10 * 80, 10 * 20 ** 3 / 12, 10
    assert r["value"] == pytest.approx(M * c / I, rel=1e-3)        # 1.2 MPa
    assert r["limit"] == pytest.approx(48 / 2)                      # PETG xy (stress along layers when printed flat)
    assert r["ok"]


def test_weak_axis_and_oblique_load(tmp_path):
    r = _run(tmp_path, "{check: cantilever_stress, part: bar, " + SEC + ", loads: [{at: [L, 0, 0], force_n: [0, 10, 0]}]}")
    assert r["value"] == pytest.approx(800 * 5 / (20 * 10 ** 3 / 12), rel=1e-3)   # 2.4 MPa
    r = _run(tmp_path, "{check: cantilever_stress, part: bar, " + SEC + ", loads: [{at: tip, force_n: [0, 10, -10]}]}")
    assert r["value"] == pytest.approx(1.2 + 2.4, rel=1e-3)                        # stresses add at a corner


def test_axial_plus_bending(tmp_path):
    r = _run(tmp_path, "{check: cantilever_stress, part: bar, " + SEC + ", loads: [{at: tip, force_n: [500, 0, -10]}]}")
    assert r["value"] == pytest.approx(500 / 200 + 1.2, rel=1e-3)


def test_tube_section(tmp_path):
    r = _run(tmp_path, "{check: cantilever_stress, part: bar, section: {at: [0, 0, 10], normal: [0, 0, 1]}, "
                       "loads: [{at: [0, 0, 100], force_n: [5, 0, 0]}], kt: 1.5}", part=TUBE)
    I = math.pi / 4 * (10 ** 4 - 8 ** 4)
    assert r["value"] == pytest.approx(1.5 * 5 * 90 * 10 / I, abs=0.005)  # value is reported to 0.01 MPa


def test_layer_direction_from_print_rot(tmp_path):
    req = "{check: cantilever_stress, part: bar, " + SEC + ", loads: [{at: tip, force_n: [0, 0, -10]}], sf: 3}"
    stood_up = _run(tmp_path, req, rot="[0, 90, 0]")   # bar printed standing: its length (x) is build Z
    assert stood_up["limit"] == pytest.approx(39 / 3)  # PETG z strength
    assert "across layers" in stood_up["detail"]
    forced = _run(tmp_path, req.replace("sf: 3", "sf: 3, direction: xy"), rot="[0, 90, 0]")
    assert forced["limit"] == pytest.approx(48 / 3)


def test_load_on_wrong_side_fails(tmp_path):
    r = _run(tmp_path, "{check: cantilever_stress, part: bar, section: {at: [20, 0, 0], normal: [-1, 0, 0]}, "
                       "loads: [{at: tip, force_n: [0, 0, -10]}]}")
    assert not r["ok"] and "free side" in r["detail"]
