"""Simulate it moving (kerf/req_dynamic.py): impacts, hard stops and natural frequencies from one FEA solve of the
part's stiffness, each checked against hand calculations."""
import math

import pytest

from kerf import assembly as A, project as P, requirements as R
from kerf.checks import item_mass_g
from kerf.req_dynamic import RAYLEIGH_BEAM, _inertia_kgm2, rotor_hz
from test_engine import HINGE_ARM, _write_project

E_PETG = 1460.0   # catalog materials.PETG
BEAM = """
from build123d import *
def build(ctx):
    ctx.rigid("root", Location((0, 0, 0)))
    return ctx.finish(Box(100, 10, 10, align=(Align.MIN, Align.CENTER, Align.CENTER)))
"""
FIX = "{box: [[-0.1, -6, -6], [0.1, 6, 6]]}"
TIP = "[{box: [[99.9, -6, -6], [100.1, 6, 6]], force_n: [0, 0, -10]}]"


def _beam(tmp_path, reqs):
    y = f"""
name: Beam
params: {{}}
parts:
  beam: {{file: parts/beam.py, material: PETG, walls: 4}}
assembly:
  root: beam
  joints: []
requirements:
{reqs}
"""
    d = _write_project(tmp_path / "beam", y, {"beam": BEAM})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    return proj, asm, R.run_all(proj, asm)


def test_cantilever_stiffness_drop_crash_and_frequency_match_hand_calculations(tmp_path):
    reqs = f"""  - {{id: drop, check: impact_fea, part: beam, fixed: {FIX}, loads: {TIP}, height_m: 0.5, mass_g: 200}}
  - {{id: crash, check: impact_fea, part: beam, fixed: {FIX}, loads: {TIP}, speed_m_s: 2, mass_g: 200}}
  - {{id: fn, check: natural_freq, part: beam, fixed: {FIX}, loads: {TIP}, carried_g: 50, excitation: {{hz: 40}}, min_ratio: 1.5}}
"""
    proj, asm, (drop, crash, fn) = _beam(tmp_path, reqs)
    k = drop["impact"]["stiffness_n_mm"]
    k_hand = 3 * E_PETG * (10 * 10 ** 3 / 12) / 100 ** 3                 # 3 E I / L^3 = 3.65 N/mm
    assert k == pytest.approx(k_hand, rel=0.06)                           # FEA adds shear and end effects
    W = 0.2 * 9.80665
    F_drop = W + math.sqrt(W * W + 2 * k * 1000 * W * 0.5)               # m g + sqrt((m g)^2 + 2 k m g h)
    assert drop["impact"]["force_n"] == pytest.approx(F_drop, rel=1e-3)
    assert crash["impact"]["force_n"] == pytest.approx(2 * math.sqrt(k * 1000 * 0.2), rel=1e-3)          # v sqrt(k m)
    assert crash["impact"]["contact_ms"] == pytest.approx(math.pi * math.sqrt(0.2 / (k * 1000)) * 1000, rel=1e-3)
    # stresses scale with the force: sigma = M c / I at the root for the crash force (p99.9 sits a bit under the peak)
    sig_hand = crash["impact"]["force_n"] * 100 * 5 / (10 * 10 ** 3 / 12)
    assert 0.6 * sig_hand < crash["value"] < 1.3 * sig_hand
    m = 0.05 + RAYLEIGH_BEAM * item_mass_g(proj.items["beam"]) / 1000
    assert fn["value"] == pytest.approx(math.sqrt(k * 1000 / m) / (2 * math.pi), rel=1e-2)
    assert fn["ok"] == (fn["value"] >= 60)


STOP_BASE = """
from build123d import *
def build(ctx):
    s = Box(40, 20, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)) + Pos(25, 0, 0) * Box(10, 10, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.revolute("pivot", Axis((0, 0, 10), (0, 1, 0)), range=(-90, 90))
    return ctx.finish(s)
"""


def test_stop_impact_uses_the_moving_inertia_and_the_stops_lever(tmp_path):
    y = """
name: Stop
params: {L: 60}
parts:
  base: {file: parts/base.py, material: PETG, walls: 4}
  arm: {file: parts/arm.py, material: PETG}
assembly:
  root: base
  joints:
    - {parent: base.pivot, child: arm.hub, name: swing, range: [-90, 90]}
requirements:
  - {id: stop, check: stop_impact, joint: swing, part: base, speed_dps: 300, fixed: {box: [[-31, -11, -0.1], [31, 11, 0.1]]},
     loads: [{box: [[19.9, -5.1, 19.9], [30.1, 5.1, 20.1]], force_n: [0, 0, -10]}]}
"""
    d = _write_project(tmp_path / "stop", y, {"base": STOP_BASE, "arm": HINGE_ARM})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    m = item_mass_g(proj.items["arm"]) / 1000
    I_hand = m * ((60 ** 2 + 4 ** 2) / 12 + 30 ** 2 + 2 ** 2) * 1e-6       # box about its end axis, parallel-axis
    import numpy as np
    assert _inertia_kgm2(proj, {"arm"}, np.array([0, 0, 10.0]), np.array([0, 1.0, 0])) == pytest.approx(I_hand, rel=2e-3)
    r = R.run_all(proj, asm)[0]
    assert "impact" in r, r["detail"]
    imp = r["impact"]
    assert imp["lever_mm"] == pytest.approx(25, abs=0.3)
    kt = imp["stiffness_n_mm"] * 1000 * 0.025 ** 2
    assert imp["impact_torque_nm"] == pytest.approx(math.radians(300) * math.sqrt(kt * I_hand), rel=5e-3)
    assert imp["force_n"] == pytest.approx(imp["torque_nm"] / 0.025, rel=1e-2)


def test_rotor_frequencies_from_kv_and_hover_thrust():
    from types import SimpleNamespace as NS
    items = {f"m{i}": NS(role="purchased", spec={"catalog": "drone.motors.2207_1855kv_6s", "mass_g": 150}, shape=None) for i in range(4)}
    items["pack"] = NS(role="purchased", spec={"catalog": "drone.batteries.6S_1100", "mass_g": 0}, shape=None)
    items["prop"] = NS(role="keepout", spec={"catalog": "drone.props.5_1in"}, shape=None)
    proj = NS(items=items, data={"electrical": {"battery": "pack"}})
    rot, bp = rotor_hz(proj, "m0", "hover", prop="prop")
    rpm = 1855 * 22.2 * math.sqrt(150 / 1685)                              # 600 g / 4 motors of 1685 g max thrust
    assert rot == pytest.approx(rpm / 60, rel=1e-6) and bp == pytest.approx(3 * rpm / 60, rel=1e-6)
    assert rotor_hz(proj, "m0", "max", blades=2)[0] == pytest.approx(1855 * 22.2 / 60)
