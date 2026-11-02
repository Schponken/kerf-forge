"""Hardware inventory quantities/evidence, independent of engineering mass or physical verification."""
from types import SimpleNamespace

import pytest

from kerf import assembly as A, catalog, export, fastener_mass as M, pipeline, project as P, ship
from test_engine import BOLT_BLOCK, BOLT_PLATE, BOLT_YAML, _write_project

STOCK = "fastener_mass.accu_sscf_m3_8_a2"
KEY = "screw:M3x8:socket"


def row(**kwargs):
    return {"type": "fastener", "item": "M3 x 8 mm socket head screw", "qty": 2,
            "hardware_key": KEY, "spec": "ISO 4762", "note": "", **kwargs}


def project(data=None):
    return SimpleNamespace(printed={}, items={}, data=data or {})


def stock_entry(monkeypatch, **changes):
    e = {**catalog.get(STOCK), **changes}
    original = catalog.get
    monkeypatch.setattr(catalog, "get", lambda path: e if path == "fixture.stock" else original(path))
    return {KEY: "fixture.stock"}


def test_published_mass_is_per_hardware_piece_not_pack_or_stock_quantity():
    r = M.inventory([row(qty=3)], {KEY: STOCK})
    assert r["complete"] and r["total_g"] == pytest.approx(2.4)
    assert r["rows"][0]["unit_g"] == .8
    assert r["rows"][0]["reported_mass_g"] == 80 and r["rows"][0]["reported_qty"] == 100
    assert r["rows"][0]["source"].endswith("3818-SSCF-M3-8-A2")
    assert r["rows"][0]["status"] == "vendor-published"
    assert r["subtotals_g"] == {"vendor-published": pytest.approx(2.4), "measured": 0, "estimated": 0}
    assert r["included_in_engineering_totals"] is False


def test_unknowns_and_missing_stock_never_become_zero():
    rows = [row(), row(item="M3 heat-set insert", hardware_key="insert:M3")]
    r = M.inventory(rows, {KEY: STOCK})
    assert r["known_g"] == 1.6 and r["total_g"] is None and not r["complete"]
    assert r["unknown"] == ["M3 heat-set insert"] and r["problems"] == []
    assert r["rows"][1]["unit_g"] is None and r["rows"][1]["total_g"] is None
    assert M.inventory(rows)["total_g"] is None
    assert M.inventory([row(hardware_key=None)], {KEY: STOCK})["total_g"] is None
    # A price fallback cannot identify a physical stock mass.
    assert M.inventory([row()], {"screw:M3:socket": STOCK})["total_g"] is None


@pytest.mark.parametrize("field,value", [
    ("head", "flat"), ("size", "M4"), ("length_mm", 10), ("kind", "nut"),
    ("kind", "washer"), ("mass_kind", "guessed"), ("source", ""), ("mass_basis", ""),
    ("reported_mass_g", 0), ("reported_mass_g", -1), ("reported_mass_g", float("nan")),
    ("reported_mass_g", float("inf")), ("reported_mass_g", True), ("reported_qty", 0),
    ("reported_qty", 1.5), ("reported_qty", float("inf")), ("length_mm", None),
])
def test_bad_stock_is_a_problem_not_a_weight(monkeypatch, field, value):
    r = M.inventory([row()], stock_entry(monkeypatch, **{field: value}))
    assert r["problems"] and r["total_g"] is None and r["rows"][0]["status"] == "unknown"


@pytest.mark.parametrize("stock", [[], "stock", False, {KEY: None}, {2: STOCK}, {KEY: " "}])
def test_bad_selection_contract(stock):
    r = M.inventory([row()], stock)
    assert r["problems"] and "fastener_stock must map" in r["problems"][0]
    assert r["total_g"] is None


@pytest.mark.parametrize("path", ["missing.stock", "fastener_mass.accu_sscf_m3_8_a2.reported_mass_g"])
def test_missing_or_scalar_catalog_path_is_reported(path):
    r = M.inventory([row()], {KEY: path})
    assert r["problems"] and r["total_g"] is None


@pytest.mark.parametrize("qty", [0, -1, 1.2, None, True, float("nan"), float("inf"), "oops"])
def test_invalid_hardware_quantity(qty):
    r = M.inventory([row(qty=qty)], {KEY: STOCK})
    assert r["problems"] and r["total_g"] is None


