"""Engine tests with hand-calculated answers. Run: .venv/bin/pytest -q"""
import math
import textwrap
from pathlib import Path

import pytest
from build123d import Align, Axis, Box, Cylinder, Location, Pos

from kerf import assembly as A, geom, pipeline, project as P, requirements
from kerf.ctx import Ctx, Site


def test_overlap_exact():
    a = Box(10, 10, 10)
    b = Pos(5, 0, 0) * Box(10, 10, 10)
    assert geom.overlap(a, b) == pytest.approx(500, rel=1e-6)
    c = Pos(10, 0, 0) * Box(10, 10, 10)            # touching faces only
    assert geom.overlap(a, c) < geom.OVERLAP_TOL_MM3
    d = Pos(30, 0, 0) * Box(10, 10, 10)
    assert geom.overlap(a, d) == 0.0


def test_box_minus_cylinder_volume():
    s = Box(10, 10, 10) - Cylinder(4, 20)
    assert geom.volume(s) == pytest.approx(1000 - math.pi * 16 * 10, rel=1e-4)


def test_overhang_t_shape():
    post = Box(10, 10, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    top = Pos(0, 0, 20) * Box(40, 10, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    v, f = geom.mesh(post + top)
    area, frac, _ = geom.overhang(v, f, 45, bed_z=0)
    assert area == pytest.approx(300, rel=1e-3)      # 2 wings 15 x 10 underside


def test_thickness_plate():
    v, f = geom.mesh(Box(40, 40, 2))
    th = geom.thickness_samples(v, f, n=400)
    assert pytest.approx(2.0, abs=0.05) == float(sorted(th)[len(th) // 2])


def _write_project(tmp: Path, yaml_text: str, parts: dict):
    (tmp / "parts").mkdir(parents=True, exist_ok=True)
    (tmp / "project.yaml").write_text(textwrap.dedent(yaml_text))
    for name, src in parts.items():
        (tmp / "parts" / f"{name}.py").write_text(textwrap.dedent(src))
    return tmp


HINGE_YAML = """
name: Hinge test
params: {L: 60}
parts:
  base: {file: parts/base.py, material: PETG}
  arm: {file: parts/arm.py, material: PETG}
assembly:
  root: base
  joints:
    - {parent: base.pivot, child: arm.hub, name: swing, range: [-90, 90]}
requirements:
  - {id: t, check: static_torque, joint: swing, stall_kgcm: 10, max_fraction: 0.5, payload_g: 100, payload_at: arm.tip}
"""
HINGE_BASE = """
from build123d import *
def build(ctx):
    s = Box(20, 20, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.revolute("pivot", Axis((0, 0, 10), (0, 1, 0)), range=(-90, 90))
    return ctx.finish(s)
"""
HINGE_ARM = """
from build123d import *
def build(ctx):
    L = ctx.p.L
    s = Pos(0, 0, 2) * Box(L, 6, 4, align=(Align.MIN, Align.CENTER, Align.CENTER))
    ctx.rigid("hub", Location((0, 0, 0)))
    ctx.rigid("tip", Location((L, 0, 2)))
    return ctx.finish(s)
"""


def test_hinge_sweep_and_torque(tmp_path):
    d = _write_project(tmp_path / "hinge", HINGE_YAML, {"base": HINGE_BASE, "arm": HINGE_ARM})
    proj = P.build(P.load(str(d)))
    assert all(it.error is None for it in proj.items.values()), [it.error for it in proj.items.values()]
    asm = A.plan(proj)
    A.solve(asm)
    assert A.interference(asm) == []
    sw = A.sweeps(asm, samples=7)
    # swinging down to -90/+90 about Y drives the arm into the base block
    assert not sw[0]["clear"]
    r = requirements.run_all(proj, asm)[0]
    # worst case horizontal: payload 100 g at 60 mm + arm mass at ~30 mm
    arm_mass = requirements.item_mass_g(proj.items["arm"])
    expect = (0.1 * 60 + arm_mass / 1000 * 30) / 10  # kg*cm
    assert r["value"] == pytest.approx(expect, rel=0.03)


BOLT_YAML = """
name: Bolt test
params: {}
parts:
  plate: {file: parts/plate.py}
  block: {file: parts/block.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
"""
BOLT_BLOCK = """
from build123d import *
from kerf.ctx import Site
def build(ctx):
    s = Box(30, 30, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (-10, 10):
        ctx.site(Site("g", "female", "M3", "heatset", Location((x, 0, 20)), engage=6.2, min_engage=4.0))
    ctx.rigid("top", Location((0, 0, 20)))
    return ctx.finish(s)
"""
BOLT_PLATE = """
from build123d import *
from kerf.ctx import Site
def build(ctx):
    s = Box(30, 30, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (-10, 10):
        ctx.site(Site("g", "male", "M3", "clearance", Location((x, 0, 4)), grip=4))
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(s)
"""


def test_fastener_alignment_and_length(tmp_path):
    d = _write_project(tmp_path / "bolt", BOLT_YAML, {"block": BOLT_BLOCK, "plate": BOLT_PLATE})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    joints, problems = A.fasteners(asm)
    assert problems == []
    assert len(joints) == 2 and all(j["length_mm"] == 8 for j in joints)   # grip 4 + 4..6.2 engage -> M3x8
    assert all(abs(j["gap_mm"]) < 1e-6 for j in joints)


def test_fastener_misalignment_detected(tmp_path):
    d = _write_project(tmp_path / "bolt2", BOLT_YAML, {"block": BOLT_BLOCK,
                       "plate": BOLT_PLATE.replace("(x, 0, 4)", "(x + 0.5, 0, 4)")})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    _, problems = A.fasteners(asm)
    assert len(problems) >= 2
