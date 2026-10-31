"""ENG-6: per-part print settings (infill, wall loops) reach the plate 3MF and PRINT_SETTINGS.md; strength-checked
parts default to 4 walls and their mass estimate counts them (hand check on a box)."""
import types
import zipfile

import pytest
from build123d import Box

from kerf import checks, export


def test_shell_volume_hand_calc():
    b = Box(40, 20, 10)                       # top+bottom 1600 mm2, sides 1200 mm2
    assert checks.shell_volume(b, {"walls": 2}) == pytest.approx(1600 * 0.84 + 1200 * 2 * 0.42)
    assert checks.shell_volume(b, {"walls": 4}) == pytest.approx(1600 * 0.84 + 1200 * 4 * 0.42)


def test_plate_3mf_carries_settings(tmp_path):
    from build123d import Mesher
    f = tmp_path / "p.3mf"
    m = Mesher()
    m.add_shape(Box(10, 10, 10), part_number="arm_1")
    m.add_shape(Box(5, 5, 5), part_number="base_1")
    m.write(str(f))
    export._write_part_settings(f, {"arm_1": {"infill": 0.4, "walls": 4}, "base_1": {"infill": 0.25}})
    cfg = zipfile.ZipFile(f).read("Metadata/model_settings.config").decode()
    assert cfg.count("<object") == 2 and 'value="40%"' in cfg and 'key="wall_loops" value="4"' in cfg
    assert 'value="25%"' in cfg and 'key="wall_loops" value="2"' in cfg
    assert "3D/3dmodel.model" in zipfile.ZipFile(f).namelist()


def test_stressed_parts_default_to_four_walls(tmp_path):
    from kerf import project as P
    d = tmp_path / "w"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(
        "name: w\nparts:\n  a: {file: parts/a.py}\n  a2: {file: parts/a.py}\n  b: {file: parts/b.py}\n  c: {file: parts/b.py, walls: 3}\n"
        "assembly: {root: a, joints: []}\nrequirements:\n  - {id: f, check: fea_static, part: a, fixed: {box: [[0,0,0],[1,1,1]]}, loads: []}\n")
    proj = P.load(str(d))
    assert [proj.items[k].spec["walls"] for k in ("a", "a2", "b", "c")] == [4, 4, 2, 3]
