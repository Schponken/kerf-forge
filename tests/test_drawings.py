"""Engineering drawings (kerf/drawings.py, cadgen eng_drawing): three views + iso on a sheet that holds every
annotation, one hole callout per interface hole group with the size measured on the part, and Studio lists the PDFs."""
import json

import pytest

from kerf import drawings, partcache, project as P
from test_engine import _write_project

YAML = """
name: Drawing test
params: {}
parts:
  plate: {file: parts/plate.py, material: PETG, print_rot: [0, 0, 0]}
  block: {file: parts/block.py, material: PETG}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
"""
PLATE = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(60, 40, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "corners", "M3", iface.rect(48, 28), Location((0, 0, 6)), kind="clearance", depth=6)
    s -= iface.bolt_pattern(ctx, "lid", "M3", [(0, 0)], Location((0, 0, 6)), kind="counterbore", depth=6)
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(s)
"""
BLOCK = """
from build123d import *
from kerf import iface
def build(ctx):
    s = Box(60, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s -= iface.bolt_pattern(ctx, "corners", "M3", iface.rect(48, 28), Location((0, 0, 20)), kind="heatset", depth=20)
    s -= iface.bolt_pattern(ctx, "side", "M3", [(0, 10)], Location((30, 0, 0), (0, 90, 0)), kind="tap", depth=20)
    ctx.rigid("top", Location((0, 0, 20)))
    return ctx.finish(s)
"""


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.setattr(partcache, "DIR", tmp_path / "cache")
    d = _write_project(tmp_path / "dp", YAML, {"plate": PLATE, "block": BLOCK})
    return P.build(P.load(str(d)))


def test_views_and_one_callout_per_hole_group(proj, tmp_path):
    from kerf import iface
    res = drawings.write_all(proj, tmp_path / "drawings")
    assert set(res) == {"plate", "block"}
    for pid, r in res.items():
        assert "error" not in r, r
        assert r["views"] == ["top", "front", "right", "iso"]
        pdf = tmp_path / "drawings" / r["pdf"]
        assert pdf.read_bytes().startswith(b"%PDF") and pdf.stat().st_size > 5000
    sp = iface.screw_spec("M3", "PETG")              # the parts are PETG: PETG pilot size
    plate = {c["group"]: c for c in res["plate"]["callouts"]}
    assert set(plate) == {"corners", "lid"}                                      # one callout per hole group
    assert plate["corners"]["count"] == 4 and plate["corners"]["view"] == "top"
    assert plate["corners"]["hole"] == {"diameter": pytest.approx(sp["clearance"], abs=0.01), "thru": True}
    cb = plate["lid"]["hole"]
    assert cb["thru"] and cb["diameter"] == pytest.approx(sp["clearance"], abs=0.01)
    assert cb["cbore"][0] == pytest.approx(sp["head_d"] + 0.6, abs=0.01)         # iface: head_d/2 + 0.3 radius
    block = {c["group"]: c for c in res["block"]["callouts"]}
    assert set(block) == {"corners", "side"}
    hs = block["corners"]["hole"]
    assert hs["diameter"] == pytest.approx(sp["insert_hole"], abs=0.01) and "depth" in hs and "thru" not in hs
    assert "HEAT-SET" in block["corners"]["label"]
    assert block["side"]["view"] == "right" and block["side"]["hole"]["diameter"] == pytest.approx(sp["tap"], abs=0.01)
    assert json.loads((tmp_path / "drawings" / "index.json").read_text())["plate"]["sheet"] in drawings.SIZES


def test_print_orientation_named():
    assert drawings._print_up({"print_rot": [0, 0, 0]}).startswith("+Z")
    assert drawings._print_up({"print_rot": [90, 0, 0]}).startswith("+Y")    # Rot(X=90) turns +Y to +Z


def test_drawing_reused_from_cache(proj, tmp_path, monkeypatch):
    monkeypatch.delenv("KERF_NO_CACHE", raising=False)
    drawings.write_all(proj, tmp_path / "a")
    warm = P.build(P.load(str(proj.dir)))
    assert all(it.cached for it in warm.printed.values())
    monkeypatch.setattr(drawings, "part_drawing", lambda *a, **k: 1 / 0)   # would fail if it drew again
    res = drawings.write_all(warm, tmp_path / "b")
    assert all("error" not in r for r in res.values())
    assert (tmp_path / "b" / "plate.pdf").read_bytes() == (tmp_path / "a" / "plate.pdf").read_bytes()


def test_studio_lists_drawings(tmp_path, monkeypatch):
    from kerf import studio
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(studio, "TRIALS", tmp_path / "trials")
    d = tmp_path / "projects" / "p"
    (d / "out" / "drawings").mkdir(parents=True)
    (d / "project.yaml").write_text("name: P\nparts: {}\nassembly: {}\n")
    (d / "out" / "drawings" / "arm.pdf").write_bytes(b"%PDF-1.4")
    assert "out/drawings/arm.pdf" in studio.detail("p")["files"]
    html = (studio.Path(studio.__file__).parent / "assets" / "studio.html").read_text(encoding="utf-8")
    assert 'x.startsWith("out/drawings/")' in html


def test_drawn_in_part_frame_after_assembly(proj, tmp_path):
    """The fit check places parts (assembled position); the drawing must not follow them there."""
    from kerf import assembly as A
    before = drawings.write_all(proj, tmp_path / "a")
    asm = A.plan(proj)
    A.solve(asm)
    assert proj.items["plate"].shape.location.position.Z != 0          # really moved
    after = drawings.write_all(proj, tmp_path / "b")
    for pid in before:
        assert after[pid]["callouts"] == before[pid]["callouts"] and after[pid]["sheet"] == before[pid]["sheet"]
        assert all(c["hole"] for c in after[pid]["callouts"])            # holes still found on the part
