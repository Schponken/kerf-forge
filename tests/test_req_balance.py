"""Balance checks against hand-calculated answers."""
import textwrap

import pytest

from kerf import assembly as A, project as P, requirements
from kerf.checks import item_mass_g

# base: 40 x 40 x 10 solid block (16000 mm3), centroid (0, 0, 5)
# top:  10 x 10 x 10 solid block (1000 mm3), centroid 15 mm from the spin axis at z = 15; same material, 100 % infill
# so masses are 16 : 1 and the CG is x = 15/17 = 0.882 mm, z = (16*5 + 15)/17 = 5.588 mm at home.
YAML = """
name: cg
parts:
  base: {file: parts/base.py, material: PLA, infill: 1.0}
  top: {file: parts/top.py, material: PLA, infill: 1.0}
assembly:
  root: base
  joints: [{name: spin, parent: base.spin, child: top.bottom, range: [0, 180]}]
requirements: []
"""
BASE = """
from build123d import *
def build(ctx):
    ctx.revolute("spin", Axis((0, 0, 10), (0, 0, 1)), range=(0, 180))
    return ctx.finish(Box(40, 40, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
TOP = """
from build123d import *
def build(ctx):
    ctx.rigid("bottom", Location((0, 0, 0)))
    ctx.rigid("tip", Location((15, 0, 10)))
    return ctx.finish(Pos(15, 0, 0) * Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("cg")
    (d / "parts").mkdir()
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "base.py").write_text(textwrap.dedent(BASE))
    (d / "parts" / "top.py").write_text(textwrap.dedent(TOP))
    proj = P.build(P.load(str(d)))
    assert not [it.error for it in proj.items.values() if it.error]
    asm = A.plan(proj)
    A.solve(asm)
    return proj, asm


def _run(built, **kw):
    proj, asm = built
    return requirements.REGISTRY["cg"](proj, asm, **kw)


def test_cg_hand_calc(built):
    r = _run(built, point=[0, 0, 0], max_lateral_mm=0.9, min_along_mm=5.5, max_along_mm=5.6)
    assert r["ok"], r
    assert r["value"]["lateral_mm"] == pytest.approx(15 / 17, abs=0.01)
    assert r["value"]["along_mm"][0] == pytest.approx(95 / 17, abs=0.01)
    assert not _run(built, point=[0, 0, 0], max_lateral_mm=0.85)["ok"]
    assert not _run(built, point=[0, 0, 0], max_along_mm=5.5)["ok"]


def test_cg_reference_joint_axis_and_poses(built):
    # reference line through the spin joint origin (0, 0, 10): along = 5.588 - 10
    r = _run(built, ref="base.spin", max_lateral_mm=1.0, poses=[{"spin": 90}, {"spin": 180}])
    assert r["value"]["along_mm"][0] == pytest.approx(95 / 17 - 10, abs=0.01)
    assert r["value"]["lateral_mm"] == pytest.approx(15 / 17, abs=0.01)  # same radius in every pose
    # horizontal reference axis (world X through the origin): lateral = |(y, z)|; at spin 90 the top moves to +y
    home = _run(built, point=[0, 0, 0], axis=[1, 0, 0], max_lateral_mm=100)
    assert home["value"]["lateral_mm"] == pytest.approx(95 / 17, abs=0.01)
    turned = _run(built, point=[0, 0, 0], axis=[1, 0, 0], max_lateral_mm=100, poses=[{"spin": 90}])
    assert turned["value"]["lateral_mm"] == pytest.approx(((15 / 17) ** 2 + (95 / 17) ** 2) ** 0.5, abs=0.01)


def test_cg_payload_and_include(built):
    proj, _ = built
    mb, mt = item_mass_g(proj.items["base"]), item_mass_g(proj.items["top"])
    assert mb / mt == pytest.approx(16, rel=1e-6)
    pay = 2 * mt  # at top.tip = (15, 0, 10) in top's frame = (15, 0, 20) in the world (top sits on z = 10)
    r = _run(built, point=[0, 0, 0], max_lateral_mm=10, payload_g=pay, payload_at="top.tip")
    assert r["value"]["lateral_mm"] == pytest.approx(15 * 3 / 19, abs=0.01)
    assert r["value"]["along_mm"][0] == pytest.approx((16 * 5 + 15 + 2 * 20) / 19, abs=0.01)
    only_top = _run(built, point=[0, 0, 0], max_lateral_mm=100, include=["top"])
    assert only_top["value"]["lateral_mm"] == pytest.approx(15, abs=0.01)


def test_cg_needs_a_limit(built):
    with pytest.raises(ValueError):
        _run(built, point=[0, 0, 0])
