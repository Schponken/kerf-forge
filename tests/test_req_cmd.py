"""`kerf req <p> [id ...]` (pipeline.run_requirements): only the named requirements, on the assembled project, with
the same results `kerf check` reports for them."""
import pytest

from kerf import cli, partcache, pipeline
from test_engine import _write_project

YAML = """
name: Req test
params: {w: 30}
parts:
  block: {file: parts/block.py}
  plate: {file: parts/plate.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
requirements:
  - {id: light, check: mass_max, max_g: 500}
  - {id: tiny, check: mass_max, max_g: 1}
  - {id: tall, check: size_max, max_mm: 200}
"""
BLOCK = """
from build123d import *
def build(ctx):
    ctx.rigid("top", Location((0, 0, 10)))
    return ctx.finish(Box(ctx.p.w, ctx.p.w, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
PLATE = """
from build123d import *
def build(ctx):
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(Box(30, 30, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.setattr(partcache, "DIR", tmp_path / "cache")
    return str(_write_project(tmp_path / "rq", YAML, {"block": BLOCK, "plate": PLATE}))


def test_only_the_named_requirements_run(proj):
    r = pipeline.run_requirements(proj, ["light"])
    assert [x["id"] for x in r["results"]] == ["light"] and r["ok"]
    r = pipeline.run_requirements(proj, ["mass_max"])                  # a check name selects every use of it
    assert [x["id"] for x in r["results"]] == ["light", "tiny"] and not r["ok"]
    assert len(pipeline.run_requirements(proj)["results"]) == 3          # none named: all


def test_same_numbers_as_the_full_check(proj):
    full = {x["id"]: x for x in pipeline.run(proj, sweeps=False)["requirements"]}
    for x in pipeline.run_requirements(proj)["results"]:
        assert x["value"] == pytest.approx(full[x["id"]]["value"]) and x["ok"] == full[x["id"]]["ok"]


def test_unknown_id_lists_what_exists(proj, capsys):
    r = pipeline.run_requirements(proj, ["nope"])
    assert not r["ok"] and "nope" in r["problems"][0] and "light" in r["problems"][0]
    assert cli.main(["req", proj, "tiny"]) == 1
    out = capsys.readouterr().out
    assert "tiny: BAD" in out and "1 requirement(s)" in out
