"""Kerf Studio features Spencer picked (2026-11-01): materials per part, duplicate, compare, thumbnails, notifications,
"Do it" edit jobs. Everything here runs without Claude Code, a display or the network."""
import base64
import gzip
import json
import subprocess

import numpy as np
import pytest
import yaml

from kerf import studio

YAML = """name: Demo rig   # the title
params:
  arm_len: {value: 100, min: 60, max: 140}
parts:
  base: {file: parts/base.py, material: PETG, infill: 0.3,
         note: "a note, with: commas {and braces}"}   # keep me
  arm: {file: parts/arm.py, infill: 0.3}
  block:
    file: parts/block.py
    material: PLA   # block style
  bare:
    file: parts/bare.py
purchased: {}
"""


def _proj(tmp_path, monkeypatch, name="demo"):
    root = tmp_path / "projects"
    d = root / name
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(YAML)
    (d / "parts" / "base.py").write_text("# base\n")
    (d / "DESIGN.md").write_text("# design\n")
    (d / "out").mkdir()
    (d / "out" / "report.json").write_text("{}")
    (d / "review.json").write_text("{}")
    monkeypatch.setattr(studio, "PROJECTS", root)
    return d


def test_write_materials_flow_block_and_missing_keep_comments(tmp_path, monkeypatch):
    d = _proj(tmp_path, monkeypatch)
    f = d / "project.yaml"
    assert sorted(studio.write_materials(f, {"base": "ASA", "arm": "PLA", "block": "PETG", "bare": "TPU"})) == ["arm", "bare", "base", "block"]
    txt = f.read_text()
    assert "# keep me" in txt and "# block style" in txt and "# the title" in txt and "commas {and braces}" in txt
    parts = yaml.safe_load(txt)["parts"]
    assert {k: v["material"] for k, v in parts.items()} == {"base": "ASA", "arm": "PLA", "block": "PETG", "bare": "TPU"}
    assert parts["base"]["infill"] == 0.3 and parts["block"]["file"] == "parts/block.py"
    assert studio.write_materials(f, {"base": "ASA"}) == []            # no change, file untouched
    with pytest.raises(ValueError, match="unknown material"):
        studio.write_materials(f, {"base": "UNOBTAINIUM"})
    with pytest.raises(ValueError, match="unknown printed part"):
        studio.write_materials(f, {"nope": "PLA"})


def test_materials_come_from_the_catalog_with_prices():
    M = {m["key"]: m for m in studio.materials()}
    assert {"PLA", "PETG", "ASA", "TPU"} <= set(M)
    assert M["PETG"]["xy_mpa"] > M["PETG"]["z_mpa"] > 0 and M["PETG"]["density"] > 1
    assert M["PETG"]["usd_per_kg"] and M["PETG"]["source"].startswith("http")


def test_trial_copy_takes_materials_and_leaves_the_project_alone(tmp_path, monkeypatch):
    d = _proj(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "TRIALS", tmp_path / "trials")
    dst = studio.trial_copy("demo", {"arm_len": 90}, {"arm": "PLA"})
    assert yaml.safe_load((dst / "project.yaml").read_text())["parts"]["arm"]["material"] == "PLA"
    assert "material" not in yaml.safe_load((d / "project.yaml").read_text())["parts"]["arm"]


def test_duplicate_copies_design_files_only_and_renames(tmp_path, monkeypatch):
    _proj(tmp_path, monkeypatch)
    dst = studio.duplicate("demo", "demo_v2", "Demo rig, long arm")
    assert (dst / "parts" / "base.py").exists() and (dst / "DESIGN.md").exists()
    assert not (dst / "out").exists() and not (dst / "review.json").exists()
    txt = (dst / "project.yaml").read_text()
    assert yaml.safe_load(txt)["name"] == "Demo rig, long arm" and "# the title" in txt
    assert yaml.safe_load(studio.duplicate("demo", "demo_v3").joinpath("project.yaml").read_text())["name"] == "Demo rig (copy)"
    for bad in ("Bad Name", "demo_v2", "x"):
        with pytest.raises(ValueError):
            studio.duplicate("demo", bad)
    with pytest.raises(ValueError, match="no such project"):
        studio.duplicate("nope", "fine_name")


def _item(iid, verts, tris):
    return {"id": iid, "role": "printed", "verts": base64.b64encode(np.asarray(verts, np.float32).tobytes()).decode(),
            "tris": base64.b64encode(np.asarray(tris, np.uint32).tobytes()).decode()}


def _box(dx=0.0, sx=10.0):
    import trimesh
    m = trimesh.creation.box((sx, 10, 10))
    m.apply_translation((dx, 0, 0))
    return m.vertices, m.faces


def test_compare_reports_moved_same_added_removed(monkeypatch):
    a = {"fingerprint": "A", "items": [_item("same", *_box()), _item("grown", *_box()), _item("gone", *_box())]}
    b = {"fingerprint": "B", "items": [_item("same", *_box()), _item("grown", *_box(sx=14.0)), _item("new", *_box())]}
    monkeypatch.setattr(studio, "_geom_of", lambda name, which: (a, "the old one") if which == "old" else (b, "now"))
    c = studio.compare("demo", "old", "saved")
    S = {x["id"]: x for x in c["summary"]}
    assert S["same"]["status"] == "same" and S["new"]["status"] == "added" and S["gone"]["status"] == "removed"
    assert S["grown"]["status"] == "changed" and S["grown"]["max_mm"] == pytest.approx(2.0, abs=0.05)
    d = np.frombuffer(base64.b64decode(c["dist"]["grown"]), np.uint8) / 20   # per vertex of the new box: 2 mm on the ends
    assert d.max() == pytest.approx(2.0, abs=0.05)
    assert {it["id"] for it in c["items"]} == {"grown", "gone"} and c["label"] == "the old one"


