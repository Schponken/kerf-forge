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


def test_model_first(rig, monkeypatch, capsys):
    """The 3D model comes first (Spencer, 2026-11-02): a preview viewer is written and announced before the print
    checks start, the parts go back to where they were modelled for those checks, and the full viewer replaces it."""
    from kerf import pipeline, viewer
    seen = {}
    real = viewer.write

    def spy(proj, asm, rep, path, fea=None, preview=False):
        if preview:
            seen["at_stage"] = list(seen.get("stages", []))
            seen["data"] = viewer.data(proj, asm, rep, preview=True)
        return real(proj, asm, rep, path, fea=fea, preview=preview)
    stage = pipeline.progress.stage
    monkeypatch.setattr(pipeline.progress, "stage", lambda k: (seen.setdefault("stages", []).append(k), stage(k)))
    monkeypatch.setattr(pipeline.viewer, "write", spy)
    before = run(str(rig), mode="check")["parts"]                 # no viewer stage: no preview
    assert "data" not in seen
    seen["stages"] = []
    rep = run(str(rig), mode="sketch")
    assert "print" not in seen["at_stage"]                        # written before the print checks began
    d = seen["data"]
    assert d["report"]["preview"] is True and d["steps"] is None and "when the checks finish" in d["attr_error"]
    assert "3D model ready" in capsys.readouterr().out
    assert {k: v["problems"] for k, v in rep["parts"].items()} == {k: v["problems"] for k, v in before.items()}
    full = viewer.embedded(rig / "out" / "viewer.html")
    assert full["report"]["preview"] is False                     # the final viewer replaced the preview


def test_studio_shows_the_model_first():
    """Studio opens the 3D tab on the run's "model" event and says the rest is still running."""
    html = (ROOT / "kerf" / "assets" / "studio.html").read_text(encoding="utf-8")
    assert 'j.events.some(e => e.k === "model")' in html and "async function modelReady(j)" in html
    assert "still checking, making the print files and pictures in the background" in html
    viewer_html = (ROOT / "kerf" / "assets" / "viewer.html").read_text(encoding="utf-8")
    assert "R.preview ? 'checks running…'" in viewer_html
