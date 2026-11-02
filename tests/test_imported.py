"""Check it on a user's own design (kerf/imported.py): STEP and STL models become printed parts with declared joints
and fastener sites, and the normal checks run on them."""
from pathlib import Path

import pytest
from build123d import Box, export_stl

from kerf import imported
from kerf.ctx import Ctx

ROOT = Path(__file__).resolve().parent.parent
STEP = ROOT / "projects" / "check_shelf_bracket" / "imports" / "shelf_bracket.step"


def test_step_model_loads_as_one_solid_with_its_joints_and_sites():
    ctx = Ctx("bracket", {}, {"spec": {}})
    spec = {"import": "imports/shelf_bracket.step", "joints": {"shelf": [80, 0, 5]},
            "revolute": {"flip": {"at": [0, 0, 0], "axis": [0, 1, 0], "range": [0, 90]}},
            "sites": [{"group": "wall", "screw": "M5", "at": [0, 0, 20], "dir": [-1, 0, 0], "kind": "clearance", "grip": 5}]}
    s = imported.build(ctx, spec, STEP.parent.parent)
    assert len(s.solids()) == 1 and s.volume == pytest.approx(33081.4, rel=1e-3)
    assert {"origin", "shelf", "flip"} <= set(s.joints) and s.kerf_sites[0].role == "male"


def test_stl_mesh_is_sewn_into_a_solid_and_units_scale(tmp_path):
    f = tmp_path / "cube.stl"
    export_stl(Box(1, 2, 3), str(f))                     # a model drawn in inches
    s = imported.load(f, units="in")
    assert s.volume == pytest.approx(6 * 25.4 ** 3, rel=1e-3)
    with pytest.raises(imported.ImportError_, match="units"):
        imported.load(f, units="furlong")
    with pytest.raises(imported.ImportError_, match="not found"):
        imported.load(tmp_path / "none.step")
