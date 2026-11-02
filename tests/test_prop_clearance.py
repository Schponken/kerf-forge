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


def test_pruned_sampling_equals_full_subdivision():
    """requirements._min_dist_sampled subdivides only triangles that can hold the minimum: same value as the old
    whole-surface subdivision, at random placements of real shapes against a prop-disc cylinder."""
    import numpy as np
    import trimesh
    from build123d import Box, Cylinder, Pos, Rot, Sphere
    from kerf import geom, requirements as rq
    rng = np.random.default_rng(3)
    R, h = 60.0, 8.0
    for shape in (Box(200, 30, 6), Rot(20, 10, 0) * Cylinder(10, 120), Sphere(25), Box(40, 40, 40) - Sphere(24)):
        v, f = geom.mesh(shape, tol=0.05, ang=0.2)
        memo = {}
        for _ in range(6):
            M = Rot(*rng.uniform(-180, 180, 3)) * Pos(*rng.uniform(-90, 90, 3))
            t = M.wrapped.Transformation()
            A = np.array([[t.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
            b = np.array([t.Value(i, 4) for i in (1, 2, 3)])
            q = v @ A.T + b
            full, _ = trimesh.remesh.subdivide_to_size(q, f, max_edge=rq.SAMPLE_MM, max_iter=20)
            want = float(rq._cyl_dist(full, R, h).min())
            got = rq._min_dist_sampled(q, f, lambda p: rq._cyl_dist(p, R, h))
            assert got == pytest.approx(want, abs=1e-9)
            got = rq._min_dist_sampled(v, f, lambda p: rq._cyl_dist(p, R, h), move=lambda p: p @ A.T + b, memo=memo)
            assert got == pytest.approx(want, abs=1e-9)                 # own frame + memo shared across placements
