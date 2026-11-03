"""Actual Studio work serialization into cards; no process, timer, git fetch or agent connection."""
from types import SimpleNamespace

import pytest

from kerf import codex_work, studio, work

NOW = 1_800_000_000


def job(jid, **changes):
    fields = dict(id=jid, kind="edit", project="fixture", label=f"Task {jid}", agent="claude", state="running",
                  started=NOW-100, ended=None, mode=None, events=[], usage=None, resumed_by=None, session="test-session")
    fields.update(changes)
    return SimpleNamespace(**fields)


@pytest.fixture
def snapshot(monkeypatch):
    monkeypatch.setattr(studio, "JOBS", {})
    monkeypatch.setattr(studio, "_live_thread", lambda: None)
    monkeypatch.setattr(studio, "_git", lambda *a: "fixture-revision")
    monkeypatch.setattr(studio, "_times", lambda: {})
    monkeypatch.setattr(studio, "settings", lambda: {"autoresume": True})
    monkeypatch.setattr(studio, "budget_stop", lambda: "")
    monkeypatch.setattr(studio.time, "time", lambda: NOW)
    monkeypatch.setattr(studio, "LIVE", {**studio.LIVE, "work": {}, "work_key": ("fixture-revision", NOW//60),
                                      "last_fetch": NOW, "fetch_error": None})
    monkeypatch.setattr(codex_work, "snapshot", lambda root: {"sessions": [], "source": {"name": "Codex", "state": "ok"}})
    def get(*jobs):
        studio.JOBS = {j.id: j for j in jobs}
        return studio.work()
    return get


@pytest.mark.parametrize("kind", ["design", "edit", "fix", "quote"])
@pytest.mark.parametrize("agent,label", [("codex", "Codex"), ("claude", "Claude")])
def test_agent_provider_survives_studio_serialization(snapshot, kind, agent, label):
    item, = snapshot(job("j", kind=kind, agent=agent))["items"]
    assert item["provider"] == label and item["state"] == "running"
    assert item["eta"] is None and item["progress"] is None


@pytest.mark.parametrize("agent", [None, "unknown", ["codex"]])
def test_invalid_agent_metadata_keeps_historical_claude_fallback(snapshot, agent):
    assert snapshot(job("j", agent=agent))["items"][0]["provider"] == "Claude"


def test_missing_agent_metadata_and_non_agent_jobs(snapshot):
    old = job("old"); del old.agent
    items = {i["job_id"]: i for i in snapshot(old, job("build", kind="build", agent="codex"))["items"]}
    assert items["old"]["provider"] == "Claude" and items["build"]["provider"] == "Studio"


def paused(jid="paused", **changes):
    fields = dict(state="paused", ended=NOW-5, usage={"until": NOW+600, "text": "raw private usage log"},
                  events=[{"k": "note", "text": "Designing the next part", "t": NOW-20},
                          {"k": "usage", "until": NOW+600, "t": NOW-5}])
    fields.update(changes)
    return job(jid, **fields)


def test_pause_replaces_obsolete_activity_without_inventing_work_or_finish_time(snapshot):
    result = snapshot(paused())
    item, = result["items"]
    assert item["state"] == "paused" and item["status_label"] == "Paused · usage limit"
    assert item["activity"] == "Usage limit reached; this run is paused."
    assert item["pause"] == {"reset_at": NOW+600} and item["updated_at"] == NOW-5
    assert "Automatic retry is enabled" in item["attention"] and "retry timing is unavailable" in item["attention"]
    assert item["eta"] is None and item["action"] is None
    assert "Designing the next part" not in repr(item) and "raw private usage log" not in repr(item)
    assert result["counts"]["paused"] == result["counts"]["attention"] == 1
    assert result["counts"]["running"] == result["counts"]["waiting"] == result["counts"]["done"] == 0


@pytest.mark.parametrize("enabled,blocked,session,expected", [
    (False, "", "s", "Automatic retry is off"),
    (True, "budget reason", "s", "budget switch currently blocks"),
    (False, "budget reason", "s", "budget switch currently blocks"),
    (True, "", None, "no resumable session is reported"),
])
def test_pause_policy_is_read_only_and_does_not_promise_a_queued_retry(snapshot, monkeypatch, enabled, blocked, session, expected):
    monkeypatch.setattr(studio, "settings", lambda: {"autoresume": enabled})
    monkeypatch.setattr(studio, "budget_stop", lambda: blocked)
    item, = snapshot(paused(session=session))["items"]
    assert expected in item["attention"] and item["state"] == "paused" and item["eta"] is None


@pytest.mark.parametrize("reset", [None, 0, -1, float("nan"), float("inf")])
def test_unknown_or_invalid_reset_time_stays_unknown(snapshot, reset):
    item, = snapshot(paused(usage={"until": reset}))["items"]
    assert item["pause"]["reset_at"] is None and item["eta"] is None


def test_generic_pause_does_not_invent_a_usage_reason_or_retry_policy():
    item, = work.overview({}, jobs=[{"id": "j", "state": "paused"}])["items"]
    assert item["status_label"] == "Paused" and item["activity"] == "This run is paused."
    assert "retry status is not reported" in item["attention"]


@pytest.mark.parametrize("state,label", [("running", "Working"), ("failed", "Failed"), ("done", "Finished")])
def test_continuation_references_observed_successor_without_inventing_success(snapshot, state, label):
    data = snapshot(paused(resumed_by="next"), job("next", agent="codex", state=state))
    items = {i["job_id"]: i for i in data["items"]}
    old = items["paused"]
    assert old["state"] == "continued" and old["attention"] is None and old["pause"] is None
    assert old["continuation"] == {"job_id": "next", "observed": True, "provider": "Codex", "status_label": label}
    assert old["activity"] == "Codex continued this task in another job."
    assert data["counts"]["paused"] == 0 and data["counts"]["done"] == int(state == "done")


def test_missing_successor_and_self_reference_do_not_invent_observation(snapshot):
    items = {i["job_id"]: i for i in snapshot(paused("old", resumed_by="gone"), paused("self", resumed_by="self"))["items"]}
    assert items["old"]["state"] == "continued" and not items["old"]["continuation"]["observed"]
    assert "current state is not reported" in items["old"]["activity"]
    assert items["self"]["state"] == "paused" and "continuation" not in items["self"]


def test_explicit_stop_survives_retained_usage_and_continuation_metadata(snapshot):
    item, = snapshot(paused(state="stopped", resumed_by="next"))["items"]
    assert item["state"] == "stopped" and "continuation" not in item and "pause" not in item


def test_provider_specific_setup_hint(snapshot):
    item, = snapshot(job("j", agent="codex", state="failed", events=[{"k": "hint", "code": "auth"}]))["items"]
    assert item["attention"] == "Codex needs you to sign in again."


def test_chained_continuations_are_independent_of_input_order(snapshot):
    rows = [paused("first", resumed_by="second"), paused("second", resumed_by="third"), job("third", agent="codex")]
    forward = snapshot(*rows)["items"]
    assert snapshot(*reversed(rows))["items"] == forward
    assert next(i for i in forward if i["job_id"] == "first")["continuation"]["status_label"] == "Continued in another job"
