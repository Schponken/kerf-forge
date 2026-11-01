"""tools/render/render.mjs through pipeline.render_glb: call-out labels, focus framing, sheet title, readable dark parts."""
import shutil

import numpy as np
import pytest
from PIL import Image

from kerf import geom
from kerf.pipeline import render_glb

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def glb(tmp_path_factory):
    from build123d import Box, Color, Pos
    d = tmp_path_factory.mktemp("r")
    a = Box(20, 20, 20)
    a.color, a.label = Color("#F58518"), "part_a"
    b = Pos(80, 0, 0) * Box(40, 30, 10)
    b.color, b.label = Color("#202326"), "servo_b"          # a near-black purchased part
    g = d / "t.glb"
    geom.write_glb([a, b], g, 0.1, 0.3, label="t")
    return d, g


def test_labels_focus_and_title(glb):
    d, g = glb
    render_glb(g, d / "plain", views="iso", sheet=False)
    render_glb(g, d / "lab", views="iso", sheet=False, labels=["part_a"])
    render_glb(g, d / "foc", views="iso", sheet=False, focus=["part_a"])
    plain, lab, foc = (np.asarray(Image.open(d / f"{n}_iso.png").convert("RGB"), float) for n in ("plain", "lab", "foc"))
    assert np.abs(plain - lab).mean() > 0.2                 # the call-out is drawn
    assert np.abs(plain - foc).mean() > 2.0                 # the camera moved in on part_a
    render_glb(g, d / "sheet", views="iso,front,right,top", sheet=True, title="part_a: 20 x 20 x 20 mm overall")
    w, h = Image.open(d / "sheet_sheet.png").size
    assert (w, h) == (2048, 1536 + 56)                      # a title band above the 2x2 views


def test_dark_parts_are_lifted(tmp_path):
    """A near-black part (servo case, PCB) renders as readable grey with light edges, not a black hole (glTF's default
    metallic = 1 used to make every part dark)."""
    from build123d import Box, Color
    b = Box(40, 30, 10)
    b.color, b.label = Color("#202326"), "servo_b"
    geom.write_glb([b], tmp_path / "d.glb", 0.1, 0.3, label="t")
    render_glb(tmp_path / "d.glb", tmp_path / "dk", views="iso", sheet=False)
    im = np.asarray(Image.open(tmp_path / "dk_iso.png").convert("L"), float)
    assert np.median(im[im < 180]) > 80                     # measured 105; the old renderer gave 17
