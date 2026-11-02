"""Downloaded declared sources rebuild independently; caches, secrets and approval never travel with them."""
import io
import shutil
import urllib.error
import urllib.request
import zipfile

import pytest
import yaml

from kerf import partcache, project, sources, studio
from test_studio import server  # noqa: F401


def make_project(tmp_path, monkeypatch, data=None, files=None):
    root = tmp_path / "projects" / "demo"
    root.mkdir(parents=True)
    data = data or {"name": "Synthetic export", "parts": {"body": {"file": "parts/body.py"}}, "assembly": {"root": "body"}}
    (root / "project.yaml").write_text(yaml.safe_dump(data))
    for relative, content in (files or {"parts/body.py": b"# source"}).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    monkeypatch.setattr(studio, "PROJECTS", root.parent)
    return root


def archive():
    return zipfile.ZipFile(io.BytesIO(studio.export_zip("demo")))


def test_extracted_sources_build_with_nested_helper_data_layout_and_import(tmp_path, monkeypatch):
    from build123d import Box, export_step

    data = {"name": "Synthetic export", "source_files": ["parts/helpers/profile.csv", "./parts/helpers/profile.csv"], "layout": "parts/layout.py",
            "parts": {"body": {"file": "parts/body.py"}, "lid": {"import": "imports/lid.step"}}, "assembly": {"root": "body"}}
    files = {
        "parts/body.py": b"from pathlib import Path\nimport runpy\nfrom build123d import Box\ndef build(ctx):\n    helper = runpy.run_path(str(Path(__file__).parent / 'helpers/profile.py'))\n    return ctx.finish(Box(helper['width'](), 2, ctx.p.height))\n",
        "parts/helpers/profile.py": b"from pathlib import Path\nimport csv\ndef width():\n    with Path(__file__).with_suffix('.csv').open() as f:\n        return float(next(csv.DictReader(f))['width'])\n",
        "parts/helpers/profile.csv": b"width\n7\n",
        "parts/layout.py": b"def layout(p, cat):\n    return {'height': 3}\n",
        "DESIGN.md": b"# Synthetic assembly\n", "REFERENCES.md": b"# Test fixture; no engineering evidence\n",
        "out/bom.md": b"# Maker BOM\n", "out/plates/plate.3mf": b"maker plate fixture",
        "out/parts/body.stl": b"maker mesh fixture", "out/parts/body.glb": b"viewer cache",
        "parts/__pycache__/cached.py": b"# do not export", "parts/.private.py": b"# do not export",
        "parts/unlisted.csv": b"unrelated data", ".env": b"PRIVATE=fixture", "secrets.json": b"{}",
        "review.json": b'{"ok":true}', "catalog_deps.json": b"[]", "out/report.json": b"{}",
    }
    root = make_project(tmp_path, monkeypatch, data, files)
    (root / "imports").mkdir()
    export_step(Box(2, 3, 4), root / "imports/lid.step")
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    z = archive()
    expected = {"project.yaml", "DESIGN.md", "REFERENCES.md", "parts/body.py", "parts/layout.py",
                "parts/helpers/profile.py", "parts/helpers/profile.csv", "imports/lid.step"}
    assert {n.removeprefix("demo/design/") for n in z.namelist() if n.startswith("demo/design/")} == expected
    assert {"demo/bom.md", "demo/plates/plate.3mf", "demo/parts/body.stl"} <= set(z.namelist())
    assert not any(n.endswith(("review.json", "report.json", ".glb", ".env")) for n in z.namelist())
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    z.extractall(tmp_path / "download")
    shutil.rmtree(root)  # The rebuilt project cannot accidentally read the original helper, data or STEP.
    extracted = tmp_path / "download/demo/design"
    monkeypatch.setattr(partcache, "DIR", tmp_path / "partcache")
    built = project.build(project.load(str(extracted)), cache=False)
    assert all(item.error is None for item in built.items.values()), [i.error for i in built.items.values()]
    assert built.items["body"].shape.volume == pytest.approx(42)
    assert built.items["lid"].shape.volume == pytest.approx(24)
    assert not (extracted / "review.json").exists()


@pytest.mark.parametrize("asset", ["imports/lid.step", "imports/lid.stp", "imports/lid.stl", "imports/lid.3mf"])
def test_declared_import_formats_keep_their_bytes(tmp_path, monkeypatch, asset):
    data = {"name": "Synthetic import", "parts": {"lid": {"import": asset}}, "assembly": {"root": "lid"}}
    make_project(tmp_path, monkeypatch, data, {asset: b"illustrative imported bytes"})
    assert archive().read(f"demo/design/{asset}") == b"illustrative imported bytes"


