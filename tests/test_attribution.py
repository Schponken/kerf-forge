"""Click-to-edit attribution: each face is traced to the part-file line that made it and to the params that change it."""
import base64
import textwrap

import numpy as np
import pytest
from build123d import Box

from kerf import assembly as A, attribution as AT, project as P, viewer

YAML = """
name: Attribution
params:
  plate_l: {value: 60, min: 40, max: 80, step: 1, label: Plate length}
  hole_d: {value: 5, min: 3, max: 8, step: 0.5, label: Hole diameter}
  boss_h: {value: 8, min: 4, max: 12, step: 1, label: Boss height}
parts:
  plate: {file: parts/plate.py}
assembly:
  root: plate
"""
PLATE = """
from build123d import *
def build(ctx):
    p = ctx.p
    s = Box(p.plate_l, 30, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s += Pos(-15, 0, 4) * Cylinder(6, p.boss_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= Pos(15, 0, -1) * Cylinder(p.hole_d / 2, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return ctx.finish(s)
"""
LINE_BOX, LINE_BOSS, LINE_HOLE = 4, 5, 6  # line numbers in PLATE (line 1 is the import)


@pytest.fixture()
def proj(tmp_path):
    d = tmp_path / "p"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "plate.py").write_text(textwrap.dedent(PLATE).lstrip("\n"))
    pr = P.build(P.load(str(d)))
    assert pr.items["plate"].error is None, pr.items["plate"].error
    return pr


def _faces(proj):
    return proj.items["plate"].shape.located(__import__("build123d").Location()).faces()


def _find(faces, pred):
    hits = [i for i, f in enumerate(faces) if pred(f)]
    assert len(hits) == 1, hits
    return hits[0]


def test_surface_key_ignores_face_orientation():
    b = Box(10, 10, 10)
    top = b.faces().sort_by(lambda f: f.center().Z)[-1]
    assert AT.surface_key(top) == AT.surface_key(top.reversed() if hasattr(top, "reversed") else top)
    assert AT.surface_key(top)[0] == "plane"


def test_lines_and_params(proj):
    a = AT.compute(proj)["plate"]
    faces = _faces(proj)
    assert len(a["faces"]) == len(faces)
    assert all(f["line"] for f in a["faces"]), "every face traced to a line"
    hole = _find(faces, lambda f: f.geom_type.name == "CYLINDER" and abs(f.bounding_box().center().X - 15) < 1e-6)
    boss_side = _find(faces, lambda f: f.geom_type.name == "CYLINDER" and abs(f.bounding_box().center().X + 15) < 1e-6)
    boss_top = _find(faces, lambda f: f.geom_type.name == "PLANE" and abs(f.center().Z - 12) < 1e-6)
    end = _find(faces, lambda f: f.geom_type.name == "PLANE" and abs(f.center().X - 30) < 1e-6)
    assert a["faces"][hole]["line"] == LINE_HOLE and a["lines"][LINE_HOLE].startswith("s -= Pos(15")
    assert a["faces"][boss_side]["line"] == LINE_BOSS and a["faces"][boss_top]["line"] == LINE_BOSS
    assert a["faces"][end]["line"] == LINE_BOX
    # params: what moves each face (surface changes) vs. only resizes it (same surface, new area)
    assert a["faces"][hole]["moves"] == ["hole_d"]
    assert a["faces"][boss_top]["moves"] == ["boss_h"]
    assert a["faces"][end]["moves"] == ["plate_l"]
    assert "boss_h" in a["faces"][boss_side]["resizes"] and "hole_d" not in a["faces"][boss_side]["moves"]
    assert a["whole"] == []


def test_viewer_face_ranges_match_attribution(proj):
    asm = A.plan(proj)
    d = viewer.data(proj, asm, {"project": "t", "problems": []})
    it = next(i for i in d["items"] if i["id"] == "plate")
    fs = np.frombuffer(base64.b64decode(it["faceStart"]), dtype=np.uint32)
    assert it["attr"] and len(fs) == len(it["attr"]["faces"]) == len(_faces(proj))
    assert np.all(np.diff(fs.astype(int)) >= 0) and fs[0] == 0 and fs[-1] < it["nt"]
    assert set(d["params"]) == {"plate_l", "hole_d", "boss_h"} and d["params"]["hole_d"]["max"] == 8
