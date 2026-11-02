"""Material edits target only requested YAML fields, including insertion, with no implicit alias edits."""
import pytest
import yaml

from kerf import studio
from test_studio_params import source, unchanged
from test_studio import _post, server  # noqa: F401 (local HTTP fixture)


def test_shared_part_definition_cannot_change_an_unrequested_part(tmp_path):
    text = "parts:\n  base: &shared {file: parts/base.py, material: PETG}\n  arm: *shared\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    with pytest.raises(ValueError, match="parts.base: aliased/shared"):
        studio.write_materials(p, {"base": "PLA"})
    unchanged(p, text.encode(), stamp)
    assert yaml.safe_load(p.read_text(encoding="utf-8"))["parts"]["arm"]["material"] == "PETG"


def test_nested_and_unrelated_same_name_fields_are_preserved(tmp_path):
    text = ("metadata:\n  base: {material: PETG}\nparts:\n  base:\n"
            "    settings: {material: PETG}\n    material: PETG # selected\n"
            "  arm: {material: PETG}\n")
    p = source(tmp_path, text)
    assert studio.write_materials(p, {"base": "PLA"}) == ["base"]
    assert p.read_text(encoding="utf-8") == text.replace("material: PETG # selected", "material: PLA # selected")


@pytest.mark.parametrize("text,old,new", [
    ('parts:\n  "base": {"material": "PETG"}\n', '"PETG"', '"PLA"'),
    ("parts:\n  'base':\n    'material': 'PETG' # note\n", "'PETG'", "'PLA'"),
    ('{"parts": {"base": {"material": "PETG"}}, "metadata": {"material": "PETG"}}\n', '"PETG"', '"PLA"'),
    ("parts: {base: {material: &one !!str 'PETG'}}\n", "'PETG'", "'PLA'"),
    ('\ufeffname: Démo 🛠\r\nparts:\r\n  "básé": {material: PETG} # µ\r\n', "PETG", "PLA"),
])
def test_flow_block_quoted_keys_prefixes_and_original_bytes(tmp_path, text, old, new):
    p = source(tmp_path, text)
    part = next(iter(yaml.safe_load(text)["parts"]))
    assert studio.write_materials(p, {part: "PLA"}) == [part]
    assert p.read_bytes() == text.replace(old, new, 1).encode("utf-8")


@pytest.mark.parametrize("text,expected", [
    ("parts: {base: {}}\n", "parts: {base: {material: PLA}}\n"),
    ("parts: {base: { file: parts/base.py }}\n", "parts: {base: {material: PLA,  file: parts/base.py }}\n"),
    ("parts:\n  base: &one {} # keep\n", "parts:\n  base: &one {material: PLA} # keep\n"),
    ("parts:\n  base:\n    file: parts/base.py # keep\n", "parts:\n  base:\n    material: PLA\n    file: parts/base.py # keep\n"),
    ("parts:\n  base: &one # keep\n    file: parts/base.py\n", "parts:\n  base: &one # keep\n    material: PLA\n    file: parts/base.py\n"),
    ("parts:\r\n  base:\r\n    file: parts/base.py\r\n", "parts:\r\n  base:\r\n    material: PLA\r\n    file: parts/base.py\r\n"),
    ("parts:\n  base:\n    file: parts/base.py", "parts:\n  base:\n    material: PLA\n    file: parts/base.py"),
    ("parts: {base: { # note\n file: parts/base.py}}\n", "parts: {base: {material: PLA,  # note\n file: parts/base.py}}\n"),
])
def test_missing_field_inserts_at_its_mapping_token(tmp_path, text, expected):
    p = source(tmp_path, text)
    assert studio.write_materials(p, {"base": "PLA"}) == ["base"]
    assert p.read_bytes() == expected.encode("utf-8")
    assert yaml.safe_load(p.read_text(encoding="utf-8"))["parts"]["base"]["material"] == "PLA"


@pytest.mark.parametrize("body", ["{}", "{file: parts/base.py}", "{material: 'PETG'}", "{material: &one !!str PETG}"])
def test_default_and_explicit_petg_noop_preserves_bytes_and_mtime(tmp_path, body):
    text = f"parts: {{base: {body}}}\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    assert studio.write_materials(p, {"base": "PETG"}) == []
    unchanged(p, text.encode(), stamp)


