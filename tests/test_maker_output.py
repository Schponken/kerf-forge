"""Maker-facing report wording: units and limit direction, device vs off-board mass, items nothing holds,
plain-language notes, and off-board items kept out of the fit steps."""
import json
import textwrap

import pytest

from kerf import pipeline, requirements

YAML = """
name: t
parts:
  base: {file: parts/base.py, material: PETG}
purchased:
  brick: {catalog: electronics.supplies.meanwell_gst60a05, proxy: box, off_board: "on the desk"}
  loose: {catalog: boards.arduino_nano, proxy: board}
  pressed: {catalog: bearings.608, proxy: bearing, held_by: "press fit"}
assembly:
  root: base
  joints:
    - {parent: base.a, child: brick.bottom}
    - {parent: base.b, child: loose.bottom}
    - {parent: base.c, child: pressed.face}
requirements:
  - {id: weight, check: mass_max, max_g: 5000}
"""
BASE = """
from build123d import *
def build(ctx):
    ctx.rigid("a", Location((200, 0, 0)))
    ctx.rigid("b", Location((0, 200, 0)))
    ctx.rigid("c", Location((0, 0, 50)))
    return ctx.finish(Box(40, 40, 10))
"""


@pytest.fixture()
def proj(tmp_path):
    d = tmp_path / "t"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "base.py").write_text(textwrap.dedent(BASE))
    return d


def test_units_and_limit_direction():
    assert requirements.describe({"value": 0.55, "limit": 4.7, "unit": "kg·cm", "bound": "max"}) == "0.55 kg·cm (max 4.7)"
    assert requirements.describe({"value": 37.1, "limit": 15, "unit": "°", "bound": "min"}) == "37.1 ° (min 15)"
    assert requirements.describe({"value": 44.0, "limit": [40, 48], "unit": "mm", "bound": "range"}) == "44.0 mm (range 40–48)"
    assert requirements.describe({"value": 6.0, "limit": 4, "unit": ":1", "bound": "min"}) == "6.0:1 (min 4)"
    assert set(requirements.UNITS) == set(requirements.REGISTRY)     # every check says what its numbers mean


def test_report_mass_split_unattached_and_units(proj):
    rep = pipeline.run(str(proj), sweeps=False)
    m = rep["mass"]
    assert m["off_board_g"] > 0 and m["device_g"] == pytest.approx(m["printed_g"] + m["on_board_g"], abs=0.11)
    assert rep["purchased"]["brick"]["off_board"] == "on the desk"
    loose = [w for w in rep["warnings"] if "nothing holds it" in w]
    assert len(loose) == 1 and loose[0].startswith("loose:")          # held_by and off_board items are not flagged
    r = rep["requirements"][0]
    assert r["unit"] == "g" and r["bound"] == "max"


def test_maker_notes_translate_known_warnings_only():
    w = ["bracket: 4 M3 tap hole(s) of group 'g1' sit closer than 1.5 x d (4.5 mm) to a free edge (worst 22 % ...",
         "M3 screw in servo (group 'g2') at [1, 2, 3]: a straight 2.5 mm hex key hits ['servo']; it needs a ball-end key",
         "M3 screw in servo (group 'g2') at [1, 2, 9]: a straight 2.5 mm hex key hits ['servo']; it needs a ball-end key",
         "something for the designer only"]
    n = pipeline.maker_notes(w)
    assert len(n) == 2 and "by hand" in n[0] and "ball-end 2.5 mm" in n[1]


def test_off_board_items_get_their_own_assembly_section(proj, tmp_path):
    from kerf import assembly as A, project as P, ship
    pr = P.build(P.load(str(proj)))
    asm = A.plan(pr)
    A.solve(asm)
    seq = ship.steps(asm)
    assert not any("brick" in grp for grp in seq)                      # never a "fit onto" step
    ship.write_assembly(pr, asm, {"assembly": {}}, tmp_path)
    md = (tmp_path / "ASSEMBLY.md").read_text()
    assert "## Bench electronics (not mounted)" in md and "**brick**" in md and "on the desk" in md
    assert "electronics.supplies" not in md                             # a human name, not the catalog id
    assert "Fit **brick**" not in md


