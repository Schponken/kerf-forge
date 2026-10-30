"""channel_clear: a declared internal channel is open end to end. Known answers by hand."""
import math
import textwrap

import pytest

from kerf import assembly as A, project as P, requirements as R

YAML = """
name: c
parts:
  base: {file: parts/base.py}
  gate: {file: parts/gate.py}
assembly:
  root: base
  joints: [{parent: base.slide, child: gate.mount, name: slide, range: [0, 12]}]
"""
BASE = """
from build123d import *
def build(ctx):
    s = Box(30, 12, 10, align=(Align.MIN, Align.CENTER, Align.MIN))
    s -= Pos(-1, 0, 5) * Rot(0, 90, 0) * Cylinder(1.0, 32, align=(Align.CENTER, Align.CENTER, Align.MIN))   # 2 mm channel along X
    s -= Pos(15, 0, 5) * Box(2.4, 13, 3.0)                                    # a slot across it for the gate
    ctx.linear("slide", Axis((15, -14, 5), (0, 1, 0)), range=(0, 20))
    return ctx.finish(s)
"""
GATE = """
from build123d import *
def build(ctx):
    s = Box(2.0, 6, 2.6, align=(Align.CENTER, Align.MAX, Align.CENTER))       # thin blade, ends at its mount
    ctx.rigid("mount", Location((0, 0, 0)))
    return ctx.finish(s)
"""
PATH = [{"item": "base", "at": [0, 0, 5]}, {"item": "base", "at": [30, 0, 5]}]


@pytest.fixture(scope="module")
def asm(tmp_path_factory):
    d = tmp_path_factory.mktemp("ch")
    (d / "parts").mkdir()
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "base.py").write_text(textwrap.dedent(BASE))
    (d / "parts" / "gate.py").write_text(textwrap.dedent(GATE))
    proj = P.build(P.load(str(d)))
    assert not {k: v.error for k, v in proj.items.items() if v.error}
    a = A.plan(proj)
    A.solve(a)
    return proj, a


def test_open_channel_measures_its_bore(asm):
    proj, a = asm
    r = R.channel_clear(proj, a, PATH, 1.8)
    assert r["ok"] and r["value"] == pytest.approx(2.0, abs=0.01)       # the drilled 2 mm bore


def test_too_big_a_tendon_is_blocked(asm):
    proj, a = asm
    r = R.channel_clear(proj, a, PATH, 2.2)
    assert not r["ok"] and r["value"] == pytest.approx(2.0, abs=0.01)
    # hand: ring between d 2.2 and 2.0 over 30 mm, minus the 2.4 mm slot it crosses = pi (1.1^2 - 1^2) (30 - 2.4)
    hand = math.pi * (1.1 ** 2 - 1.0 ** 2) * (30 - 2.4)
    vol = float(r["detail"].split("{'base': ")[1].split("}")[0])
    assert vol == pytest.approx(hand, rel=0.01)


def test_a_part_moving_into_the_channel_is_caught_at_that_pose(asm):
    proj, a = asm
    # gate blade spans y in [mount - 6, mount]; mount starts at y = -14 and slides +y. Home: blade y in [-20, -14],
    # clear. At slide = 12 the blade spans [-8, -2]: still clear of the 2 mm bore (|y| <= 1). At slide 18 it would
    # cut it: the check follows whatever poses are declared.
    assert R.channel_clear(proj, a, PATH, 1.8, poses=[{"slide": 12}])["ok"]
    r = R.channel_clear(proj, a, PATH, 1.8, poses=[{"slide": 18}])
    assert not r["ok"] and r["value"] == pytest.approx(0.0, abs=0.01) and "gate" in r["detail"]
    r = R.channel_clear(proj, a, PATH, 1.8, poses=[{"slide": 18}], ignore=["gate"])
    assert r["ok"]


def test_runs_from_project_yaml(asm):
    proj, a = asm
    proj.data["requirements"] = [{"id": "tendon", "check": "channel_clear", "path": PATH, "diameter": 1.5}]
    out = R.run_all(proj, a)
    assert out[0]["ok"] and out[0]["value"] == pytest.approx(2.0, abs=0.01)
    proj.data["requirements"] = []
