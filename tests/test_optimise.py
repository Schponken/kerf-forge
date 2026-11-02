"""Optimise then explain (kerf/optimise.py): pattern search over declared params within every check."""
import pytest

from kerf import optimise as O
from test_engine import _write_project


def _fake(vals):
    """Thickness t: mass grows with t, stress ~ 1 / t^2 must stay <= 10 (passes for t >= 4)."""
    t = vals["t"]
    stress = 160.0 / t ** 2
    ok = stress <= 10.0
    return {"ok": ok, "mass": {"device_g": 5 * t},
            "requirements": [{"id": "root", "ok": ok, "value": stress, "limit": 10.0, "bound": "max"}],
            "problems": [] if ok else ["requirement 'root' failed"]}


def test_search_walks_into_the_passing_region_then_minimises_mass():
    space = {"t": {"lo": 2, "hi": 8, "step": 1, "start": 7}}
    res = O.search(space, _fake, {"minimise": "mass"}, max_runs=20)
    assert res["best"]["t"] == 4 and res["best_report"]["ok"]
    from_bad = O.search({"t": {"lo": 2, "hi": 8, "step": 1, "start": 2}}, _fake, {"minimise": "mass"}, max_runs=20)
    assert from_bad["best"]["t"] == 4                                  # infeasible start: walks by how far it misses
    why = O.explain(res, space, {"minimise": "mass"})
    assert any("Binding: `root` uses 100%" in w for w in why) and any("t -1 fails root" in w for w in why)
    stiff = O.search(space, _fake, {"maximise": "root"}, max_runs=20)
    assert stiff["best"]["t"] == 8                                      # most margin on root


def test_use_reads_max_and_min_bounds():
    assert O.use({"value": 5, "limit": 10, "bound": "max"}) == 0.5
    assert O.use({"value": 20, "limit": 10, "bound": "min"}) == 0.5
    assert O.use({"value": "clear", "limit": 1}) is None


BAR = """
from build123d import *
def build(ctx):
    ctx.rigid("root", Location((0, 0, 0)))
    ctx.rigid("tip", Location((100, 0, 0)))
    return ctx.finish(Box(100, 10, ctx.p.t, align=(Align.MIN, Align.CENTER, Align.CENTER)))
"""


@pytest.mark.slow
def test_real_run_on_a_beam_writes_the_trade_off(tmp_path, monkeypatch):
    monkeypatch.setattr(O, "SCRATCH", tmp_path / "scratch")
    y = """
name: Beam to lighten
params: {t: {value: 14, min: 6, max: 16, step: 2}}
parts:
  bar: {file: parts/bar.py, material: PETG}
assembly:
  root: bar
  joints: []
requirements:
  - {id: root, check: cantilever_stress, part: bar, section: {name: root, at: [20, 0, 0], normal: [1, 0, 0]},
     loads: [{at: tip, force_n: [0, 0, -20]}], sf: 2}
optimise:
  vary: [t]
  goal: {minimise: mass}
  max_runs: 8
"""
    d = _write_project(tmp_path / "beam", y, {"bar": BAR})
    res = O.run(str(d))
    # sigma = 6 M / (b t^2) = 6 * 20 * 80 / (10 t^2) <= 24 MPa (PETG 48 / SF 2) -> t >= 6.3: step 2 reaches 8, the
    # halved step 1 then finds 7 (19.6 MPa) and rejects 6 (26.7 MPa)
    assert res["best"]["t"] == 7 and res["best_report"]["ok"]
    md = (d / "out" / "OPTIMISE.md").read_text()
    assert "**t = 7**" in md and "| 6 | no |" in md and "Binding: `root`" in md
    assert not (d / "out" / "report.json").exists()                   # the project's own out/ only gets the trade-off
