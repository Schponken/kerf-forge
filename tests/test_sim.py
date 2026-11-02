"""MuJoCo motion simulation (kerf/sim.py, kerf/req_motion.py) checked against hand calculations, not just "it runs":
pendulum period from the URDF's mass and inertia, a servo holding (or not) a static load of 0.9 (1.1) x its stall
torque, a no-load move timed by the catalog speed, the slip limit of a friction grip (2 mu N = m (g + a)), and the
peak force of a drop (Hertz impact, linear spring, effective mass of an off-centre hit)."""
import math

import numpy as np
import pytest

from kerf import catalog, project as P, sim
from test_engine import _write_project

G = sim.G

PEND_YAML = """
name: Pendulum test
params: {}
parts:
  base: {file: parts/base.py}
  bar: {file: parts/bar.py}
assembly:
  root: base
  joints:
    - {parent: base.pivot, child: bar.hub, name: swing, range: [-270, 270]}
"""
PEND_BASE = """
from build123d import *
def build(ctx):
    s = Box(40, 40, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.revolute("pivot", Axis((0, 30, 150), (0, 1, 0)), range=(-270, 270))
    return ctx.finish(s)
"""
PEND_BAR = """
from build123d import *
def build(ctx):
    s = Box(100, 10, 10, align=(Align.MIN, Align.CENTER, Align.CENTER))   # along X; the pivot axis is its Z
    ctx.rigid("hub", Location((0, 0, 0)))
    ctx.rigid("end", Location((100, 0, 0)))
    return ctx.finish(s)
"""

GRIP_YAML = """
name: Grip test
params: {}
parts:
  palm: {file: parts/palm.py}
  finger: {file: parts/finger.py}
assembly:
  root: palm
  joints:
    - {parent: palm.axis, child: finger.hub, name: grip, range: [-40, 40]}
"""
GRIP_PALM = """
from build123d import *
def build(ctx):
    s = Pos(0, -40, 0) * Box(80, 20, 6)
    ctx.revolute("axis", Axis((0, 0, 0), (0, 0, 1)), range=(-40, 40))
    ctx.rigid("jaw", Location((50, -20, 0)))
    return ctx.finish(s)
"""
GRIP_FINGER = """
from build123d import *
def build(ctx):
    s = Pos(25, 0, 0) * Box(50, 6, 6)
    ctx.rigid("hub", Location((0, 0, 0)))
    ctx.rigid("tip", Location((50, 0, 0)))
    return ctx.finish(s)
"""


@pytest.fixture(scope="module")
def pend(tmp_path_factory):
    d = _write_project(tmp_path_factory.mktemp("pend"), PEND_YAML, {"base": PEND_BASE, "bar": PEND_BAR})
    proj = P.build(P.load(str(d)), cache=False)
    return proj


@pytest.fixture(scope="module")
def gripper(tmp_path_factory):
    d = _write_project(tmp_path_factory.mktemp("grip"), GRIP_YAML, {"palm": GRIP_PALM, "finger": GRIP_FINGER})
    return P.build(P.load(str(d)), cache=False)


def _hanging(M):
    """The swing angle (rad, a multiple of 90 deg in 0..180) where the bar hangs straight down: lowest centre of mass."""
    import mujoco
    mj = M.spec().compile()
    d = mujoco.MjData(mj)
    z = {}
    for q in (0.0, math.pi / 2, -math.pi / 2, math.pi):
        d.qpos[0] = q
        mujoco.mj_forward(mj, d)
        z[q] = d.body("bar").xipos[2]
    return min(z, key=z.get), mj, d


def _period(M, amp_deg=2.0, seconds=3.0):
    import mujoco
    q0, mj, d = _hanging(M)
    mujoco.mj_resetData(mj, d)
    d.qpos[0] = q0 + math.radians(amp_deg)
    ups, prev = [], d.qpos[0] - q0
    while d.time < seconds:
        mujoco.mj_step(mj, d)
        x = d.qpos[0] - q0
        if prev < 0 <= x:
            ups.append(d.time)
        prev = x
    return float(np.mean(np.diff(ups)))


def test_pendulum_period_from_urdf_mass_and_inertia(pend):
    """A 100 x 10 x 10 mm bar of 50 g swinging about one end: T = 2 pi sqrt(I / (m g d)),
    I = m (L^2 + t^2) / 12 + m (L/2)^2 (box about its end, axis across the 10 mm side)."""
    M = sim.load(pend, masses={"base": 100.0, "bar": 50.0})
    m, L, t, dd = 0.05, 0.1, 0.01, 0.05
    I = m * (L ** 2 + t ** 2) / 12 + m * dd ** 2
    assert _hanging(M)[1].body("bar").mass[0] == pytest.approx(m)
    T_hand = 2 * math.pi * math.sqrt(I / (m * G * dd))
    assert _period(M) == pytest.approx(T_hand, rel=0.005)


