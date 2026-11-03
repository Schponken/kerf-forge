"""kerf/diary.py (Learning Mode phase 2): stage inference, cost, finding follow-through and the session-token sum,
on a small throwaway git repo with fake review.json versions."""
import json
import os
import subprocess

import pytest

from kerf import diary

STUB = "def build(ctx):\n    return ctx.finish(None)\n"
REAL = "def build(ctx):\n" + "".join(f"    x{i} = {i} * 2  # detail line {i} with a long comment to make the file big\n" for i in range(40)) + "    return ctx.finish(None)\n"
YAML = "parts:\n  hub_r: {file: parts/hub.py}\n  hub_l: {file: parts/hub.py}\n  spine: {file: parts/spine.py}\n"


def git(repo, *a, when=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)


def commit(repo, msg, when, files):
    for rel, text in files.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", msg, when=when)


def review(verdict, *finds):
    return json.dumps({"verdict": verdict, "date": "2026-11-02", "findings": [
        {"severity": s, "part": p, "issue": i, "fix": "f"} for s, p, i in finds]})


STRESS = "hub_fea fails: von Mises stress 24 MPa against 17 allowed, the root section is too thin and would snap"
KEY = "the four sweep servo screws need a ball-end key because a straight key hits the servo body"


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    P = "projects/demo/"
    commit(tmp_path, "demo: contract", "2026-11-01T10:00:00+00:00", {P + "project.yaml": YAML, P + "DESIGN.md": "plan"})
    commit(tmp_path, "demo: stub parts", "2026-11-01T11:00:00+00:00", {P + "parts/hub.py": STUB, P + "parts/spine.py": STUB})
    commit(tmp_path, "demo: parts done, quick check PASS", "2026-11-01T14:00:00+00:00", {P + "parts/hub.py": REAL, P + "parts/spine.py": REAL})
    commit(tmp_path, "demo: review round 1", "2026-11-01T15:00:00+00:00",
           {P + "review.json": review("FAIL", ("blocker", "hub_r", STRESS), ("minor", "spine", KEY))})
    commit(tmp_path, "demo: thicken hub root", "2026-11-01T15:40:00+00:00", {P + "parts/hub.py": REAL + "# thicker\n"})
    commit(tmp_path, "demo: build FAIL on clearance", "2026-11-01T16:00:00+00:00", {P + "notes.txt": "x"})
    commit(tmp_path, "demo: build PASS again", "2026-11-01T16:20:00+00:00", {P + "parts/spine.py": REAL + "# clear\n"})
    commit(tmp_path, "demo: review round 2", "2026-11-01T17:00:00+00:00",
           {P + "review.json": review("PASS", ("minor", "spine", KEY + " (carried over, minor)"))})
    return tmp_path


def test_review_rounds_and_stage(repo):
    d = diary.build(repo, "demo")
    assert [r["verdict"] for r in d["reviews"]] == ["FAIL", "PASS"]
    assert d["problems"][0]["stage"] == "final review"        # real parts at the review commit
    assert all(p["stage"] != "before parts" for p in d["problems"])


def test_stage_before_parts_and_rough(repo):
    first, stub, real = [c["hash"] for c in diary.commits(repo, "demo")[:3]]
    assert diary.stage_at(repo, "demo", first)[0] == "before parts"
    assert diary.stage_at(repo, "demo", stub)[0] == "rough"
    assert diary.stage_at(repo, "demo", real)[0] == "final review"
    assert diary.stage_at(repo, "demo", real, "check")[0] == "detail"


def test_finding_followed_and_costed(repo):
    d = diary.build(repo, "demo")
    stress = next(p for p in d["problems"] if p["source"] == "review" and "hub_fea" in p["issue"])
    assert stress["status"] == "resolved" and stress["target_redrawn"]
    assert stress["parts_redrawn"] == ["hub"]                  # the commit after the finding that redrew hub.py
    assert stress["wall_minutes"] == 40                       # 15:00 -> 15:40
    assert stress["resolved_how"].startswith("first commit after the finding that redrew its part")
    key = next(p for p in d["problems"] if p["part"] == "spine" and p["source"] == "review")
    assert key["rounds_seen"] and len(key["rounds_seen"]) == 2   # same finding re-worded in round 2: one problem, not two
    assert key["status"] == "accepted at PASS"
    assert d["cost_is_estimate"] is True


def test_check_fail_is_a_problem_until_next_pass(repo):
    d = diary.build(repo, "demo")
    chk = [p for p in d["problems"] if p["source"] == "check"]
    assert len(chk) == 1 and chk[0]["stage"] == "detail" and chk[0]["status"] == "resolved"
    assert chk[0]["wall_minutes"] == 20 and chk[0]["parts_redrawn"] == ["spine"]


def test_write_outputs(repo):
    f = diary.write(repo, "demo")
    assert f == repo / "learning/diary/demo.json" and (repo / "learning/diary/demo.md").read_text().startswith("# Diary: demo")
    assert diary.all_projects(repo) == ["demo"]


def _log(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_session_usage_counts_each_message_once(tmp_path):
    u = lambda i, o, cw, cr: {"input_tokens": i, "output_tokens": o, "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr}
    rows = [{"sessionId": "s1", "timestamp": "2026-11-02T01:00:00Z", "type": "user", "message": {"role": "user", "content": "hi"}},
            # one API message written as three content blocks: the same usage repeated
            *[{"sessionId": "s1", "timestamp": "2026-11-02T01:00:05Z", "message": {"id": "m1", "model": "x", "usage": u(2, 700, 100, 50)}}] * 3,
            {"sessionId": "s1", "timestamp": "2026-11-02T01:01:00Z", "message": {"id": "m2", "model": "x", "usage": u(3, 10, 0, 200)}}]
    f = tmp_path / "s1.jsonl"
    _log(f, rows)
    s = diary.session_usage(f)
    assert (s["input_tokens"], s["output_tokens"], s["cache_creation_tokens"], s["cache_read_tokens"]) == (5, 710, 100, 250)
    assert s["messages"] == 2 and s["session_id"] == "s1" and s["first"] < s["last"]


def test_log_session_is_idempotent_and_shows_in_diary(repo, tmp_path):
    f = tmp_path / "s.jsonl"
    _log(f, [{"sessionId": "s9", "message": {"id": "a", "usage": {"input_tokens": 1, "output_tokens": 2}}}])
    diary.log_session(repo, "demo", f, "first")
    _log(f, [{"sessionId": "s9", "message": {"id": "a", "usage": {"input_tokens": 1, "output_tokens": 2}}},
             {"sessionId": "s9", "message": {"id": "b", "usage": {"input_tokens": 4, "output_tokens": 8}}}])
    diary.log_session(repo, "demo", f, "later")
    d = diary.build(repo, "demo")
    assert len(d["sessions"]) == 1 and d["totals"]["tokens"]["input_tokens"] == 5 and d["totals"]["tokens"]["output_tokens"] == 10
