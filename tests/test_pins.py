"""Pinned hinges: a clevis (two lugs on the base) and a knuckle on the arm, joined by a dowel or a screw pivot.
The pin check must accept the correct hinge and catch each way a real hinge goes wrong."""
import textwrap

import pytest
from build123d import Location

from kerf import assembly as A, catalog, export, iface, pins, project as P
from kerf.ctx import Ctx

# Pin axis along world Y at x=0, z=20. Lugs y in [4, 8] and [-8, -4]; knuckle y in [-3.5, 3.5]: span 16 mm = a stocked
# D3 dowel length, 0.5 mm side gaps.
YAML = """
name: hinge
params: {joint_x: 0.0, knuckle_dx: 0.0, arm_fit: free, lug_fit: press, pin: motion.pin_3mm, lug_out: 8.0}
parts:
  base: {file: parts/base.py}
  arm: {file: parts/arm.py}
assembly:
  root: base
  joints: [{name: swing, parent: base.pivot, child: arm.hub, range: [-60, 0]}]
"""
BASE = """
from build123d import *
from kerf import iface
def build(ctx):
    p = ctx.p
    s = Box(30, 24, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sy in (1, -1):
        y0 = sy * (p.lug_out + 4) / 2
        s += Pos(0, y0, 10) * Box(12, p.lug_out - 4, 16, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sy, rx in ((1, -90), (-1, 90)):
        loc = Location((0, sy * p.lug_out, 20), (rx, 0, 0))
        s -= iface.pin_hole(ctx, p.pin, loc, "hinge", depth=p.lug_out - 4, fit=p.lug_fit, through=False, teardrop=0)
    ctx.revolute("pivot", Axis((p.joint_x, 0, 20), (0, 1, 0)), range=(-60, 0))
    return ctx.finish(s)
"""
ARM = """
from build123d import *
from kerf import iface
def build(ctx):
    p = ctx.p
    s = Pos(0, 0, 20) * Rot(90, 0, 0) * Cylinder(6, 7)
    s += Pos(0, 0, 16) * Box(50, 7, 8, align=(Align.MIN, Align.CENTER, Align.MIN))
    s -= iface.pin_hole(ctx, p.pin, Location((p.knuckle_dx, 3.5, 20), (-90, 0, 0)), "hinge", depth=7, fit=p.arm_fit,
                        teardrop=0)
    ctx.rigid("hub", Location((0, 0, 20), (-90, 0, 0)))  # child Z = the hinge axis (local +Y)
    return ctx.finish(s)
"""


def _asm(tmp, **params):
    d = tmp / "hinge"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "base.py").write_text(textwrap.dedent(BASE))
    (d / "parts" / "arm.py").write_text(textwrap.dedent(ARM))
    proj = P.build(P.load(str(d), params))
    errs = {k: v.error for k, v in proj.items.items() if v.error}
    assert not errs, errs
    asm = A.plan(proj)
    A.solve(asm)
    return proj, asm


def test_hole_sizes_from_catalog():
    f = catalog.get("fdm_fits.pin")
    d = catalog.get("motion.pin_3mm")["d"]
    for fit in ("free", "press"):
        ctx = Ctx("t", {})
        c = iface.pin_hole(ctx, "motion.pin_3mm", Location(), "g", depth=5, fit=fit)
        bb = c.bounding_box()
        assert bb.size.X == pytest.approx(d + f[f"{fit}_allowance_d"], abs=1e-3)
        assert ctx.pins[0].fit == fit and ctx.pins[0].d == d
    assert f["press_allowance_d"] < f["free_allowance_d"]
    with pytest.raises(ValueError):
        iface.pin_hole(Ctx("t", {}), "motion.pin_3mm", Location(), "g", depth=5, fit="heatset")
    with pytest.raises(ValueError):
        iface.pin_hole(Ctx("t", {}), "M3", Location(), "g", depth=5, fit="press")


