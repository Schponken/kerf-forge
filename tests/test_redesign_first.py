"""Check in order of redesign cost (Spencer, 2026-11-02): concept requirements, then structure of the most connected
parts, before any detail check; a failure there stops the run before the detail checks unless --all."""
from types import SimpleNamespace

import pytest

from kerf import partcache, pipeline, requirements
from test_engine import _write_project
from test_req_cmd import BLOCK, PLATE


def test_redesign_order():
    proj = SimpleNamespace(data={"assembly": {"joints": [
        {"parent": "frame.a", "child": "arm.b"}, {"parent": "frame.c", "child": "leg.d"}, {"parent": "arm.e", "child": "tip.f"}]}})
    reqs = [{"id": "gap", "check": "clearance_min"},
            {"id": "tip_fea", "check": "fea_static", "part": "tip"},
            {"id": "frame_fea", "check": "fea_static", "part": "frame"},
            {"id": "weight", "check": "mass_max"},
            {"id": "arm_fea", "check": "fea_static", "part": "arm"}]
    assert [r["id"] for r in requirements.redesign_order(proj, reqs)] == \
        ["weight", "frame_fea", "arm_fea", "tip_fea", "gap"]
    assert requirements.redesign_tier({"check": "hard_stop"}) is None


YAML = """
name: Redesign test
params: {w: 30}
parts:
  block: {file: parts/block.py}
  plate: {file: parts/plate.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
requirements:
  - {id: tall, check: size_max, max_mm: [200, 200, 200]}
  - {id: weight, check: mass_max, max_g: MAXG}
"""


def _proj(tmp_path, monkeypatch, max_g):
    monkeypatch.setattr(partcache, "DIR", tmp_path / "cache")
    return str(_write_project(tmp_path / f"rd{max_g}", YAML.replace("MAXG", str(max_g)), {"block": BLOCK, "plate": PLATE}))


def test_redesign_level_failure_stops_before_detail_checks(tmp_path, monkeypatch):
    p = _proj(tmp_path, monkeypatch, 1)
    r = pipeline.run(p, sweeps=False)
    assert not r["ok"] and r.get("stopped_early")
    assert "interference" not in r["assembly"] and not r["parts"]          # no print / fit checks were spent
    assert any("requirement 'weight' failed" in x for x in r["problems"])
    assert any("stopped before the detail checks" in x for x in r["problems"])
    assert "FAIL" in pipeline.summary(r)
    full = pipeline.run(p, sweeps=False, everything=True)                  # --all
    assert not full["ok"] and not full.get("stopped_early") and "interference" in full["assembly"] and full["parts"]
    assert [x["id"] for x in full["requirements"]] == ["tall", "weight"]


def test_passing_design_runs_everything_once(tmp_path, monkeypatch):
    r = pipeline.run(_proj(tmp_path, monkeypatch, 500), sweeps=False)
    assert r["ok"] and not r.get("stopped_early") and "interference" in r["assembly"]
    assert sorted(x["id"] for x in r["requirements"]) == ["tall", "weight"]  # each requirement exactly once
