"""Per-part build cache (kerf/partcache.py): an unchanged part is a hit with identical geometry and metadata; a param
the part reads, its source, a helper it imports, a catalog entry it read, or the engine changing is a miss."""
import json

import pytest

from kerf import catalog, partcache, pipeline, project as P
from test_engine import _write_project

YAML = """
name: Cache test
params: {w: 30, h: 20, unused: 1}
parts:
  block: {file: parts/block.py}
  plate: {file: parts/plate.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
"""
BLOCK = """
from build123d import *
from kerf import iface
import importlib.util as _iu, pathlib as _pl
_s = _iu.spec_from_file_location("cache_helper", _pl.Path(__file__).with_name("helper.py"))
helper = _iu.module_from_spec(_s); _s.loader.exec_module(helper)
def build(ctx):
    p = ctx.p
    s = Box(p.w, p.w, p.h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = s - Pos(0, 0, p.h) * Cylinder(helper.R, 4)
    s -= iface.bolt_pattern(ctx, "g", "M3", iface.rect(16, 0), Location((0, 0, p.h)), kind="heatset", depth=8)
    ctx.rigid("top", Location((0, 0, p.h)))
    ctx.revolute("spin", Axis((0.1, 0.2, 0.3), (0, 0, 1)), range=(-30, 45))
    ctx.notes.append("a note")
    return ctx.finish(s, color=(0.2, 0.4, 0.6))
"""
PLATE = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(30, 30, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "g", "M3", iface.rect(16, 0), Location((0, 0, 4)), kind="clearance", depth=4)
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(s)
"""


@pytest.fixture
def proj_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(partcache, "DIR", tmp_path / "cache")
    monkeypatch.delenv("KERF_NO_CACHE", raising=False)
    d = _write_project(tmp_path / "cp", YAML, {"block": BLOCK, "plate": PLATE})
    (d / "parts" / "helper.py").write_text("R = 3.0\n")
    return d


def _build(d, **ov):
    return P.build(P.load(str(d), ov or None))


def _sig(sh):
    bb = sh.bounding_box()
    return (round(sh.volume, 9), tuple(round(v, 9) for v in (*bb.min, *bb.max)), len(sh.faces()), len(sh.edges()))


def test_unchanged_part_is_a_hit_with_identical_geometry(proj_dir):
    a = _build(proj_dir)
    assert not any(it.cached for it in a.printed.values())
    b = _build(proj_dir)
    assert all(it.cached for it in b.printed.values())
    x, y = a.items["block"].shape, b.items["block"].shape
    assert _sig(x) == _sig(y)
    assert y.label == "block" and y.kerf_notes == ["a note"] and tuple(y.color) == tuple(x.color)
    assert [(s.group, s.role, s.screw, s.kind, s.engage) for s in y.kerf_sites] == \
           [(s.group, s.role, s.screw, s.kind, s.engage) for s in x.kerf_sites]
    for s, t in zip(x.kerf_sites, y.kerf_sites):     # locations survive exactly (build123d's pickle is float32)
        assert (s.loc.position - t.loc.position).length == 0.0
        assert (s.loc.orientation - t.loc.orientation).length < 1e-12
    assert set(y.joints) == {"top", "spin"}
    j = [j for j in y.kerf_joints if j.label == "spin"][0]
    assert tuple(j.axis.position) == pytest.approx((0.1, 0.2, 0.3)) and j.range == (-30, 45)


def test_misses(proj_dir, monkeypatch):
    _build(proj_dir)
    p = _build(proj_dir, h=25)                                        # a param the part reads
    assert not p.items["block"].cached and p.items["block"].shape.bounding_box().max.Z == pytest.approx(25)
    (proj_dir / "parts" / "helper.py").write_text("R = 4.0\n")       # a helper the part imports
    assert not _build(proj_dir).items["block"].cached
    assert _build(proj_dir).items["block"].cached
    src = proj_dir / "parts" / "plate.py"                             # editing one part leaves the other a hit
    src.write_text(src.read_text().replace("Box(30, 30, 4", "Box(30, 30, 5"))
    q = _build(proj_dir)
    assert q.items["block"].cached and not q.items["plate"].cached
    monkeypatch.setattr(partcache, "_ENGINE", "different-engine")     # engine change
    assert not any(it.cached for it in _build(proj_dir).printed.values())
    monkeypatch.setenv("KERF_NO_CACHE", "1")                          # kerf verify
    assert not any(it.cached for it in _build(proj_dir).printed.values())


def test_param_test_is_honest(proj_dir):
    """The plan's case 'editing a param that the part reads = miss' holds; an unread param is a miss too (whole-params key)."""
    _build(proj_dir)
    assert not _build(proj_dir, unused=2).items["block"].cached


def test_catalog_entry_the_part_read_is_a_miss(proj_dir, tmp_path, monkeypatch):
    def cat(edit=None):
        data = json.loads(catalog.CATALOG.read_text())
        if edit:
            edit(data)
        f = tmp_path / f"cat_{len(list(tmp_path.glob('cat_*')))}.json"
        f.write_text(json.dumps(data))
        monkeypatch.setattr(catalog, "CATALOG", f)
        catalog.load.cache_clear()
    try:
        cat()
        _build(proj_dir)
        cat(lambda c: c["servos"]["SG90"].update(weight_g=99))         # unrelated entry: hit
        assert _build(proj_dir).items["block"].cached
        cat(lambda c: c["screws"]["M3"].update(note="edited"))         # the screw entry iface read: miss
        assert not _build(proj_dir).items["block"].cached
    finally:
        catalog.load.cache_clear()


def test_check_report_identical_from_cache(proj_dir):
    cold = pipeline.run(str(proj_dir), sweeps=False)
    warm = pipeline.run(str(proj_dir), sweeps=False)
    assert cold["cached_parts"] == [] and sorted(warm["cached_parts"]) == ["block", "plate"]
    for r in (cold, warm):
        for v in r["parts"].values():
            v.pop("build_ms")                           # wall time, not a result
    for k in ("ok", "problems", "warnings", "parts", "assembly", "requirements"):
        assert json.dumps(cold[k], sort_keys=True, default=str) == json.dumps(warm[k], sort_keys=True, default=str), k


def test_prune_keeps_newest(tmp_path, monkeypatch):
    import os
    monkeypatch.setattr(partcache, "DIR", tmp_path)
    for i in range(30):
        f = tmp_path / f"e{i}.pkl"
        f.write_bytes(b"x")
        os.utime(f, (i, i))
    partcache.prune(keep=10)
    assert sorted(int(f.stem[1:]) for f in tmp_path.glob("*.pkl")) == list(range(20, 30))


def test_attribution_traces_fresh_build_even_when_cached(proj_dir):
    """kerf/attribution.py traces build() line by line, so it must bypass the cache."""
    from kerf import attribution
    _build(proj_dir)
    _build(proj_dir)                                    # warm
    a = attribution.compute(_build(proj_dir))["block"]
    assert a["faces"] and all(f["line"] for f in a["faces"])
