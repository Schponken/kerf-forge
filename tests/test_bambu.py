"""kerf print (kerf/bambu.py): orientation choice, slicer command, LAN payloads and the send/poll loop with fake
FTPS/MQTT links (dry run: no printer, no network, no slicer needed)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from build123d import Align, Box, Pos

from kerf import bambu
from kerf.ctx import Ctx
from test_engine import HINGE_ARM, HINGE_BASE, HINGE_YAML, _write_project


def test_24_orientations():
    rs = bambu.rotations()
    assert len(rs) == 24 and (0, 0, 0) in rs


def _tee(load_axis=None, rot=(0, 0, 0)):
    """A T: 10 x 10 post 20 tall, 40 x 10 wings on top, extruded 40 deep in Y (so lying on its side is tall)."""
    post = Box(10, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    top = Pos(0, 0, 20) * Box(40, 40, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    shape = Ctx("tee", {}).finish(post + top)
    spec = {"print_rot": list(rot)}
    if load_axis:
        spec["load_axis"] = load_axis
    return SimpleNamespace(id="tee", shape=shape, spec=spec)


def test_orient_removes_support_and_reports_it():
    o = bambu.orient(_tee(), "Bambu Lab A2L")
    assert o["designed"]["overhang_mm2"] == pytest.approx(2 * 15 * 40, rel=0.02)   # wing undersides
    assert o["changed"] and o["chosen"]["overhang_mm2"] < 1 and o["chosen"]["height_mm"] == pytest.approx(25)
    assert "less support" in o["why"]


def test_orient_respects_load_axis():
    # flipped (wings on the bed) is support-free but leaves the post's load axis Z vertical, across the layers:
    # with load_axis Z the part must lie on its side instead (also support-free, Z in the bed plane)
    o = bambu.orient(_tee(load_axis="z"), "Bambu Lab A2L")
    assert o["chosen"]["load_ok"] and o["chosen"]["overhang_mm2"] < 1 and o["chosen"]["height_mm"] == pytest.approx(40)


def test_orient_keeps_a_good_design_choice():
    o = bambu.orient(_tee(rot=(180, 0, 0)), "Bambu Lab A2L")
    assert not o["changed"] and o["rot"] == [180, 0, 0] and o["why"] == "keeps the designed print_rot"


def test_slice_command_and_missing_settings(tmp_path):
    sl = {"machine": "/m.json", "process": "/p.json", "filaments": {"PETG": "/petg.json"}}
    c = bambu.slice_cmd("/bin/bs", tmp_path / "plate_1.3mf", tmp_path / "plate_1.gcode.3mf", sl, ["PETG"])
    assert c == ["/bin/bs", "--arrange", "0", "--load-settings", "/m.json;/p.json", "--load-filaments", "/petg.json",
                 "--slice", "0", "--debug", "2", "--export-3mf", str(tmp_path / "plate_1.gcode.3mf"), str(tmp_path / "plate_1.3mf")]
    with pytest.raises(ValueError, match="filaments.PLA"):
        bambu.slice_cmd("/bin/bs", tmp_path / "a.3mf", tmp_path / "b.3mf", sl, ["PETG", "PLA"])


def test_payloads_and_import_url():
    p = bambu.project_file_payload("finger plate_1.gcode.3mf", plate=1, seq=7)["print"]
    assert p["command"] == "project_file" and p["param"] == "Metadata/plate_1.gcode" and p["url"] == "ftp:///finger plate_1.gcode.3mf"
    assert p["sequence_id"] == "7" and p["bed_type"] == "auto" and p["project_id"] == p["task_id"] == "0" and p["use_ams"] is False
    assert bambu.pushall_payload(3) == {"pushing": {"sequence_id": "3", "command": "pushall", "version": 1, "push_target": 1}}
    assert bambu.import_url(Path("/tmp/a b.3mf"), "Cube") == "bambu-connect://import-file?path=%2Ftmp%2Fa%20b.3mf&name=Cube&version=1.0.0"


class FakeFTPS:
    def __init__(self):
        self.uploads = []

    def upload(self, local, remote):
        self.uploads.append((Path(local).name, remote))


class FakeMQTT:
    """Answers each pushall with the next canned report; P-series printers send only changed fields."""

    def __init__(self, script):
        self.sent, self.reports, self.script = [], [], list(script)

    def publish(self, payload):
        self.sent.append(payload)
        if "pushing" in payload and self.script:
            self.reports.append({"print": self.script.pop(0)})


def test_send_uploads_starts_and_polls(tmp_path):
    f = tmp_path / "rig plate_1.gcode.3mf"
    f.write_bytes(b"x")
    cfg = {"printer": {"host": "10.0.0.5", "serial": "SN1", "access_code": "12345678"}}
    ftp, mq = FakeFTPS(), FakeMQTT([{"gcode_state": "IDLE", "mc_percent": 0}, {"gcode_state": "PREPARE"},
                                    {"gcode_state": "RUNNING", "mc_percent": 1}])
    r = bambu.send(cfg, f, ftps=ftp, mqtt=mq, sleep=lambda s: None)
    assert ftp.uploads == [(f.name, f.name)]
    assert mq.sent[0]["print"]["command"] == "project_file" and all("pushing" in m for m in mq.sent[1:])
    assert r["started"] and r["status"] == {"gcode_state": "PREPARE", "mc_percent": 0}   # merged partial reports


def test_send_reports_a_failure_and_needs_credentials(tmp_path):
    f = tmp_path / "x.gcode.3mf"
    f.write_bytes(b"x")
    cfg = {"printer": {"host": "h", "serial": "s", "access_code": "a"}}
    r = bambu.send(cfg, f, ftps=FakeFTPS(), mqtt=FakeMQTT([{"gcode_state": "FAILED", "print_error": 50348044}]), sleep=lambda s: None)
    assert not r["started"] and r["status"]["print_error"] == 50348044
    with pytest.raises(ValueError, match="access_code"):
        bambu.send({"printer": {"host": "h", "serial": "s"}}, f, ftps=FakeFTPS(), mqtt=FakeMQTT([]))
    assert bambu.mask(cfg)["printer"]["access_code"] == "********" and cfg["printer"]["access_code"] == "a"


def test_run_dry_and_fallback(tmp_path):
    d = _write_project(tmp_path / "hinge", HINGE_YAML, {"base": HINGE_BASE, "arm": HINGE_ARM})
    out = []
    r = bambu.run(str(d), dry_run=True, cfg={}, say=out.append)          # no slicer here -> fallback
    assert r["fallback"] and r["fallback"]["bambu_connect"][0].startswith("bambu-connect://import-file?path=")
    assert all(Path(p).exists() for p in r["fallback"]["plates"])
    fake = tmp_path / "BambuStudio"
    fake.write_text("")
    cfg = {"slicer": {"bin": str(fake), "machine": "/m.json", "process": "/p.json", "filaments": {"PETG": "/f.json"}},
           "printer": {"host": "10.0.0.5", "serial": "SN1", "access_code": "12345678"}}
    out.clear()
    r = bambu.run(str(d), dry_run=True, send_plate=1, cfg=cfg, say=out.append)
    assert r["sliced"] and r["sliced"][0].endswith("plate_1.gcode.3mf")
    assert any(l.startswith("would run: ") and "--export-3mf" in l for l in out)
    assert any("would upload plate_1.gcode.3mf" in l and "12345678" not in l for l in out)   # never prints the code

    def runner(cmd, **kw):                                               # a slicer that writes its output
        Path(cmd[-2]).write_bytes(b"sliced")
        return SimpleNamespace(returncode=0, stderr="")
    r = bambu.run(str(d), cfg=cfg, runner=runner, say=lambda s: None)
    assert Path(r["sliced"][0]).read_bytes() == b"sliced"
