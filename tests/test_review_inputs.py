"""Temporary synthetic projects: review proof and cached geometry follow their declared local inputs."""
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from kerf import calibrate, catalog, cli, gallery, partcache, pipeline, project, studio


def make_project(tmp_path, monkeypatch, changes=None, files=None):
    root = tmp_path / "projects" / "fixture"
    (root / "parts").mkdir(parents=True)
    data = {"name": "Synthetic review inputs", "parts": {"body": {}}, "assembly": {"root": "body"}} | (changes or {})
    (root / "project.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    (root / "parts/body.py").write_text("# synthetic part source\n", encoding="utf-8")
    for relative, content in (files or {}).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    hardware = tmp_path / "hardware.json"
    hardware.write_text('{"servos":{"used":{"weight_g":10},"unused":{"weight_g":20}}}', encoding="utf-8")
    monkeypatch.setattr(catalog, "CATALOG", hardware)
    monkeypatch.setattr(calibrate, "PRINTERS", tmp_path / "printers")
    monkeypatch.setattr(partcache, "DIR", tmp_path / "partcache")
    monkeypatch.setattr(project, "PROJECTS", root.parent)
    monkeypatch.setattr(studio, "PROJECTS", root.parent)
    monkeypatch.setattr(gallery, "ROOT", tmp_path)
    monkeypatch.delenv("KERF_NO_CACHE", raising=False)
    (root / project.DEPS).write_text('["servos.used"]', encoding="utf-8")
    return root


CASES = [
    ({}, "parts/helpers/dimensions.py"),
    ({"parts": {"body": {"file": "code/body.py"}}}, "code/body.py"),
    ({"layout": "code/layout.py"}, "code/layout.py"),
    ({"parts": {"body": {"import": "imports/nested/body.step"}}}, "imports/nested/body.step"),
    ({"parts": {"body": {"source": "meshy", "mesh": "assets/body.stl"}}}, "assets/body.stl"),
    ({"source_files": ["data/profile.csv", "./data/profile.csv"]}, "data/profile.csv"),
]


@pytest.mark.parametrize("changes,relative", CASES)
def test_declared_input_edit_invalidates_review_comparison(tmp_path, monkeypatch, changes, relative):
    root = make_project(tmp_path, monkeypatch, changes, {relative: b"synthetic before"})
    fp = project.load(str(root)).fingerprint()
    # Fixture-only reviewer response: never write or approve a real project's review.json.
    review = {"verdict": "PASS", "fingerprint": fp, "scores": {"body": {key: 4 for key in cli.INTENT}}}
    original_exists, original_read = Path.exists, Path.read_text
    monkeypatch.setattr(Path, "exists", lambda p: p == root / "review.json" or original_exists(p))
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw: json.dumps(review) if p == root / "review.json" else original_read(p, *a, **kw))
    assert cli.review_status(str(root))["ok"]
    (root / relative).write_bytes(b"synthetic after")
    changed = cli.review_status(str(root))
    assert not changed["ok"] and changed["fingerprint"] != fp and "review again" in changed["why"]


@pytest.mark.parametrize("changes,relative", CASES[1:])
def test_missing_declared_input_has_no_current_fingerprint(tmp_path, monkeypatch, changes, relative):
    root = make_project(tmp_path, monkeypatch, changes, {relative: b"synthetic input"})
    assert project.load(str(root)).fingerprint()
    (root / relative).unlink()
    expected = sorted(changes.get("source_files", [relative]))[0]
    with pytest.raises(project.ProjectError, match=f"Missing design source: {expected}"):
        project.load(str(root)).fingerprint()
    status = cli.review_status(str(root))
    assert status["ok"] is False and status["fingerprint"] is None and relative in status["why"]


def test_nested_helper_rename_and_removal_change_fingerprint(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch, files={"parts/left/helper.py": b"# same bytes"})
    before = project.load(str(root)).fingerprint()
    (root / "parts/left").rename(root / "parts/right")
    renamed = project.load(str(root)).fingerprint()
    assert renamed != before
    (root / "parts/right/helper.py").unlink()
    assert project.load(str(root)).fingerprint() not in {before, renamed}


@pytest.mark.parametrize("manifest", [True, False])
def test_legacy_inputs_keep_their_original_hash_stream(tmp_path, monkeypatch, manifest):
    root = make_project(tmp_path, monkeypatch, files={"meshes/body.stl": b"mesh", "imports/body.step": b"model"})
    profile = calibrate.profile_path(calibrate.DEFAULT_PRINTER)
    profile.parent.mkdir(parents=True)
    profile.write_text('{}', encoding="utf-8")
    if not manifest:
        (root / project.DEPS).unlink()
    # Frozen pre-expansion stream: trusted external catalog/calibration keep their original position and names.
    old = hashlib.sha256()
    if manifest:
        old.update(catalog.deps_hash({"servos.used"}).encode())
    files = [root / "project.yaml", root / "parts/body.py", *([] if manifest else [catalog.CATALOG]),
             root / "meshes/body.stl", root / "imports/body.step", profile]
    for path in files:
        old.update(path.name.encode())
        old.update(path.read_bytes())
    assert project.load(str(root)).fingerprint() == old.hexdigest()[:16]


