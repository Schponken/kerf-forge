"""prop_clearance: hand-placed discs with known gaps."""
import math

import pytest

from kerf import assembly as A, project as P, requirements
from test_engine import _write_project

FRAME = """
from build123d import *
def build(ctx):
    s = Box(200, 40, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))      # top face z = 5
    ctx.rigid("m1", Location((-60, 0, 15)))
    ctx.revolute("m2", Axis((20, 0, 15), (0, 0, 1)), range=(-20, 20))   # swing arm pivot 40 mm inboard of prop_2
    ctx.rigid("mast", Location((0, 0, 5)))
    return ctx.finish(s)
"""
SWING = """
from build123d import *
def build(ctx):
    ctx.rigid("pivot", Location((-40, 0, 0)))
    ctx.rigid("prop", Location((0, 0, 0)))
    return ctx.finish(Pos(-20, 0, -8) * Box(44, 4, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
POST = """
from build123d import *
def build(ctx):
    ctx.rigid("foot", Location((0, 0, 0)))
    return ctx.finish(Box(4, 4, 30, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""


def _proj(tmp_path, reqs, post=True):
    y = f"""
name: Prop test
params: {{}}
parts:
  frame: {{file: parts/frame.py}}
  swing: {{file: parts/swing.py}}
{"  post: {file: parts/post.py}" if post else ""}
keepouts:
  prop_1: {{proxy: prop_disc, diameter: 100, h: 10}}
  prop_2: {{proxy: prop_disc, diameter: 100, h: 10, owner: swing}}
assembly:
  root: frame
  joints:
    - {{parent: frame.m1, child: prop_1.hub}}
    - {{parent: frame.m2, child: swing.pivot, name: gimbal, range: [-20, 20]}}
    - {{parent: swing.prop, child: prop_2.hub}}
{"    - {parent: frame.mast, child: post.foot}" if post else ""}
requirements:
""" + "".join(f"  - {r}\n" for r in reqs)
    d = _write_project(tmp_path / "props", y, {"frame": FRAME, "post": POST, "swing": SWING})
    proj = P.build(P.load(str(d)))
    assert all(it.error is None for it in proj.items.values()), [it.error for it in proj.items.values()]
    return requirements.run_all(proj, A.plan(proj))


def test_disc_to_disc_and_frame(tmp_path):
    between, frame = _proj(tmp_path, ["{check: prop_clearance, min_mm: 5, min_between_mm: 25, joints: []}",
                                      "{check: prop_clearance, min_mm: 5, joints: []}"], post=False)
    assert between["value"] == pytest.approx(20.0, abs=0.01)   # tips at x = -10 and +10
    assert not between["ok"] and "prop_1 to prop_2" in between["detail"]
    assert frame["value"] == pytest.approx(10.0, abs=0.01)     # disc bottom z 15, frame top z 5
    assert frame["ok"]


def test_post_between_discs(tmp_path):
    r, = _proj(tmp_path, ["{check: prop_clearance, min_mm: 9, joints: []}"])
    assert r["value"] == pytest.approx(8.0, abs=0.01) and "post" in r["detail"] and not r["ok"]
    r, = _proj(tmp_path, ["{check: prop_clearance, min_mm: 9, joints: [], ignore: [post]}"])
    assert r["value"] == pytest.approx(10.0, abs=0.01) and r["ok"]


def test_swinging_prop_is_swept(tmp_path):
    req = "{check: prop_clearance, min_mm: 1, min_between_mm: 15%s}"
    home, = _proj(tmp_path, [req % ", joints: []"], post=False)
    swept, = _proj(tmp_path, [req % ""], post=False)
    assert home["value"] == pytest.approx(20.0, abs=0.01)
    # prop_2's centre swings on a 40 mm arm about (20, 0): at +/-20 deg it is at (20 + 40 cos20, 40 sin20)
    gap = math.hypot(20 + 40 * math.cos(math.radians(20)) + 60, 40 * math.sin(math.radians(20))) - 100
    assert swept["value"] == pytest.approx(gap, abs=0.01) and "gimbal" in swept["detail"]   # 18.38
