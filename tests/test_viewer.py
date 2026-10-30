"""Assembly viewer: the page must pose every part exactly like the joint solver, with no network and no JS errors."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from kerf import assembly as A, project as P, viewer

from test_engine import _write_project

# A chain with both joint kinds, a tilted revolute axis and non-zero homes: base -slide-> carriage -tilt-> arm
CHAIN_YAML = """
name: Viewer chain
params: {}
parts:
  base: {file: parts/base.py}
  carriage: {file: parts/carriage.py}
  arm: {file: parts/arm.py}
assembly:
  root: base
  joints:
    - {parent: base.rail, child: carriage.shoe, name: slide, range: [0, 40], home: 10}
    - {parent: carriage.pivot, child: arm.hub, name: tilt, range: [-60, 75], home: 15}
"""
CHAIN_BASE = """
from build123d import *
def build(ctx):
    ctx.linear("rail", Axis((-20, 0, 10), (1, 0, 0)), range=(0, 40))
    return ctx.finish(Box(80, 20, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
CHAIN_CARRIAGE = """
from build123d import *
def build(ctx):
    ctx.rigid("shoe", Location((0, 0, 0)))
    ctx.revolute("pivot", Axis((0, 0, 30), (1, 1, 1)), range=(-60, 75))
    return ctx.finish(Box(16, 16, 30, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
CHAIN_ARM = """
from build123d import *
def build(ctx):
    ctx.rigid("hub", Location((0, 0, 0)))
    return ctx.finish(Pos(0, 0, 3) * Box(50, 6, 6, align=(Align.MIN, Align.CENTER, Align.CENTER)))
"""
POSES = [{}, {"slide": 0}, {"slide": 40, "tilt": -60}, {"slide": 27.5, "tilt": 75}, {"tilt": 0}]


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    d = _write_project(tmp_path_factory.mktemp("v") / "chain", CHAIN_YAML,
                       {"base": CHAIN_BASE, "carriage": CHAIN_CARRIAGE, "arm": CHAIN_ARM})
    proj = P.build(P.load(str(d)))
    assert all(it.error is None for it in proj.items.values()), [it.error for it in proj.items.values()]
    asm = A.plan(proj)
    return proj, asm, viewer.model(proj, asm, {"ok": True, "fingerprint": "test"})


def test_measured_joints(chain):
    _, _, data = chain
    j = {x["name"]: x for x in data["joints"]}
    assert j["slide"]["kind"] == "linear" and j["tilt"]["kind"] == "revolute"
    assert np.allclose(j["slide"]["axis"], [1, 0, 0], atol=1e-9)
    assert np.allclose(np.abs(j["tilt"]["axis"]), np.ones(3) / np.sqrt(3), atol=1e-9)   # unit axis, any sign convention


def test_fk_matches_solver(chain):
    proj, asm, data = chain
    for pose in POSES:
        A.solve(asm, pose)
        want = viewer._world(proj)
        got = viewer.fk(data, pose)
        for iid in want:
            assert np.abs(got[iid] - want[iid]).max() < 1e-6, (pose, iid)
    A.solve(asm)


def test_meshes_are_local_and_complete(chain):
    proj, _, data = chain
    for it in data["items"]:
        n = len(np.frombuffer(viewer.base64.b64decode(it["pos"]), "<f4")) // 3
        f = np.frombuffer(viewer.base64.b64decode(it["idx"]), "<u4")
        assert n == it["nv"] and len(f) == 3 * it["nt"] and f.max() < n


def test_page_in_browser(chain, tmp_path):
    """Open the real page headlessly, drive the sliders through the test hook, compare part poses to the solver."""
    proj, asm, data = chain
    html = tmp_path / "viewer.html"
    html.write_text(viewer.page(data))
    assert "<script src" not in html.read_text()          # everything inline; viewer_check also fails on any network request
    poses = [{"name": f"p{k}", "joints": p} for k, p in enumerate(POSES)] + [{"name": "exp", "explode": 1, "theme": "dark"},
                                                                          {"name": "phone", "width": 390, "height": 844}]
    r = subprocess.run(["node", str(viewer.RENDER_DIR / "viewer_check.mjs"), str(html), str(tmp_path / "shot"), json.dumps(poses)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == []
    for k, pose in enumerate(POSES):
        want = viewer.fk(data, pose)
        for iid, m in out["poses"][f"p{k}"]["world"].items():
            got = np.array(m).reshape(4, 4).T                     # three.js stores column-major
            assert np.abs(got - want[iid]).max() < 1e-3, (pose, iid)  # float32 on the page
    for name in ("p0", "exp", "phone"):
        assert (tmp_path / f"shot_{name}.png").stat().st_size > 20000