def test_docs_outputs_and_unused_catalog_do_not_change_review_inputs(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch)
    before = project.load(str(root)).fingerprint()
    for relative in ["DESIGN.md", "REFERENCES.md", "out/report.json", "parts/__pycache__/body.py",
                     "parts/out/generated.py", ".cache/part.py", "review.json", "data/unlisted.csv"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic metadata, not a review approval", encoding="utf-8")
        assert project.load(str(root)).fingerprint() == before, relative
    hardware = json.loads(catalog.CATALOG.read_text(encoding="utf-8"))
    hardware["servos"]["unused"]["weight_g"] = 50
    catalog.CATALOG.write_text(json.dumps(hardware), encoding="utf-8")
    assert project.load(str(root)).fingerprint() == before
    hardware["servos"]["used"]["weight_g"] = 11
    catalog.CATALOG.write_text(json.dumps(hardware), encoding="utf-8")
    assert project.load(str(root)).fingerprint() != before
    data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    data["source_files"] = ["DESIGN.md"]
    (root / "project.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    declared = project.load(str(root)).fingerprint()
    (root / "DESIGN.md").write_text("explicitly a geometry input", encoding="utf-8")
    assert project.load(str(root)).fingerprint() != declared


@pytest.mark.parametrize("invalid", ["missing", "escaping", "linked", "legacy_link", "unreadable", "unreadable_legacy_dir"])
def test_invalid_inputs_fail_closed_without_following_links(tmp_path, monkeypatch, invalid):
    root = make_project(tmp_path, monkeypatch, {"source_files": ["data/profile.csv"]}, {"data/profile.csv": b"2\n"})
    target = root / "data/profile.csv"
    if invalid == "missing":
        target.unlink()
    elif invalid == "escaping":
        data = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
        data["source_files"] = ["../outside.csv"]
        (root / "project.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    elif invalid in {"linked", "legacy_link"}:
        outside = tmp_path / "outside.csv"
        outside.write_text("harmless outside fixture", encoding="utf-8")
        if invalid == "legacy_link":
            (root / "imports").mkdir()
            target = root / "imports/model.step"
        else:
            target.unlink()
        target.symlink_to(outside)
        original = Path.read_bytes
        def no_outside(path):
            assert path != target and path != outside, "must reject link before reading"
            return original(path)
        monkeypatch.setattr(Path, "read_bytes", no_outside)
    elif invalid == "unreadable":
        original = Path.read_bytes
        def unreadable(path):
            if path == target:
                raise PermissionError("synthetic unreadable profile.csv")
            return original(path)
        monkeypatch.setattr(Path, "read_bytes", unreadable)
    else:
        (root / "imports").mkdir()
        original = Path.iterdir
        def unreadable(path):
            if path == root / "imports":
                raise PermissionError("synthetic unreadable imports")
            return original(path)
        monkeypatch.setattr(Path, "iterdir", unreadable)
    with pytest.raises(project.ProjectError):
        project.load(str(root)).fingerprint()
    status = cli.review_status(str(root))
    assert status["ok"] is False and status["fingerprint"] is None
    (root / "out").mkdir()
    (root / "out/report.json").write_text(json.dumps({"ok": True, "fingerprint": None, "files": {"parts": ["body.stl"]}}), encoding="utf-8")
    collected = gallery.collect("fixture", {})
    assert not collected["built"] and not collected["ok"] and not collected["review"]
    assert studio.summary("fixture")["stale"] is True


def test_missing_input_keeps_failed_report_and_build_diagnostics(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch)
    (root / "parts/body.py").unlink()
    report = pipeline.run(str(root), mode="sketch")
    assert report["ok"] is False and report["fingerprint"] is None
    assert any("Missing design source: parts/body.py" in p for p in report["problems"])
    assert "body" in report["diagnoses"]
    assert json.loads((root / "out/report.json").read_text(encoding="utf-8"))["ok"] is False


def test_declared_external_data_recomputes_cached_tiny_geometry(tmp_path, monkeypatch):
    source = b"from pathlib import Path\nfrom build123d import Box\ndef build(ctx):\n    width = float((Path(__file__).parents[1] / 'data/profile.csv').read_text())\n    return ctx.finish(Box(width, 2, 3).solid())\n"
    root = make_project(tmp_path, monkeypatch, {"source_files": ["data/profile.csv"]},
                        {"parts/body.py": source, "data/profile.csv": b"2\n"})
    cold = project.build(project.load(str(root)))
    assert cold.items["body"].error is None and cold.items["body"].shape.volume == pytest.approx(12)
    warm = project.build(project.load(str(root)))
    assert warm.items["body"].cached
    (root / "data/profile.csv").write_bytes(b"4\n")
    changed = project.build(project.load(str(root)))
    assert changed.items["body"].error is None and not changed.items["body"].cached
    assert changed.items["body"].shape.volume == pytest.approx(24)
    assert project.build(project.load(str(root))).items["body"].cached
