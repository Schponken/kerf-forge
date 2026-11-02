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


def test_misses_say_how_far_off():
    near = {"ok": False, "value": 186.0, "limit": 195.0, "bound": "min"}
    assert requirements.miss_scale(near) == "near miss: 5 % short"
    assert requirements.miss_scale({"ok": False, "value": 300, "limit": 250, "bound": "max"}) == "close: 20 % over"
    assert requirements.miss_scale({"ok": False, "value": 0.30, "limit": [0.05, 0.15], "bound": "range"}).startswith("far off: 100 %")
    assert requirements.miss_scale({"ok": True, "value": 1, "limit": 2, "bound": "max"}) == ""
    assert requirements.miss_scale({"ok": False, "value": [1, 2], "limit": [3, 3], "bound": "max"}) == ""
    probs, _ = pipeline.req_misses([{**near, "id": "f", "detail": "first mode", "unit": "Hz"}])
    assert probs[0].endswith("[near miss: 5 % short]")
    from kerf import explain
    assert "(Near miss: 5 % short.)" in explain.explain_requirement({**near, "id": "f", "check": "natural_freq", "unit": "Hz"})["why"]


def test_infill_lattice_strength_inside_the_walls():
    from kerf import infill
    assert infill.lattice_factor(1.0) == 1.0 and abs(infill.lattice_factor(0.25) - 0.0375) < 1e-9   # Ashby 2006 eq. 3.5
    shape = Box(40, 20, 10)                                          # walls 2 x 0.42 = 0.84 mm shell
    pts = [[0, 0, 0], [0, 0, 4.8]]                                   # centre (5 mm deep) and just under the top skin
    d = infill.depth_below_surface(shape, __import__("numpy").array(pts, float))
    assert abs(d[0] - 5.0) < 0.2 and d[1] < 0.84
    field = {"c": pts, "vol": [1.0, 1.0], "vm": [2.0, 30.0]}         # inside: 2 MPa; skin: 30 MPa
    item = NS(id="p", spec={"infill": 0.25, "walls": 2}, shape=shape)
    r = infill.check(item, [{"field": field, "allow": 20.0}])        # lattice allows 20 x 0.0375 = 0.75 MPa inside
    assert r["use"] > 2.5 and "100 % infill modifier" in r["warning"]
    boxed = NS(id="p", spec={"infill": 0.25, "walls": 2, "modifiers": [{"box": [[-5, -5, -5], [5, 5, 5]], "infill": 1.0}]}, shape=shape)
    assert infill.check(boxed, [{"field": field, "allow": 20.0}])["warning"] == ""
    assert infill.check(NS(id="s", spec={"infill": 1.0}, shape=shape), [{"field": field, "allow": 20.0}]) is None


def test_bumper_pad_lowers_crash_force_only_while_it_does_not_bottom_out(monkeypatch):
    import math
    from kerf import req_dynamic as D
    ku, kl, S = D.bumper_k("TPU", 400, 4)                     # 20 x 20 mm TPU pad, 4 mm thick: S = 400 / 320 = 1.25
    assert abs(S - 1.25) < 1e-9 and abs(kl - 9.2 * 100) < 1e-6 and abs(ku - 9.2 * (1 + 2.2 * 1.25 ** 2) * 100) < 1e-6
    r0 = {"ok": True, "value": 10.0, "limit": 20.0, "max_disp_mm": 0.1, "applied_force_n": [0, 0, 10], "detail": ""}
    monkeypatch.setattr(D, "_solve", lambda *a, **k: (dict(r0), 10.0, 2000.0))   # part: 2000 N/mm
    proj = NS(items={"pad": NS(spec={"material": "TPU"})}, data={})
    pad = {"item": "pad", "area_mm2": 400, "thick_mm": 4}
    bare = D.impact_fea(proj, None, "arm", {}, [], speed_m_s=1.0, mass_kg=0.1)
    soft = D.impact_fea(proj, None, "arm", {}, [], speed_m_s=1.0, mass_kg=0.1, bumper=pad)
    assert abs(bare["impact"]["force_n"] - math.sqrt(2e6 * 0.1)) < 1
    ks = 1 / (1 / 2000 + 1 / ku)
    assert soft["impact"]["bumper"]["credited"] and abs(soft["impact"]["force_n"] - math.sqrt(ks * 1e3 * 0.1)) < 1
    hard = D.impact_fea(proj, None, "arm", {}, [], speed_m_s=3.0, mass_kg=0.6, bumper=pad)   # 2.9 mm squash > 0.8 mm
    hard_bare = D.impact_fea(proj, None, "arm", {}, [], speed_m_s=3.0, mass_kg=0.6)
    assert not hard["impact"]["bumper"]["credited"] and hard["impact"]["force_n"] == hard_bare["impact"]["force_n"]
    assert "no credit" in hard["detail"]
