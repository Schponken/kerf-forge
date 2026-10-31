"""FEA load cases (pressure, torque about an axis, bearing seat) against hand calculations, and the stress render."""
import json
import math

import numpy as np
import pytest
from build123d import Align, Box, Cylinder, Pos, Rot

from kerf import fea, fea_render, pipeline
from test_engine import _write_project

E, NU = 2000.0, 0.3


def test_pressure_on_a_face():
    bar = Box(10, 10, 80, align=(Align.CENTER, Align.CENTER, Align.MIN))
    r = fea.static(bar, E, NU, fixed=lambda x, y, z: z < 0.01,
                   loads=[{"pred": lambda x, y, z: z > 79.99, "pressure": 5.0}])
    assert r["applied_force_n"] == pytest.approx([0, 0, -500.0], abs=1e-3)   # p x A, pushing into the face
    assert r["median_vm_mpa"] == pytest.approx(5.0, rel=0.01)
    assert r["max_disp_mm"] == pytest.approx(5.0 * 80 / E, rel=0.02)          # 0.2 mm


def test_torque_about_an_axis():
    rod = Cylinder(5, 80, align=(Align.CENTER, Align.CENTER, Align.MIN))
    T = 1000.0
    r = fea.static(rod, E, NU, fixed=lambda x, y, z: z < 0.01,
                   loads=[{"pred": lambda x, y, z: z > 79.99, "torque": T, "axis_at": [0, 0, 0], "axis_dir": [0, 0, 1]}])
    J, G = math.pi * 5 ** 4 / 2, E / (2 * (1 + NU))
    assert r["applied_moment_nmm"] == pytest.approx([0, 0, T], abs=0.5)
    assert np.abs(r["applied_force_n"]).max() < 1e-3                       # a pure couple
    assert r["max_vm_mpa"] == pytest.approx(math.sqrt(3) * T * 5 / J, rel=0.03)   # sqrt(3) x tau_max = 8.82 MPa
    assert r["max_disp_mm"] == pytest.approx(T * 80 / (G * J) * 5, rel=0.03)      # twist angle x radius