def test_overflow_is_not_a_valid_total(monkeypatch):
    stock = stock_entry(monkeypatch, reported_mass_g=1e308, reported_qty=1)
    r = M.inventory([row(qty=2)], stock)
    assert r["total_g"] is None and r["problems"]
    r = M.inventory([row(qty=1), row(qty=1, item="another screw")], stock)
    assert r["total_g"] is None and r["known_g"] is None and r["subtotals_g"]["vendor-published"] is None


@pytest.mark.parametrize("kind", ["measured", "estimated"])
def test_other_evidence_categories_stay_separate(monkeypatch, kind):
    stock = stock_entry(monkeypatch, mass_kind=kind, mass_basis="Synthetic arithmetic fixture, not a real weight")
    r = M.inventory([row()], stock)
    assert r["subtotals_g"][kind] == 1.6 and r["subtotals_g"]["vendor-published"] == 0


def test_insert_length_must_match_the_generated_fit(monkeypatch):
    e = {**catalog.get(STOCK), "kind": "insert", "length_mm": 4}
    original = catalog.get
    monkeypatch.setattr(catalog, "get", lambda path: e if path == "fixture.insert" else original(path))
    r = M.inventory([row(hardware_key="insert:M3")], {"insert:M3": "fixture.insert"})
    assert "does not match" in r["problems"][0] and r["total_g"] is None


def test_generated_quantities_share_the_final_bom_and_do_not_double_count(tmp_path):
    d = _write_project(tmp_path / "bolts", BOLT_YAML, {"plate": BOLT_PLATE, "block": BOLT_BLOCK})
    p = P.build(P.load(str(d)))
    asm = A.plan(p)
    A.solve(asm)
    joints, problems = A.fasteners(asm)
    assert not problems and len(joints) == 2 and all(j["length_mm"] == 8 for j in joints)
    # One extra pin needs one extra screw and insert; identical manual extras are already generated.
    pivot = {"screw_pivot": True, "pin": "M3", "length_mm": 8, "group": "pivot", "fixed_fit": "heatset"}
    p.data["bom_extra"] = [{"type": "fastener", "item": "M3 heat-set insert", "qty": 100},
                           {"type": "fastener", "item": "M3 x 8 mm socket head screw", "qty": 100}]
    p.data["fastener_stock"] = {KEY: STOCK}
    before = {k: pipeline.checks.item_mass_g(it) for k, it in p.items.items()}
    rows = export.bom(p, joints, {}, tmp_path, pins=[pivot])
    r = M.inventory(rows, p.data["fastener_stock"])
    screws = [x for x in r["rows"] if x["hardware_key"] == KEY]
    inserts = [x for x in r["rows"] if x["hardware_key"] == "insert:M3"]
    assert sum(x["qty"] for x in screws) == 3
    assert len(inserts) == 1 and inserts[0]["qty"] == 3
    assert r["known_g"] == pytest.approx(2.4) and r["total_g"] is None
    assert before == {k: pipeline.checks.item_mass_g(it) for k, it in p.items.items()}
    assert all("at" in j and "dir" in j for j in joints)  # original spatial site data retained
    assert "unknown" in (tmp_path / "FASTENER_MASS.md").read_text()


def test_included_for_cost_does_not_remove_physical_mass(tmp_path):
    p = project({"fastener_stock": {KEY: STOCK}})
    rows = export.bom(p, [], {}, tmp_path, extra=[row(included=True)])
    r = M.inventory(rows, p.data["fastener_stock"])
    assert r["total_g"] == 1.6 and r["rows"][0]["included_for_cost"]
    price = ship.price_bom(rows, {})
    ship.write_bom(rows, price, tmp_path)
    assert rows[0]["total_usd"] == 0
    assert "1.6 g for this row" in (tmp_path / "bom.md").read_text()
    assert "FASTENER_MASS.md" in (tmp_path / "bom.csv").read_text()
    assert "80 g" in (tmp_path / "FASTENER_MASS.md").read_text()


def test_unidentified_supplied_horn_and_wiring_hardware_stay_unknown():
    p = project()
    p.items["horn"] = SimpleNamespace(role="purchased", spec={"catalog": "servo_horns.aluminum_25T"})
    rows = export.bom_rows(p, [], {}, extra=[row(type="hardware", item="bootlace ferrule", hardware_key=None)])
    r = M.inventory(rows)
    assert len(r["rows"]) == 2 and len(r["unknown"]) == 2 and r["total_g"] is None
    assert any(x["included_for_cost"] for x in r["rows"])