def test_static_holding_torque(pend):
    """The bar held out level by an MG996R (0.922 N*m stall) with a point load at its end: a load needing 0.9 x
    stall is held inside the servo band; 1.1 x stall is not (the joint falls away)."""
    stall, _ = sim.servo_limits(catalog.get("servos.MG996R"))
    m_bar, r_bar, r_end = 0.05, 0.05, 0.1
    for frac, holds in ((0.9, True), (1.1, False)):
        payload = (frac * stall / G - m_bar * r_bar) / r_end
        M = sim.load(pend, masses={"base": 100.0, "bar": 50.0}, actuators={"swing": "servos.MG996R"}, refs=["bar.end"])
        flat = math.degrees(_hanging(M)[0]) - 90.0                 # 90 deg from hanging: the bar sticks out level
        r = sim.move(M, {"swing": flat}, {"swing": flat}, 0.5, payload_g=payload * 1000, payload_at="bar.end")
        assert (r["time_s"] is not None) == holds, (frac, r)
        if holds:
            assert r["peak_fraction"]["swing"] == pytest.approx(0.9, abs=0.05)
            assert abs(r["final_error_deg"]["swing"]) < sim.BAND_DEG


def test_no_load_move_time_matches_catalog_speed(pend):
    """With almost no load, a 60 deg move takes the catalog 0.17 s / 60 deg (+ a few ms to settle into the band)."""
    M = sim.load(pend, masses={"base": 100.0, "bar": 0.5}, actuators={"swing": "servos.MG996R"})
    r = sim.move(M, {"swing": 0}, {"swing": 60}, 0.5, payload_g=0.0)
    s60 = catalog.get("servos.MG996R")["speed_s_per_60"]
    # the joint enters the 3 deg band 3/60 of the way before the end
    assert r["time_s"] == pytest.approx(s60 * 57 / 60, abs=0.02)


def _grip_hand(proj, width_mm, torque_fraction, mu, shake_g=1.0):
    """Hand calc: the finger (tip 50 mm from the axis) closes on a jaw point 20 mm to the side; the pads are 6 mm thick."""
    c = 50.0 - 0.0
    # tip on the circle r = 50 at angle th; jaw at (50, -20): centre distance = width + 6
    D = width_mm + 6.0
    th = min((math.radians(a) for a in np.linspace(-40, 40, 80001)),
             key=lambda a: abs(math.hypot(c * math.cos(a) - 50, c * math.sin(a) + 20) - D))
    tip = np.array([c * math.cos(th), c * math.sin(th)])
    n = (tip - [50, -20]) / np.linalg.norm(tip - [50, -20])
    lever = abs(tip[0] * -n[1] - tip[1] * -n[0]) / 1000.0
    stall, _ = sim.servo_limits(catalog.get("servos.MG996R"))
    N = stall * torque_fraction / lever
    return N, 2 * mu * N / ((1 + shake_g) * G)


def test_grip_hold_matches_friction_hand_calc(gripper):
    """2 mu N >= m (g + 1 g shake): 0.85 x the hand slip mass stays put, 1.15 x slides out."""
    mu, frac, width = 0.27, 0.1, 20.0
    N, m_slip = _grip_hand(gripper, width, frac, mu)
    M = sim.load(gripper, masses={"palm": 50.0, "finger": 10.0}, actuators={"grip": "servos.MG996R"},
                 refs=["finger.tip", "palm.jaw"])
    kw = dict(joint="grip", pads=["finger.tip", "palm.jaw"], mu=mu, width_mm=width, pad_t_mm=(6.0, 6.0),
              torque_fraction=frac)
    held = sim.grip(M, mass_g=0.85 * m_slip * 1000, **kw)
    assert held["squeeze_n"] == pytest.approx(N, rel=0.01)
    assert held["hand_slip_mass_g"] == pytest.approx(m_slip * 1000, rel=0.01)
    assert max(held["slip_mm"].values()) < 0.5, held
    lost = sim.grip(M, mass_g=1.15 * m_slip * 1000, **kw)
    assert max(lost["slip_mm"].values()) > 5.0, lost


