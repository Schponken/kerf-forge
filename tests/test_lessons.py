"""kerf/lessons.py (Learning Mode phase 3): rule-based classification, grouping across projects, the promotion ladder,
the 'review only at the end' lesson, and the files written. Fake diaries; no git, no AI."""
import json

from kerf import lessons


def prob(p, n, issue, stage="final review", part="hub", redrawn=(), source="review", rnd=1, sev="major", mins=10):
    return {"id": f"{p}-{n}", "source": source, "severity": sev, "part": part, "issue": issue, "fix": "", "stage": stage,
            "review_round": rnd, "active_minutes_est": mins, "parts_redrawn": list(redrawn), "status": "resolved"}


def diary(p, *probs):
    return {"project": p, "problems": list(probs)}


STRESS = "hub_fea fails: von Mises 24 MPa against 17 allowed, the root section would snap"
KEY = "the four sweep servo screws need a ball-end 2.5 mm key; a straight key hits the servo body"
ROUTE = "About 45 wiring routes pass through solid parts instead of holes or channels"
LEAD = "The aileron servo leads are too short: declared at 620 mm, the routed path needs 750 mm"
STOP = "servo travel runs past the stop: the full sweep crashed at 97 deg past the default"


def test_classification_by_kind():
    ids = {lessons._classify(t, t[:140]) for t in (STRESS, KEY, ROUTE, LEAD, STOP)}
    assert ids == {"strength-size-from-loads", "access-tools-and-fasteners", "wiring-routes-through-solid",
                   "wiring-lead-lengths", "motion-stops-and-travel"}
    kinds = {r[0]: r[1] for r in lessons.RULES}
    assert {kinds[i] for i in ids} == {"strength", "access/fasteners", "wiring", "motion/assembly"}
    assert lessons._classify("The colour of the label is dull", "The colour of the label is dull") is None


def test_every_lesson_has_stage_and_catcher():
    for r in lessons.RULES:
        assert r[3] in ("before parts", "rough", "detail", "final review") and r[4] and r[5] and r[2] and r[1] in lessons.KINDS


def test_ladder_note_instruction_gate():
    a = diary("a", prob("a", 1, STRESS), prob("a", 2, KEY, stage="detail"), prob("a", 3, STRESS))
    b = diary("b", prob("b", 1, STRESS), prob("b", 2, LEAD, stage="detail"))
    c = diary("c", prob("c", 1, KEY, stage="detail", redrawn=[]))
    data = lessons.group([a, b, c])
    lv = {x["id"]: x for x in data["lessons"]}
    assert lv["strength-size-from-loads"]["level"] == "proposed gate" and lv["strength-size-from-loads"]["count"] == 3     # 2 projects, final review
    assert lv["wiring-lead-lengths"]["level"] == "note"                                                                  # one project
    assert lv["access-tools-and-fasteners"]["level"] == "instruction"             # 2 projects, but found at detail without a redraw
    assert lv["access-tools-and-fasteners"]["projects"] == ["a", "c"]
    # a redraw makes the same repeat costly
    c2 = diary("c", prob("c", 1, KEY, stage="detail", redrawn=["hub"]))
    d2 = diary("a", prob("a", 2, KEY, stage="detail", redrawn=["spine"]))
    assert {x["id"]: x for x in lessons.group([d2, c2])["lessons"]}["access-tools-and-fasteners"]["level"] == "proposed gate"
    assert data["by_problem"]["a-1"] == "strength-size-from-loads"
    assert [x["level"] for x in data["lessons"]] == sorted((x["level"] for x in data["lessons"]), key=lessons.LEVELS.index)


def test_review_only_at_the_end_lesson():
    many = [prob("a", n, STRESS if n % 2 else ROUTE) for n in range(1, 7)]
    data = lessons.group([diary("a", *many)])
    r = next(x for x in data["lessons"] if x["id"] == "process-review-early")
    assert r["level"] == "note" and r["earliest_stage"] == "rough" and r["kind"] == "process"
    # few findings, or an earlier stage already saw problems: no such lesson
    assert not any(x["id"] == "process-review-early" for x in lessons.group([diary("a", *many[:3])])["lessons"])
    early = [prob("a", 1, STRESS, stage="rough")] + many[1:]
    assert not any(x["id"] == "process-review-early" for x in lessons.group([diary("a", *early)])["lessons"])
    two = lessons.group([diary("a", *many), diary("b", *many)])
    assert next(x for x in two["lessons"] if x["id"] == "process-review-early")["level"] == "proposed gate"


def test_late_by_stages_and_cost():
    data = lessons.group([diary("a", prob("a", 1, STRESS, mins=30), prob("a", 2, STRESS, mins=12))])
    x = data["lessons"][0]
    assert x["late_by_stages"] == 2 and x["cost_min"] == 42            # catchable at rough, found at final review


def test_run_writes_files_and_never_says_enforced(tmp_path):
    (tmp_path / "learning" / "diary").mkdir(parents=True)
    for d in (diary("a", prob("a", 1, STRESS)), diary("b", prob("b", 1, STRESS))):
        (tmp_path / "learning" / "diary" / f"{d['project']}.json").write_text(json.dumps(d))
    (tmp_path / "learning" / "diary" / "a.sessions.json").write_text("[]")      # not a diary
    r = lessons.run(None, tmp_path)
    md = (tmp_path / "learning" / "LESSONS.md").read_text()
    assert "## Proposed gates" in md and "PROPOSAL" in md and "strength" in md
    assert json.loads((tmp_path / "learning" / "lessons.json").read_text())["projects"] == ["a", "b"]
    assert "proposed gate" in r["summary"]
