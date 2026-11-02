"""Selectable modes (kerf/modes.py, `kerf run --mode`): each mode runs only its stages and writes only its files;
Ship it never runs without an explicit confirmation."""
import shutil
from pathlib import Path

import pytest

from kerf import cli, modes
from kerf.pipeline import run

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    d = tmp_path_factory.mktemp("m") / "servo_link"
    shutil.copytree(ROOT / "projects" / "servo_link", d, ignore=shutil.ignore_patterns("out", "__pycache__"))
    return d


def test_mode_table():
    assert modes.stages("sketch") < modes.stages("print") and modes.stages("check") < modes.stages("simulate") < modes.stages("kit")
    assert "fea" not in modes.stages("print") and "files" not in modes.stages("simulate")
    assert modes.legacy(True, True, True) == modes.stages("kit")                      # kerf build = the kit
    assert modes.legacy(False, False, False) == modes.stages("check") - {"motion", "fea"}   # kerf check --quick
    with pytest.raises(ValueError, match="unknown mode"):
        modes.stages("fast")


def test_sketch_gives_a_viewer_and_nothing_to_print(rig):
    rep = run(str(rig), mode="sketch")
    out = rig / "out"
    assert rep["ok"] and rep["mode"] == "sketch" and rep["requirements"] == []
    assert (out / "viewer.html").exists() and (out / "assembly.glb").exists()
    assert not (out / "plates").exists() and not (out / "bom.md").exists() and not (out / "renders").exists()


def test_print_mode_adds_plates_but_no_fea_or_bom(rig):
    rep = run(str(rig), mode="print")
    out = rig / "out"
    assert rep["ok"] and list((out / "plates").glob("plate_*.3mf")) and (out / "plates" / "PRINT_SETTINGS.md").exists()
    assert not (out / "bom.md").exists()
    fea = [r for r in rep["requirements"] if r["check"] == "fea_static"]
    assert fea and all(r.get("value") is None for r in fea)                         # FEA skipped, not run
    assert rep["cached_parts"]                                                        # the sketch's parts were reused


def test_ship_refuses_without_confirmation(capsys):
    def boom(*a, **k):
        raise AssertionError("nothing may run before Ship it is confirmed")
    assert cli.run_mode("servo_link", "ship", ship_confirmed=False, runner=boom) == 2
    assert "explicit go-ahead" in capsys.readouterr().out