def test_meshy_default_asset_and_external_python_entry_are_declared_inputs(tmp_path, monkeypatch):
    data = {"name": "Synthetic shell", "parts": {"shell": {"file": "code/shell.py", "source": "meshy"}},
            "assembly": {"root": "shell"}, "source_files": ["code/helper.py"]}
    make_project(tmp_path, monkeypatch, data, {"code/shell.py": b"# source", "code/helper.py": b"# helper",
                                              "meshes/shell.glb": b"illustrative shell bytes"})
    assert {"demo/design/code/shell.py", "demo/design/code/helper.py", "demo/design/meshes/shell.glb"} <= set(archive().namelist())


@pytest.mark.parametrize("change, missing", [
    ({"parts": {"body": {"file": "parts/missing.py"}}}, "parts/missing.py"),
    ({"parts": {"body": {"import": "imports/missing.step"}}}, "imports/missing.step"),
    ({"parts": {"body": {"source": "meshy"}}}, "meshes/body.glb"),
    ({"layout": "parts/missing_layout.py"}, "parts/missing_layout.py"),
    ({"source_files": ["data/missing.csv"]}, "data/missing.csv"),
])
def test_missing_declared_input_refuses_archive(tmp_path, monkeypatch, change, missing):
    root = make_project(tmp_path, monkeypatch)
    data = yaml.safe_load((root / "project.yaml").read_text()) | change
    (root / "project.yaml").write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match=f"Missing design source: {missing}"):
        studio.export_zip("demo")


@pytest.mark.parametrize("relative", ["../outside.csv", "/tmp/outside.csv", "C:/outside.csv", "..\\outside.csv",
    "out/report.json", "review.json", "parts/__pycache__/input.pyc", ".env", "data/secrets.json", "data/key.pem"])
def test_unsafe_or_private_manifest_inputs_refuse_archive(tmp_path, monkeypatch, relative):
    root = make_project(tmp_path, monkeypatch)
    data = yaml.safe_load((root / "project.yaml").read_text()) | {"source_files": [relative]}
    (root / "project.yaml").write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="stay inside|Not a design source"):
        studio.export_zip("demo")


@pytest.mark.parametrize("link", ["part", "helper_dir", "project"])
def test_symlink_sources_are_not_followed(tmp_path, monkeypatch, link):
    root = make_project(tmp_path, monkeypatch)
    outside = tmp_path / "private"
    outside.mkdir()
    (outside / "secret.py").write_text("private bytes")
    if link == "part":
        (root / "parts/body.py").unlink()
        (root / "parts/body.py").symlink_to(outside / "secret.py")
    elif link == "helper_dir":
        (root / "parts/helpers").symlink_to(outside, target_is_directory=True)
    else:
        renamed = root.with_name("actual")
        root.rename(renamed)
        root.symlink_to(renamed, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic links"):
        studio.export_zip("demo")


@pytest.mark.parametrize("extra", ["data/table.csv", {"file": "data/table.csv"}, [None]])
def test_source_manifest_requires_an_explicit_file_list(tmp_path, monkeypatch, extra):
    root = make_project(tmp_path, monkeypatch)
    data = yaml.safe_load((root / "project.yaml").read_text()) | {"source_files": extra}
    (root / "project.yaml").write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="source_files must be a list"):
        sources.design_files(root)


def test_export_route_explains_missing_source_instead_of_returning_a_partial_zip(tmp_path, monkeypatch, server):
    root = make_project(tmp_path, monkeypatch)
    (root / "parts/body.py").unlink()
    with pytest.raises(urllib.error.HTTPError) as failed:
        urllib.request.urlopen(server + "/export/demo.zip")
    assert failed.value.code == 400
    assert "application/json" in failed.value.headers["Content-Type"]
    assert "Missing design source: parts/body.py" in failed.value.read().decode()


@pytest.mark.parametrize("content", [b"name: [broken YAML", b"name: \xff"])
def test_export_route_explains_malformed_contract(tmp_path, monkeypatch, server, content):
    root = make_project(tmp_path, monkeypatch)
    (root / "project.yaml").write_bytes(content)
    with pytest.raises(urllib.error.HTTPError) as failed:
        urllib.request.urlopen(server + "/export/demo.zip")
    assert failed.value.code == 400
    assert "application/json" in failed.value.headers["Content-Type"]
    assert "Invalid project.yaml" in failed.value.read().decode()