def test_torque_on_a_region_off_the_axis_is_a_pure_couple():
    """Four screw pads on one side of the axis (like servo tab screws, centred on the case, not the output): the
    torque must not smuggle in a net force; the moment about the axis is exactly T."""
    plate = Box(80, 30, 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pads = lambda x, y, z: (z > 5.99) & (np.abs(np.abs(x - 10) - 25) < 3) & (np.abs(np.abs(y) - 5) < 3)  # noqa: E731
    T = 2000.0
    r = fea.static(plate, E, NU, fixed=lambda x, y, z: z < 0.01,
                   loads=[{"pred": pads, "torque": T, "axis_at": [30, 0, 0], "axis_dir": [0, 0, 1]}])
    assert np.abs(r["applied_force_n"]).max() < 1e-3
    assert r["applied_moment_nmm"][2] == pytest.approx(T, rel=1e-3)


def test_bearing_seat_radial_load():
    blk = Box(30, 20, 30, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Pos(0, 0, 20) * Rot(90, 0, 0) * Cylinder(4, 40)
    bore = lambda x, y, z: np.hypot(x, z - 20) < 4.2  # noqa: E731
    down = fea.static(blk, E, NU, fixed=lambda x, y, z: z < 0.01, loads=[{"pred": bore, "bearing": (0, 0, -100.0)}])
    assert down["applied_force_n"] == pytest.approx([0, 0, -100.0], abs=0.5)   # resultant = the shaft force
    side = fea.static(blk, E, NU, fixed=lambda x, y, z: z < 0.01, loads=[{"pred": bore, "bearing": (100.0, 0, 0)}])
    assert side["applied_force_n"] == pytest.approx([100.0, 0, 0], abs=0.5)
    # a radial pressure acts through the bore centre (0, 0, 20): no moment about it
    for r, F in ((down, (0, 0, -100.0)), (side, (100.0, 0, 0))):
        Fa, M = np.array(r["applied_force_n"]), np.array(r["applied_moment_nmm"])
        assert M - np.cross([0, 0, 20.0], Fa) == pytest.approx([0, 0, 0], abs=0.5)


BLOCK = """
from build123d import *
def build(ctx):
    s = Box(30, 20, 30, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Pos(0, 0, 20) * Rot(90, 0, 0) * Cylinder(4, 40)
    ctx.revolute("shaft", Axis((0, 0, 20), (0, 1, 0)))
    return ctx.finish(s)
"""
YAML = """
name: FEA loads
params: {F: 100}
parts:
  block: {file: parts/block.py, material: PETG}
assembly: {root: block, joints: []}
requirements:
  - id: seat
    check: fea_static
    part: block
    sf: 2
    fixed: {box: [[-100, -100, -1], [100, 100, 0.01]]}
    loads:
      - {cylinder: {at: shaft, r: 4}, bearing_n: [0, 0, -F]}
      - {cylinder: {at: shaft, r: 4}, torque_nmm: 200, axis: {at: shaft}}
      - {box: [[-100, -100, 29.99], [100, 100, 31]], pressure_mpa: 0.1}
"""


def test_yaml_load_cases_and_render(tmp_path):
    d = _write_project(tmp_path / "fl", YAML, {"block": BLOCK})
    rep = pipeline.run(str(d), sweeps=True)
    r = rep["requirements"][0]
    assert r["ok"], r
    # bearing 100 N down + pressure 0.1 MPa x 30 x 20 mm top = 160 N down; torque 200 N*mm about the shaft (+Y)
    assert r["applied_force_n"] == pytest.approx([0, 0, -160.0], abs=0.6)
    Fa, M = np.array(r["applied_force_n"]), np.array(r["applied_moment_nmm"])
    assert (M - np.cross([0, 0, 20.0], Fa))[1] == pytest.approx(200.0, abs=1.0)   # about the shaft centre
    assert "_viz" not in r and "_viz" not in (d / "out" / "report.json").read_text()
    # the reviewer's picture, from the same solve
    from kerf import assembly as A, project as P, requirements
    proj = P.build(P.load(str(d)))
    res = requirements.run_all(proj, A.plan(proj))[0]
    png = fea_render.render(res["_viz"], tmp_path / "fea_seat.png", res["_viz"]["title"])
    assert (tmp_path / "fea_seat.png").stat().st_size > 20000 and png.endswith(".png")
    # the picture's title states the same checked p99.9 as the report (review finding: render and report disagreed)
    assert res["_viz"]["p999"] == pytest.approx(r["value"], abs=0.01) and res["_viz"]["peak"] >= res["_viz"]["p999"]
    h = fea_render.heading(res["_viz"], "seat", 3.21)
    assert f"volume p99.9 {r['value']:.2f}" in h and f"volume peak {res['_viz']['peak']:.2f}" in h and "surface peak 3.21" in h
    json.dumps({k: v for k, v in res.items() if k != "_viz"})


def test_region_union():
    from types import SimpleNamespace
    from kerf import requirements
    item = SimpleNamespace(id="x", shape=None)
    pred = requirements._region(item, {"any": [{"box": [[0, 0, 0], [1, 1, 1]]}, {"box": [[5, 5, 5], [6, 6, 6]]}]})
    x = np.array([0.5, 5.5, 3.0])
    assert pred(x, x, x).tolist() == [True, True, False]


def test_direct_fallback_when_amg_stalls(monkeypatch):
    """If AMG+CG stalls, a small system is solved directly and still matches beam theory."""
    import pyamg

    class Stalled:
        def solve(self, b, residuals=None, **kw):
            residuals += [1.0, 1.0]
            return np.zeros_like(b)
    monkeypatch.setattr(pyamg, "smoothed_aggregation_solver", lambda *a, **k: Stalled())
    beam = Box(100, 10, 10, align=(Align.MIN, Align.CENTER, Align.CENTER))
    r = fea.static(beam, 2000, 0.3, fixed=lambda x, y, z: x < 0.01, loads=[(lambda x, y, z: x > 99.99, (0, 0, -10.0))])
    assert r["max_disp_mm"] == pytest.approx(10 * 100 ** 3 / (3 * 2000 * (10 * 10 ** 3 / 12)), rel=0.03)


@pytest.mark.parametrize("extra, sf, ok", [("", 2, True), ("    direction: z\n", 2, False), ("    direction: z\n", 3, True),
                                          ("    case: landing\n", 2, False), ("    case: crash\n", 3, True)])
def test_sf_floor_from_engineering_s3(tmp_path, extra, sf, ok):
    """ENG-2: fea_static refuses a safety factor under ENGINEERING.md s3 (3 across layers, 3 for crash/landing)."""
    y = YAML.replace("    sf: 2\n", f"    sf: {sf}\n" + extra)
    d = _write_project(tmp_path / "sf", y, {"block": BLOCK})
    from kerf import assembly as A, project as P, requirements
    proj = P.build(P.load(str(d)))
    r = requirements.run_all(proj, A.plan(proj))[0]
    assert r["ok"] is ok, r["detail"]
    assert ("below the ENGINEERING.md section 3 minimum" in r["detail"]) is (not ok)
