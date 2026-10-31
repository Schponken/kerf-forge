"""tip_over must match atan(edge distance / CG height) by hand."""
import math

import pytest

from kerf import assembly as A, project as P, requirements
from test_engine import _write_project

BLOCK = """
from build123d import *
def build(ctx):
    s = Box(100, 60, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("root", Location((0, 0, 0)))
    ctx.rigid("tip", Location((100, 0, 20)))
    return ctx.finish(s)
"""
MAST = """
from build123d import *
def build(ctx):
    s = Box(100, 100, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s += Pos(40, 0, 10) * Box(10, 10, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("root", Location((0, 0, 0)))
    return ctx.finish(s)
"""
LEGS = """
from build123d import *
def build(ctx):
    s = Pos(0, 0, 30) * Box(120, 120, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (-40, 40):
        for y in (-40, 40):
            s += Pos(x, y, 0) * Box(4, 4, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("root", Location((0, 0, 0)))
    return ctx.finish(s)
"""


def _run(tmp_path, req, part):
    y = f"""
name: Tip test
params: {{}}
parts:
  body: {{file: parts/body.py, material: PETG}}
assembly:
  root: body
  joints: []
requirements:
  - {req}
"""
    d = _write_project(tmp_path / "tip", y, {"body": part})
    proj = P.build(P.load(str(d)))
    assert proj.items["body"].error is None, proj.items["body"].error
    return proj, requirements.run_all(proj, A.plan(proj))[0]


def test_plain_block(tmp_path):
    _, r = _run(tmp_path, "{check: tip_over, min_deg: 30}", BLOCK)
    assert r["value"] == pytest.approx(math.degrees(math.atan(30 / 10)), abs=0.06)   # 71.6, narrow side governs
    assert r["ok"]


def test_offset_mast_moves_cg(tmp_path):
    _, r = _run(tmp_path, "{check: tip_over, min_deg: 30}", MAST)
    v_base, v_mast = 100 * 100 * 10, 10 * 10 * 100
    cx = v_mast * 40 / (v_base + v_mast)
    cz = (v_base * 5 + v_mast * 60) / (v_base + v_mast)
    assert r["value"] == pytest.approx(math.degrees(math.atan((50 - cx) / cz)), abs=0.06)   # toward the mast side


def test_legs_footprint(tmp_path):
    _, r = _run(tmp_path, "{check: tip_over, min_deg: 30}", LEGS)
    v_top, v_leg = 120 * 120 * 6, 4 * 4 * 30
    cz = (v_top * 33 + 4 * v_leg * 15) / (v_top + 4 * v_leg)
    assert r["value"] == pytest.approx(math.degrees(math.atan(42 / cz)), abs=0.06)   # legs' outer faces at +/-42


def test_payload_outside_footprint_falls(tmp_path):
    proj, r = _run(tmp_path, "{check: tip_over, min_deg: 10, payload_g: 2000, payload_at: body.tip}", BLOCK)
    m = requirements.item_mass_g(proj.items["body"])
    cx = 2000 * 100 / (m + 2000)
    cz = (m * 10 + 2000 * 20) / (m + 2000)
    assert cx > 50
    assert r["value"] == pytest.approx(math.degrees(math.atan2(50 - cx, cz)), abs=0.06)
    assert r["value"] < 0 and not r["ok"]


def test_worst_pose_is_reported(tmp_path):
    from test_engine import HINGE_ARM, HINGE_BASE
    y = """
name: Tip hinge
params: {L: 60}
parts:
  base: {file: parts/base.py, material: PETG}
  arm: {file: parts/arm.py, material: PETG}
assembly:
  root: base
  joints:
    - {parent: base.pivot, child: arm.hub, name: swing, range: [-90, 90]}
"""
    d = _write_project(tmp_path / "hinge", y, {"base": HINGE_BASE, "arm": HINGE_ARM})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    a = requirements.tip_over(proj, asm, 0, poses=[{"swing": 0}])["value"]
    b = requirements.tip_over(proj, asm, 0, poses=[{"swing": 90}])["value"]
    both = requirements.tip_over(proj, asm, 0, poses=[{"swing": 0}, {"swing": 90}])
    assert b < 0 < a                       # arm straight up (home) stands; out to the side it falls
    assert both["value"] == min(a, b)
    assert f"'swing': {0 if a < b else 90}" in both["detail"]


def test_include_limits_the_mass(tmp_path):
    """include: only the listed items count (a payload far outside would tip it; leaving it out does not)."""
    proj, r = _run(tmp_path, "{check: tip_over, min_deg: 10, payload_g: 2000, payload_at: body.tip, include: [body]}", BLOCK)
    assert r["value"] < 0                       # the payload still counts (it is not an item)
    proj, r = _run(tmp_path, "{check: tip_over, min_deg: 30, include: [body]}", BLOCK)
    assert r["value"] == pytest.approx(math.degrees(math.atan(30 / 10)), abs=0.06)
