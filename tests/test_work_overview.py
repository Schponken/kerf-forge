"""Work status comes from evidence: ownership is not activity, and step counts are not time estimates."""
from kerf import work


def test_plan_steps_only_counts_explicit_leaf_checkboxes():
    plan = """# Plan
- [ ] Make an arm: include a motor, battery and frame
  - [x] Find parts
  - [ ] Build it
    - [x] Base
    - [ ] Arm
- [ ] Another task
"""
    assert work.plan_steps(plan, "Make an arm: include a motor, battery and frame") == [
        {"title": "Find parts", "status": "done"}, {"title": "Base", "status": "done"},
        {"title": "Arm", "status": "pending"}]
    assert work.plan_steps(plan, "Another task") == []
    assert work.plan_steps(plan, "Unknown work") == []


def test_claim_is_ownership_not_a_live_session_or_time_estimate():
    data = {"cards": [{"claim_id": "arm", "item": "Arm work", "full": "Arm work: strengthen the base",
                       "session": "s1", "provider": "codex", "project": "robot_arm", "updated_at": 950,
                       "started_at": 900, "steps": [{"title": "Design", "status": "done"},
                                                      {"title": "Check", "status": "pending"}]}],
            "plan_done": 1, "plan_total": 4, "feed": []}
    before = repr(data)
    result = work.overview(data, now=1000)
    item, = result["items"]
    assert repr(data) == before  # API callers may cache the raw git result.
    assert item["provider"] == "Codex" and item["state"] == "claimed"
    assert item["source_label"] == "Git claim" and "live activity is not available" in item["activity"]
    assert item["progress"] == {"done": 1, "total": 2, "label": "task steps"}
    assert item["remaining"] == ["Check"] and item["eta"] is None
    assert item["projects"] == [{"name": "robot_arm", "title": "robot arm"}]
    assert result["counts"]["running"] == 0 and result["counts"]["claimed"] == 1


def test_explicit_thread_link_deduplicates_without_guessing_from_project():
    claim = {"claim_id": "work", "session": "claim-session", "thread_id": "thread-1", "item": "Work page",
             "full": "Make work easy to follow", "project": "servo_link", "provider": "codex", "updated_at": 999}
    sessions = [{"id": "thread-1", "provider": "codex", "title": "Improve Work", "state": "running",
                 "activity": "Adding the session cards", "updated_at": 999},
                {"id": "thread-2", "provider": "codex", "title": "Separate task", "state": "running",
                 "project": "servo_link", "updated_at": 998}]
    result = work.overview({"cards": [claim]}, sessions=sessions, now=1000)
    assert len(result["items"]) == 2
    merged = next(i for i in result["items"] if i["id"] == "session:thread-1")
    assert merged["state"] == "running" and merged["description"] == claim["full"]
    assert merged["source_label"] == "Local session + Git claim"
    assert merged["projects"][0]["name"] == "servo_link"


def test_history_only_session_keeps_claim_without_inventing_running_state():
    result = work.overview({"cards": [{"thread_id": "t1", "item": "Work overview", "updated_at": 999,
                                      "activity": "Adding the cards"}]},
                           sessions=[{"id": "t1", "provider": "codex", "state": "idle", "title": "Old chat title",
                                      "updated_at": 900, "activity": "Previous task finished"}], now=1000)
    item, = result["items"]
    assert item["state"] == "claimed" and "live status unavailable" in item["status_label"]
    assert item["activity"] == "Adding the cards" and item["updated_at"] == 999
    assert item["title"] == "Work overview" and item["chat_title"] == "Old chat title"
    assert result["counts"]["running"] == 0
    unloaded = work.overview({}, sessions=[{"id": "t2", "state": "notLoaded"}], now=1000)
    assert unloaded["items"][0]["state"] == "idle"


def test_session_status_labels_and_source_details_are_preserved():
    sessions = [{"id": "live", "provider": "Codex", "state": "working", "title": "Work",
                 "source": "Codex live session", "branch": "codex/work-overview"},
                {"id": "approval", "provider": "Codex", "state": "waiting", "status_label": "Needs approval"},
                {"id": "broken", "provider": "Claude Code", "state": "blocked", "status_label": "Last turn failed"},
                {"id": "saved", "state": "idle", "status_label": "Saved chat · live status unavailable",
                 "source": "Codex saved history", "source_detail": "Read-only saved session snapshot"}]
    items = {i["session"]: i for i in work.overview({}, sessions=sessions, now=1000)["items"]}
    assert items["live"]["state"] == "running" and items["live"]["source_label"] == "Codex live session"
    assert items["live"]["branch"] == "codex/work-overview"
    assert items["approval"]["status_label"] == "Needs approval"
    assert items["broken"]["state"] == "failed" and items["broken"]["provider"] == "Claude Code"
    assert items["broken"]["status_label"] == "Last turn failed"
    assert items["saved"]["state"] == "idle" and items["saved"]["status_label"] == sessions[-1]["status_label"]
    assert items["saved"]["source_detail"] == "Read-only saved session snapshot"


