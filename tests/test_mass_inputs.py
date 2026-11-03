"""Bad print/mass inputs fail before geometry or physical calculations; valid settings retain the same formulas."""
import math
from types import SimpleNamespace

import pytest
import yaml
from build123d import Box

from kerf import checks, export, pipeline, project as P


BAD_PRINT = [
    ("infill", -0.01), ("infill", 1.01), ("infill", float("nan")), ("infill", float("inf")),
    ("infill", -float("inf")), ("infill", True), ("infill", False), ("infill", None),
    ("infill", "NaN"), ("infill", "25%"), ("infill", []),
    ("walls", -1), ("walls", 2.5), ("walls", float("nan")), ("walls", float("inf")),
    ("walls", True), ("walls", False), ("walls", None), ("walls", "2.5"), ("walls", "many"),
]
BAD_MASS = [-1, float("nan"), float("inf"), -float("inf"), True, False, None, "NaN", "5 grams", {}]


def write_project(tmp_path, spec=None, purchased=None):
    data = {"name": "input validation fixture", "parts": {"cube": {"file": "parts/cube.py", **(spec or {})}},
            "assembly": {"root": "cube", "joints": []}}
    if purchased is not None:
        data["purchased"] = {"load": purchased}
    (tmp_path / "project.yaml").write_text(yaml.safe_dump(data))
    return tmp_path


@pytest.mark.parametrize("field,value", BAD_PRINT)
def test_project_rejects_bad_print_inputs_before_build(tmp_path, monkeypatch, field, value):
    d = write_project(tmp_path, {field: value})
    def must_not_build(*args, **kwargs):
        raise AssertionError("geometry must not run for invalid inputs")
    monkeypatch.setattr(P, "build", must_not_build)
    with pytest.raises(P.ProjectError, match=f"parts.cube: {field}"):
        pipeline.run(str(d), sweeps=False)


@pytest.mark.parametrize("field,value", BAD_PRINT)
def test_direct_print_and_mass_paths_share_validation(field, value):
    spec = {field: value}
    it = SimpleNamespace(role="printed", shape=Box(10, 10, 10), spec=spec)
    calls = [lambda: checks.item_mass_g(it), lambda: checks._printed_mass_g(it),
             lambda: checks.shell_volume(it.shape, spec),
             lambda: checks.part_checks(it, "Bambu Lab A2L"), lambda: export.part_print_settings(spec)]
    for call in calls:
        with pytest.raises(ValueError, match=field):
            call()


@pytest.mark.parametrize("value", BAD_MASS)
def test_explicit_mass_cannot_be_negative_nonfinite_or_boolean(tmp_path, value):
    d = write_project(tmp_path, purchased={"mass_g": value, "catalog": "servos.MG90S"})
    with pytest.raises(P.ProjectError, match="purchased.load: mass_g"):
        P.load(str(d))
    it = SimpleNamespace(role="purchased", spec={"mass_g": value, "catalog": "servos.MG90S"})
    for call in (checks.item_mass_g, checks._purchased_mass_g):
        with pytest.raises(ValueError, match="mass_g"):
            call(it)  # invalid overrides must not fall back to an otherwise valid catalog weight


@pytest.mark.parametrize("infill,walls", [(0, 0), (1, 0), (0, 2), (1, 2), (0.25, 2),
                                           (0.25, 2.0), ("0.25", "2"), ("0.25", "2.0")])
def test_valid_boundaries_and_numeric_strings_keep_mass_and_print_settings_consistent(tmp_path, infill, walls):
    d = write_project(tmp_path, {"infill": infill, "walls": walls, "material": "PETG"})
    p = P.load(str(d))
    it = p.items["cube"]
    it.shape = Box(40, 20, 10)
    # 1600 mm² top/bottom, 1200 mm² sides; existing 0.84 mm skins and 0.42 mm perimeter lines.
    shell = min(8000, 1600 * 0.84 + 1200 * float(walls) * 0.42)
    expected = (shell + float(infill) * (8000 - shell)) / 1000 * checks.density("PETG")
    assert checks.item_mass_g(it) == pytest.approx(expected)
    assert isinstance(it.spec["walls"], int) and it.spec["infill"] == float(infill)
    for spec in (it.spec, {"infill": infill, "walls": walls}):
        settings = export.part_print_settings(spec)
        assert settings["walls"] == int(float(walls)) and settings["infill_pct"] == round(float(infill) * 100)
    report = checks.part_checks(it, "Bambu Lab A2L")
    assert report["mass_est_g"] == round(expected, 1) and report["walls"] == int(float(walls))


