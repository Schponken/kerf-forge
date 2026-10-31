"""Screw heads are solids in interference + sweeps (robot_arm review round 2: the turntable platform swept over the
yaw-gear horn screw heads and nothing saw it, because heads were not modelled)."""
import math

import pytest

from kerf import assembly as A, heads, project as P
from test_engine import BOLT_BLOCK, BOLT_PLATE, _write_project

YAML = """
name: Head test
params: {}
parts:
  plate: {file: parts/plate.py}
  block: {file: parts/block.py}
  bar: {file: parts/bar.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
    - {parent: block.pivot, child: bar.origin, name: swing, range: [0, 90]}
"""
# a 6 mm wide bar from the axis out along +Y, its underside at ZB; turning +90 deg about Z swings it over x = -10
BAR = """
from build123d import *
def build(ctx):
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(Pos(0, 2, ZB) * Box(6, 30, 3, align=(Align.CENTER, Align.MIN, Align.MIN)))
"""
PIVOT = '    ctx.revolute("pivot", Axis.Z, (0, 90))\n    ctx.rigid("top"'


def _asm(tmp_path, zb):
    block = BOLT_BLOCK.replace('    ctx.rigid("top"', PIVOT)
    d = _write_project(tmp_path / f"h{zb}", YAML, {"block": block, "plate": BOLT_PLATE, "bar": BAR.replace("ZB", str(zb))})
    proj = P.build(P.load(str(d)))
    assert all(it.error is None for it in proj.items.values()), [it.error for it in proj.items.values()]
    asm = A.plan(proj)
    A.solve(asm)
    joints, probs = A.fasteners(asm)
    assert probs == [] and len(joints) == 2
    asm.heads = heads.build(asm, joints)
    return asm


def test_head_hit_at_home_has_the_hand_calculated_volume(tmp_path):
    # plate top z 24; M3 socket head (catalog 5.5 x 3.0) up to z 27; bar underside at 26. At home the bar lies along
    # +Y over x in [-3, 3], clear of both heads (x = +-10).
    asm = _asm(tmp_path, 26)
    assert A.interference(asm) == []
    # turned 90 deg the bar runs along -X over the head at x = -10: overlap = pi * (2.75 - 0.05)^2 * (27 - 26)
    # (the head starts 0.05 above its seat and is 0.05 shorter, so its top stays at 27)
    A.solve(asm, {"swing": 90})
    hits = A.interference(asm)
    assert len(hits) == 1 and hits[0]["b"] == "bar" and "screw head" in hits[0]["a"]
    assert hits[0]["volume_mm3"] == pytest.approx(math.pi * 2.7 ** 2 * (27 - 26), rel=0.01)


def test_sweep_catches_a_head_and_clears_when_the_bar_is_higher(tmp_path):
    sw = A.sweeps(_asm(tmp_path, 26))
    assert not sw[0]["clear"] and "screw head" in sw[0]["collisions"][0]["a"]
    sw = A.sweeps(_asm(tmp_path, 27.5))                        # 0.5 mm over the head tops
    assert sw[0]["clear"]
