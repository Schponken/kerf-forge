"""Reusable assemblies keep their complete contract but never inherit a check/review approval."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from kerf import cli, modules, project


def test_servo_instance_preserves_inputs_and_is_independent(tmp_path):
    source = project.load("servo_link")
    before = (source.dir / "parts/arm.py").read_bytes()
    title = 'My joint: "quoted"\nparts: not_yaml'
    target = modules.instantiate("servo_joint", "my_joint", title, projects_dir=tmp_path)
    instance = project.load(str(target))
    expected = copy.deepcopy(source.data)
    expected["name"] = title
    assert instance.data == expected  # All checks, safety factors, wiring and manufacturing settings remain.
    assert "# stall torque about the output axis" in (target / "project.yaml").read_text()
    proof = json.loads((target / "module.json").read_text())
    assert proof["source_review_record"] == json.loads((source.dir / "review.json").read_text())
    assert proof["source_files_sha256"]["parts/arm.py"] == hashlib.sha256(before).hexdigest()
    assert not any((target / p).exists() for p in ["out", "review.json", "catalog_deps.json", ".cache", "feedback"])
    assert not cli.review_status(str(target))["ok"]
    (target / "parts/arm.py").write_text("# a new design\n")
    assert (source.dir / "parts/arm.py").read_bytes() == before


def test_inspection_uses_real_source_review_and_lists_checks():
    module = modules.describe("servo_joint")
    assert module["source_review"] == cli.review_status("servo_link")
    assert {r["id"] for r in module["requirements"]} >= {"arm_torque", "arm_fea", "bracket_fea", "power"}
    assert module["ports"] == {"mount": "base", "output": "arm.tip", "motion": "swing"}


def test_cli_lists_contract_and_creates_module(tmp_path, monkeypatch, capsys):
    assert cli.main(["modules", "servo_joint", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)[0]
    assert row["id"] == "servo_joint" and row["source_review"]["fingerprint"]
    assert cli.main(["modules", "servo_joint"]) == 0
    out = capsys.readouterr().out
    assert "Interfaces:" in out and "arm_fea" in out and "own check" in out
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["new", "my_joint", "New joint", "--module", "servo_joint"]) == 0
    assert "not checked or reviewed" in capsys.readouterr().out
    assert project.load(str(tmp_path / "projects/my_joint")).name == "New joint"


@pytest.mark.parametrize("name", ["../escape", "/tmp/outside", "a", "bad name", "UPPER", "a" * 42])
def test_invalid_names_create_nothing(tmp_path, name):
    with pytest.raises(ValueError, match="desk_arm"):
        modules.instantiate("servo_joint", name, "Title", projects_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_existing_project_and_symlink_never_overwritten(tmp_path):
    existing = tmp_path / "keep_me"
    existing.mkdir()
    (existing / "precious.txt").write_text("user data")
    alias = tmp_path / "alias"
    alias.symlink_to(existing, target_is_directory=True)
    for name in ["keep_me", "alias"]:
        with pytest.raises(ValueError, match="already exists"):
            modules.instantiate("servo_joint", name, "Title", projects_dir=tmp_path)
    assert (existing / "precious.txt").read_text() == "user data"


def test_unknown_module_has_recovery_and_no_output(tmp_path, capsys):
    with pytest.raises(ValueError, match="kerf modules"):
        modules.instantiate("missing", "my_joint", "Title", projects_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert cli.main(["modules", "missing"]) == 1
    assert "kerf modules" in capsys.readouterr().out


@pytest.mark.parametrize("entry_change, message", [
    ({"source": "../outside"}, "stay inside"),
    ({"files": ["project.yaml", "../secret.txt"]}, "stay inside"),
    ({"files": ["project.yaml", "review.json"]}, "Not a module design input"),
    ({"files": ["project.yaml", "parts/arm.py"]}, "missing source files"),
])
def test_bad_manifest_does_not_make_partial_instance(tmp_path, monkeypatch, entry_change, message):
    entry = modules.entries()["servo_joint"] | entry_change
    monkeypatch.setattr(modules, "entries", lambda: {"servo_joint": entry})
    with pytest.raises(ValueError, match=message):
        modules.instantiate("servo_joint", "my_joint", "Title", projects_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_source_symlink_is_rejected(tmp_path):
    (tmp_path / "outside.py").write_text("private")
    (tmp_path / "parts").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        modules._inside(tmp_path, "parts/outside.py")


@pytest.mark.parametrize("asset, present, error", [
    ("imports/lid.3mf", False, "missing source files"),
    ("../outside.step", False, "stay inside"),
    ("imports/lid.obj", False, "Unsupported imported model"),
    ("imports/lid.3mf", True, None),
])
def test_imported_asset_is_required_and_confined(tmp_path, monkeypatch, asset, present, error):
    source = tmp_path / "projects/source"
    source.mkdir(parents=True)
    text = yaml.safe_dump({"name": "Source", "parts": {"lid": {"import": asset}}, "assembly": {"root": "lid"}})
    (source / "project.yaml").write_text(text)
    files = ["project.yaml"]
    if present:
        (source / "imports").mkdir()
        (source / asset).write_bytes(b"asset snapshot")
        files.append(asset)
    monkeypatch.setattr(modules, "ROOT", tmp_path)
    monkeypatch.setattr(modules, "entries", lambda: {"example": {"source": "source", "files": files}})
    if error:
        with pytest.raises(ValueError, match=error):
            modules._source("example")
    else:
        assert modules._source("example")[2][asset] == b"asset snapshot"


@pytest.mark.parametrize("source_name", ["name: Plain # keep comment\n", "name: |\n  A long\n  old title\n"])
def test_title_changes_preserve_rest_of_yaml(source_name):
    text = source_name + "# engineering notes\nparts: {}\nassembly: {root: base}\n"
    title = "New: title\nwith a newline"
    replaced = modules._title(text, title)
    assert yaml.safe_load(replaced) == {"name": title, "parts": {}, "assembly": {"root": "base"}}
    assert "# engineering notes" in replaced


def test_failed_copy_removes_only_new_directory(tmp_path, monkeypatch):
    original = Path.write_bytes

    def failing(path, content):
        if path.name == "arm.py":
            raise OSError("disk full")
        return original(path, content)

    monkeypatch.setattr(Path, "write_bytes", failing)
    with pytest.raises(OSError, match="disk full"):
        modules.instantiate("servo_joint", "my_joint", "Title", projects_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_instantiated_servo_geometry_and_ports_build(tmp_path):
    from kerf import assembly, requirements

    target = modules.instantiate("servo_joint", "new_joint", "Independent servo joint", projects_dir=tmp_path)
    instance = project.build(project.load(str(target)), cache=False)
    assert all(it.error is None for it in instance.items.values()), [it.error for it in instance.items.values()]
    asm = assembly.plan(instance)
    assembly.solve(asm)
    assert instance.items["arm"].shape.joints["tip"]
    assert [edge.name for edge in asm.movable] == ["swing"]
    result = requirements.run_all(instance, asm, only={"arm_torque"})
    assert len(result) == 1 and result[0]["ok"], result