def test_dowel_hinge_passes_and_sizes_pin(tmp_path):
    proj, asm = _asm(tmp_path)
    out, problems, warnings = pins.check(asm)
    assert problems == [], problems
    (pj,) = out
    assert pj["length_mm"] == 16 and pj["span_mm"] == pytest.approx(16)
    assert pj["fixed_in"] == ["base"] and pj["free_in"] == ["arm"]
    # the hinge really swings: no collisions through the range
    assert all(s["clear"] for s in A.sweeps(asm, samples=5))
    # and it lands in the BOM
    rows = export.bom(proj, [], {}, tmp_path, pins=out)
    assert any(r["type"] == "pin" and r["item"] == "3 x 16 mm steel dowel pin" for r in rows)


def test_joint_axis_off_pin_binds(tmp_path):
    _, asm = _asm(tmp_path, joint_x=1.0)
    _, problems, _ = pins.check(asm)
    assert any("joint 'swing'" in p and "bind" in p for p in problems), problems


def test_misaligned_hole_detected(tmp_path):
    _, asm = _asm(tmp_path, knuckle_dx=0.3)
    _, problems, _ = pins.check(asm)
    assert any("off the pin axis" in p and "arm" in p for p in problems), problems


def test_pin_free_everywhere_falls_out(tmp_path):
    _, asm = _asm(tmp_path, lug_fit="free")
    _, problems, _ = pins.check(asm)
    assert any("free in every part" in p for p in problems), problems


def test_pin_fixed_both_sides_locks_joint(tmp_path):
    _, asm = _asm(tmp_path, arm_fit="press")
    _, problems, _ = pins.check(asm)
    assert any("locks the joint" in p for p in problems), problems


def test_span_without_stocked_length(tmp_path):
    _, asm = _asm(tmp_path, lug_out=8.5)  # span 17 mm, 4.5 mm lugs: 16 mm pin can't fill both lugs, 20 too long
    _, problems, _ = pins.check(asm)
    assert any("no stocked" in p for p in problems), problems


SCREW_BASE = BASE.replace('''    for sy, rx in ((1, -90), (-1, 90)):
        loc = Location((0, sy * p.lug_out, 20), (rx, 0, 0))
        s -= iface.pin_hole(ctx, p.pin, loc, "hinge", depth=p.lug_out - 4, fit=p.lug_fit, through=False, teardrop=0)''',
'''    s -= iface.pin_hole(ctx, "M3", Location((0, p.lug_out, 20), (-90, 0, 0)), "hinge", depth=p.lug_out - 4, fit="free")
    s -= iface.pin_hole(ctx, "M3", Location((0, -4, 20), (-90, 0, 0)), "hinge", depth=p.lug_out - 4 + 4, fit="heatset")''')


def test_screw_pivot_into_heatset(tmp_path):
    """M3 screw through the +Y lug and the knuckle, threaded into a heat-set insert in the -Y lug (a deeper boss)."""
    d = tmp_path / "hinge"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    (d / "parts" / "base.py").write_text(textwrap.dedent(SCREW_BASE).replace("Box(12, p.lug_out - 4, 16",
                                                                               "Box(12, p.lug_out - 4 + (4 if sy < 0 else 0), 16").replace(
        "y0 = sy * (p.lug_out + 4) / 2", "y0 = sy * (p.lug_out + 4) / 2 + (-2 if sy < 0 else 0)"))
    (d / "parts" / "arm.py").write_text(textwrap.dedent(ARM))
    proj = P.build(P.load(str(d), {"pin": "M3"}))
    assert not {k: v.error for k, v in proj.items.items() if v.error}
    asm = A.plan(proj)
    A.solve(asm)
    out, problems, warnings = pins.check(asm)
    assert problems == [], problems
    (pj,) = out
    assert pj["screw_pivot"] and pj["fixed_fit"] == ["heatset"]
    # head on the +Y lug face (y=8); insert hole from y=-4, tip may reach 6.7 - 0.5 = 6.2 deep (y=-10.2); thread
    # engagement >= min(0.7*5.7, 4.5) = 3.99 -> 15.99 <= L <= 18.2: 16 or 18; the longest (most thread) wins
    assert pj["length_mm"] == 18
    assert any("threadlocker" in w for w in warnings)
    rows = export.bom(proj, [], {}, tmp_path, pins=out)
    assert any("M3 x 18 mm socket head screw (pivot)" in r["item"] for r in rows)
    assert any(r["item"] == "M3 heat-set insert" for r in rows)
