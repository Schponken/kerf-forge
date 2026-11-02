"""Conventional aircraft with pivoting (folding / variable-sweep) wings: lift slope, neutral point with a tail at a
folded pose, and the aerodynamic moment on the sweep actuator - each against a hand calculation."""
import math
from types import SimpleNamespace

import numpy as np
import pytest
from build123d import Location, Pos, Rot

from kerf import aero, req_aero
from kerf import assembly as A

ETA = 0.95


def test_lift_slope_by_hand():
    # Raymer eq. 12.6, beta 1, eta 0.95: A 6, no sweep: 2 pi 6 / (2 + sqrt(4 + 36 / 0.9025)) = 37.699 / 8.6249 = 4.3710
    assert aero.lift_slope(6, 0) == pytest.approx(4.3710, abs=1e-3)
    # 45 deg: sqrt(4 + 39.889 x 2) = 9.1530 -> 37.699 / 11.153 = 3.3802
    assert aero.lift_slope(6, 45) == pytest.approx(3.3802, abs=1e-3)
    # slender-wing limit: a -> pi A / 2 for small A
    assert aero.lift_slope(0.2, 0) == pytest.approx(math.pi * 0.2 / 2, rel=0.02)


def _proj(monkeypatch, cg_x=60.0, mass=1000.0, fold=None):
    """Rectangular wing 1000 x 200 (naca0012, thickest at 30 %), tail 400 x 100 with its LE at x 600. With `fold`, the
    halves |y| >= 50 are items wing_r / wing_l that pivot about their root trailing-edge corners (200, +-50) by the
    pose's 'fold' angle (aft)."""
    params = dict(wing_span=1000, wing_root_chord=200, wing_tip_chord=200, wing_airfoil="naca0012",
                  htail_span=400, htail_root_chord=100, htail_tip_chord=100, htail_x_le0=600, htail_airfoil="naca0010")
    items = {k: SimpleNamespace(role="part", shape=SimpleNamespace(location=Location())) for k in ("wing_r", "wing_l")}
    proj = SimpleNamespace(params=params, items=items)
    asm = SimpleNamespace(proj=proj, edges=[])

    def solve(a, values=None):
        f = float((values or {}).get("fold", 0.0))
        items["wing_r"].shape.location = Pos(200, 50, 0) * Rot(0, 0, -f) * Pos(-200, -50, 0)
        items["wing_l"].shape.location = Pos(200, -50, 0) * Rot(0, 0, f) * Pos(-200, 50, 0)
    monkeypatch.setattr(A, "solve", solve)
    monkeypatch.setattr(req_aero, "assembly_cg", lambda p: (np.array([cg_x, 0, 0]), mass))
    return proj, asm


def test_static_margin_tail_fixed_wing_by_hand(monkeypatch):
    proj, asm = _proj(monkeypatch, cg_x=60.0)
    r = req_aero.static_margin_tail(proj, asm, min=0.05, max=0.25)
    a_w = 2 * math.pi * 5 / (2 + math.sqrt(4 + 25 / ETA ** 2))          # A 5 -> 4.1172 /rad
    a_t = 2 * math.pi * 4 / (2 + math.sqrt(4 + 16 / ETA ** 2))          # A 4 -> 3.7729 /rad
    deps = 2 * a_w / (math.pi * 5)                                       # 0.5242
    kt = 0.9 * a_t * 40000 * (1 - deps)
    x_np = (a_w * 200000 * 50 + kt * 625) / (a_w * 200000 + kt)          # 91.84 mm
    assert r["np_x_mm"] == pytest.approx(x_np, abs=0.05) and x_np == pytest.approx(91.84, abs=0.01)
    assert r["value"] == pytest.approx((x_np - 60) / 200, abs=1e-4) and r["ok"]       # 15.9 % MAC
    assert r["wing"]["aspect"] == pytest.approx(5.0) and r["wing"]["sweep_deg"] == pytest.approx(0.0, abs=1e-6)
    assert not req_aero.static_margin_tail(*_proj(monkeypatch, cg_x=95.0))["ok"]     # CG behind the NP
    # fuselage term (Raymer 16.25): K 0.01 / deg, W 60, L 500 -> Cm_alpha 0.01 x 3600 x 500 / (200 x 200000) x 57.3
    f = req_aero.static_margin_tail(proj, asm, fuselage={"k_fus": 0.01, "width_mm": 60, "length_mm": 500})
    cma = 0.01 * 60 ** 2 * 500 / (200 * 200000) * 180 / math.pi
    assert f["np_x_mm"] == pytest.approx(x_np - cma / (a_w + kt / 200000) * 200, abs=0.05)


