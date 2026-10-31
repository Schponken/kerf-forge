"""Screw shanks and blind-thread length tolerance (from the fpv_5in review: a stack screw tip ran into an arm)."""
import pytest

from kerf import assembly as A, project as P, shanks
from test_engine import BOLT_BLOCK, BOLT_PLATE, _write_project

YAML = """
name: Shank test
params: {}
parts:
  plate: {file: parts/plate.py}
  block: {file: parts/block.py}
  under: {file: parts/under.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
    - {parent: block.origin, child: under.origin}
"""
UNDER = """
from build123d import *
def build(ctx):
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(Pos(0, 0, ZTOP) * Box(60, 60, 3, align=(Align.CENTER, Align.CENTER, Align.MAX)))
"""


def _run(tmp_path, ztop):
    block = BOLT_BLOCK.replace('    ctx.rigid("top"', '    ctx.rigid("origin", Location((0, 0, 0)))\n    ctx.rigid("top"')
    d = _write_project(tmp_path / f"s{ztop}", YAML, {"block": block, "plate": BOLT_PLATE, "under": UNDER.replace("ZTOP", str(ztop))})
    proj = P.build(P.load(str(d)))
    assert all(it.error is None for it in proj.items.values()), [it.error for it in proj.items.values()]
    asm = A.plan(proj)
    A.solve(asm)
    joints, probs = A.fasteners(asm)
    assert probs == [] and joints
    return joints, shanks.check(asm, joints)


def test_tip_inside_receiver_is_fine_and_tip_into_a_third_part_is_caught(tmp_path):
    joints, problems = _run(tmp_path, -20)                     # plate far below the block: nothing in the way
    assert problems == []
    lowest_tip = min(j["at"][2] + j["dir"][2] * j["length_mm"] for j in joints)
    joints, problems = _run(tmp_path, lowest_tip + 1.0)         # a part whose top face is 1 mm above the tips
    assert len(problems) == len(joints) and "runs into under" in problems[0]


TWO = """
name: Thread test
params: {}
parts:
  plate: {file: parts/plate.py}
  block: {file: parts/block.py}
assembly:
  root: block
  joints: [{parent: block.top, child: plate.bottom}]
"""


def _threaded(tmp_path, grip):
    """Motor-like blind thread: 3.0 mm deep, 2.0 mm minimum engagement; plate grip `grip`."""
    block = BOLT_BLOCK.replace('"heatset", Location((x, 0, 20)), engage=6.2, min_engage=4.0', '"threaded", Location((x, 0, 20)), engage=3.0, min_engage=2.0')
    plate = BOLT_PLATE.replace("Box(30, 30, 4", f"Box(30, 30, {grip}").replace("Location((x, 0, 4)), grip=4", f"Location((x, 0, {grip})), grip={grip}")
    d = _write_project(tmp_path / f"t{grip}", TWO, {"block": block, "plate": plate})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    return A.fasteners(asm)


def test_blind_thread_length_keeps_tolerance_margin(tmp_path):
    # grip 7: an M3 x 10 would end exactly at the 3.0 mm thread bottom; with the +/-0.29 mm length tolerance it is refused
    joints, problems = _threaded(tmp_path, 7)
    assert any("no standard M3 length" in p for p in problems)
    # grip 7.5: M3 x 10 leaves 2.5 mm engagement, 0.5 mm short of the bottom (> 0.29 mm ISO 4762 tolerance)
    joints, problems = _threaded(tmp_path, 7.5)
    assert problems == [] and all(j["length_mm"] == 10 for j in joints)