def test_multiple_claims_preserve_scopes_without_counting_one_session_twice():
    claims = [{"claim_id": "wing", "thread_id": "t1", "item": "Repair wing", "full": "Repair wing: reinforce the spar",
               "project": "fpv_wing", "updated_at": 999, "activity": "Checking the spar",
               "steps": [{"title": "Design", "status": "done"}, {"title": "Check", "status": "pending"}]},
              {"claim_id": "arm", "thread_id": "t1", "item": "Repair arm", "full": "Repair arm: strengthen the base",
               "project": "robot_arm", "updated_at": 950}]
    sessions = [{"id": "t1", "provider": "Codex", "state": "working", "title": "Mechanical fixes",
                 "steps": [{"title": "Wing only", "status": "completed"}], "updated_at": 900}]
    result = work.overview({"cards": claims}, sessions=sessions, now=1000)
    item, = result["items"]
    assert item["title"] == "Repair wing + Repair arm" and item["chat_title"] == "Mechanical fixes"
    assert all(c["full"] in item["description"] for c in claims)
    assert [c["title"] for c in item["claimed_tasks"]] == ["Repair wing", "Repair arm"]
    assert {p["name"] for p in item["projects"]} == {"fpv_wing", "robot_arm"}
    assert item["activity"] == "Checking the spar" and item["updated_at"] == 999
    assert item["progress"] is None and item["remaining"] == []
    assert result["counts"]["running"] == 1 and result["counts"]["total"] == 1
    claims[1]["steps"] = [{"title": "Check", "status": "pending"}]
    combined, = work.overview({"cards": claims}, sessions=sessions, now=1000)["items"]
    assert combined["progress"] == {"done": 1, "total": 3, "label": "claimed task steps"}
    assert combined["remaining"] == ["Repair wing: Check", "Repair arm: Check"]


def test_claim_metadata_cannot_claim_a_process_is_running():
    result = work.overview({"cards": [{"item": "Legacy task", "state": "running", "status_label": "Working"}]}, now=1000)
    item, = result["items"]
    assert item["provider"] == "Session" and item["state"] == "claimed" and item["status_label"] == "Claimed"
    assert result["counts"]["running"] == 0 and result["counts"]["claimed"] == 1


def test_linked_claims_keep_each_owner_and_stale_attention_without_changing_live_chat():
    claims = [
        {"claim_id": "one", "thread_id": "chat", "session": "owner-a", "provider": "Codex", "item": "First task",
         "activity": "Checking the first task", "updated_at": 990,
         "steps": [{"title": "Prepare", "status": "done"}, {"title": "Check", "status": "pending"}]},
        {"claim_id": "two", "thread_id": "chat", "session": "owner-b", "provider": "Claude Code", "item": "Second task",
         "activity": "Waiting on source measurements", "updated_at": 100, "stale": True},
        {"claim_id": "three", "thread_id": "chat", "session": "owner-c", "item": "Third task", "stale": True},
    ]
    session = {"id": "chat", "provider": "Codex", "state": "working", "live": True,
               "title": "Shared work", "activity": "Reviewing the combined changes", "updated_at": 995}
    result = work.overview({"cards": claims}, sessions=[session], now=1000)
    item, = result["items"]
    first, second, third = item["claimed_tasks"]
    assert [c["id"] for c in item["claimed_tasks"]] == ["claim:one", "claim:two", "claim:three"]
    assert [c["session"] for c in item["claimed_tasks"]] == ["owner-a", "owner-b", "owner-c"]
    assert [c["provider"] for c in item["claimed_tasks"]] == ["Codex", "Claude Code", "Session"]
    assert first["activity"] == claims[0]["activity"] and first["updated_at"] == 990
    assert first["progress"]["done"] == 1 and first["remaining"] == ["Check"]
    assert second["activity"] == claims[1]["activity"] and second["updated_at"] == 100
    assert second["state"] == third["state"] == "stale" and "ownership" in second["attention"]
    assert "session may have stopped" not in second["attention"]
    assert third["updated_at"] is None and third["progress"] is None and third["eta"] is None
    assert item["state"] == "running" and item["activity"] == session["activity"] and item["updated_at"] == 995
    assert item["attention"].startswith("2 claimed tasks need attention")
    assert item["progress"] is None and item["remaining"] == [] and item["eta"] is None
    assert result["counts"]["running"] == result["counts"]["attention"] == result["counts"]["total"] == 1
    session["attention"] = "Confirm the design choice."
    kept, = work.overview({"cards": claims}, sessions=[session], now=1000)["items"]
    assert kept["attention"] == session["attention"] and kept["claimed_tasks"][1]["attention"]


