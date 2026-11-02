"""Studio ownership uses fetched shared claims, never stale feature-branch copies or control files."""
import json
import time

import pytest

from kerf import codex_work, explain, live, studio
from test_live import commit, g, repo  # noqa: F401


def test_shared_claims_reach_guards_activity_checks_and_work(repo, monkeypatch):
    now = time.time()
    empty = g(repo, "rev-parse", "HEAD")
    local = {"item": "Fix other", "session": "old", "heartbeat": now}
    branch = commit(repo, "old ownership", {"claims/released.json": json.dumps(local)})
    shared = {"item": "Fix demo", "session": "codex", "provider": "Codex", "heartbeat": now - 120}
    main = commit(repo, "shared ownership", {"claims/released.json": None, "claims/active.json": json.dumps(shared)})
    g(repo, "update-ref", "refs/remotes/origin/main", main)
    g(repo, "checkout", "-q", "-b", "feature", branch)
    assert not (repo / "claims/active.json").exists()
    monkeypatch.setattr(studio, "ROOT", repo)
    monkeypatch.setattr(studio, "PROJECTS", repo / "projects")
    monkeypatch.setattr(studio, "JOBS", {})
    monkeypatch.setattr(studio, "SESSIONS", {"at": 0, "list": []})
    monkeypatch.setattr(studio, "_live_thread", lambda: None)
    monkeypatch.setattr(studio, "_work_picture", lambda name: None)
    monkeypatch.setattr(studio, "LIVE", {"work": None, "work_key": None, "last_fetch": now, "fetch_error": "offline"})
    monkeypatch.setattr(codex_work, "snapshot", lambda root: {"sessions": [], "source": {"name": "Codex", "state": "unavailable"}})

    assert explain.claims(repo) == [shared]
    assert studio._worked_on("demo") and not studio._worked_on("other")
    with pytest.raises(studio.Claimed, match="Another session"):
        studio.guard_claimed("demo", False)
    studio.guard_claimed("demo", True)
    detail = studio.explained("demo", {"problems": []}, {})["work"]
    assert detail["state"] == "claimed" and "Codex" in detail["text"] and "claimed" in detail["text"]
    assert "working" not in detail["text"]
    assert [s["project"] for s in studio.sessions(max_age=0)] == ["demo"]
    work = studio.work()
    assert [c["session"] for c in work["cards"]] == ["codex"]
    source = next(s for s in work["sources"] if s["name"] == "Shared claims")
    assert source["state"] == "partial" and "Last fetched" in source["detail"]

    # A valid empty shared tree means released, even while local feature files still claim the project.
    g(repo, "update-ref", "refs/remotes/origin/main", empty)
    assert explain.claims(repo) == []
    assert not studio._worked_on("other") and not studio._worked_on("demo")
    assert studio.work()["cards"] == []
    assert (repo / "claims/released.json").exists() and g(repo, "status", "--porcelain") == ""


def test_claim_readers_skip_controls_and_malformed_records(repo):
    now = time.time()
    valid = {"item": "Fix demo", "session": "session", "heartbeat": now}
    records = {
        "valid": valid, "budget": valid, "batch-verify": valid,
        "array": [], "scalar": 2, "empty": {},
        "bad-item": {**valid, "item": []}, "empty-item": {**valid, "item": "  "},
        "bad-session": {**valid, "session": None}, "bad-heartbeat": {**valid, "heartbeat": "later"},
        "nan": {**valid, "heartbeat": float("nan")}, "infinity": {**valid, "heartbeat": float("inf")},
        "negative": {**valid, "heartbeat": -1}, "boolean": {**valid, "heartbeat": True},
        "huge": {**valid, "heartbeat": 10 ** 400}, "bad-start": {**valid, "since": float("inf")},
    }
    files = {f"claims/{name}.json": json.dumps(c) for name, c in records.items()}
    files["claims/broken.json"] = "{bad"
    commit(repo, "claim and non-task records", files)
    assert explain.claims(repo) == [valid]
    work = live.work_data(repo, "HEAD", now=now)
    assert [c["claim_id"] for c in work["cards"]] == ["valid"] and work["sessions"] == 1


def test_new_commit_does_not_refresh_an_old_heartbeat(repo):
    now = time.time()
    stale = {"item": "Fix demo", "session": "old", "heartbeat": now - 100 * 60}
    gone = {"item": "Fix other", "session": "gone", "heartbeat": now - 200 * 60}
    commit(repo, "recent commit with unchanged old heartbeats", {
        "claims/stale.json": json.dumps(stale), "claims/gone.json": json.dumps(gone)})
    work = live.work_data(repo, "HEAD", now=now)
    assert work["sessions"] == 0 and len(work["cards"]) == 1
    card = work["cards"][0]
    assert card["stale"] and card["heartbeat_at"] == card["updated_at"] == stale["heartbeat"]
    assert explain.work_status("demo", [], explain.claims(repo), now)["state"] == "idle"


def test_non_git_copy_keeps_valid_local_claims(tmp_path):
    (tmp_path / "claims").mkdir()
    claim = {"item": "Fix demo", "session": "local", "heartbeat": time.time()}
    (tmp_path / "claims/local.json").write_text(json.dumps(claim))
    (tmp_path / "claims/budget.json").write_text(json.dumps(claim))
    assert explain.claims(tmp_path) == [claim]


def test_normal_activity_poll_refreshes_shared_ownership_without_opening_work(repo, monkeypatch):
    now = time.time()
    old = g(repo, "rev-parse", "HEAD")
    claim = {"item": "Fix demo", "session": "remote", "heartbeat": now}
    latest = commit(repo, "new remote owner", {"claims/active.json": json.dumps(claim)})
    g(repo, "update-ref", "refs/remotes/origin/main", old)
    g(repo, "checkout", "-q", "-b", "feature", old)
    monkeypatch.setattr(studio, "ROOT", repo)
    monkeypatch.setattr(studio, "PROJECTS", repo / "projects")
    monkeypatch.setattr(studio, "SESSIONS", {"at": 0, "list": []})
    monkeypatch.setattr(studio, "LIVE", {"follow": {}, "last_fetch": 0, "fetch_error": None, "work_until": 0, "work": None})
    starts, fetches = [], []
    monkeypatch.setattr(studio, "_live_thread", lambda: starts.append(True))
    def fetch(root):
        fetches.append(root)
        g(root, "update-ref", "refs/remotes/origin/main", latest)
    monkeypatch.setattr(live, "fetch", fetch)

    assert studio.sessions() == []  # /api/jobs polls Activity on every Studio page.
    assert starts and studio.LIVE["work_until"] > now
    studio.live_tick(now)
    assert fetches == [repo] and studio._worked_on("demo")
    assert [s["project"] for s in studio.sessions()] == ["demo"]  # cached empty list was invalidated
    studio.live_tick(now + 1)
    assert fetches == [repo]  # the same one-minute fetch limit still applies
