"""Fixed wing (kerf/aero.py, kerf/req_aero.py) against hand calculations."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

from kerf import aero, req_aero
from kerf import electrical as E
from test_electrical import _proj as _quad


def test_naca4_thickness_and_camber():
    assert aero.thickness(aero.airfoil("naca0012")) == pytest.approx(0.12, abs=0.002)
    af = aero.airfoil("naca2412")
    assert aero.thickness(af) == pytest.approx(0.12, abs=0.003)
    zu, zl = aero.mid_z(af, 0.4)
    assert (zu + zl) / 2 == pytest.approx(0.02, abs=0.001)            # max camber 2 % at 40 % chord
    assert af[0, 0] == pytest.approx(1) and af[np.argmin(af[:, 0]), 0] == pytest.approx(0, abs=1e-9)


def test_dat_formats():
    selig = "TEST\n1.0 0.001\n0.5 0.05\n0.0 0.0\n0.5 -0.03\n1.0 -0.001\n"
    led = "TEST\n3. 3.\n\n0.0 0.0\n0.5 0.05\n1.0 0.001\n\n0.0 0.0\n0.5 -0.03\n1.0 -0.001\n"
    a, b = aero.parse_dat(selig), aero.parse_dat(led)
    assert np.allclose(a, b) and a.shape == (5, 2)
    assert aero.parse_dat("X\n100 1\n50 5\n0 0\n50 -3\n100 -1\n")[1, 1] == pytest.approx(0.05)   # scaled to unit chord
    with pytest.raises(ValueError, match="UIUC"):
        aero.airfoil("no_such_foil")


def test_planform_geometry_by_hand():
    pf = aero.Planform(span=1000, root_chord=300, tip_chord=150, sweep_le_deg=30)
    g = pf.geometry()
    # S = 1000 (300+150)/2; taper 0.5; MAC = 2/3 300 (1+.5+.25)/1.5 = 233.33; y_mac = 1000/6 x 2/1.5 = 222.22
    assert g["area_mm2"] == pytest.approx(225000) and g["aspect_ratio"] == pytest.approx(1e6 / 225000)
    assert g["mac_mm"] == pytest.approx(233.333, abs=1e-3) and g["y_mac_mm"] == pytest.approx(222.222, abs=1e-3)
    assert g["x_le_mac_mm"] == pytest.approx(222.222 * math.tan(math.radians(30)), abs=1e-3)
    assert g["x_np_mm"] == pytest.approx(128.300 + 58.333, abs=1e-2)
    assert pf.chord(-250) == pytest.approx(225) and pf.x_le(-250) == pytest.approx(pf.x_le(250))   # symmetric


def test_wing_solid_volume_matches_section_areas():
    pf = aero.Planform(span=1000, root_chord=300, tip_chord=150, sweep_le_deg=25, root_airfoil="naca0012", te_min=0.6)
    s = aero.wing_solid(pf, 100, 400)
    k = abs(np.trapezoid(pf.section_af(0)[:, 1], pf.section_af(0)[:, 0]))    # area / chord^2 of the polygon
    c0, c1 = pf.chord(100), pf.chord(400)
    # area(c) = k c^2 + te_min c / 2 (thickened TE); c linear in y -> integral exact
    vol = k * 300 / 3 * (c0 ** 2 + c0 * c1 + c1 ** 2) + 0.6 / 2 * 300 * (c0 + c1) / 2
    assert s.is_valid and s.volume == pytest.approx(vol, rel=0.003)
    assert s.is_inside(tuple(aero.spar_point(pf, 250, 0.3)))
    lo = s.bounding_box()
    assert lo.min.Y == pytest.approx(100, abs=1e-3) and lo.max.Y == pytest.approx(400, abs=1e-3)


def test_elevon_is_cut_off_and_deflects_both_ways_without_touching_the_wing():
    from build123d import Axis
    pf = aero.Planform(span=1000, root_chord=280, tip_chord=150, sweep_le_deg=25, twist_tip_deg=-2, root_airfoil="naca2410")
    s = aero.wing_solid(pf, 60, 300) - aero.spar_channel(pf, aero.spar_line(pf, .3, .3, 60, 480), 8.2)
    w, e, (a, b) = aero.elevon_split(pf, s, 150, 300, 0.78)
    w, e = aero.largest(w), aero.largest(e)
    assert w.is_valid and e.is_valid and e.volume > 30000
    assert w.volume + e.volume < s.volume and w.volume + e.volume > 0.98 * s.volume   # only the V gap and the end gaps
    d = tuple((b - a) / np.linalg.norm(b - a))
    for ang in (-28, -15, 15, 28):
        x = w & e.rotate(Axis(tuple(a), d), ang)
        assert x is None or x.volume < 1e-3, ang
    assert a[2] < aero.spar_point(pf, 150, 0.78)[2]                       # hinge on the lower surface


def test_stall_speed_and_root_moment_by_hand():
    # V = sqrt(2 x 1.3 x 9.80665 / (1.225 x 0.215 x 0.9)) = 10.372 m/s = 37.34 km/h
    assert aero.stall_speed_kmh(1300, 0.215, 0.9) == pytest.approx(37.34, abs=0.01)
    # elliptical half-wing lift W/2 acts 4 s / (3 pi) from the root: 1 kg, 1 g, s 500 -> 4.9033 N x 212.21 = 1040.5 N mm
    assert aero.root_moment_nmm(1000, 1, 500, 0) == pytest.approx(4.90333 * 4 * 500 / (3 * math.pi), rel=2e-3)
    assert aero.root_moment_nmm(1000, 6, 500, 0) == pytest.approx(6 * aero.root_moment_nmm(1000, 1, 500, 0))
    assert aero.root_moment_nmm(1000, 1, 500, 100) < aero.root_moment_nmm(1000, 1, 500, 0)


def _fake(monkeypatch, cg_x=150.0, mass=1000.0):
    params = dict(wing_span=1000, wing_root_chord=300, wing_tip_chord=150, wing_sweep_le_deg=30, wing_airfoil="naca0012")
    proj = SimpleNamespace(params=params, items={})
    monkeypatch.setattr(req_aero, "assembly_cg", lambda p: (np.array([cg_x, 0, 0]), mass))
    monkeypatch.setattr(req_aero, "_mass", lambda p: mass)
    return proj


def test_static_margin_wing_loading_stall(monkeypatch):
    proj = _fake(monkeypatch, cg_x=163.3)
    r = req_aero.static_margin(proj, None, 0.05, 0.15)
    # NP 186.633, MAC 233.333: (186.633 - 163.3) / 233.333 = 0.1000
    assert r["value"] == pytest.approx(0.1, abs=1e-4) and r["ok"]
    assert not req_aero.static_margin(_fake(monkeypatch, cg_x=190), None)["ok"]          # CG behind the NP: unstable
    assert req_aero.wing_loading(proj, None, 50)["value"] == pytest.approx(1000 / 22.5, abs=0.05)
    st = req_aero.stall_speed(proj, None, 60, cl_max=0.8)
    assert st["value"] == pytest.approx(aero.stall_speed_kmh(1000, 0.225, 0.8), abs=0.05)
    with pytest.raises(ValueError, match="airfoils.json"):
        req_aero.stall_speed(proj, None, 60, airfoil="naca0012x")


def test_spar_bending_by_hand(monkeypatch):
    proj = _fake(monkeypatch, mass=1200.0)
    tube = {"od_mm": 8, "id_mm": 6, "flexural_strength_mpa": 600, "modulus_gpa": 100, "source": "x"}
    monkeypatch.setattr(req_aero.catalog, "get", lambda path: tube)
    r = req_aero.spar_bending(proj, None, tubes=["rods.carbon_8x6"], y_root=60, load_factor=6, sf=1.5)
    M = aero.root_moment_nmm(1200, 6, 500, 60)
    I = math.pi / 64 * (8 ** 4 - 6 ** 4)                                  # 137.44 mm^4
    assert r["moment_nmm"] == pytest.approx(M, abs=1) and r["load_factor"] == 6
    assert r["value"] == pytest.approx(M * 4 / I / (600 / 1.5), rel=1e-3)
    two = req_aero.spar_bending(proj, None, tubes=["a", "b"], y_root=60, load_factor=6, sf=1.5)
    assert two["value"] == pytest.approx(r["value"] / 2, abs=1e-4)        # two equal tubes share the moment


def test_cruise_power_and_time_by_hand(tmp_path):
    proj, asm = _quad(tmp_path, extra="  cruise: {speed_kmh: 72, l_over_d: 8, eta: 0.5, why: test}")
    m = E.analyse(proj)
    # 260.8 g x 9.80665 x 20 m/s / 8 / 0.5 = 12.788 W; battery 12.788 / 14.8 + 0.3 + 0.0372 = 1.2013 A; 1.2 Ah / 1.2013 A
    assert m["hover"]["mode"] == "cruise" and m["hover"]["power_w"] == pytest.approx(12.79, abs=0.05)
    assert m["avg_a"] == pytest.approx(1.2013, abs=0.002)
    assert m["minutes"] == pytest.approx(59.9, abs=0.1)
    from kerf import req_electrical
    assert req_electrical.flight_time(proj, asm, 10)["detail"].startswith("cruise flight time (min)")


def test_clmax_from_the_catalog_picks_a_safe_reynolds_number():
    cl, re = aero.clmax_2d("mh45")                      # no Re given: the lowest listed (lower clmax = conservative)
    assert re == 200000 and cl == pytest.approx(1.185)
    assert aero.clmax_2d("MH45", 600000)[1] == 500000 and aero.clmax_2d("mh45", 300000)[1] == 200000
    assert aero.thickness(aero.airfoil("mh45")) == pytest.approx(0.0985, abs=0.001)
    assert aero.mid_z(aero.airfoil("mh45"), 0.98)[0] + aero.mid_z(aero.airfoil("mh45"), 0.98)[1] < 0   # reflexed TE
