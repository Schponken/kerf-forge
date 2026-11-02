"""Realistic limits (Spencer, 2026-11-02): thin walls are only blocking on load-carrying parts, `advisory` requirements
warn instead of block (never on strength checks, always with a reason), and declared squashable items may be pressed
into by their compress_mm."""
from types import SimpleNamespace as NS

from build123d import Box, Pos

from kerf import assembly, checks, pipeline, requirements


def _proj(reqs, structural=False):
    return NS(items={"lid": NS(spec={"structural": structural}), "arm": NS(spec={})}, data={"requirements": reqs})


def _thin(p02):
    return {"min_wall_p02": p02, "problems": [f"lid: walls as thin as {p02:.2f} mm (2nd percentile); minimum is 0.8 mm"], "warnings": []}


def test_thin_walls_block_only_load_carrying_parts():
    free = pipeline.thin_wall_rule(_proj([]), "lid", _thin(0.5))
    assert free["problems"] == [] and "one 0.42 mm line" in free["warnings"][0]
    loaded = [{"check": "fea_static", "part": "lid", "sf": 2}]
    assert pipeline.thin_wall_rule(_proj(loaded), "lid", _thin(0.5))["problems"]               # named by a strength check
    assert pipeline.thin_wall_rule(_proj([], structural=True), "lid", _thin(0.5))["problems"]  # marked structural
    assert pipeline.thin_wall_rule(_proj([]), "lid", _thin(0.3))["problems"]                   # under one line: never prints
    other = [{"check": "fea_static", "part": "arm"}, {"check": "mass_max", "max_g": 9}]
    assert not pipeline.thin_wall_rule(_proj(other), "lid", _thin(0.5))["problems"]
    assert checks.MIN_WALL_LINE == 0.42


def test_advisory_misses_warn_but_never_for_strength(monkeypatch):
    monkeypatch.setitem(requirements.REGISTRY, "mass_max", lambda proj, asm, **kw: {"ok": False, "value": 260, "limit": 250, "detail": "mass"})
    monkeypatch.setitem(requirements.REGISTRY, "fea_static", lambda proj, asm, **kw: {"ok": False, "value": 30, "limit": 20, "detail": "stress"})
    soft = requirements._run_one(None, None, {"id": "m", "check": "mass_max", "advisory": "a heavier build is fine for a bench test"}, False)
    no_reason = requirements._run_one(None, None, {"id": "n", "check": "mass_max", "advisory": ""}, False)
    strong = requirements._run_one(None, None, {"id": "s", "check": "fea_static", "advisory": "please"}, False)
    assert soft["advisory"] and not no_reason.get("advisory") and not strong.get("advisory")
    assert "not allowed on a strength check" in strong["detail"] and "needs the reason" in no_reason["detail"]
    probs, warns = pipeline.req_misses([soft, no_reason, strong])
    assert len(probs) == 2 and len(warns) == 1 and warns[0].startswith("advisory requirement 'm' failed")


def test_squashable_items_take_a_press_up_to_their_depth():
    foam = NS(spec={"compress_mm": 2, "compress_why": "EVA foam pad under the battery"}, shape=Box(40, 40, 10))   # top at z = 5
    def block(dz):
        return NS(spec={}, shape=Pos(0, 0, 5 + 5 - dz) * Box(20, 20, 10))   # bottom face dz below the foam's top
    assert assembly.squashed(foam, block(1.5)) and assembly.squashed(block(1.5), foam)
    assert not assembly.squashed(foam, block(3.0))
    rigid = NS(spec={"compress_mm": 2}, shape=foam.shape)                       # no reason given: stays rigid
    assert not assembly.squashed(rigid, block(1.0))
    assert abs(assembly.press_depth(foam, block(1.5)) - 1.5) < 0.05
