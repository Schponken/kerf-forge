"""Maker ZIP inputs are regular contained files; invalid outputs fail before any archive is started."""
import io
import os
from pathlib import Path
import socket
import urllib.error
import urllib.request
import zipfile

import pytest

from kerf import studio
from test_source_export import make_project
from test_studio import server  # noqa: F401


def test_regular_nested_outputs_and_additive_supplier_reports_keep_their_bytes(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch)
    # The separately developed supplier and fastener report additions extend these same lists.
    monkeypatch.setattr(studio, "EXPORT_DIRS", (*studio.EXPORT_DIRS, "manufacturing"))
    monkeypatch.setattr(studio, "EXPORT_FILES", (*studio.EXPORT_FILES, "FASTENER_MASS.md"))
    wanted = {"parts/nested/body.stl": b"mesh", "plates/set one/plate.3mf": b"plate",
              "firmware/src/main.ino": b"firmware", "drawings/side.svg": b"drawing",
              "manufacturing/panel.dxf": b"supplier geometry", "manufacturing/ORDER.md": b"supplier guide",
              "FASTENER_MASS.md": b"fastener inventory", "bom.md": b"BOM"}
    for relative, content in {**wanted, "parts/preview.glb": b"preview cache", "report.json": b"not a maker file"}.items():
        path = root / "out" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with zipfile.ZipFile(io.BytesIO(studio.export_zip("demo"))) as z:
        maker = {n.removeprefix("demo/"): z.read(n) for n in z.namelist() if not n.startswith("demo/design/")}
    assert maker == wanted
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("case", ["output-root-link", "selected-directory-link", "nested-directory-link", "file-link",
    "named-file-link", "dangling-link", "fifo", "socket", "output-not-directory", "selected-not-directory", "named-not-file"])
def test_invalid_maker_outputs_refuse_before_zip_creation(tmp_path, monkeypatch, case):
    root = make_project(tmp_path, monkeypatch)
    private = tmp_path / "private_fixture"
    private.mkdir()
    (private / "fixture.stl").write_bytes(b"harmless private fixture")
    out = root / "out"
    connection = None
    if case == "output-root-link":
        out.symlink_to(private, target_is_directory=True)
    elif case == "output-not-directory":
        out.write_bytes(b"wrong type")
    else:
        out.mkdir()
        if case == "selected-directory-link":
            (out / "parts").symlink_to(private, target_is_directory=True)
        elif case == "selected-not-directory":
            (out / "parts").write_bytes(b"wrong type")
        elif case == "named-file-link":
            (out / "bom.md").symlink_to(private / "fixture.stl")
        elif case == "named-not-file":
            (out / "bom.md").mkdir()
        else:
            (out / "parts").mkdir()
            target = out / "parts" / "fixture.stl"
            if case == "nested-directory-link":
                (out / "parts" / "nested").symlink_to(private, target_is_directory=True)
            elif case == "file-link":
                target.symlink_to(private / "fixture.stl")
            elif case == "dangling-link":
                target.symlink_to(private / "absent.stl")
            elif case == "fifo":
                os.mkfifo(target)
            elif case == "socket":
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                monkeypatch.chdir(target.parent)  # macOS limits the socket pathname length; the fixture path is long.
                connection.bind(target.name)
    def no_archive(*args, **kwargs):
        raise AssertionError("An invalid output reached ZipFile")
    monkeypatch.setattr(zipfile, "ZipFile", no_archive)
    try:
        with pytest.raises(ValueError, match="symbolic links|Expected maker output"):
            studio.export_zip("demo")
    finally:
        if connection:
            connection.close()


@pytest.mark.parametrize("empty_directory", [False, True])
def test_absent_optional_outputs_still_export_sources(tmp_path, monkeypatch, empty_directory):
    root = make_project(tmp_path, monkeypatch)
    if empty_directory:
        (root / "out").mkdir()
    with zipfile.ZipFile(io.BytesIO(studio.export_zip("demo"))) as z:
        assert set(z.namelist()) == {"demo/design/project.yaml", "demo/design/parts/body.py"}


def test_unreadable_output_traversal_refuses_without_a_partial_archive(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch)
    denied = root / "out/parts/nested"
    denied.mkdir(parents=True)
    (denied / "body.stl").write_bytes(b"maker fixture")
    scandir = os.scandir
    def fail_nested(path):
        if Path(path) == denied:
            raise PermissionError("Unreadable maker output directory")
        return scandir(path)
    monkeypatch.setattr(os, "scandir", fail_nested)
    with pytest.raises(PermissionError, match="Unreadable maker output directory"):
        studio.export_zip("demo")


def test_export_route_explains_invalid_maker_output(tmp_path, monkeypatch, server):
    root = make_project(tmp_path, monkeypatch)
    (root / "out").mkdir()
    os.mkfifo(root / "out/bom.md")
    with pytest.raises(urllib.error.HTTPError) as failed:
        urllib.request.urlopen(server + "/export/demo.zip")
    assert failed.value.code == 400 and "application/json" in failed.value.headers["Content-Type"]
    assert "Expected maker output regular file: out/bom.md" in failed.value.read().decode()
