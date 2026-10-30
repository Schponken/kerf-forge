"""Gear and belt helpers (kerf/drives.py) against hand-calculated answers and real assembled geometry."""
import math
import textwrap

import pytest
from build123d import Location, Pos, Rot

from kerf import assembly as A, drives, geom, project as P


def _ov(a, b):
    return geom.volume(a & b)


@pytest.fixture(scope="module")
def pair():
    return drives.spur_pair(1.5, 20, 40, 6)


# ------------------------------------------------------------------------------------------- gears
def test_gear_pair_numbers_by_hand(pair):
    g1, g2, i = pair
    # m (z1 + z2) / 2 = 1.5 * 60 / 2 = 45; tip = m (z + 2) = 33 and 63; ratio 40 / 20 = 2, opposite directions
    assert i.center == pytest.approx(45.0)
    assert i.tip_d == pytest.approx((33.0, 63.0)) and i.pitch_d == pytest.approx((30.0, 60.0))
    assert i.ratio == 2.0 and i.ratio_signed == -0.5
    assert g1.is_valid and g2.is_valid and len(geom.solids(g1)) == 1 and len(geom.solids(g2)) == 1
    assert g1.bounding_box().size.Z == pytest.approx(6.0)
    for g, tip in ((g1, 33.0), (g2, 63.0)):
        rmax = max(math.hypot(v.X, v.Y) for v in g.vertices())
        assert rmax <= tip / 2 + 1e-6 and rmax > tip / 2 - 0.3      # tips truncated by py_gearworks 0.1 m at most


def test_gears_mesh_without_touching_through_a_full_turn(pair):
    g1, g2, i = pair
    for a1 in range(0, 360, 9):
        a2 = i.ratio_signed * a1
        assert _ov(Rot(0, 0, a1) * g1, Pos(i.center, 0, 0) * Rot(0, 0, a2) * g2) < 1e-4, f"teeth collide at {a1} deg"


def test_teeth_really_engage(pair):
    g1, g2, i = pair
    # moving the gears 0.3 mm circumferential backlash / (2 tan 20 deg) = 0.41 mm closer takes up all the play; 0.6 mm
    # closer the flanks must cut into each other (tip-root clearance 0.25 m = 0.375 mm is larger, so it is the flanks)
    assert _ov(g1, Pos(i.center - 0.6, 0, 0) * g2) > 0.05
    assert _ov(g1, Pos(i.center - 0.3, 0, 0) * g2) < 1e-4


def test_backlash_is_the_fdm_value(pair):
    """Hold gear 1, rock gear 2 each way until a tooth touches: the free arc at gear 2's pitch circle is the backlash."""
    g1, g2, i = pair

    def touches(deg):
        return _ov(g1, Pos(i.center, 0, 0) * Rot(0, 0, deg) * g2) > 1e-4

    def limit(sign):
        lo, hi = 0.0, 3.0
        assert touches(sign * hi)
        for _ in range(22):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if touches(sign * mid) else (mid, hi)
        return lo

    play_deg = limit(1) + limit(-1)
    arc = math.radians(play_deg) * i.pitch_d[1] / 2
    # circumferential backlash ~ 0.3 mm (Sovol: 0.2-0.4 total for FDM); involute flank thinning measured at the pitch
    # circle differs from the transverse arc by cos(20 deg) at most
    assert 0.3 * math.cos(math.radians(20)) - 0.03 <= arc <= 0.3 / math.cos(math.radians(20)) + 0.03, arc


def test_gear_refusals():
    with pytest.raises(ValueError):
        drives.spur_pair(0.8, 20, 40, 6)         # too fine for a 0.4 mm nozzle
    with pytest.raises(ValueError):
        drives.spur_pair(1.5, 8, 40, 6)          # undercut root too weak
    with pytest.raises(ValueError):
        drives.spur_pair(1.5, 20, 40, 6, bore1=24)   # root d = 1.5 * 17.5 = 26.25 -> 1.1 mm wall
    _, _, i = drives.spur_pair(1.0, 20, 30, 5, bore1=8.0, bore2=8.0)
    assert i.warnings and "module" in i.warnings[0]


