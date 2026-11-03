"""size_max `include`: the bounding box of only the named items (e.g. the body with the wings off, for a case)."""
import pytest

from kerf import partcache, pipeline
from test_engine import _write_project

YAML = """
name: Size include test
parts:
  block: {file: parts/block.py}
  plate: {file: parts/plate.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
requirements:
  - {id: all, check: size_max, max_mm: [200, 200, 200]}
  - {id: body, check: size_max, max_mm: [30, 30, 10], include: [block]}
"""
BLOCK = """
from build123d import *
def build(ctx):
    ctx.rigid("top", Location((0, 0, 10)))
    return ctx.finish(Box(30, 30, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
PLATE = """
from build123d import *
def build(ctx):
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(Box(80, 30, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""


def test_include_measures_only_the_named_items(tmp_path, monkeypatch):
    monkeypatch.setattr(partcache, "DIR", tmp_path / "cache")
    proj = str(_write_project(tmp_path / "sz", YAML, {"block": BLOCK, "plate": PLATE}))
    r = {x["id"]: x for x in pipeline.run_requirements(proj)["results"]}
    assert r["all"]["value"] == pytest.approx([80, 30, 14], abs=0.2)
    assert r["body"]["value"] == pytest.approx([30, 30, 10], abs=0.2) and r["body"]["ok"]