def test_snapshot_keeps_geometry_and_compare_reads_it(tmp_path, monkeypatch):
    from kerf import viewer
    d = _proj(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "HISTORY", tmp_path / "hist")
    rep = {"fingerprint": "F1", "ok": True, "problems": [], "params": {"arm_len": 100}}
    (d / "out" / "report.json").write_text(json.dumps(rep))
    page = viewer.html({"items": [_item("arm", *_box())], "report": {"project": "x", "fingerprint": "F1"}, "joints": [],
                        "bounds": [[0, 0, 0], [1, 1, 1]]})
    (d / "out" / "viewer.html").write_text(page)
    e = studio.snapshot("demo")
    assert e["geom"] and (tmp_path / "hist" / "demo" / e["stamp"] / "geom.json.gz").exists()
    g = json.loads(gzip.decompress((tmp_path / "hist" / "demo" / e["stamp"] / "geom.json.gz").read_bytes()))
    assert g["fingerprint"] == "F1" and [i["id"] for i in g["items"]] == ["arm"]
    c = studio.compare("demo", e["stamp"], "saved")
    assert c["summary"] == [{"id": "arm", "status": "same", "max_mm": 0.0}]
    with pytest.raises(ValueError):
        studio.compare("demo", "../../etc", "saved")


def test_thumbnails_only_take_pngs(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "THUMBS", tmp_path / "th")
    png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()
    assert studio.thumb_info("demo")["url"] is None
    studio.save_thumb("demo", png, "FP")
    t = studio.thumb_info("demo")
    assert t["url"].startswith("/thumb/demo.png?v=") and t["fingerprint"] == "FP"
    for bad in ("data:image/jpeg;base64,AAAA", "data:image/png;base64," + base64.b64encode(b"GIF89a").decode()):
        with pytest.raises(ValueError):
            studio.save_thumb("demo", bad, None)


class _Job:
    def __init__(self, kind="build", state="done", secs=120.0, project="demo", label="Build demo"):
        self.kind, self.state, self.project, self.label = kind, state, project, label
        self.started, self.ended = 1000.0, 1000.0 + secs


def test_notifications_mac_linux_off_and_quiet_cases(tmp_path, monkeypatch):
    _proj(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "SETTINGS", tmp_path / "s.json")
    calls = []
    monkeypatch.setattr(studio.subprocess, "run", lambda cmd, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0))
    monkeypatch.setattr(studio.platform, "system", lambda: "Darwin")
    (studio.PROJECTS / "demo" / "out" / "report.json").write_text(json.dumps({"problems": ["a", "b"]}))
    assert studio.notify_job(_Job(label='Build "demo"'))
    script = calls[-1][2]
    assert calls[-1][:2] == ["osascript", "-e"] and 'subtitle "Build \\"demo\\""' in script
    assert "2 problems to fix (2:00)" in script and 'sound name "Basso"' in script
    assert not studio.notify_job(_Job(secs=5))                       # a quick check: you watched it
    assert studio.notify_job(_Job(kind="edit", secs=5))              # Claude Code jobs always
    assert not studio.notify_job(_Job(state="stopped"))              # you stopped it yourself
    studio.save_settings({"notify": False})
    n = len(calls)
    assert not studio.notify_job(_Job()) and len(calls) == n
    studio.save_settings({"notify": True})
    monkeypatch.setattr(studio.platform, "system", lambda: "Linux")
    monkeypatch.setattr(studio.shutil, "which", lambda x: "/usr/bin/notify-send" if x == "notify-send" else None)
    assert studio.notify_job(_Job()) and calls[-1][0] == "notify-send"
    monkeypatch.setattr(studio.shutil, "which", lambda x: None)
    assert not studio.notify_job(_Job())


def test_edit_job_is_scoped_to_its_project(tmp_path, monkeypatch):
    _proj(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "claude_ready", lambda: {"ok": False, "code": "auth", "why": "not signed in"})
    with pytest.raises(studio.ClaudeNotReady):
        studio.edit_job("demo", "make it longer")
    monkeypatch.setattr(studio, "claude_ready", lambda: {"ok": True, "code": None, "why": "ready"})
    monkeypatch.setattr(studio, "claude_bin", lambda: "/bin/claude")
    got = {}
    monkeypatch.setattr(studio, "start_job", lambda *a, **k: got.update(args=a, kw=k) or "job")
    studio.edit_job("demo", "make the arm 20 mm longer", "arm_len 100 -> 120")
    kind, project, cmd, label = got["args"]
    assert kind == "edit" and project == "demo" and got["kw"]["env"] == {"KERF_STUDIO_JOB": "demo"}
    assert cmd[1] == "-p" and cmd[2].startswith("make the arm 20 mm longer") and "projects/demo only" in cmd[2]
    assert label == "Change demo: arm_len 100 -> 120"
    for bad in (("nope", "x"), ("demo", "  ")):
        with pytest.raises(ValueError):
            studio.edit_job(*bad)
