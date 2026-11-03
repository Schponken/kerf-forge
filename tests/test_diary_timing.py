"""Historical rework timing is unknown when author dates cannot support an estimate."""
import json
from datetime import datetime

import pytest

from kerf import diary, lessons
from test_diary import commit, git
from test_lessons import STRESS, diary as lesson_diary, prob


def history(repo, times, messages):
    git(repo, "init", "-q", "--template=")
    for index, (when, message) in enumerate(zip(times, messages)):
        files = {"projects/demo/parts/hub.py": f"# synthetic part revision {index}\n"}
        if index == 0:
            files["projects/demo/project.yaml"] = "parts:\n  hub: {file: parts/hub.py}\n"
        commit(repo, message, when, files)
    return diary.build(repo, "demo")


@pytest.mark.parametrize("times", [
    ["2026-11-01T12:00:00+00:00", "2026-11-01T10:00:00+00:00", "2026-11-01T13:00:00+00:00"],
    ["2026-11-01T12:00:00+00:00", "2026-11-01T11:00:00+00:00", "2026-11-01T10:00:00+00:00"],
])
def test_backward_span_keeps_resolution_and_redraw_evidence_but_no_timing(tmp_path, times):
    data = history(tmp_path, times, ["check FAIL on fixture", "adjust fixture", "check PASS"])
    problem, = data["problems"]
    assert problem["status"] == "resolved" and problem["resolved_how"] == "next check PASS"
    assert problem["wall_minutes"] is problem["active_minutes_est"] is None
    assert "move backward" in problem["timing_note"]
    assert problem["parts_redrawn"] == ["hub"] and data["totals"]["parts_redrawn"] == ["hub"]
    assert [datetime.fromisoformat(c["time"]) for c in data["commits"]] == list(map(datetime.fromisoformat, times))
    assert problem["found_commit"] == data["commits"][0]["hash"]
    assert problem["resolved_commit"] == data["commits"][-1]["hash"]
    assert data["totals"]["active_minutes_est"] is None
    md = diary.render_md(data)
    assert "Estimated active fix time unknown" in md and "| unknown |" in md
    assert problem["timing_note"] in md and "None min" not in md and "0 min" not in md
    occurrence, = lessons.from_diary(data)
    assert occurrence["cost_min"] is None and occurrence["redrawn"] == ["hub"]
    assert lessons.group([data])["lessons"][0]["cost_min"] is None
    assert not (tmp_path / "learning").exists()  # Audit/build did not write a diary.


@pytest.mark.parametrize("times,wall,active", [
    (["2026-11-01T10:00:00+00:00", "2026-11-01T12:00:00+00:00", "2026-11-01T12:30:00+00:00"], 150, 120),
    (["2026-11-01T10:00:00+00:00", "2026-11-01T10:00:00+00:00", "2026-11-01T10:00:00+00:00"], 0, 0),
    (["2026-11-01T10:00:00+02:00", "2026-11-01T09:00:00+00:00", "2026-11-01T09:30:00+00:00"], 90, 90),
])
def test_valid_intervals_preserve_gap_cap_true_zero_and_timezone_order(tmp_path, times, wall, active):
    data = history(tmp_path, times, ["check FAIL on fixture", "adjust fixture", "check PASS"])
    problem, = data["problems"]
    assert problem["wall_minutes"] == wall and problem["active_minutes_est"] == active
    assert problem["timing_note"] is None and data["totals"]["active_minutes_est"] == active
    assert f"Estimated active fix time {active} min" in diary.render_md(data)
    assert lessons.group([data])["lessons"][0]["cost_min"] == active


@pytest.mark.parametrize("times,expected", [
    (["2026-11-01T10:00:00+00:00"], None),
    (["2026-11-01T10:00:00+00:00", "2026-11-01T09:00:00+00:00"], None),
    (["2026-11-01T10:00:00+00:00", "2026-11-01T10:00:00+00:00"], 0),
    (["2026-11-01T10:00:00+00:00", "2026-11-01T12:00:00+00:00"], 90),
])
def test_same_commit_fix_uses_prior_anchor_without_inventing_one(tmp_path, times, expected):
    data = history(tmp_path, times, ["initial fixture"] * (len(times)-1) + ["fixture was too short"])
    problem, = data["problems"]
    assert problem["source"] == "commit" and problem["status"] == "resolved"
    assert problem["active_minutes_est"] == expected and problem["parts_redrawn"] == ["hub"]
    if expected is None:
        assert problem["wall_minutes"] is None and problem["timing_note"]
    else:
        assert problem["wall_minutes"] == (120 if expected else 0) and problem["timing_note"] is None


@pytest.mark.parametrize("when", [None, "bad timestamp", "2026-11-01T10:00:00"])
def test_missing_invalid_or_timezone_free_anchor_is_unknown_without_losing_redraw(when):
    cms = [{"time": "2026-11-01T09:00:00+00:00", "files": []},
           {"time": when, "files": ["projects/demo/parts/hub.py"]}]
    cost = diary._cost(cms, 0, 1, "hub", "demo", {})
    assert cost["wall_minutes"] is cost["active_minutes_est"] is None
    assert "missing or invalid" in cost["timing_note"]
    assert cost["parts_redrawn"] == ["hub"] and cost["target_redrawn"]


def test_unresolved_problem_and_empty_history_totals_remain_distinct(tmp_path):
    data = history(tmp_path, ["2026-11-01T10:00:00+00:00"], ["check FAIL on fixture"])
    problem, = data["problems"]
    assert problem["status"] == "open" and problem["active_minutes_est"] is None
    assert "No resolving commit" in problem["timing_note"]
    assert data["totals"]["active_minutes_est"] is None
    assert diary.totals({"problems": [], "sessions": []})["active_minutes_est"] == 0


@pytest.mark.parametrize("unknown", [None, -30, float("inf"), float("nan")])
def test_diary_and_lesson_totals_preserve_unknown_legacy_costs(unknown):
    problems = [prob("demo", 1, STRESS, mins=30, redrawn=["hub"]), prob("demo", 2, STRESS, mins=unknown)]
    data = {**lesson_diary("demo", *problems), "sessions": [{"input_tokens": 12, "output_tokens": 8}]}
    total = diary.totals(data)
    assert total["active_minutes_est"] is None and total["problems"] == 2 and total["parts_redrawn"] == ["hub"]
    assert total["tokens"]["input_tokens"] == 12 and total["tokens"]["output_tokens"] == 8
    result, = lessons.group([data])["lessons"]
    assert result["cost_min"] is None and result["count"] == 2 and result["level"] == "note"
    assert [x["cost_min"] for x in result["evidence"]] == [30, None]
    assert json.loads(json.dumps(result, allow_nan=False))["cost_min"] is None
    md = diary.render_md({**data, "totals": total, "reviews": []})
    assert "Estimated active fix time unknown" in md and "| unknown |" in md and "| 30 |" in md


def test_first_review_lesson_does_not_hide_unknown_timing_or_change_promotion():
    problems = [prob("demo", n, STRESS, mins=None if n == 1 else 10) for n in range(1, 7)]
    result = lessons.group([lesson_diary("demo", *problems)])
    first = next(row for row in result["lessons"] if row["id"] == "process-review-early")
    assert first["cost_min"] is None and first["evidence"][0]["cost_min"] is None
    assert first["count"] == 1 and first["level"] == "note"
    assert first["earliest_stage"] == "rough" and "6 problems" in first["evidence"][0]["issue"]