# ------------------------------------------------------------------------------------------- belts
def test_belt_lengths_by_hand():
    # equal 20T pulleys: L = 2C + pi D = 200 + 40 = 240 mm = 120 teeth
    assert drives.belt_length(100, 20, 20) == pytest.approx(240.0)
    assert drives.belt_teeth(100, 20, 20) == 120
    # 20T / 40T at 100 mm: D = 12.732 / 25.465; L = 200 + 60 + 12.732^2 / 400 = 260.405
    assert drives.belt_length(100, 20, 40) == pytest.approx(260.405, abs=1e-3)
    assert drives.belt_teeth(100, 20, 40) == 130          # the 130T / 260 mm belt in the catalog source
    c = drives.center_for_belt(130, 20, 40)
    assert c == pytest.approx(99.797, abs=1e-3)
    assert drives.belt_length(c, 20, 40) == pytest.approx(260.0, abs=1e-9)
    # wrap on the small pulley: 180 - 2 asin(12.732 / 200) = 172.70 deg -> 9.59 teeth in mesh
    assert drives.wrap_deg(100, 20, 40) == pytest.approx(172.70, abs=0.01)
    assert drives.teeth_in_mesh(100, 20, 40) == pytest.approx(9.59, abs=0.01)
    assert drives.teeth_in_mesh(100, 20, 40) >= drives.MIN_TEETH_IN_MESH
    with pytest.raises(ValueError):
        drives.center_for_belt(30, 20, 40)
    with pytest.raises(ValueError):
        drives.belt_length(10, 20, 40)


def test_belt_keepout_band():
    k = drives.belt_keepout(100, 20, 40, 6, margin=0.0)
    assert k.is_valid
    pld = drives.pulley_pld()
    assert pld == pytest.approx((12.73 - 12.2) / 2)
    r1 = drives.pulley_pitch_d(20) / 2
    # hand volume: band = (outer hull - inner hull) area x width. Both hulls are two circles + tangent lines; with
    # r_out = r_in + 1.52 the area difference is 1.52 x (mean perimeter) where mean perimeter = belt_length at the
    # mid-band radius offset. Use the pitch formula with the mid radius (exact for this shape).
    t = 1.52
    def perim(dr):
        a = drives.pulley_pitch_d(20) / 2 - pld + dr
        b = drives.pulley_pitch_d(40) / 2 - pld + dr
        phi = math.asin((b - a) / 100)
        return 2 * 100 * math.cos(phi) + a * (math.pi - 2 * phi) + b * (math.pi + 2 * phi)
    assert geom.volume(k) == pytest.approx(t * perim(t / 2) * 6, rel=0.01)
    # the belt sits outside the pulley tips and the empty loop between the pulleys is not keep-out
    from build123d import Box
    probe = lambda x, y: Pos(x, y, 3) * Box(0.05, 0.05, 0.05)  # noqa: E731
    assert _ov(k, probe(0, -(r1 - pld + 0.7))) > 0
    assert _ov(k, probe(50, 0)) == 0 and _ov(k, probe(0, 0)) == 0


# ------------------------------------------------------------------------------------------- in a project
GEAR_YAML = """
name: g
parts:
  frame: {file: parts/frame.py}
  g1: {file: parts/g1.py}
  g2: {file: parts/g2.py}
assembly:
  root: frame
  joints:
    - {parent: frame.a1, child: g1.axis, name: j1, range: [-180, 180]}
    - {parent: frame.a2, child: g2.axis, name: j2, range: [-90, 90]}
  sweeps: SWEEPS
"""
FRAME = """
from build123d import *
def build(ctx):
    s = Pos(22.5, 0, 0) * Box(120, 50, 4, align=(Align.CENTER, Align.CENTER, Align.MAX))
    ctx.revolute("a1", Axis((0, 0, 1), (0, 0, 1)))
    ctx.revolute("a2", Axis((45, 0, 1), (0, 0, 1)))
    return ctx.finish(s)
"""
GEAR = """
from build123d import *
from kerf import drives
def build(ctx):
    g = drives.spur_pair(1.5, 20, 40, 6)[IDX]
    ctx.rigid("axis", Location((0, 0, 0)))
    return ctx.finish(g)
"""


