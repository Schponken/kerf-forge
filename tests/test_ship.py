"""Ship package: priced BOM rows (hand-computed totals) and the assembly-step plan / ASSEMBLY.md."""
from pathlib import Path

import numpy as np
import pytest

from kerf import assembly as A, pins, project as P, ship
from test_engine import BOLT_BLOCK, BOLT_PLATE, BOLT_YAML, HINGE_ARM, HINGE_BASE, HINGE_YAML, _write_project

PRICES = {
    "servos.MG996R": {"buy": "https://shop/mg996r", "pack_qty": 1, "pack_usd": 9.0},
    "screw:M3:socket": {"buy": "https://shop/m3", "pack_qty": 100, "pack_usd": 8.0},       # fallback, 0.08 each
    "screw:M3x8:socket": {"buy": "https://shop/m3x8", "pack_qty": 50, "pack_usd": 5.0},    # exact, 0.10 each
    "insert:M3": {"buy": "https://shop/ins", "pack_qty": 100, "pack_usd": 12.0},
    "dowel:3": {"buy": "https://shop/dowel", "pack_qty": 20, "pack_usd": 4.0},
    "material:PETG": {"buy": "https://shop/petg", "pack_qty": 1000, "pack_usd": 20.0},
    "tie": {"buy": "https://shop/tie", "pack_qty": 10, "pack_usd": 1.0},
}


def test_price_keys():
    assert ship.price_key({"type": "purchased", "item": "servo", "spec": "servos.MG996R"}) == ["servos.MG996R"]
    assert ship.price_key({"type": "fastener", "item": "M3 x 8 mm socket head screw"}) == ["screw:M3x8:socket", "screw:M3:socket"]
    assert ship.price_key({"type": "fastener", "item": "M2.5 x 10 mm flat head screw"}) == ["screw:M2.5x10:flat", "screw:M2.5:flat"]
    assert ship.price_key({"type": "fastener", "item": "M3 heat-set insert"}) == ["insert:M3"]
    assert ship.price_key({"type": "fastener", "item": "M3 hex nut"}) == ["nut:M3"]
    assert ship.price_key({"type": "pin", "item": "3 x 16 mm steel dowel pin"}) == ["dowel:3x16", "dowel:3"]
    assert ship.price_key({"type": "hardware", "item": "zip tie", "price_key": "tie"}) == ["tie"]
    assert ship.price_key({"type": "hardware", "item": "mystery"}) == []


def test_price_bom_totals():
    rows = [
        {"type": "printed", "item": "arm", "qty": 2, "spec": "PETG"},
        {"type": "purchased", "item": "servo", "qty": 1, "spec": "servos.MG996R"},
        {"type": "fastener", "item": "M3 x 8 mm socket head screw", "qty": 4, "spec": ""},
        {"type": "fastener", "item": "M3 x 12 mm socket head screw", "qty": 5, "spec": ""},   # falls back to the M3 pack
        {"type": "fastener", "item": "M3 heat-set insert", "qty": 4, "spec": ""},
        {"type": "pin", "item": "3 x 16 mm steel dowel pin", "qty": 3, "spec": ""},
        {"type": "hardware", "item": "zip tie", "qty": 3, "spec": "", "price_key": "tie"},
        {"type": "hardware", "item": "unobtainium", "qty": 1, "spec": ""},
    ]
    s = ship.price_bom(rows, PRICES, {"arm": {"mass_est_g": 25.0}})
    # 2 x 25 g x 0.02 + 9 + 4 x 0.10 + 5 x 0.08 + 4 x 0.12 + 3 x 0.20 + 3 x 0.10
    expect = 1.0 + 9.0 + 0.4 + 0.4 + 0.48 + 0.6 + 0.3
    assert s["total_usd"] == pytest.approx(expect, abs=0.01)
    assert s["unpriced"] == ["unobtainium"]
    assert rows[2]["price_key"] == "screw:M3x8:socket" and rows[2]["unit_usd"] == 0.1
    assert rows[3]["price_key"] == "screw:M3:socket" and rows[3]["total_usd"] == 0.4
    assert rows[0]["unit_usd"] == 0.5 and rows[0]["buy"] == "https://shop/petg"


