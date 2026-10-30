"""proxy: step — vendor STEP models checked against the catalog, keeping catalog joints and fastener sites."""
import textwrap

import pytest
from build123d import Align, Box, Cylinder, Pos, export_step

from kerf import assembly as A, project as P, proxies
from kerf.ctx import Ctx

PICO = {"catalog": "boards.rpi_pico", "proxy": "step", "base": "board", "model": "rpi_pico.step",
        "model_rot": [90, -90, 0], "model_pos": [-25.5, 10.5, 0.5], "groups": {"holes": "p"}}


def _build(spec):
    ctx = Ctx("x", {}, {"spec": spec})
    return proxies.build(ctx, spec)


def _board(spec):
    return _build({k: v for k, v in spec.items() if k not in ("proxy", "model", "model_rot", "model_pos", "models_dir")} | {"proxy": "board"})


def test_real_pico_model_matches_catalog_and_keeps_sites():
    s, ref = _build(PICO), _board(PICO)
    bb = s.bounding_box()
    # datasheet: 51 x 21 PCB + 1.3 mm USB overhang; official model is 2.73 mm tall above the 1 mm PCB
    assert (bb.size.X, bb.size.Y, bb.size.Z) == pytest.approx((52.3, 21.0, 3.73), abs=1e-3)
    assert sorted(s.joints) == sorted(ref.joints)
    got = sorted((x.group, x.role, x.screw, round(x.loc.position.X, 6), round(x.loc.position.Y, 6), round(x.loc.position.Z, 6)) for x in s.kerf_sites)
    want = sorted((x.group, x.role, x.screw, round(x.loc.position.X, 6), round(x.loc.position.Y, 6), round(x.loc.position.Z, 6)) for x in ref.kerf_sites)
    assert got == want and len(got) == 4
    assert len(s.solids()) == 17          # the vendor's parts, untouched


@pytest.mark.parametrize("change,axis", [({"model_pos": [-24.5, 10.5, 0.5]}, "X"),       # 1 mm off along the board
                                         ({"model_pos": [-25.5, 10.5, 1.5]}, "Z"),       # floating 1 mm above its joint
                                         ({"model_rot": [-90, -90, 0], "model_pos": [-25.5, 10.5, -0.5]}, "Z")])  # upside down
def test_wrong_placement_is_refused(change, axis):
    with pytest.raises(ValueError, match=f"{axis} m"):
        _build(PICO | change)


def test_usb_end_reversed_is_refused():
    # rotated 180 deg about Z: same box size, but the USB overhang lands on the wrong end -> X faces off by 1.3 mm
    with pytest.raises(ValueError, match="X m"):
        _build(PICO | {"model_rot": [90, -90, 180], "model_pos": [25.5, -10.5, 0.5]})


def _fake(tmp_path, solid, name="fake.step"):
    export_step(solid, str(tmp_path / name))
    return {"models_dir": str(tmp_path), "model": name, "model_rot": [0, 0, 0], "model_pos": [0, 0, 0]}


def test_model_without_the_mounting_holes_is_refused(tmp_path):
    ref = _board(PICO)
    lo, hi = ref.bounding_box().min, ref.bounding_box().max
    blank = Pos(lo.X, lo.Y, lo.Z) * Box(hi.X - lo.X, hi.Y - lo.Y, hi.Z - lo.Z, align=(Align.MIN, Align.MIN, Align.MIN))
    with pytest.raises(ValueError, match="no M2 hole"):
        _build(PICO | _fake(tmp_path, blank))
    # same blank with the four 2.1 mm holes drilled at the catalog positions passes
    for x, y in [(-23.5, -5.7), (23.5, -5.7), (-23.5, 5.7), (23.5, 5.7)]:
        blank -= Pos(x, y, -1) * Cylinder(1.05, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    assert len(_build(PICO | _fake(tmp_path, blank, "drilled.step")).kerf_sites) == 4


def test_model_in_inches_is_refused(tmp_path):
    ref = _board(PICO)
    tiny = ref.scale(1 / 25.4)
    with pytest.raises(ValueError, match="off by"):
        _build(PICO | _fake(tmp_path, tiny))


def test_missing_file_and_base():
    with pytest.raises(FileNotFoundError):
        _build(PICO | {"model": "nope.step"})
    with pytest.raises(ValueError, match="base"):
        _build({k: v for k, v in PICO.items() if k != "base"} | {"catalog": "drone.motors.2207_1855kv_6s"})


YAML = """
name: v
parts:
  tray: {file: parts/tray.py}
purchased:
  pico: {catalog: boards.rpi_pico, proxy: step, base: board, model: rpi_pico.step,
         model_rot: [90, -90, 0], model_pos: [-25.5, 10.5, 0.5], groups: {holes: pico}}
assembly:
  root: tray
  joints: [{parent: tray.seat, child: pico.bottom}]
"""
TRAY = """
from build123d import *
from kerf import iface
def build(ctx):
    pts = [(-23.5, -5.7), (23.5, -5.7), (-23.5, 5.7), (23.5, 5.7)]
    s = Box(62, 30, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x, y in pts:
        s += Pos(x, y, 3) * Cylinder(2.6, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))     # standoffs
    s -= iface.bolt_pattern(ctx, "pico", "M2", pts, Location((0, 0, 6)), kind="heatset", depth=6)
    ctx.rigid("seat", Location((0, 0, 6)))
    return ctx.finish(s)
"""


def test_vendor_model_in_an_assembly(tmp_path):
    d = tmp_path / "v"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "tray.py").write_text(textwrap.dedent(TRAY))
    proj = P.build(P.load(str(d)))
    assert not {k: v.error for k, v in proj.items.items() if v.error}
    asm = A.plan(proj)
    A.solve(asm)
    joints, problems = A.fasteners(asm)
    assert problems == [] and len(joints) == 4
    assert A.interference(asm) == []      # the real underside (castellations, test pads) clears the standoffs