def test_cached_mass_does_not_hide_invalid_mutated_settings():
    it = SimpleNamespace(role="printed", shape=Box(10, 10, 10), spec={"infill": 0.25, "walls": 2})
    expected = checks.item_mass_g(it)
    for field, value in (("walls", 2.5), ("infill", float("nan"))):
        old = it.spec[field]
        it.spec[field] = value
        with pytest.raises(ValueError, match=field):
            checks.item_mass_g(it)
        it.spec[field] = old
        assert checks.item_mass_g(it) == expected


def test_defaults_and_unknown_mass_semantics_stay_unchanged(tmp_path):
    p = P.load(str(write_project(tmp_path)))
    assert p.items["cube"].spec["walls"] == 2 and "infill" not in p.items["cube"].spec
    assert export.part_print_settings({})["infill_pct"] == 25
    for value in (0, 0.0, "0", "0.0", 2.5, "2.5"):
        it = SimpleNamespace(role="purchased", spec={"mass_g": value, "catalog": "servos.MG90S"})
        assert checks.item_mass_g(it) == float(value)
    assert checks.item_mass_g(SimpleNamespace(role="purchased", spec={})) == 0
    assert checks.item_mass_g(SimpleNamespace(role="purchased", spec={"catalog": "missing"})) == 0
    assert checks.item_mass_g(SimpleNamespace(role="purchased", spec={"catalog": "servos.MG90S"})) > 0


@pytest.mark.parametrize("field,value", [("infill", 1.01), ("infill", float("nan")),
                                        ("walls", -1), ("walls", 2.5), ("walls", True)])
def test_modifier_settings_get_the_same_scalar_validation(tmp_path, field, value):
    mod = {"where": "near insert", field: value}
    d = write_project(tmp_path, {"modifiers": [mod]})
    with pytest.raises(P.ProjectError, match=rf"parts.cube.modifiers\[0\]: {field}"):
        P.load(str(d))
    p = SimpleNamespace(printed={"cube": SimpleNamespace(spec={"modifiers": [mod]})})
    with pytest.raises(ValueError, match=field):
        export.modifiers_md(p)


def test_modifier_validation_preserves_local_output_defaults_and_mass_model(tmp_path):
    p = P.load(str(write_project(tmp_path, {"modifiers": [{"where": "near insert", "walls": "2.0"}]})))
    it = p.items["cube"]
    it.shape = Box(10, 10, 10)
    before = checks.item_mass_g(it)
    text = "\n".join(export.modifiers_md(p))
    assert "| 100 % | 2 |" in text
    del it.spec["modifiers"][0]["walls"]
    assert "| 100 % |  |" in "\n".join(export.modifiers_md(p))
    assert math.isfinite(before) and checks.item_mass_g(it) == before  # no new local-mass model


@pytest.mark.parametrize("spec", [None, 0, False, [], ["mass_g"], "stock"])
def test_purchased_item_requires_a_mapping(tmp_path, spec):
    d = write_project(tmp_path)
    data = yaml.safe_load((d / "project.yaml").read_text())
    data["purchased"] = {"load": spec}
    (d / "project.yaml").write_text(yaml.safe_dump(data))
    with pytest.raises(P.ProjectError, match="purchased.load: .*mapping"):
        P.load(str(d))
    with pytest.raises(ValueError, match="mapping"):
        checks.explicit_mass_g(spec)


@pytest.mark.parametrize("modifiers", [None, {}, 0, False, "", "volume", [None], [False], [3], ["volume"], [[]]])
def test_modifier_collection_requires_a_list_of_mappings(tmp_path, modifiers):
    d = write_project(tmp_path, {"modifiers": modifiers})
    with pytest.raises(P.ProjectError, match=r"parts.cube.modifiers.*mapping"):
        P.load(str(d))
    p = SimpleNamespace(printed={"cube": SimpleNamespace(spec={"modifiers": modifiers})})
    with pytest.raises(ValueError, match=r"cube.modifiers.*mapping"):
        export.modifiers_md(p)
