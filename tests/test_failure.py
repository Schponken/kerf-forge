"""Failure modes (kerf/failure.py): the per-part failure table and weak_link (the cheap part breaks first)."""
from types import SimpleNamespace as NS

import pytest

from kerf import assembly as A, failure, project as P, requirements as R
from test_engine import _write_project

BEAM = """
from build123d import *
def build(ctx):
    ctx.rigid("root", Location((0, 0, 0)))
    ctx.rigid("next", Location((0, 40, 0)))
    return ctx.finish(Box(100, 10, {t}, align=(Align.MIN, Align.CENTER, Align.CENTER)))
"""
CASE = "{{id: {i}, check: fea_static, part: {p}, sf: 3.0, case: crash, fixed: {{box: [[-0.1, -6, -7], [0.1, 6, 7]]}}, loads: [{{box: [[99.9, -6, -7], [100.1, 6, 7]], force_n: [0, 0, {f}]}}]}}"


def _proj(tmp_path, extra):
    y = f"""
name: Two beams
params: {{}}
parts:
  thin: {{file: parts/thin.py, material: PETG, walls: 4}}
  thick: {{file: parts/thick.py, material: PETG, walls: 4}}
assembly:
  root: thin
  joints:
    - {{parent: thin.next, child: thick.root}}
requirements:
  - {CASE.format(i="thin_hit", p="thin", f=-10)}
  - {CASE.format(i="thick_hit", p="thick", f=-20)}
{extra}
"""
    d = _write_project(tmp_path / "two", y, {"thin": BEAM.format(t=6), "thick": BEAM.format(t=12)})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    return proj, asm, R.run_all(proj, asm)


def test_weak_link_compares_uses_at_the_same_force(tmp_path):
    extra = """  - {id: weak, check: weak_link, cheap: thin_hit, expensive: [thick_hit]}
  - {id: wrong, check: weak_link, cheap: thick_hit, expensive: thin_hit}"""
    proj, asm, rows = _proj(tmp_path, extra)
    r = {x["id"]: x for x in rows}
    thin, thick = r["thin_hit"], r["thick_hit"]
    # same 10 N event: the thick case ran at 20 N, so its use is halved before comparing (stress is linear in load)
    expect = (thin["value"] / thin["limit"]) / (thick["value"] / thick["limit"] / 2)
    assert r["weak"]["ok"] and r["weak"]["value"] == pytest.approx(expect, rel=1e-2)
    assert expect == pytest.approx(4.0, rel=0.15)                    # M c / I ~ 1 / t^2: (12 / 6)^2
    assert not r["wrong"]["ok"] and "NOT the weak link" in r["wrong"]["detail"]
    rep = {"requirements": rows, "parts": {"thin": {"mass_est_g": 5.0}, "thick": {"mass_est_g": 10.0}},
           "assembly": {"fasteners": [{"male": "thin", "female": "thick"}]}}
    t = failure.table(proj, asm, rep)
    assert [x["part"] for x in t] == ["thin", "thick"]            # most used first
    assert t[0]["fails_in"] == "thin_hit" and t[0]["screws_to_undo"] == 1 and "along its print layers" in t[0]["how"]
    assert t[0]["reprint_min_at_least"] > 0 and t[0]["filament_usd"] is not None
    md = "\n".join(failure.lines(t))
    assert "| thin | thin_hit |" in md and "undo 1 screws" in md


def test_mounted_items_stop_at_the_next_printed_part():
    items = {"arm": NS(role="printed", spec={}), "motor": NS(role="purchased", spec={"catalog": "drone.motors.x"}),
             "prop": NS(role="keepout", spec={"catalog": "drone.props.y", "owner": "motor"}),
             "cover": NS(role="printed", spec={}), "cam": NS(role="purchased", spec={"catalog": "c"}),
             "zone": NS(role="keepout", spec={"owner": "motor"})}
    asm = NS(children={"arm": ["motor", "cover"], "cover": ["cam"]})
    assert failure._mounted(NS(items=items), asm, "arm") == ["motor", "prop"]


def test_deflection_governs_when_it_is_the_larger_use():
    use, what = failure._use({"value": 5, "limit": 10, "max_disp_mm": 0.9}, {"max_disp_mm": 1.0})
    assert use == pytest.approx(0.9) and what == "deflection" and "bends too far" in failure._how({}, what)
    assert "between print layers" in failure._how({"direction": "z"}, "stress")
