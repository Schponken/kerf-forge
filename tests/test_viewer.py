"""The assembly viewer reproduces the engine's kinematics: each moving joint's axis is measured from solve(), and moving
it in the page must move exactly the items the engine moves, to the same place."""
import base64
import json
import re
import textwrap

import numpy as np
import pytest

from kerf import assembly as A, project as P, viewer

YAML = """
name: Slide and hinge
parts:
  base: {file: parts/base.py}
  carriage: {file: parts/carriage.py}
  flap: {file: parts/flap.py}
assembly:
  root: base
  joints:
    - {parent: base.rail, child: carriage.mount, name: slide, range: [0, 40]}
    - {parent: carriage.hinge, child: flap.pin, name: tilt, range: [-30, 60], home: 10}
"""
BASE = """
from build123d import *
def build(ctx):
    ctx.linear("rail", Axis((0, 0, 10), (1, 0, 0)), range=(0, 40))
    return ctx.finish(Box(100, 30, 10, align=(Align.MIN, Align.CENTER, Align.MIN)))
"""
CARRIAGE = """
from build123d import *
def build(ctx):
    ctx.rigid("mount", Location((0, 0, 0)))
    ctx.revolute("hinge", Axis((10, 0, 20), (0, 1, 0)), range=(-30, 60))
    return ctx.finish(Box(20, 30, 20, align=(Align.MIN, Align.CENTER, Align.MIN)))
"""
FLAP = """
from build123d import *
def build(ctx):
    ctx.rigid("pin", Location((0, 0, 0)))
    return ctx.finish(Pos(0, 0, 1) * Box(4, 20, 30, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""


@pytest.fixture()
def proj(tmp_path):
    d = tmp_path / "p"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    for n, src in {"base": BASE, "carriage": CARRIAGE, "flap": FLAP}.items():
        (d / "parts" / f"{n}.py").write_text(textwrap.dedent(src))
    pr = P.build(P.load(str(d)))
    assert not {k: v.error for k, v in pr.items.items() if v.error}
    return pr


def _apply(j, v, pts):
    """The page's joint motion (kerf/assets/viewer.html jointMatrix), in numpy."""
    d = v - j["home"]
    if j["kind"] == "linear":
        return pts + np.array(j["axis"]) * d * j.get("scale", 1)
    a, p, th = np.array(j["axis"]), np.array(j["point"]), np.radians(d)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K
    return (pts - p) @ R.T + p


def _verts(item):
    return np.frombuffer(base64.b64decode(item["verts"]), dtype=np.float32).reshape(-1, 3).astype(float)


def test_page_kinematics_match_engine(proj):
    asm = A.plan(proj)
    d = viewer.data(proj, asm, {"project": "t", "problems": []})
    J = {j["name"]: j for j in d["joints"]}
    assert J["slide"]["kind"] == "linear" and J["tilt"]["kind"] == "revolute"
    assert sorted(J["slide"]["moves"]) == ["carriage", "flap"] and J["tilt"]["moves"] == ["flap"]
    items = {i["id"]: i for i in d["items"]}
    assert items["flap"]["joints"] == ["slide", "tilt"] and items["base"]["joints"] == []
    # pose the engine and the page the same way and compare every flap vertex
    pose = {"slide": 25.0, "tilt": 45.0}
    page = _apply(J["slide"], pose["slide"], _apply(J["tilt"], pose["tilt"], _verts(items["flap"])))
    A.solve(asm, pose)
    eng, _ = viewer.mesh(proj.items["flap"].shape)
    assert page.shape == eng.shape
    assert np.abs(page - eng).max() < 1e-3
    A.solve(asm)


def test_html_is_self_contained(proj, tmp_path):
    asm = A.plan(proj)
    out = viewer.write(proj, asm, {"project": "t </script> & <b>", "problems": []}, tmp_path / "v.html")
    s = out.read_text()
    assert "/*KV3*/" not in s and "/*DATA*/" not in s and "{{TITLE}}" not in s
    assert not re.search(r"""(src|href)=["']https?://""", s)          # no network resources
    data = s.split('id="kerf-data">', 1)[1].split("</script>", 1)[0]  # the data block ends at the real tag
    assert json.loads(data)["report"]["project"] == "t </script> & <b>"