def test_write_bom_files(tmp_path):
    rows = [{"type": "purchased", "item": "servo", "qty": 2, "spec": "servos.MG996R", "note": ""}]
    s = ship.price_bom(rows, PRICES)
    ship.write_bom(rows, s, tmp_path)
    md = (tmp_path / "bom.md").read_text()
    assert "[link](https://shop/mg996r)" in md and "**Total: $18.00**" in md
    assert "buy,unit_usd,total_usd" in (tmp_path / "bom.csv").read_text().splitlines()[0]


def test_real_price_file_is_well_formed():
    """Every entry in catalog/prices.json has a buy link, a source, a date and a positive pack price."""
    p = ship.load_prices()
    for k, e in p.items():
        assert e["buy"].startswith("http") and e["source"].startswith("http"), k
        assert float(e["pack_usd"]) > 0 and float(e["pack_qty"]) > 0 and e.get("checked"), k


def _bolt(tmp_path):
    d = _write_project(tmp_path / "bolt", BOLT_YAML, {"block": BOLT_BLOCK, "plate": BOLT_PLATE})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    fj, _ = A.fasteners(asm)
    return proj, asm, fj


def test_plan_screws_go_in_with_the_later_part(tmp_path):
    proj, asm, fj = _bolt(tmp_path)
    st = ship.plan(asm, fj, [])
    assert [s["items"] for s in st] == [["block"], ["plate"]]
    assert st[0]["inserts"] == [{"item": "block", "screw": "M3", "qty": 2}]      # pressed before anything goes on
    assert st[0]["screws"] == []
    assert st[1]["screws"] == [{"screw": "M3", "length_mm": 8, "head": "socket head", "qty": 2}]
    assert st[1]["fits"][0]["onto"]["parent"] == "block"


def test_steps_follow_order_and_parents(tmp_path):
    yaml_text = BOLT_YAML.replace("    - {parent: block.top, child: plate.bottom}",
                                  "    - {parent: block.top, child: plate.bottom}\n  order: [plate]")
    d = _write_project(tmp_path / "bolt2", yaml_text, {"block": BOLT_BLOCK, "plate": BOLT_PLATE})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    assert ship.steps(asm) == [["block"], ["plate"]]
    proj.data["assembly"]["order"] = ["nope"]
    with pytest.raises(ValueError, match="unknown item 'nope'"):
        ship.steps(asm)


def test_assembly_md_and_step_renders(tmp_path):
    d = _write_project(tmp_path / "hinge", HINGE_YAML, {"base": HINGE_BASE, "arm": HINGE_ARM})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    calls = []

    def fake_render(glb, prefix):
        assert Path(glb).stat().st_size > 1000          # a real GLB of the parts present at this step
        calls.append(Path(prefix).name)
        Path(f"{prefix}_iso.png").write_bytes(b"png")

    rep = {"assembly": {"fasteners": [], "pins": []}, "parts": {}, "bom": []}
    out = ship.write_assembly(proj, asm, rep, tmp_path, render=fake_render)
    md = (tmp_path / "ASSEMBLY.md").read_text()
    assert out["steps"] == 2 and calls == ["step_01", "step_02"]
    assert "## Step 2 — arm" in md and "onto **base** (joint `swing`)" in md and "-90 to 90 deg" in md
    assert "![step 2](assembly_steps/step_02_iso.png)" in md


def test_new_part_is_drawn_away_from_its_parent(tmp_path):
    proj, asm, _ = _bolt(tmp_path)
    off = ship._explode_offset(proj, asm, "plate", ["block", "plate"])
    assert off[2] > 10 and abs(off[0]) < 1e-6 and abs(off[1]) < 1e-6     # plate sits on top of the block -> lifted up
