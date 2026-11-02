"""Placeholder parts during design (ctx.stub / a STUB file): the report says "design in progress" once instead of
listing every collision with the placeholder solid (the Hawk-fold contract showed 64 'problems' that were all stubs)."""
from kerf import pipeline
from test_engine import _write_project

BLOCK = '''{doc}
from build123d import *
def build(ctx):
    {stub}ctx.rigid("in", Location((0, 0, 0)))
    return ctx.finish(Box(40, 40, 40))
'''
INNER = '''
from build123d import *
def build(ctx):
    ctx.rigid("at", Location((0, 0, 0)))
    return ctx.finish(Box(10, 10, 10))
'''
Y = """
name: Stub test
params: {}
parts:
  shell: {file: parts/shell.py}
  core: {file: parts/core.py}
  other: {file: parts/other.py}
assembly:
  root: shell
  joints:
    - {parent: shell.in, child: core.at}
    - {parent: shell.in, child: other.at}
"""


def test_stub_collisions_fold_into_one_design_in_progress_problem(tmp_path):
    for i, (doc, stub) in enumerate([('"""STUB shell."""', ""), ("", 'ctx.stub("fuselage not modelled yet")\n    ')]):
        d = _write_project(tmp_path / f"s{i}", Y, {"shell": BLOCK.format(doc=doc, stub=stub), "core": INNER, "other": INNER})
        rep = pipeline.run(str(d), mode="sketch")
        assert rep["stubs"] == ["shell"]
        assert rep["problems"][0].startswith("design in progress: 1 of 3 printed parts are still placeholders (shell)")
        assert any("shell" in p and "overlap" in p for p in rep["stub_problems"])
        assert any(p.startswith("core and other overlap") or p.startswith("other and core overlap") for p in rep["problems"])  # real ones stay
        assert not rep["ok"]


def test_no_stubs_no_fold(tmp_path):
    d = _write_project(tmp_path / "n", Y, {"shell": BLOCK.format(doc="", stub=""), "core": INNER, "other": INNER})
    rep = pipeline.run(str(d), mode="sketch")
    assert rep["stubs"] == [] and "stub_problems" not in rep and not rep["problems"][0].startswith("design in progress")
