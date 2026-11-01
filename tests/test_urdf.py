"""URDF export (kerf/urdf.py): valid per cadgen's validator, loads in PyBullet, and PyBullet's forward kinematics put
every link where Kerf's own joint solver puts its items, for revolute, prismatic and geared (mimic) joints."""
import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from build123d import Location

from kerf import assembly as A, project as P, urdf
from test_engine import _write_project

YAML = """
name: URDF test
params: {}
parts:
  base: {file: parts/base.py}
  arm: {file: parts/arm.py}
  slider: {file: parts/slider.py}
  lid: {file: parts/lid.py}
  gear: {file: parts/gear.py}
assembly:
  root: base
  joints:
    - {parent: base.pivot, child: arm.hub, name: swing, range: [-90, 90]}
    - {parent: arm.rail, child: slider.mount, name: slide, range: [0, 30]}
    - {parent: base.top, child: lid.bottom}
    - {parent: base.gear_axle, child: gear.hub, name: gear_turn, range: [-180, 180]}
  sweeps:
    - {joint: gear_turn, follows: swing, ratio: -0.5}
"""
BASE = """
from build123d import *
def build(ctx):
    s = Box(40, 20, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.revolute("pivot", Axis((5, 0, 10), (0, 1, 0)), range=(-90, 90))
    ctx.revolute("gear_axle", Axis((-15, 0, 10), (0, 0, 1)), range=(-180, 180))
    ctx.rigid("top", Location((-15, 5, 10), (0, 0, 30)))
    return ctx.finish(s)
"""
ARM = """
from build123d import *
def build(ctx):
    s = Pos(0, 0, 2) * Box(60, 6, 4, align=(Align.MIN, Align.CENTER, Align.CENTER))
    ctx.rigid("hub", Location((0, 0, 0)))
    ctx.linear("rail", Axis((10, 0, 4), (1, 0, 0)), range=(0, 30))
    return ctx.finish(s)
"""
SLIDER = """
from build123d import *
def build(ctx):
    s = Box(8, 8, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("mount", Location((0, 0, 0)))
    return ctx.finish(s)
"""
LID = """
from build123d import *
def build(ctx):
    s = Box(6, 6, 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(s)
"""
GEAR = """
from build123d import *
def build(ctx):
    s = Pos(4, 0, 0) * Cylinder(6, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("hub", Location((0, 0, 0)))
    return ctx.finish(s)
"""


@pytest.fixture
def written(tmp_path):
    d = _write_project(tmp_path / "u", YAML, {"base": BASE, "arm": ARM, "slider": SLIDER, "lid": LID, "gear": GEAR})
    proj = P.build(P.load(str(d)))
    out = tmp_path / "out"
    out.mkdir()
    return proj, out, urdf.write(proj, out, masses={"base": 50, "arm": 20, "slider": 5, "lid": 2, "gear": 3})


def test_structure_and_validation(written):
    proj, out, r = written
    assert r["findings"] == [] or all(sev != "error" for sev, _, _ in r["findings"]), r["findings"]
    root = ET.parse(out / r["path"]).getroot()
    links = {l.get("name"): l for l in root.iter("link")}
    assert set(links) == {"base", "arm", "slider", "gear"}                 # lid is rigid: merged into base
    assert {v.get("name") for v in links["base"].iter("visual")} == {"base", "lid"}
    assert float(links["base"].find("inertial/mass").get("value")) == pytest.approx(0.052)
    joints = {j.get("name"): j for j in root.iter("joint")}
    assert joints["swing"].get("type") == "revolute" and joints["slide"].get("type") == "prismatic"
    lim = joints["swing"].find("limit")
    assert float(lim.get("lower")) == pytest.approx(-math.pi / 2) and float(lim.get("upper")) == pytest.approx(math.pi / 2)
    assert float(joints["slide"].find("limit").get("upper")) == pytest.approx(0.030)
    m = joints["gear_turn"].find("mimic")
    assert m.get("joint") == "swing" and float(m.get("multiplier")) == pytest.approx(-0.5)
    for l in links.values():                                              # every mesh file exists
        for mesh in l.iter("mesh"):
            assert (out / mesh.get("filename")).exists()


def _kerf_point(proj, asm, item, values, local):
    A.solve(asm, values)
    p = (proj.items[item].shape.location * Location(local)).position
    return np.array([p.X, p.Y, p.Z]) / 1000.0


def test_pybullet_forward_kinematics_match_kerf(written):
    import pybullet                                  # a pyproject dependency: missing = fail, never skip
    proj, out, r = written
    asm = A.plan(proj)
    cid = pybullet.connect(pybullet.DIRECT)
    try:
        body = pybullet.loadURDF(str(out / r["path"]), useFixedBase=True, physicsClientId=cid)
        idx = {pybullet.getJointInfo(body, i, physicsClientId=cid)[1].decode(): i
               for i in range(pybullet.getNumJoints(body, physicsClientId=cid))}
        assert set(idx) == {"swing", "slide", "gear_turn"}
        _, _, meta = urdf.build(proj)
        for swing, slide in [(0, 0), (30, 10), (-60, 25), (90, 30)]:
            vals = {"swing": swing, "slide": slide, "gear_turn": -0.5 * swing}
            for j, v in vals.items():
                q = math.radians(v) if j != "slide" else v / 1000.0
                pybullet.resetJointState(body, idx[j], q, physicsClientId=cid)
            for item in ("arm", "slider", "gear"):
                link = meta["link_of"][item]
                o = np.array(meta["origin_mm"][link])
                for local in [(0, 0, 0), (7, 3, 2)]:              # points on the item, in its own frame
                    A.solve(asm, {})                              # zero pose: link frame = assembly frame + origin
                    want0 = _kerf_point(proj, asm, item, {k: 0.0 for k in vals}, local) * 1000.0 - o
                    pos, orn = pybullet.getLinkState(body, idx[{"arm": "swing", "slider": "slide", "gear": "gear_turn"}[item]],
                                                     computeForwardKinematics=True, physicsClientId=cid)[4:6]
                    R = np.array(pybullet.getMatrixFromQuaternion(orn)).reshape(3, 3)
                    got = np.array(pos) + R @ (want0 / 1000.0)
                    want = _kerf_point(proj, asm, item, vals, local)
                    assert np.allclose(got, want, atol=1e-6), (item, vals, local, got, want)
    finally:
        pybullet.disconnect(cid)
        A.solve(asm)


def test_zip_and_studio_listing(written, tmp_path, monkeypatch):
    import zipfile
    from kerf import studio
    proj, out, r = written
    names = set(zipfile.ZipFile(out / r["zip"]).namelist())
    assert r["path"] in names and {f"urdf_meshes/{i}.stl" for i in ("base", "arm", "slider", "lid", "gear")} <= names
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(studio, "TRIALS", tmp_path / "trials")
    d = tmp_path / "projects" / "p"
    (d / "out").mkdir(parents=True)
    (d / "project.yaml").write_text("name: P\nparts: {}\nassembly: {}\n")
    (d / "out" / "p_urdf.zip").write_bytes(b"PK")
    assert "out/p_urdf.zip" in studio.detail("p")["files"]
