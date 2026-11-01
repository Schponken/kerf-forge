"""Print package (kerf/printpkg.py): per plate grams/time, per part slicer settings, orientation in words, slicer path."""
import json
import os
import stat
import sys
import zipfile
from types import SimpleNamespace as NS

from kerf import printpkg


def test_orientation_words_follow_the_print_rotation():
    assert printpkg.orientation_words([0, 0, 0]) == "on its bottom (-Z) face"
    assert printpkg.orientation_words([180, 0, 0]) == "on its top (+Z) face"
    assert printpkg.orientation_words([90, 0, 0]) == "on its -Y face"      # +90 about X takes -Y to -Z
    assert printpkg.orientation_words([0, 90, 0]) == "on its +X face"
    assert printpkg.orientation_words([30, 0, 0]).endswith("(tilted)")


def test_supports_and_brim_rules():
    flat = {"size_mm": [80, 60, 10], "overhang_pct": 2.6}
    assert printpkg.part_settings(flat, {})["supports"] is False             # bridges / hole tops: no supports
    assert printpkg.part_settings({**flat, "overhang_pct": 11}, {})["supports"] is True
    assert printpkg.part_settings({**flat, "overhang_pct": 11}, {"supports": "avoid"})["supports"] is False
    assert printpkg.part_settings(flat, {"supports": "needed"})["supports"] is True
    tall = {"size_mm": [10, 12, 60], "overhang_pct": 0}
    st = printpkg.part_settings(tall, {})
    assert st["brim"] == "outer_only" and st["brim_mm"] == 5
    assert printpkg.part_settings(flat, {})["brim"] == "auto_brim"


def _sliced(path, seconds, grams):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Metadata/slice_info.config", f'<config><plate><metadata key="index" value="1"/>'
                   f'<metadata key="prediction" value="{seconds}"/><metadata key="weight" value="{grams}"/></plate></config>')


def test_read_slice_info(tmp_path):
    _sliced(tmp_path / "s.3mf", 5400, 41.7)
    assert printpkg.read_slice_info(tmp_path / "s.3mf") == {"seconds": 5400.0, "grams": 41.7}
    assert printpkg.read_slice_info(tmp_path / "missing.3mf") is None


def _proj():
    items = {"a": NS(spec={"material": "PETG", "print_rot": [0, 0, 0], "infill": 0.4, "walls": 4}, role="printed")}
    return NS(items=items, printed=items, data={"name": "t", "supports": "allowed"}, name="t")


def test_write_estimate_and_slicer_paths(tmp_path, monkeypatch):
    proj = _proj()
    (tmp_path / "plate_1.3mf").write_bytes(b"")
    with zipfile.ZipFile(tmp_path / "plate_1.3mf", "w") as z:
        z.writestr("3D/3dmodel.model", '<model><resources><object id="1" partnumber="a_1"/></resources></model>')
    rep = {"parts": {"a": {"mass_est_g": 25.0, "size_mm": [40, 40, 10], "overhang_pct": 0.0}}, "printer": "Bambu Lab A2L"}
    plates = [{"file": "plate_1.3mf", "parts": ["a #1"]}]
    r = printpkg.write(proj, rep, plates, tmp_path, use_slicer=False)
    p = r["plates"][0]
    assert p["grams"] == 25.0 and p["sliced"] is None
    # 25 g / 1.25 g/cm3 = 20 cm3 = 20000 mm3 at 8 mm3/s (Bambu PETG Basic max flow) = 2500 s
    assert p["min_seconds"] == 2500
    md = (tmp_path / "PRINT_SETTINGS.md").read_text()
    assert "at least 42 min" in md and "on its bottom (-Z) face" in md and "255 C" in md and "0.2 mm" in md
    cfg = zipfile.ZipFile(tmp_path / "plate_1.3mf").read("Metadata/model_settings.config").decode()
    assert 'key="layer_height" value="0.2"' in cfg and 'key="enable_support" value="0"' in cfg and 'key="wall_loops" value="4"' in cfg
    # a slicer set up for `kerf print` (binary + full exported settings): its own prediction and weight win
    fake = tmp_path / "fake_slicer.py"
    fake.write_text("import sys, zipfile\nout = sys.argv[sys.argv.index('--export-3mf') + 1]\n"
                    "assert '--load-settings' in sys.argv and '--load-filaments' in sys.argv\n"
                    "z = zipfile.ZipFile(out, 'w')\nz.writestr('Metadata/slice_info.config', "
                    "'<config><plate><metadata key=\"prediction\" value=\"7200\"/><metadata key=\"weight\" value=\"26.5\"/></plate></config>')\nz.close()\n")
    sh = tmp_path / "slicer"
    sh.write_text(f"#!/bin/sh\nexec {sys.executable} {fake} \"$@\"\n")
    sh.chmod(sh.stat().st_mode | stat.S_IEXEC)
    for f in ("m.json", "p.json", "petg.json"):
        (tmp_path / f).write_text("{}")
    cfg = tmp_path / "bambu.json"
    cfg.write_text(json.dumps({"slicer": {"bin": str(sh), "machine": str(tmp_path / "m.json"), "process": str(tmp_path / "p.json"),
                                          "filaments": {"PETG": str(tmp_path / "petg.json")}}}))
    monkeypatch.setenv("KERF_BAMBU_CONFIG", str(cfg))
    r = printpkg.write(proj, rep, plates, tmp_path)
    assert r["slicer"] == str(sh) and r["plates"][0]["sliced"] == {"seconds": 7200.0, "grams": 26.5}
    assert "2.0 h (sliced)" in (tmp_path / "PRINT_SETTINGS.md").read_text()
    # a binary without the exported settings does not slice (the CLI needs full configs): estimate
    cfg.write_text(json.dumps({"slicer": {"bin": str(sh)}}))
    assert printpkg.write(proj, rep, plates, tmp_path)["plates"][0]["sliced"] is None
