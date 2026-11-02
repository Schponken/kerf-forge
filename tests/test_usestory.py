"""Use story (kerf/usestory.py): who / where / how often / what goes wrong becomes requirement checks. Each check is
tested on a tiny hand-made assembly with a known answer."""
import math
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from build123d import Box, Pos

from kerf import assembly as A, usestory as U
from kerf.requirements import REGISTRY


@pytest.fixture(autouse=True)
def _no_solve(monkeypatch):
    monkeypatch.setattr(A, "solve", lambda asm, values=None: None)


def proj(items, data=None, name="new_thing"):
    its = {k: NS(id=k, role=r, spec=s, shape=sh) for k, (r, s, sh) in items.items()}
    return NS(items=its, data=data or {}, params={}, dir=Path("/x") / name,
              printed={k: v for k, v in its.items() if v.role == "printed"})


def test_story_is_required_for_new_projects_and_checked_for_fields():
    assert "use_story: missing" in U.problems(proj({}))[0]
    assert U.problems(proj({}, name="pan_tilt")) == []                       # made before use stories
    bad = {"use_story": {"who": "me", "where": ["desk"], "goes_wrong": [{"hazard": "lava"}, {"hazard": "drop"},
                                                                        {"hazard": "crash", "survive": False}]}}
    p = " | ".join(U.problems(proj({}, bad)))
    assert "'how_often' missing" in p and "unknown hazard" in p and "needs `height_m`" in p and "consequence" in p


def test_hazards_become_requirements():
    s = {"who": "a pilot", "where": ["outdoor"], "how_often": "weekly", "goes_wrong": [
        {"hazard": "heat", "max_c": 45}, {"hazard": "rain"}, {"hazard": "gloves", "handles": [{"item": "battery"}]},
        {"hazard": "drop", "height_m": 1}, {"hazard": "crash", "speed_m_s": 15, "survive": False, "consequence": "arm breaks"},
        {"hazard": "other", "what": "lifts 150 g", "covered_by": ["torque"]}]}
    reqs = U.requirements(proj({}, {"use_story": s}))
    assert [r["check"] for r in reqs] == ["heat_limit", "rain_cover", "access_opening", "impact_case", "story_covered"]
    assert all(r["check"] in REGISTRY for r in reqs)
    two = U.requirements(proj({}, {"use_story": {"goes_wrong": [{"hazard": "other", "what": "a", "covered_by": []},
                                                                {"hazard": "other", "what": "b", "covered_by": []}]}}))
    assert [r["id"] for r in two] == ["story_other", "story_other_2"]
    assert U.summary(proj({}, {"use_story": s}))["accepted_failures"] == [{"hazard": "crash", "consequence": "arm breaks"}]


def test_heat_limit_uses_datasheet_hdt_and_the_loaded_value_for_strength_parts():
    b = Box(10, 10, 10)
    p = proj({"lid": ("printed", {"material": "PLA"}, b), "arm": ("printed", {"material": "PETG"}, b)},
             {"requirements": [{"check": "fea_static", "part": "arm"}]})
    r = REGISTRY["heat_limit"](p, None, max_c=50)
    assert r["ok"] and r["value"] == 7          # PLA 57 °C at 0.45 MPa; PETG (loaded) 65 °C at 1.8 MPa
    r = REGISTRY["heat_limit"](p, None, max_c=60)
    assert not r["ok"] and "lid: PLA softens at 57" in r["detail"] and "arm" not in r["detail"]
    r = REGISTRY["heat_limit"](proj({"boot": ("printed", {"material": "TPU"}, b)}), None, max_c=30)
    assert not r["ok"] and "no heat deflection value" in r["detail"]       # unknown never passes