def _gear_proj(tmp, sweeps):
    d = tmp / "g"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(GEAR_YAML.replace("SWEEPS", sweeps)))
    (d / "parts" / "frame.py").write_text(textwrap.dedent(FRAME))
    (d / "parts" / "g1.py").write_text(textwrap.dedent(GEAR.replace("IDX", "0")))
    (d / "parts" / "g2.py").write_text(textwrap.dedent(GEAR.replace("IDX", "1")))
    proj = P.build(P.load(str(d)))
    assert not {k: v.error for k, v in proj.items.items() if v.error}
    asm = A.plan(proj)
    A.solve(asm)
    return asm


def test_coupled_gear_sweep(tmp_path):
    asm = _gear_proj(tmp_path, "[{joint: j2, follows: j1, ratio: -0.5}]")
    assert A.interference(asm) == []
    sw = A.sweeps(asm, samples=13)
    assert [s["joint"] for s in sw] == ["j1"]            # j2 only moves with j1
    assert sw[0]["clear"], sw


def test_uncoupled_gears_collide(tmp_path):
    asm = _gear_proj(tmp_path, "[]")
    sw = {s["joint"]: s for s in A.sweeps(asm, samples=13)}
    assert not sw["j1"]["clear"]                         # turning one gear alone jams the teeth: coupling is needed


BELT_YAML = """
name: b
parts:
  plate: {file: parts/plate.py}
purchased:
  p1: {catalog: motion.GT2_20T_pulley, proxy: pulley}
  p2: {catalog: motion.GT2_20T_pulley, proxy: pulley}
keepouts:
  belt: {proxy: belt, center: CDIST, teeth: [20, 20], owner: p1}
assembly:
  root: plate
  joints:
    - {parent: plate.s1, child: p1.bore}
    - {parent: plate.s2, child: p2.bore}
    - {parent: p1.bore, child: belt.axis1}
  allow_overlap: [{pair: [belt, p2], max_mm3: 1.0e9, why: belt wraps pulley 2 inside its flanges}]
"""
BELT_PLATE = """
from build123d import *
def build(ctx):
    s = Pos(40, 0, 0) * Box(140, 40, 4, align=(Align.CENTER, Align.CENTER, Align.MAX))
    s += Pos(40, POST, 0) * Box(6, 6, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))   # a post near the belt
    ctx.rigid("s1", Location((0, 0, 1)))
    ctx.rigid("s2", Location((CDIST, 0, 1)))
    return ctx.finish(s)
"""


@pytest.mark.parametrize("post_y,hit", [(14.0, False), (8.0, True)])
def test_belt_keepout_catches_a_post_in_the_belt_path(tmp_path, post_y, hit):
    c = drives.center_for_belt(120, 20, 20)
    assert c == pytest.approx(100.0)
    d = tmp_path / "b"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(BELT_YAML.replace("CDIST", repr(c))))
    (d / "parts" / "plate.py").write_text(textwrap.dedent(BELT_PLATE.replace("POST", str(post_y)).replace("CDIST", repr(c))))
    proj = P.build(P.load(str(d)))
    assert not {k: v.error for k, v in proj.items.items() if v.error}
    asm = A.plan(proj)
    A.solve(asm)
    hits = A.interference(asm)
    assert bool([h for h in hits if {"belt", "plate"} == {h["a"], h["b"]}]) == hit, hits
    assert not [h for h in hits if "plate" not in (h["a"], h["b"])], hits
