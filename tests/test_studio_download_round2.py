"""Saved maker downloads stay complete and contained, using temporary fixtures only."""
import io
import urllib.error
import urllib.request
import zipfile

import pytest

from kerf import studio
from test_source_export import make_project
from test_studio import server  # noqa: F401


def test_everything_zip_includes_saved_simulation_archive(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch)
    (root / "out").mkdir()
    saved = b"saved URDF with its simulator meshes"
    (root / "out/demo_urdf.zip").write_bytes(saved)
    with zipfile.ZipFile(io.BytesIO(studio.export_zip("demo"))) as archive:
        assert archive.read("demo/demo_urdf.zip") == saved
    assert (root / "out/demo_urdf.zip").read_bytes() == saved


def test_simulation_archive_obeys_output_containment(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch)
    (root / "out").mkdir()
    private = tmp_path / "private.zip"
    private.write_bytes(b"private fixture")
    (root / "out/demo_urdf.zip").symlink_to(private)
    with pytest.raises(ValueError, match="symbolic links"):
        studio.export_zip("demo")


@pytest.mark.parametrize("surface", ["files", "trial", "history"])
@pytest.mark.parametrize("alias", ["..", "linked"])
def test_download_roots_cannot_escape_via_project_segment(tmp_path, monkeypatch, server, surface, alias):
    root = tmp_path / surface
    root.mkdir()
    private = tmp_path / "private"
    private.mkdir()
    (private / "thumb.png").write_bytes(b"private thumbnail fixture")
    (tmp_path / "private.txt").write_bytes(b"private file fixture")
    (root / "linked").symlink_to(tmp_path, target_is_directory=True)
    monkeypatch.setattr(studio, {"files": "PROJECTS", "trial": "TRIALS", "history": "HISTORY"}[surface], root)
    suffix = "private/thumb.png" if surface == "history" else "private.txt"
    with pytest.raises(urllib.error.HTTPError) as denied:
        urllib.request.urlopen(f"{server}/{surface}/{alias}/{suffix}")
    assert denied.value.code == 404
    assert b"private" not in denied.value.read()


def test_contained_file_trial_and_history_downloads_keep_their_bytes(tmp_path, monkeypatch, server):
    roots = {key: tmp_path / key for key in ("PROJECTS", "TRIALS", "HISTORY")}
    for key, root in roots.items():
        (root / "demo").mkdir(parents=True)
        monkeypatch.setattr(studio, key, root)
    (roots["PROJECTS"] / "demo/design notes.md").write_bytes(b"# Saved guide")
    (roots["TRIALS"] / "demo/model.stl").write_bytes(b"saved trial mesh")
    stamp = "20261102-123456"
    (roots["HISTORY"] / "demo" / stamp).mkdir()
    (roots["HISTORY"] / "demo" / stamp / "thumb.png").write_bytes(b"saved thumbnail")
    for path, expected in (("files/demo/design%20notes.md", b"# Saved guide"),
                           ("trial/demo/model.stl", b"saved trial mesh"),
                           (f"history/demo/{stamp}/thumb.png", b"saved thumbnail")):
        with urllib.request.urlopen(f"{server}/{path}") as response:
            assert response.status == 200 and response.read() == expected