def test_multiple_replacements_and_insertions_use_original_positions(tmp_path):
    text = "parts: {base: {material: PETG}, arm: {}, tip: {material: TPU}, same: {material: PETG}}\n"
    p = source(tmp_path, text)
    assert studio.write_materials(p, {"base": "PA6-CF", "arm": "PLA", "tip": "ASA", "same": "PETG"}) == ["base", "arm", "tip"]
    assert p.read_text(encoding="utf-8") == text.replace("base: {material: PETG}", "base: {material: PA6-CF}").replace(
        "arm: {}", "arm: {material: PLA}").replace("tip: {material: TPU}", "tip: {material: ASA}")


@pytest.mark.parametrize("values,message", [
    ({"base": "PLA", "arm": "unobtainium"}, "unknown material"),
    ({"base": "PLA", "arm": []}, "unknown material"),
    ({"base": "PLA", "missing": "PLA"}, "unknown printed part"),
])
def test_invalid_second_change_cannot_write_the_first(tmp_path, values, message):
    text = "parts: {base: {material: PETG}, arm: {}}\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    with pytest.raises(ValueError, match=message):
        studio.write_materials(p, values)
    unchanged(p, text.encode(), stamp)


@pytest.mark.parametrize("text,message", [
    ("parts: {base: {}}\nparts: {base: {}}\n", "duplicate key"),
    ("parts: {base: {}, 'base': {}}\n", "duplicate key"),
    ("parts: {base: {material: PETG, material: TPU}}\n", "duplicate key"),
    ("defaults: &d {parts: {base: {}}}\n<<: *d\n", "merged"),
    ("defaults: &d {base: {}}\nparts: {<<: *d}\n", "merged"),
    ("defaults: &d {material: PETG}\nparts: {base: {<<: *d}}\n", "merged"),
    ("defaults: &d {base: {}}\nparts: *d\n", "aliased/shared"),
    ("parts: &p {base: {}}\nmetadata: *p\n", "aliased/shared"),
    ("parts: {base: {material: &m PETG}, arm: {material: *m}}\n", "aliased/shared"),
    ("metadata: &m PETG\nparts: {base: {material: *m}}\n", "aliased/shared"),
    ("&root\nparts: {base: {}}\nself: *root\n", "aliased/shared"),
    ("parts: {base: {material: [PETG]}}\n", "must be a scalar"),
    ("parts: {base: {material: }}\n", "explicit scalar"),
    ("parts:\n  base:\n    material: |\n      PETG\n", "inline scalar"),
])
def test_ambiguous_material_targets_never_write(tmp_path, text, message):
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    with pytest.raises(ValueError, match=message):
        studio.write_materials(p, {"base": "PLA"})
    unchanged(p, text.encode(), stamp)


def test_unrelated_recursive_alias_does_not_block_a_safe_edit(tmp_path):
    text = "metadata: &m {self: *m}\nparts: {base: {material: PETG}, arm: {material: TPU}}\n"
    p = source(tmp_path, text)
    assert studio.write_materials(p, {"base": "PLA"}) == ["base"]
    assert p.read_text(encoding="utf-8") == text.replace("material: PETG", "material: PLA")


def test_empty_material_request_does_not_rewrite_file(tmp_path):
    text = "name: demo\r\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    assert studio.write_materials(p, {}) == []
    unchanged(p, text.encode(), stamp)


def test_material_save_api_refuses_shared_target_and_only_updates_requested_part(server, tmp_path, monkeypatch):
    d = tmp_path / "demo"
    d.mkdir()
    text = "name: demo\nparts:\n  base: &shared {material: PETG}\n  arm: *shared\n"
    p = source(d, text)
    stamp = p.stat().st_mtime_ns
    monkeypatch.setattr(studio, "PROJECTS", tmp_path)
    monkeypatch.setattr(studio, "_worked_on", lambda name: False)
    code, body = _post(server + "/api/save-materials", {"project": "demo", "materials": {"base": "PLA"}})
    assert code == 400 and "aliased/shared" in body["error"]
    unchanged(p, text.encode(), stamp)
    p.write_text("name: demo\nparts: {base: {material: PETG}, arm: {material: PETG}}\n", encoding="utf-8")
    code, body = _post(server + "/api/save-materials", {"project": "demo", "materials": {"base": "PLA"}})
    assert code == 200 and body["changed"] == ["base"]
    parts = yaml.safe_load(p.read_text(encoding="utf-8"))["parts"]
    assert parts["base"]["material"] == "PLA" and parts["arm"]["material"] == "PETG"
