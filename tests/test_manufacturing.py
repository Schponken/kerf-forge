"""Mixed stock/printed assemblies: real CAD handoff, mass, quote identity and explicit proof boundaries."""
import io
import json
import math
import zipfile

import ezdxf
import pytest
import yaml
from build123d import Box, Cylinder, Location, Pos, import_step

from kerf import assembly, checks, export, manufacturing as M, pipeline, project, requirements, ship, studio, urdf, viewer
from kerf.ctx import Ctx


def stock(**changes):
    return {"process": "laser_cut", "stock": "Test sheet", "thickness_mm": 2,
            "density_g_cm3": 1.6, "density_source": "https://example.test/stock-datasheet", **changes}


def item(shape=None, **changes):
    return project.Item("panel", "manufactured", {"manufacturing": stock(**changes)},
                        Ctx("panel", {}).finish(shape if shape is not None else Box(40, 30, 2) - Cylinder(3, 4)))


@pytest.fixture
def rig(tmp_path):
    d = tmp_path / "mixed"
    (d / "parts").mkdir(parents=True)
    data = {"name": "Mixed fixture", "params": {"width": 40},
            "parts": {"panel": {"file": "parts/panel.py", "manufacturing": stock()},
                      "foot": {"file": "parts/foot.py", "material": "PETG"}},
            "assembly": {"root": "panel", "joints": [{"parent": "panel.foot", "child": "foot.origin"}]},
            "requirements": [{"id": "weight", "check": "mass_max", "max_g": 100}]}
    (d / "project.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    (d / "parts/panel.py").write_text('''from build123d import *
def build(ctx):
    ctx.rigid("foot", Location((0, 0, -8)))
    return ctx.finish(Box(ctx.p.width, 30, 2) - Cylinder(3, 4))
''', encoding="utf-8")
    (d / "parts/foot.py").write_text('''from build123d import *
def build(ctx):
    ctx.rigid("origin", Location())
    return ctx.finish(Box(12, 12, 6))
''', encoding="utf-8")
    return d


def test_plate_export_round_trips_holes_units_and_local_frame(tmp_path):
    it = item()
    assert M.part_check(it)["ok"]
    before = M.quote_fingerprint(it)
    it.shape = it.shape.moved(Pos(90, 50, 17))
    assert M.quote_fingerprint(it) == before
    p = project.Project("fixture", tmp_path, {}, {}, {"panel": it})
    files = M.write(p, tmp_path / "manufacturing")
    s = import_step(tmp_path / "manufacturing/panel.step")
    assert s.volume == pytest.approx((40 * 30 - math.pi * 9) * 2)
    assert s.bounding_box().center().X == pytest.approx(0)
    dx = ezdxf.readfile(tmp_path / "manufacturing/panel.dxf")
    assert dx.header["$INSUNITS"] == 4  # millimetres
    assert len(list(dx.modelspace().query("CIRCLE"))) == 1
    circle = list(dx.modelspace().query("CIRCLE"))[0]
    assert circle.dxf.radius == pytest.approx(3)
    assert files["parts"]["panel"]["files"] == ["panel.step", "panel.dxf"]
    assert json.loads((tmp_path / "manufacturing/order.json").read_text())["panel"]["current_quote_fingerprint"] == before


def test_no_lossy_dxf_for_pockets_bevels_or_wrong_stock(tmp_path):
    pocket = item(Box(40, 30, 2) - Pos(0, 0, 1) * Box(10, 10, 2))
    assert any("constant-thickness" in p for p in M.part_check(pocket)["problems"])
    with pytest.raises(ValueError, match="constant-thickness"):
        M.write(project.Project("fixture", tmp_path, {}, {}, {"panel": pocket}), tmp_path / "order")
    assert not (tmp_path / "order/panel.step").exists()
    assert not M.part_check(item(thickness_mm=3))["ok"]
    # A CNC solid may have pockets, but does not silently receive a flattened DXF.
    pocket.spec["manufacturing"] = stock(process="cnc")
    pocket.spec["manufacturing"].pop("thickness_mm")
    files = M.write(project.Project("fixture", tmp_path, {}, {}, {"panel": pocket}), tmp_path / "cnc")
    assert files["parts"]["panel"]["files"] == ["panel.step"]


def test_rebuild_removes_only_obsolete_generated_files(tmp_path):
    it = item()
    p = project.Project("fixture", tmp_path, {}, {}, {"panel": it})
    out = tmp_path / "manufacturing"
    M.write(p, out)
    (out / "my-note.txt").write_text("keep", encoding="utf-8")
    it.spec["manufacturing"].update(process="cnc")
    it.spec["manufacturing"].pop("thickness_mm")
    M.write(p, out)
    assert not (out / "panel.dxf").exists() and (out / "panel.step").exists()
    p.items.clear()
    M.write(p, out)
    assert not (out / "panel.step").exists()
    assert (out / "my-note.txt").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("change", [{"density_g_cm3": 0}, {"density_g_cm3": float("nan")},
                                      {"density_source": "javascript:bad"}, {"process": "cncc"}])
def test_invalid_stock_metadata_is_rejected(change):
    with pytest.raises(ValueError):
        M.validate("panel", {"manufacturing": stock(**change)})


def test_mass_changes_with_geometry_and_quotes_expire(rig):
    p = project.build(project.load(str(rig)))
    it = p.items["panel"]
    assert checks.item_mass_g(it) == pytest.approx((40 * 30 - math.pi * 9) * 2 / 1000 * 1.6)
    m = it.spec["manufacturing"]
    m.update(price_key="custom:panel", quote_fingerprint=M.quote_fingerprint(it))
    prices = {"custom:panel": {"pack_qty": 1, "pack_usd": 12.5, "buy": "https://example.test/quote"}}
    def price():
        rows = export.bom(p, [], {}, p.out())
        summary = ship.price_bom(rows, prices)
        return next(r for r in rows if r["item"] == "panel"), summary
    row, summary = price()
    assert row["total_usd"] == 12.5 and "panel" not in summary["unpriced"]
    it.spec["qty"] = 2
    assert "panel" in price()[1]["unpriced"]
    it.spec["qty"] = 1
    it.shape = Ctx("panel", {}).finish(Box(80, 30, 2) - Cylinder(3, 4))
    assert checks.item_mass_g(it) > 7 and "panel" in price()[1]["unpriced"]
    assert "out of date" in price()[0]["note"]


def test_unsupported_stock_strength_fails_in_direct_and_derived_checks(rig, monkeypatch):
    from kerf import fea
    monkeypatch.setattr(fea, "static", lambda *a, **kw: pytest.fail("unsupported stock must never reach a solver"))
    p = project.build(project.load(str(rig)))
    req = {"id": "panel_load", "check": "fea_static", "part": "panel", "fixed": {}, "loads": []}
    p.data["requirements"].append(req)
    with pytest.raises(ValueError, match="stock-specific"):
        requirements.fea_static(p, None, "panel", {}, [])
    for check in [req, {"check": "creep_limit", "case": "panel_load"},
                  {"check": "weak_link", "cheap": "panel_load", "expensive": "panel_load"},
                  {"check": "flex_strain", "part": "panel", "kind": "snap", "t_mm": 1, "L_mm": 30, "deflection_mm": 1}]:
        with pytest.raises(ValueError, match="stock-specific"):
            requirements.REGISTRY[check["check"]](p, None, **{k: v for k, v in check.items() if k not in ("check", "id")})
        result = requirements._run_one(p, None, check, False)
        if check["check"] in requirements.STRESS_SIMS and requirements.stress_paused():
            assert result["paused"] and result["skipped"] and result["value"] is None
        else:
            assert not result["ok"] and "stock-specific" in result["detail"]
    p.items["panel"].spec["structural"] = True
    assert not M.part_check(p.items["panel"])["ok"]
    from kerf.usestory import heat_limit
    assert not heat_limit(p, None, 40)["ok"]
    assert not heat_limit(p, None, 40, parts=["panel"])["ok"]
    assert heat_limit(p, None, 40, parts=["foot"])["ok"]


def test_mixed_pipeline_files_mass_ui_and_zip(rig, monkeypatch):
    # Exercise the real kit pipeline without costly raster rendering.
    rep = pipeline.run(str(rig), sweeps=False, do_export=True, do_render=False)
    assert rep["ok"], rep["problems"]
    assert set(rep["parts"]) == {"foot"} and set(rep["manufactured"]) == {"panel"}
    assert set(rep["files"]["parts"]) == {"foot"}
    assert all(not any("panel" in n for n in plate["parts"]) for plate in rep["files"]["plates"])
    assert rep["mass"]["device_g"] == pytest.approx(rep["mass"]["printed_g"] + rep["mass"]["manufactured_g"], abs=.11)
    out = rig / "out"
    text = (out / "ASSEMBLY.md").read_text(encoding="utf-8")
    assert "laser cut, Test sheet" in text and "manufacturing/ORDER.md" in text
    p = project.build(project.load(str(rig)))
    asm = assembly.plan(p)
    tree, meshes, _ = urdf.build(p, asm)
    assert "panel" in meshes
    assert sum(float(m.attrib["value"]) for m in tree.findall(".//mass")) * 1000 == pytest.approx(
        sum(checks.item_mass_g(it) for it in p.items.values()), abs=.01)
    vd = viewer.embedded(out / "viewer.html")
    assert next(it for it in vd["items"] if it["id"] == "panel")["label"] == "laser cut, Test sheet"
    monkeypatch.setattr(studio, "PROJECTS", rig.parent)
    assert studio.part_materials("mixed") == {"foot": "PETG"}
    with pytest.raises(ValueError, match="printed part"):
        studio.write_materials(rig / "project.yaml", {"panel": "PLA"})
    z = zipfile.ZipFile(io.BytesIO(studio.export_zip("mixed")))
    assert "mixed/manufacturing/panel.dxf" in z.namelist()
    assert "mixed/manufacturing/ORDER.md" in z.namelist()


def test_stock_build_does_not_apply_fdm_calibration(rig, monkeypatch):
    from kerf import calibrate
    monkeypatch.setattr(calibrate, "load_profile", lambda _: {"materials": {"PETG": {"offsets": {"hole_M3": .4}}}})
    (rig / "parts/panel.py").write_text('''from build123d import *
from kerf.calibrate import offset
def build(ctx):
    assert offset("hole", "M3") == 0
    ctx.rigid("foot", Location((0, 0, -8)))
    return ctx.finish(Box(ctx.p.width, 30, 2))
''', encoding="utf-8")
    with calibrate.active(None, "PETG"):
        p = project.build(project.load(str(rig)), cache=False)
        assert p.items["panel"].error is None
        assert calibrate.offset("hole", "M3") == .4
