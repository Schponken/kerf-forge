"""geom.overlap's fast paths (cached own-frame boxes + mesh prefilter) must give exactly what the exact B-rep boolean
gives: same hits, same volumes, at any placement, for shapes moved after their first use."""
import os

import numpy as np
import pytest
from build123d import Box, Cylinder, Location, Pos, Rot, Sphere

from kerf import geom


def _shapes():
    return [Box(20, 8, 5), Cylinder(4, 30), Sphere(6), Box(3, 3, 40) - Cylinder(1, 50),
            Rot(0, 30, 0) * Box(12, 12, 2)]


def _exact(a, b):
    os.environ["KERF_EXACT_OVERLAP"] = "1"
    try:
        return geom.overlap(a, b)
    finally:
        os.environ.pop("KERF_EXACT_OVERLAP", None)


def test_fast_paths_match_exact_at_random_placements():
    rng = np.random.default_rng(7)
    shapes = _shapes()
    n_hit = n_clear = 0
    for _ in range(60):
        i, j = rng.choice(len(shapes), 2, replace=False)
        a, b = shapes[i], shapes[j]
        for s in (a, b):                                   # move the SAME objects: cached data must follow
            s.location = Location(tuple(rng.uniform(-15, 15, 3)), tuple(rng.uniform(-180, 180, 3)))
        fast, exact = geom.overlap(a, b), _exact(a, b)
        assert fast == pytest.approx(exact, abs=1e-6), (i, j)
        n_hit += exact > geom.OVERLAP_TOL_MM3
        n_clear += exact == 0.0
    assert n_hit >= 10 and n_clear >= 10                   # the sample exercised both outcomes


def test_fast_box_contains_the_exact_box():
    rng = np.random.default_rng(3)
    for s in _shapes():
        for _ in range(8):
            s.location = Location(tuple(rng.uniform(-50, 50, 3)), tuple(rng.uniform(-180, 180, 3)))
            flo, fhi = geom._fast_box(s)
            elo, ehi = geom.bbox(s)
            assert np.all(flo <= elo + 1e-6) and np.all(fhi >= ehi - 1e-6)


def test_touching_and_near_misses():
    a = Box(10, 10, 10)
    assert geom.overlap(a, Pos(10, 0, 0) * Box(10, 10, 10)) == 0.0                 # face contact
    assert geom.overlap(a, Pos(10.5, 0, 0) * Box(10, 10, 10)) == 0.0               # gap
    assert geom.overlap(a, Pos(9.9, 0, 0) * Box(10, 10, 10)) == pytest.approx(10.0, rel=1e-6)   # 0.1 mm into it


def test_exact_switch_and_cache_follow_a_replaced_geometry():
    a = Box(10, 10, 10)
    b = Pos(5, 0, 0) * Box(10, 10, 10)
    assert geom.overlap(a, b) == pytest.approx(500, rel=1e-6)
    a.wrapped = (Box(4, 4, 4)).wrapped                     # same object, different solid: caches must notice
    assert geom.overlap(a, b) == pytest.approx(_exact(a, b), abs=1e-6)


def test_cached_shapes_can_still_be_copied_and_pickled():
    """The motion sweep deep-copies parts; the per-shape caches must not make that fail, and a copy must recompute."""
    import copy
    import pickle
    from build123d import Box, Pos
    a, b = Box(10, 10, 10), Pos(5, 0, 0) * Box(10, 10, 10)
    assert geom.overlap(a, b) > 0                        # fills both caches
    c = copy.deepcopy(a)
    d = copy.copy(a)
    pickle.loads(pickle.dumps(a._kerf_prefilter))
    c.location = Pos(30, 0, 0) * c.location
    assert geom.overlap(c, b) == 0.0
    assert geom.overlap(d, b) > 0


def test_mesh_gap_is_within_the_screen_of_the_exact_distance():
    """geom.mesh_gap (cached meshes, manifold3d min_gap) at random placements: within GAP_SCREEN_MM / 2 of OCC's
    exact distance, 0 when the shapes overlap, None for a shape without a closed mesh."""
    rng = np.random.default_rng(7)
    shapes = _shapes()
    n = 0
    for _ in range(40):
        i, j = rng.choice(len(shapes), 2, replace=False)
        a = Location(tuple(rng.uniform(-30, 30, 3)), tuple(rng.uniform(-180, 180, 3))) * shapes[i]
        b = Location(tuple(rng.uniform(-30, 30, 3)), tuple(rng.uniform(-180, 180, 3))) * shapes[j]
        g, ex = geom.mesh_gap(a, b), a.distance_to(b)
        assert g is not None and abs(g - ex) <= geom.GAP_SCREEN_MM / 2, (g, ex)
        n += ex > 0
    assert n >= 10


def test_clearance_min_screen_reports_the_exact_value(tmp_path, monkeypatch):
    """requirements.clearance_min screens poses on meshes: near the limit it measures exactly (same value as measuring
    every pose exactly); far above the limit it reports the mesh gap (within 2 x PREFILTER_DEFLECTION), labelled."""
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from test_engine import HINGE_BASE, HINGE_YAML, _write_project
    from kerf import assembly as A, project as P, requirements as rq
    arm = """
from build123d import *
def build(ctx):
    ctx.rigid("hub", Location((0, 0, 0)))
    return ctx.finish(Pos(15, 0, 2) * Box(40, 6, 4, align=(Align.MIN, Align.CENTER, Align.CENTER)))
"""
    d = _write_project(tmp_path / "h", HINGE_YAML, {"base": HINGE_BASE, "arm": arm})
    p = P.build(P.load(str(d)))
    asm = A.plan(p)
    A.solve(asm)
    real = geom.mesh_gap
    monkeypatch.setattr(geom, "mesh_gap", lambda a, b, search=1e4: None)          # every pose exact (the old path)
    exact = rq.clearance_min(p, asm, "arm", "base", 1.0)["value"]
    monkeypatch.setattr(geom, "mesh_gap", real)
    assert exact > 2.0                                                          # a real gap, well above 1 mm
    near = rq.clearance_min(p, asm, "arm", "base", exact)
    assert near["value"] == exact and "meshes" not in near["detail"]
    far = rq.clearance_min(p, asm, "arm", "base", 1.0)
    assert far["ok"] and abs(far["value"] - exact) <= 2 * geom.PREFILTER_DEFLECTION + 0.01 and "meshes" in far["detail"]