def test_empty_inventory_and_unused_stock_are_explicit():
    r = M.inventory([], {KEY: STOCK})
    assert r["evaluated"] and r["rows"] == [] and r["total_g"] == 0
    assert "not used" in r["warnings"][0]


def test_pipeline_reports_inventory_and_early_stop_as_not_evaluated(tmp_path, monkeypatch):
    from kerf import modes
    d = _write_project(tmp_path / "pipeline", BOLT_YAML + f'fastener_stock: {{"{KEY}": {STOCK}}}\n',
                       {"plate": BOLT_PLATE, "block": BOLT_BLOCK})
    # A docs-only synthetic run exercises the real fit/BOM/report path without rendering, plates or any solver.
    monkeypatch.setattr(modes, "stages", lambda mode: {"docs"})
    r = pipeline.run(str(d), mode="fixture")
    assert r["fastener_mass"]["evaluated"] and r["fastener_mass"]["known_g"] == 1.6
    assert r["fastener_mass"]["total_g"] is None and r["fastener_mass"]["unknown"] == ["M3 heat-set insert"]
    assert "not explicitly included" in " ".join(r["warnings"])
    assert r["files"]["fastener_mass"] == "FASTENER_MASS.md"
    assert "vendor-published" in (d / "out" / "FASTENER_MASS.md").read_text()
    assert M.inventory(r["bom"], {KEY: STOCK})["rows"] == r["fastener_mass"]["rows"]
    monkeypatch.setattr(modes, "stages", lambda mode: {"requirements"})
    monkeypatch.setattr(pipeline, "_redesign_first", lambda *a, **kw: [{"id": "fixture", "check": "mass_max", "ok": False, "value": 2, "limit": 1, "detail": "fixture"}])
    stopped = pipeline.run(str(d), mode="fixture")
    assert stopped["stopped_early"] and stopped["fastener_mass"]["evaluated"] is False
    assert stopped["fastener_mass"]["total_g"] is None


def test_malformed_manual_bom_keeps_existing_validation(tmp_path):
    d = _write_project(tmp_path / "bad-bom", BOLT_YAML + "bom_extra: [{qty: 3}]\n",
                       {"plate": BOLT_PLATE, "block": BOLT_BLOCK})
    r = pipeline.run(str(d), sweeps=False)
    assert any("needs an 'item'" in p for p in r["problems"])
    assert not any("crashed" in p for p in r["problems"])
    assert r["fastener_mass"]["evaluated"] is False and r["fastener_mass"]["total_g"] is None


def test_markdown_escapes_literal_text_in_every_inventory_section(tmp_path, monkeypatch):
    text = '<img src="x"> & bracket | line\nnext'
    stock = stock_entry(monkeypatch, mass_basis=text, source="https://vendor.test/?a=1&b=<literal>")
    r = M.inventory([row(item=text), row(item="invalid " + text, qty="<bad>")], stock)
    r["warnings"].append(text)
    M.write(r, tmp_path)
    md = (tmp_path / "FASTENER_MASS.md").read_text()
    escaped = '&lt;img src=&quot;x&quot;&gt; &amp; bracket \\| line next'
    assert escaped in md and "&lt;bad&gt;" in md
    assert "?a=1&amp;b=&lt;literal&gt;" in md
    assert "- Problem: invalid " + escaped in md
    assert "- Note: " + escaped in md
    assert "<img" not in md and "<literal>" not in md and "line\nnext" not in md


def test_studio_maker_zip_contains_the_exact_inventory_referenced_by_bom(tmp_path, monkeypatch):
    import io
    import zipfile
    from kerf import studio
    d = _write_project(tmp_path / "demo", BOLT_YAML, {"plate": BOLT_PLATE, "block": BOLT_BLOCK})
    out = d / "out"
    out.mkdir()
    export.bom(project({"fastener_stock": {KEY: STOCK}}), [], {}, out, extra=[row()])
    monkeypatch.setattr(studio, "PROJECTS", tmp_path)
    with zipfile.ZipFile(io.BytesIO(studio.export_zip("demo"))) as z:
        assert z.namelist().count("demo/FASTENER_MASS.md") == 1
        assert z.read("demo/FASTENER_MASS.md") == (out / "FASTENER_MASS.md").read_bytes()
        assert b"FASTENER_MASS.md" in z.read("demo/bom.md")
        assert "demo/design/project.yaml" in z.namelist()