def test_drop_hertz_peak_matches_closed_form():
    """Centre of mass right above the hit point, rigid structure: the elastic Hertz impact peak
    F = K^(2/5) (5/4 m v^2)^(3/5) (Johnson, Contact Mechanics s11.4)."""
    pet = catalog.get("materials.PETG")
    K = sim.hertz_k(pet["youngs_modulus_mpa"], pet["poisson"], 2.0)
    m, h = 0.12, 0.3
    r = sim.drop_body(m, np.eye(3) * 1e-5, np.array([0, 0, -0.03]), h, K)
    assert r["peak_n"] == pytest.approx(sim.hertz_peak(K, m, math.sqrt(2 * G * h)), rel=0.01)


def test_drop_linear_spring_and_off_centre_hit():
    """A stiff contact behind a soft structure spring ks: F = v sqrt(ks m) (+ m g); hit 40 mm off the centre of mass
    sideways: the floor sees the effective mass 1 / (1/m + r^2 / I) instead of m."""
    m, h, ks = 0.12, 0.3, 6.0e4
    K = 1e14                                             # Hertz much stiffer than the structure
    v = math.sqrt(2 * G * h)
    r = sim.drop_body(m, np.eye(3) * 2e-4, np.array([0, 0, -0.03]), h, K, ks=ks)
    assert r["peak_n"] == pytest.approx(m * G + math.sqrt((m * G) ** 2 + ks * m * v * v), rel=0.02)
    I = 2e-4
    r2 = sim.drop_body(m, np.eye(3) * I, np.array([0.04, 0, -0.03]), h, K, ks=ks)
    m_eff = 1 / (1 / m + 0.04 ** 2 / I)
    assert r2["peak_n"] == pytest.approx(v * math.sqrt(ks * m_eff), rel=0.05)


def test_requirement_checks_registered_and_wired(pend, gripper):
    """The three kinds run through requirements.REGISTRY like any project.yaml requirement: grip_hold with a catalog
    friction pair, joint_speed on an actuator-less project fails loudly, drop_impact end-on = the Hertz closed form."""
    from kerf import assembly as A, requirements as R
    assert {"grip_hold", "joint_speed", "drop_impact"} <= set(R.REGISTRY) and "drop_impact" in R.SLOW
    mu = catalog.get("friction.PETG-steel")["mu_static"]
    assert 0.1 < mu < 1.0 and catalog.get("friction.PETG-steel")["source"].startswith("https://")
    asm = A.plan(gripper)
    r = R.REGISTRY["grip_hold"](gripper, asm, joint="grip", pads=["finger.tip", "palm.jaw"], mass_g=5.0,
                                friction="PETG-steel", width_mm=20.0, actuator="servos.MG996R", torque_fraction=0.1)
    assert r["ok"] and r["value"] < 0.5 and "catalog PETG-steel" in r["detail"], r
    with pytest.raises(ValueError, match="no joint is driven"):
        R.REGISTRY["joint_speed"](pend, A.plan(pend), end={"swing": 30}, max_s=1.0)
    asm = A.plan(pend)
    r = R.REGISTRY["drop_impact"](pend, asm, part="bar", at="bar.end", height_mm=200, radius_mm=2.0, subtree="swing",
                                  down=[0, 0, 1], max_force_n=1e6)              # the bar's far end points at the floor
    M = sim.load(pend, asm, refs=["bar.end"])
    m = sim.subtree_inertia(M, {}, "swing")[0]
    pet = catalog.get("materials.PETG")
    K = sim.hertz_k(pet["youngs_modulus_mpa"], pet["poisson"], 2.0)
    assert r["value"] == pytest.approx(sim.hertz_peak(K, m, math.sqrt(2 * G * 0.2)), rel=0.01)


def test_locked_joint_is_welded_at_its_pose(pend):
    """A joint locked for a scenario (grip_hold locks the arm) is removed and its body turned to the pose: the same
    place as the free joint at that angle, and it does not move under load (no soft-constraint sag)."""
    import mujoco
    M = sim.load(pend, masses={"base": 100.0, "bar": 50.0})
    mj = M.spec().compile()
    d = mujoco.MjData(mj)
    sim._set_pose(M, mj, d, {"swing": 37.0})
    want = d.body("bar").xipos.copy()
    sp = M.spec()
    sim._lock(sp, M, set(), {"swing": 37.0})
    mj2 = sp.compile()
    assert mj2.njnt == 0
    d2 = mujoco.MjData(mj2)
    for _ in range(200):
        mujoco.mj_step(mj2, d2)
    assert np.allclose(d2.body("bar").xipos, want, atol=1e-9)