def test_bom_merges_same_items_and_keeps_included_rows_out_of_unpriced():
    from kerf import export, ship
    rows = export.tidy([
        {"type": "purchased", "item": "SG90 (servo)", "qty": 1, "spec": "servos.SG90", "for": ["pan_servo"], "note": ""},
        {"type": "purchased", "item": "SG90 (servo)", "qty": 1, "spec": "servos.SG90", "for": ["tilt_servo"], "note": ""},
        {"type": "fastener", "item": "4 x 6 mm shoulder screw, M3 thread (pivot)", "qty": 1, "note": "hinge 'a'; tighten gently; order X"},
        {"type": "fastener", "item": "4 x 6 mm shoulder screw, M3 thread (pivot)", "qty": 1, "note": "hinge 'b'; tighten gently; order X"},
        {"type": "printed", "item": "base", "qty": 1, "spec": "PETG", "note": ""}])
    sg = next(r for r in rows if r["spec"] == "servos.SG90")
    assert sg["qty"] == 2 and "pan_servo, tilt_servo" in sg["note"]
    sh = next(r for r in rows if "shoulder" in r["item"])
    assert sh["qty"] == 2 and sh["note"] == "hinges 'a', 'b'; tighten gently; order X"     # shared advice said once
    assert len(rows) == 3
    s = ship.price_bom([{"type": "fastener", "item": "M2 horn centre screw", "qty": 2, "included": True, "note": "comes with the servo"}], {})
    assert s["unpriced"] == []


def test_shoulder_screw_row_names_the_part_number_for_its_length():
    from kerf import catalog
    pn = catalog.get("motion.shoulder_4_m3")["part_numbers"]
    assert pn["6"] == "97505A105" and pn["8"] == "97505A106"    # McMaster family table, 2026-11-01


def test_review_pack_digests_the_report_for_the_reviewer(tmp_path):
    """kerf/reviewpack.py: requirements with FEA peaks, declared corners with reasons, catalog subset, contact sheet."""
    import json
    from types import SimpleNamespace
    from PIL import Image
    from kerf import reviewpack
    out = tmp_path / "out"
    (out / "renders").mkdir(parents=True)
    for n in ("fea_a.png", "pose_j_max_iso.png", "assembly_sheet.png", "assembly_iso.png"):
        Image.new("RGB", (300, 200), "white").save(out / "renders" / n)
    rep = {"project": "t", "fingerprint": "abc", "ok": True, "seconds": 3, "problems": [], "warnings": ["w1", "w1"],
           "requirements": [{"id": "arm_fea", "check": "fea_static", "value": 9.4, "unit": "MPa", "limit": 13, "bound": "max",
                             "ok": True, "detail": "FEA arm: ...; peak 17.80 MPa at [1, 2, 3], deflection 0.500 mm (limit 1.0) at [0, 0, 0]"}],
           "parts": {"arm": {"material": "PETG", "sharp_inside": [], "sharp_kept": [{"at": [1, 2, 3], "why": "servo corner"}],
                             "stress": {"utilisation": 0.7, "hot_zones": [{"at": [1, 2, 3], "peak": 0.9}]}}}}
    proj = SimpleNamespace(name="t", dir=str(tmp_path), items={"sv": SimpleNamespace(spec={"catalog": "servos.SG90"})})
    md = reviewpack.write(proj, rep, out).read_text()
    assert "peak 17.80 MPa at [1, 2, 3]; defl 0.500 mm (limit 1.0)" in md
    assert "arm: 1 x servo corner" in md and md.count("- w1") == 1
    assert "renders/assembly_sheet.png" in md and "review/contact_1.png" in md
    assert list(json.loads((out / "review" / "catalog.json").read_text())) == ["servos.SG90"]
    assert (out / "review" / "contact_1.png").exists()