def test_rain_cover_counts_the_roofed_share_of_each_electronic_top():
    board = Box(40, 20, 5)                                    # arduino-nano-sized, top at z = 2.5
    half_roof = Pos(10, 0, 20) * Box(20, 30, 2)               # covers x in [0, 20]: the right half of the board
    p = proj({"nano": ("purchased", {"catalog": "boards.arduino_nano"}, board),
              "roof": ("printed", {}, half_roof)})
    r = REGISTRY["rain_cover"](p, None)
    assert not r["ok"] and r["value"] == pytest.approx(0.6, abs=0.01)      # 3 of 5 grid columns lie under x >= 0
    p.items["roof"].shape = Pos(0, 0, 20) * Box(60, 40, 2)
    assert REGISTRY["rain_cover"](p, None)["ok"]
    p.items["roof"].shape = Pos(0, 0, -20) * Box(60, 40, 2)                # a floor is no roof
    assert REGISTRY["rain_cover"](p, None)["value"] == 0.0


def test_access_opening_is_38_mm_gloved_and_32_bare():
    batt = Box(70, 35, 30)                                     # top at z = 15
    # two posts 35 mm apart (inner faces at x = +-17.5): a 32 mm bare finger opening fits, a 38 mm gloved one does not
    posts = Pos(-22.5, 0, 40) * Box(10, 10, 40) + Pos(22.5, 0, 40) * Box(10, 10, 40)
    p = proj({"battery": ("purchased", {}, batt), "posts": ("printed", {}, posts)})
    bare = REGISTRY["access_opening"](p, None, item="battery", from_dir=[0, 0, 1], gloved=False)
    gloved = REGISTRY["access_opening"](p, None, item="battery", from_dir=[0, 0, 1], gloved=True)
    assert bare["ok"] and not gloved["ok"] and "blocked by posts" in gloved["detail"]
    assert REGISTRY["access_opening"](p, None, item="battery", gloved=True, ignore=["posts"])["ok"]


def test_impact_force_is_the_work_energy_balance_and_a_strength_case_must_carry_it():
    h = {"hazard": "drop", "height_m": 1.0, "stop_mm": 2.0, "mass_kg": 0.5}
    r = U.impact(h, 0.5)
    assert r["v_m_s"] == pytest.approx(math.sqrt(2 * 9.80665), abs=0.01)
    assert r["force_n"] == pytest.approx(0.5 * 9.80665 * 1.002 / 0.002, rel=1e-3)      # F s = m g (h + s): 2457 N
    st = {"who": "a", "where": ["desk"], "how_often": "daily", "goes_wrong": [h]}
    p = proj({}, {"use_story": st, "requirements": []})
    assert not REGISTRY["impact_case"](p, None, hazard="drop", index=0)["ok"]           # nothing carries it
    p.data["requirements"] = [{"id": "foot_drop", "check": "fea_static", "case": "drop", "share": 0.5,
                               "loads": [{"force_n": [0, 0, "-story_drop_n * 0.5"]}]}]
    ok = REGISTRY["impact_case"](p, None, hazard="drop", index=0)
    assert ok["ok"] and "foot_drop" in ok["detail"]
    p.data["requirements"][0]["share"] = 1.0                                            # claims all, carries half
    assert not REGISTRY["impact_case"](p, None, hazard="drop", index=0)["ok"]


def test_story_numbers_are_usable_in_requirement_expressions_during_the_run(monkeypatch):
    from kerf import requirements as R
    seen = {}
    monkeypatch.setitem(R.REGISTRY, "probe", lambda proj, asm, **k: seen.update(proj.params) or {"ok": True})
    st = {"who": "a", "where": ["desk"], "how_often": "daily",
          "goes_wrong": [{"hazard": "drop", "height_m": 0.75, "mass_kg": 1.0}]}
    p = proj({}, {"use_story": st, "requirements": [{"check": "probe"}]})
    rows = R.run_all(p, None)
    assert seen["story_drop_n"] == pytest.approx(9.80665 * 0.752 / 0.002, rel=1e-3) and "story_drop_n" not in p.params
    assert [r["check"] for r in rows] == ["probe", "impact_case"]


def test_accepted_failures_go_into_assembly_md():
    from kerf.ship import story_notes
    L = story_notes({"who": "me", "where": ["desk"], "how_often": "daily",
                     "accepted_failures": [{"hazard": "drop", "consequence": "the forearm cracks; reprint it"}]})
    assert "## When something goes wrong" in L and any("forearm cracks" in x for x in L)
    assert story_notes(None) == []