def test_fresh_claim_activity_beats_newer_saved_metadata_but_not_live_activity():
    claims = [{"thread_id": "t1", "item": "Work overview", "updated_at": 950,
               "activity": "Integrating Codex session visibility"}]
    session = {"id": "t1", "provider": "Codex", "state": "idle", "live": False,
               "updated_at": 990, "activity": "Last turn was interrupted"}
    saved, = work.overview({"cards": claims}, sessions=[session], now=1000)["items"]
    assert saved["state"] == "claimed" and saved["activity"] == claims[0]["activity"]
    assert saved["updated_at"] == 950  # The text's own timestamp, not the newer saved-chat metadata.
    session.update(state="working", live=True, updated_at=940, activity="Running the regression tests")
    live, = work.overview({"cards": claims}, sessions=[session], now=1000)["items"]
    assert live["state"] == "running" and live["activity"] == "Running the regression tests"
    assert live["updated_at"] == 940


def test_single_linked_claim_does_not_hide_the_observed_chats_checklist():
    claim = {"claim_id": "scope", "thread_id": "chat", "session": "worker", "item": "Claim without a checklist"}
    session = {"id": "chat", "state": "working", "live": True,
               "steps": [{"title": "Prepare", "status": "done"}, {"title": "Review the combined change", "status": "pending"}]}
    item, = work.overview({"cards": [claim]}, sessions=[session], now=1000)["items"]
    assert item["claimed_tasks"][0]["progress"] is None and item["claimed_tasks"][0]["remaining"] == []
    assert item["progress"] == {"done": 1, "total": 2, "label": "task steps"}
    assert item["remaining"] == ["Review the combined change"]


def test_real_build_stage_progress_and_historical_eta():
    job = {"id": "j1", "kind": "build", "project": "robot_arm", "label": "Build robot arm", "state": "running",
           "started": 900, "estimate_seconds": 300,
           "events": [{"k": "start", "stages": ["build", "print", "fit", "export"], "t": 901},
                      {"k": "stage", "stage": "build", "t": 902},
                      {"k": "stage", "stage": "print", "t": 950}]}
    item, = work.overview({}, jobs=[job], now=1000)["items"]
    assert item["provider"] == "Studio" and item["job_id"] == "j1"
    assert item["activity"] == "Print checks" and item["updated_at"] == 950
    assert item["progress"] == {"done": 1, "total": 4, "label": "build stages"}
    assert item["remaining"] == ["Print checks", "Fit, screws, access", "Files + plates"]
    assert item["eta"] == {"seconds": 200, "basis": "Based on previous runs of this project"}
    overdue, = work.overview({}, jobs=[job], now=1300)["items"]
    assert overdue["eta"] is None and "finish time is uncertain" in overdue["activity"]


def test_agent_commands_are_not_exposed_as_activity_or_used_for_eta():
    item, = work.overview({}, jobs=[{"id": "j", "kind": "edit", "state": "running", "started": 900,
                                    "estimate_seconds": 300, "label": "Strengthen the arm",
                                    "events": [{"k": "tool", "phase": "check", "cmd": "secret command",
                                                "what": "tool output", "t": 990}]}], now=1000)["items"]
    assert item["activity"] == "Checking the design" and item["provider"] == "Claude"
    assert item["eta"] is None and item["progress"] is None
    assert "secret command" not in repr(item) and "tool output" not in repr(item)


def test_attention_counts_and_sources_survive_partial_session_data():
    sources = [{"name": "Codex", "state": "unavailable", "detail": "Live connection unavailable", "updated_at": 990}]
    data = {"cards": [{"item": "Stale claim", "stale": True, "updated_at": "nan"}]}
    result = work.overview(data, sessions=[{"id": "s1", "state": "waiting", "title": "Needs a choice"}, None],
                           jobs=[{"id": "j1", "kind": "build", "state": "failed", "started": 800,
                                  "events": [{"k": "done", "ok": False, "t": 900}]}], sources=sources, now=1000)
    assert result["sources"] == sources
    assert result["counts"]["attention"] == 3 and result["counts"]["waiting"] == 1
    assert [i["state"] for i in result["items"]] == ["waiting", "failed", "stale"]
    assert result["items"][-1]["updated_at"] is None
