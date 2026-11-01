"""Feature intent ledger: ctx.add / ctx.cut record what each feature is and why, iface features register themselves
(one row per interface group and hole type), the ledger reaches report.json and survives the build cache, and the
after-edit lint flags body booleans that explain nothing."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from build123d import Box, Location, Pos

from kerf import intent, iface, partcache, pipeline
from kerf.ctx import Ctx, PartError
from test_engine import _write_project

ROOT = Path(__file__).resolve().parent.parent


def test_ctx_add_cut_and_iface_rows():
    ctx = Ctx("p", {}, {"spec": {}})
    body = Box(40, 20, 6)
    body += ctx.add(Pos(0, 0, 4) * Box(30, 2, 4), why="stiffens the plate against bending about Y", kind="rib")
    body -= ctx.cut(Pos(10, 0, 0) * Box(2, 4, 10), why="cable tie around the servo lead", kind="tie slot")
    body -= iface.bolt_pattern(ctx, "lid", "M3", iface.rect(30, 10), Location((0, 0, 3)), kind="clearance", depth=6)
    sh = ctx.finish(body)
    rows = sh.kerf_features
    assert [(r["op"], r["kind"]) for r in rows] == [("add", "rib"), ("cut", "tie slot"), ("cut", "fastener hole")]
    assert rows[0]["why"].startswith("stiffens") and rows[0]["volume_mm3"] == pytest.approx(240)
    assert rows[2]["count"] == 4 and "'lid'" in rows[2]["why"] and rows[2]["source"] == "iface"
    json.dumps(rows)                                                  # report.json-safe
    with pytest.raises(PartError, match="why="):
        ctx.add(Box(1, 1, 1), why="  ")


PART = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(30, 30, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s += ctx.add(Pos(0, 0, 6) * Box(30, 2, 5, align=(Align.CENTER, Align.CENTER, Align.MIN)), why="rib against bending", kind="rib")
    s -= iface.bolt_pattern(ctx, "g", "M3", iface.rect(20, 20), Location((0, 0, 6)), kind="clearance", depth=6)
    ctx.rigid("top", Location((0, 0, 6)))
    return ctx.finish(s)
"""
YAML = """
name: Intent test
params: {}
parts:
  plate: {file: parts/plate.py}
assembly:
  root: plate
  joints: []
"""


def test_ledger_in_report_and_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(partcache, "DIR", tmp_path / "cache")
    monkeypatch.delenv("KERF_NO_CACHE", raising=False)
    d = _write_project(tmp_path / "ip", YAML, {"plate": PART})
    cold = pipeline.run(str(d), sweeps=False)
    warm = pipeline.run(str(d), sweeps=False)
    assert warm["cached_parts"] == ["plate"]
    for rep in (cold, warm):
        rows = rep["parts"]["plate"]["features"]
        assert [r["kind"] for r in rows] == ["rib", "fastener hole"] and rows[1]["count"] == 4
    viewer = (ROOT / "kerf" / "assets" / "viewer.html").read_text(encoding="utf-8")
    assert "p.features" in viewer


def test_unexplained_booleans():
    src = '''
from build123d import *
from kerf import iface
def build(ctx):
    body = Box(10, 10, 10)
    n = 0
    n += 1                                              # not the body: ignored
    body += Pos(0, 0, 5) * Box(2, 2, 2)                 # boss
    # why: the strap's tension pulls here
    body += Pos(5, 0, 5) * Box(2, 2, 2)
    body -= Pos(0, 0, 0) * Box(1, 1, 30)  # why: drain hole for the resin
    body -= iface.bolt_pattern(ctx, "g", "M3", [(0, 0)], Location((0, 0, 10)), kind="clearance", depth=10)
    body += ctx.add(Box(1, 1, 1), why="x", kind="y")
    body = body + Box(3, 3, 3)
    return ctx.finish(body)
'''
    miss = intent.unexplained(src)
    assert [l for _, l in miss] == ["body += Pos(0, 0, 5) * Box(2, 2, 2)                 # boss", "body = body + Box(3, 3, 3)"]


def test_after_edit_hook_reports_unexplained(tmp_path):
    """The hook names the lines (as context, without blocking) after a part edit."""
    proj = ROOT / "projects" / "servo_link" / "parts" / "arm.py"
    data = json.dumps({"tool_input": {"file_path": str(proj)}})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
    r = subprocess.run([sys.executable, str(ROOT / ".claude" / "hooks" / "after_edit.py")], input=data, text=True,
                       capture_output=True, env=env, timeout=900)
    miss = intent.unexplained(proj.read_text(encoding="utf-8"))
    if miss:
        out = r.stdout + r.stderr
        assert "Design intent" in out and f"line {miss[0][0]}" in out
    else:
        assert "Design intent" not in r.stdout