def test_static_margin_tail_wings_swept_45_about_the_trailing_edge_corner(monkeypatch):
    proj, asm = _proj(monkeypatch, cg_x=150.0)
    r = req_aero.static_margin_tail(proj, asm, min=0.0, max=2.0, halves={"right": "wing_r", "left": "wing_l"},
                                    root_y=50, pose={"fold": 45})
    c = math.cos(math.radians(45))
    # each half's quarter-chord line (dx -150 from the pivot, dy 0..450) turns 45 deg aft: mean x = 200 + c (-150 + 225)
    x_half = 200 + c * 75                                                 # 253.03
    x_ac = (20000 * 50 + 2 * 90000 * x_half) / 200000                    # centre strip stays at x 50 -> 232.73
    span = 2 * (50 + c * 650)                                             # outer root LE corner swings out: 1019.2
    A_w = span ** 2 / 200000
    a_w = aero.lift_slope(A_w, 45)
    a_t = aero.lift_slope(4, 0)
    deps = 2 * a_w / (math.pi * A_w)
    kt = 0.9 * a_t * 40000 * (1 - deps)
    x_np = (a_w * 200000 * x_ac + kt * 625) / (a_w * 200000 + kt)
    assert r["wing_ac_x_mm"] == pytest.approx(x_ac, abs=0.05)
    assert r["wing"]["span_mm"] == pytest.approx(span, abs=0.1) and r["wing"]["sweep_deg"] == pytest.approx(45, abs=1e-6)
    assert r["wing"]["area_dm2"] == pytest.approx(20.0, abs=0.01)        # turning about a vertical axis keeps the area
    assert r["np_x_mm"] == pytest.approx(x_np, abs=0.05)
    assert r["value"] == pytest.approx((x_np - 150) / 200, abs=1e-4)
    home = req_aero.static_margin_tail(proj, asm, min=0.0, max=2.0, halves={"right": "wing_r", "left": "wing_l"}, root_y=50)
    assert home["np_x_mm"] < r["np_x_mm"]                                 # sweeping back moves the NP aft


def test_fold_hinge_moment_by_hand(monkeypatch):
    proj, asm = _proj(monkeypatch)
    proj.items["body"] = SimpleNamespace(role="part", shape=SimpleNamespace(
        location=Location(), joints={"pivot": SimpleNamespace(location=Location((200, 50, 0)))}))
    asm.edges = [SimpleNamespace(name="fold", kind="revolute", range=(0, 90), parent="body", pjoint="pivot")]
    r = req_aero.fold_hinge_moment(proj, asm, joint="fold", item="wing_r", side="right", speed_kmh=72, cd=0.05,
                                   stall_kgcm=2.0, ratio=2.0, root_y=50, samples=3)
    q = 0.5 * 1.225 * 20 ** 2 * 1e-6                                      # 2.45e-4 N/mm2 at 20 m/s
    # drag at mid-chord (dx -100 from the pivot, dy 0..450), arm about z = dy': at 0 deg sum dy = 450^2/2 = 101250;
    # at 45 deg dy' = c (100 + dy) -> c (45000 + 101250) = 103414 (the worst); at 90 deg 100 x 450 = 45000
    worst = q * 0.05 * 200 * math.cos(math.radians(45)) * (100 * 450 + 450 ** 2 / 2)
    assert r["at_deg"] == pytest.approx(45) and r["value"] == pytest.approx(worst / 98.0665, abs=1e-3)   # 2.58 kg.cm
    assert r["limit"] == pytest.approx(2.0) and not r["ok"]               # 2 x 2 x 0.5
    assert r["servo_kgcm"] == pytest.approx(r["value"] / 2, abs=1e-3)
    lift = req_aero.fold_hinge_moment(proj, asm, joint="fold", item="wing_r", side="right", speed_kmh=72, cd=0.05, cl=1.0,
                                      stall_kgcm=2.0, ratio=2.0, root_y=50, samples=3)
    assert lift["value"] == pytest.approx(r["value"], abs=1e-6)          # lift is parallel to a vertical pivot axis
