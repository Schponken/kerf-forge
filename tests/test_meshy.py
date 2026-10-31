"""Creative mode (kerf/meshy.py): a cached, deliberately broken 'Meshy' mesh is repaired, scaled to its bounds and
fused with exact mounting features into one printable body whose screw holes are real. No Meshy call is needed."""
import textwrap
from pathlib import Path

import numpy as np
import pytest
import trimesh

from kerf import assembly as A, checks, export, geom, meshy, pipeline, project as P

YAML = """
name: Meshy test
params: {}
parts:
  base: {file: parts/base.py, material: PETG}
  cover:
    file: parts/cover.py
    material: PETG
    source: meshy
    prompt: "a bumpy organic dome"
    mesh: meshes/cover.stl
    bounds: [[-20, -20, 3], [20, 20, 25]]
assembly:
  root: base
  joints:
    - {parent: base.top, child: cover.mount}
"""
BASE = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(50, 50, 8, align=(Align.CENTER, Align.CENTER, Align.MAX))
    s -= iface.bolt_pattern(ctx, "cover_base", "M3", iface.rect(24, 24), Location((0, 0, 0)), kind="heatset", depth=8)
    ctx.rigid("top", Location((0, 0, 0)))
    return ctx.finish(s)
"""
COVER = """
from build123d import *
from kerf import iface
def build(ctx):
    flange = Box(32, 32, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    holes = iface.bolt_pattern(ctx, "cover_base", "M3", iface.rect(24, 24), Location((0, 0, 4)), kind="clearance", depth=4)
    ctx.mesh_cut(holes)                      # the screws pass through the shell too
    for x in (-12, 12):                      # and a hex key must reach their heads: 7 mm access bores up through the dome
        for y in (-12, 12):
            ctx.mesh_cut(Pos(x, y, 4) * Cylinder(3.5, 60, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    ctx.mesh_cut(Pos(0, 0, 4) * Cylinder(3.0, 60, align=(Align.CENTER, Align.CENTER, Align.MIN)))   # cable hole
    ctx.rigid("mount", Location((0, 0, 0)))
    return ctx.finish(flange - holes)
"""


def broken_mesh():
    """What a bad download looks like: a lumpy dome with 30 triangles missing and a stray overlapping cube."""
    m = trimesh.creation.icosphere(subdivisions=3, radius=10)
    v = m.vertices
    m.vertices = v * (1 + 0.1 * np.sin(3 * v[:, [0]] / 4) * np.cos(2 * v[:, [1]] / 4))
    m = trimesh.Trimesh(m.vertices, np.delete(m.faces, np.random.default_rng(3).choice(len(m.faces), 30, replace=False), 0))
    junk = trimesh.creation.box((4, 4, 4)).apply_translation([0, 0, 9])
    return trimesh.util.concatenate([m, junk])


def make(tmp_path, with_mesh=True):
    d = tmp_path / "mp"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "base.py").write_text(textwrap.dedent(BASE))
    (d / "parts" / "cover.py").write_text(textwrap.dedent(COVER))
    if with_mesh:
        (d / "meshes").mkdir()
        bm = broken_mesh()
        assert not bm.is_watertight
        bm.export(str(d / "meshes" / "cover.stl"))
    return d


def test_repair_union_gives_one_closed_body():
    M, how = meshy.repair_union(broken_mesh(), pitch=0.3)
    tm = meshy.from_manifold(M)
    assert tm.is_watertight and len(tm.split(only_watertight=False)) == 1
    assert how                                    # records which rung of the repair ladder was used


def test_fit_bounds_stretch_and_uniform():
    box = trimesh.creation.box((2, 4, 8))
    s = meshy.fit_bounds(box, [[0, 0, 0], [10, 10, 10]], "stretch")
    assert np.allclose(s.bounds, [[0, 0, 0], [10, 10, 10]])
    u = meshy.fit_bounds(box, [[0, 0, 0], [10, 10, 10]], "uniform")
    assert np.allclose(u.bounds[1] - u.bounds[0], [2.5, 5, 10]) and np.allclose(u.bounds.mean(axis=0), [5, 5, 5])
    with pytest.raises(meshy.MeshyError):
        meshy.fit_bounds(box, [[0, 0, 0], [10, 10, 10]], "squash")


def test_fused_part_is_one_printable_body_with_real_holes(tmp_path):
    proj = P.build(P.load(str(make(tmp_path))))
    it = proj.items["cover"]
    assert it.error is None, it.error
    info = it.shape.kerf_mesh_info
    assert info["bodies"] == 1 and info["watertight"]
    lo, hi = geom.bbox(it.shape)
    assert np.allclose(lo, [-20, -20, 0], atol=0.05) and np.allclose(hi, [20, 20, 25], atol=0.05)   # flange + shell
    tm = trimesh.Trimesh(*geom.mesh(it.shape), process=False)
    # every M3 clearance hole (3.4 mm, catalog) is open through flange and shell; material just outside it
    for x, y in ((12, 12), (-12, 12), (12, -12), (-12, -12)):
        on_axis = [[x, y, z] for z in (0.5, 2.0, 3.5)]
        assert not tm.contains(on_axis).any()
        assert not tm.contains([[x + 1.5, y, 2.0]]).any()          # inside the 1.7 mm hole radius
        assert tm.contains([[x + 2.3, y, 2.0]]).all()               # flange material beyond it
    assert not tm.contains([[0, 0, z] for z in (5, 10, 15, 20)]).any()   # the 6 mm cable hole runs up through the dome
    assert tm.contains([[6, 0, 10]]).all()                                # dome material next to it
    r = checks.part_checks(it, "Bambu Lab A2L")
    assert r["watertight"] and r["solids"] == 1 and not [p for p in r["problems"] if "solid" in p or "watertight" in p]
    assert r["size_mm"] == pytest.approx([40, 40, 25], abs=0.1)


def test_fasteners_and_interference_use_the_fused_part(tmp_path):
    proj = P.build(P.load(str(make(tmp_path))))
    asm = A.plan(proj)
    A.solve(asm)
    fj, probs = A.fasteners(asm)
    assert probs == [] and len(fj) == 4                      # the B-rep features still carry the sites
    assert A.interference(asm) == []                          # flange sits on the base: touching, no overlap
    from build123d import Box, Pos
    probe = Pos(0, 10, 12) * Box(4, 4, 4)                     # a block buried in the dome's solid side wall
    v = geom.overlap(proj.items["cover"].shape, probe)
    inside = trimesh.Trimesh(*geom.mesh(proj.items["cover"].shape), process=False).contains(
        np.random.default_rng(0).uniform([-2, 8, 10], [2, 12, 14], (4000, 3))).mean() * 64
    assert v == pytest.approx(inside, rel=0.1) and v > 10      # mesh-space volume agrees with point sampling


def test_exports_and_glb(tmp_path):
    proj = P.build(P.load(str(make(tmp_path))))
    asm = A.plan(proj)
    A.solve(asm)
    files = export.part_files(proj, tmp_path / "parts_out")
    stl = trimesh.load(str(tmp_path / "parts_out" / "cover.stl"))
    assert stl.is_watertight and np.allclose(stl.bounds[1] - stl.bounds[0], [40, 40, 25], atol=0.1)
    assert (tmp_path / "parts_out" / "cover.3mf").stat().st_size > 1000 and files["cover"] == ["cover.stl", "cover.3mf"]
    plates = export.plates(proj, tmp_path / "plates")
    assert plates and (tmp_path / "plates" / plates[0]["file"]).stat().st_size > 1000
    export.glb(proj, tmp_path / "a.glb")
    sc = trimesh.load(str(tmp_path / "a.glb"))
    # same convention as build123d's exporter: metres, (x, y, z) -> (x, z, -y): base bottom at z = -8 -> y' = -0.008
    assert sc.bounds[0][1] == pytest.approx(-0.008, abs=1e-4) and sc.bounds[1][1] == pytest.approx(0.025, abs=1e-4)


def test_missing_mesh_names_prompt_and_path(tmp_path):
    proj = P.build(P.load(str(make(tmp_path, with_mesh=False))))
    err = proj.items["cover"].error
    assert "meshes/cover.stl is missing" in err and "a bumpy organic dome" in err


def test_fingerprint_follows_the_mesh(tmp_path):
    d = make(tmp_path)
    f0 = P.load(str(d)).fingerprint()
    trimesh.creation.icosphere(radius=10).export(str(d / "meshes" / "cover.stl"))
    assert P.load(str(d)).fingerprint() != f0


def test_pipeline_build_with_meshy_part(tmp_path):
    d = make(tmp_path)
    rep = pipeline.run(str(d), sweeps=False, do_export=True)
    assert rep["ok"], rep["problems"]
    assert rep["parts"]["cover"]["watertight"] and rep["parts"]["cover"]["solids"] == 1
    assert (d / "out" / "parts" / "cover.stl").exists() and (d / "out" / "viewer.html").exists()
