"""Exact active-run identity through real Studio serialization, without an agent connection."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from kerf import codex_work, studio
from test_work_job_states import NOW, job, paused, snapshot  # noqa: F401

THREAD = "019a4242-1234-7000-8000-0123456789ab"
NOTE = "Checking the actual Studio job's fit before saving."


def record(*, live=True, updated=NOW, waiting=False, thread=THREAD):
    return codex_work._record(
        {"id": thread, "name": "Chat about the fixture", "preview": "Public task context from the chat.",
         "updatedAt": updated, "createdAt": NOW-1000, "gitInfo": {"branch": "codex/fixture"},
         "status": {"type": "active", "activeFlags": ["waitingOnApproval"] if waiting else []}},
        {"startedAt": NOW-90, "status": "inProgress", "items": [
            {"type": "agentMessage", "text": "Checking the nested helper before the next step."},
            {"type": "plan", "text": "- [x] Read the contract\n- [ ] Check the helper"},
            {"type": "commandExecution", "status": "inProgress", "command": "private-command"}]}, live)


def observe(monkeypatch, *records, claims=()):
    monkeypatch.setattr(codex_work, "snapshot", lambda root: {
        "sessions": list(records), "source": {"name": "Codex", "state": "ok"}})
    studio.LIVE["work"] = {"cards": list(claims)}


def claim(cid, *, stale=False):
    return {"id": cid, "thread_id": THREAD, "session": f"owner-{cid}", "provider": "codex",
            "title": f"Claim {cid}", "description": f"Full scope for {cid}", "activity": f"Update from {cid}",
            "updated_at": NOW-200 if stale else NOW, "stale": stale, "projects": [f"project_{cid}"],
            "steps": [{"title": f"Finish {cid}", "status": "pending"}]}


def test_exact_chat_and_job_count_once_with_controls_context_and_every_owner(snapshot, monkeypatch):
    observed = record()
    observe(monkeypatch, observed, claims=[claim("one"), claim("two", stale=True)])
    result = snapshot(job("j", agent="codex", session=THREAD))
    item, = result["items"]
    assert result["counts"]["total"] == result["counts"]["running"] == 1
    assert item["id"] == "job:j" and item["job_id"] == "j" and item["session"] == THREAD
    assert item["chat_id"] == THREAD and item["url"] == f"codex://threads/{THREAD}"
    assert item["title"] == "Task j" and item["chat_title"] == observed["title"]
    assert item["description"] == observed["description"] and item["branch"] == "codex/fixture"
    assert item["activity"] == observed["activity"] and item["action"] == "Running a command"
    assert item["source_label"] == "Studio job + Codex live session + Git claim"
    assert [c["session"] for c in item["claimed_tasks"]] == ["owner-one", "owner-two"]
    assert [c["description"] for c in item["claimed_tasks"]] == ["Full scope for one", "Full scope for two"]
    assert {p["name"] for p in item["projects"]} == {"fixture", "project_one", "project_two"}
    assert item["progress"] == {"done": 0, "total": 2, "label": "claimed task steps"}
    assert item["remaining"] == ["Claim one: Finish one", "Claim two: Finish two"]
    assert "1 claimed task needs attention" in item["attention"] and result["counts"]["attention"] == 1
    assert item["eta"] is None and "private-command" not in repr(item)


@pytest.mark.parametrize("changes", [{"session": None}, {"session": ""}, {"session": " "},
                                    {"session": [THREAD]}, {"session": THREAD + "-other"},
                                    {"agent": "claude"}, {"kind": "build"}])
def test_nonmatching_identity_or_provider_never_uses_title_project_or_time(snapshot, monkeypatch, changes):
    observed = record(); observed.update(title="Task j", project="fixture", started_at=NOW-100)
    observe(monkeypatch, observed)
    result = snapshot(job("j", **{"agent": "codex", "session": THREAD, **changes}))
    assert result["counts"]["total"] == 2
    assert {i["id"] for i in result["items"]} == {"job:j", f"session:{THREAD}"}


@pytest.mark.parametrize("metadata", [{"thread_id": None}, {"thread_id": ""}, {"provider": "Claude"}])
def test_session_fallback_id_is_not_an_explicit_codex_thread(snapshot, monkeypatch, metadata):
    observed = record(); observed.update(metadata)
    observe(monkeypatch, observed)
    assert snapshot(job("j", agent="codex", session=THREAD))["counts"]["total"] == 2


@pytest.mark.parametrize("duplicate", ["jobs", "sessions"])
def test_ambiguous_active_identity_keeps_all_records(snapshot, monkeypatch, duplicate):
    observe(monkeypatch, *([record(), record()] if duplicate == "sessions" else [record()]))
    jobs = [job("j", agent="codex", session=THREAD)]
    if duplicate == "jobs":
        jobs.append(job("second", agent="codex", session=THREAD))
    result = snapshot(*jobs)
    assert result["counts"]["total"] == result["counts"]["running"] == 3
    assert all(not i["chat_id"] for i in result["items"] if i["job_id"])


@pytest.mark.parametrize("state", ["paused", "done", "failed", "stopped"])
def test_historical_run_and_new_external_chat_turn_stay_separate(snapshot, monkeypatch, state):
    observe(monkeypatch, record())
    result = snapshot(job("old", agent="codex", session=THREAD, state=state, ended=NOW-50))
    assert result["counts"]["total"] == 2 and result["counts"]["running"] == 1
    old = next(i for i in result["items"] if i["job_id"])
    assert old["state"] == state and old["chat_id"] is None


def test_continued_history_keeps_controls_to_joined_successor(snapshot, monkeypatch):
    observe(monkeypatch, record())
    result = snapshot(paused("old", agent="codex", session=THREAD, resumed_by="next"),
                      job("next", agent="codex", session=THREAD))
    items = {i["job_id"]: i for i in result["items"]}
    assert len(items) == 2 and result["counts"]["running"] == 1
    assert items["old"]["state"] == "continued" and items["old"]["chat_id"] is None
    assert items["old"]["continuation"] == {"job_id": "next", "observed": True,
                                            "provider": "Codex", "status_label": "Working"}
    assert items["next"]["id"] == "job:next" and items["next"]["chat_id"] == THREAD


@pytest.mark.parametrize("live,updated", [(False, NOW), (True, NOW-101), (True, None)])
def test_old_or_saved_chat_cannot_supply_current_activity_steps_or_waiting(snapshot, monkeypatch, live, updated):
    observed = record(live=live, updated=updated, waiting=True)
    observed.update(state="waiting", attention="Obsolete approval request")  # Saved/old runtime data is not current.
    observe(monkeypatch, observed, claims=[claim("old", stale=True)])
    item, = snapshot(job("j", agent="codex", session=THREAD))["items"]
    assert item["state"] == "running" and item["activity"] == "Starting the job; waiting for its first update."
    assert item["progress"] is None and item["remaining"] == [] and item["eta"] is None
    assert item["chat_id"] == THREAD and item["description"] == observed["description"]
    assert item["claimed_tasks"][0]["state"] == "stale" and "claimed task needs attention" in item["attention"]
    assert "Obsolete approval" not in repr(item)


def test_live_waiting_preserves_job_note_but_clears_current_action(snapshot, monkeypatch):
    observe(monkeypatch, record(waiting=True), claims=[claim("old", stale=True)])
    result = snapshot(job("j", agent="codex", session=THREAD, events=[
        {"k": "note", "text": NOTE, "t": NOW-10}, {"k": "tool", "phase": "check", "t": NOW-1}]))
    item, = result["items"]
    assert item["state"] == "waiting" and item["status_label"] == "Needs approval"
    assert item["activity"] == NOTE and not item["action"]
    assert "waiting for your input" in item["attention"] and "claimed task needs attention" in item["attention"]
    assert result["counts"]["waiting"] == 1 and result["counts"]["running"] == 0


def test_waiting_signal_older_than_latest_job_note_cannot_replace_running_state(snapshot, monkeypatch):
    observe(monkeypatch, record(waiting=True, updated=NOW-5))
    item, = snapshot(job("j", agent="codex", session=THREAD, events=[
        {"k": "note", "text": NOTE, "t": NOW-3}, {"k": "tool", "phase": "check", "t": NOW-1}]))["items"]
    assert item["state"] == "running" and item["activity"] == NOTE and item["action"] == "Checking the design"
    assert item["updated_at"] == NOW-1 and item["attention"] is None


def test_fresh_working_chat_does_not_replace_actual_studio_note_and_action(snapshot, monkeypatch):
    observe(monkeypatch, record())
    item, = snapshot(job("j", agent="codex", session=THREAD, events=[
        {"k": "note", "text": NOTE, "t": NOW-3}, {"k": "tool", "phase": "check", "t": NOW-1}]))["items"]
    assert item["state"] == "running" and item["activity"] == NOTE and item["action"] == "Checking the design"
    assert item["progress"] == {"done": 1, "total": 2, "label": "task steps"}
    assert item["remaining"] == ["Check the helper"] and item["eta"] is None


def test_new_nonempty_note_supersedes_old_boundary_for_live_waiting(snapshot, monkeypatch):
    observe(monkeypatch, record(waiting=True))
    item, = snapshot(job("j", agent="codex", session=THREAD, events=[
        {"k": "hint", "code": "auth", "t": NOW-10}, {"k": "note", "text": NOTE, "t": NOW-1}]))["items"]
    assert item["state"] == "waiting" and item["activity"] == NOTE
    assert item["attention"] == "This session is waiting for your input."


@pytest.mark.parametrize("started,event_time,updated,expected", [
    (NOW-0.2, None, NOW-1, "waiting"),
    (NOW-100, NOW-0.2, NOW-1, "waiting"),
    (NOW-0.2, None, NOW-2, "running"),
    (NOW-100, NOW-0.2, NOW-2, "running"),
])
def test_whole_second_chat_time_compares_at_shared_precision(snapshot, monkeypatch, started, event_time, updated, expected):
    observed = record(waiting=True, updated=updated)
    assert type(observed["updated_at"]) is int  # app-server int64 seconds pass through _record unchanged.
    observe(monkeypatch, observed)
    events = [] if event_time is None else [{"k": "note", "text": NOTE, "t": event_time}]
    item, = snapshot(job("j", agent="codex", session=THREAD, started=started, events=events))["items"]
    assert item["state"] == expected
    assert bool(item["attention"]) == (expected == "waiting")


@pytest.mark.parametrize("boundary,expected", [({"k": "hint", "code": "auth"}, "Waiting for the process to stop."),
                                              ({"k": "done", "ok": True}, "Checks completed."),
                                              ({"k": "done", "ok": False}, "Checks found problems to fix.")])
@pytest.mark.parametrize("cleanup", [False, True])
def test_live_waiting_cannot_override_authoritative_job_boundary(snapshot, monkeypatch, boundary, expected, cleanup):
    observe(monkeypatch, record(waiting=True, updated=NOW-1), claims=[claim("old", stale=True)])
    rows = [{"k": "note", "text": NOTE, "t": NOW-10}, {**boundary, "t": NOW-0.4}]
    if cleanup:
        rows += [{"k": "note", "text": " \n ", "t": NOW-0.2}, {"k": "tool", "phase": "check", "t": NOW-0.2}]
    item, = snapshot(job("j", agent="codex", session=THREAD, events=rows))["items"]
    assert item["state"] == "running" and item["activity"] == expected and not item["action"]
    assert "waiting for your input" not in item["attention"]
    assert "claimed task needs attention" in item["attention"]
    assert ("Codex needs you to sign in again." in item["attention"]) == (boundary["k"] == "hint")


@pytest.mark.browser
def test_session_discovery_preserves_work_card_focus_details_and_both_controls(snapshot, monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    initial = snapshot(job("j", agent="codex", session=None))
    observe(monkeypatch, record(), claims=[claim("one"), claim("two", stale=True)])
    joined = snapshot(job("j", agent="codex", session=THREAD))
    capture = Path(os.environ.get("KERF_WORK_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "work-job-dedup.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), initial=INITIAL, joined=JOINED;
const browser=await openBrowser();
try {
 for(const [theme,width,height] of [['dark',1440,1000],['light',1440,1000],['dark',390,844],['light',390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  let fixture=initial;
  p.on('pageerror', e=>errors.push(e.message));
  await p.route('**/*',route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/') return route.fulfill({contentType:'text/html',body:html});
   if(path==='/api/work') return route.fulfill({json:fixture});
   if(path==='/api/projects') return route.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/quotes') return route.fulfill({json:{quotes:[]}});
   if(path==='/api/jobs') return route.fulfill({json:{jobs:[],sessions:[]}});
   return route.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');
  await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();
  const card=p.locator('[data-work-item="job:j"]');
  await card.waitFor();
  assert.equal(await p.locator('.work-item').count(),1);
  await card.locator('summary').click();
  const watch=card.getByRole('button',{name:'Watch job',exact:true});
  await watch.focus();
  const focusId=await watch.getAttribute('id');
  fixture=joined;
  await p.evaluate(()=>loadWork());
  assert.equal(await p.locator('.work-item').count(),1);
  assert.equal(await p.evaluate(()=>document.activeElement.id),focusId);
  assert.equal(await card.locator('details').getAttribute('open'),'');
  assert.equal(await card.locator('.work-claim').count(),2);
  assert.match(await card.innerText(),/owner-one/);
  assert.match(await card.innerText(),/owner-two/);
  assert.match(await card.innerText(),new RegExp(joined.items[0].chat_id));
  const chat=card.getByRole('link',{name:'Open chat',exact:true});
  assert.equal(await chat.getAttribute('href'),joined.items[0].url);
  assert.equal(await chat.getAttribute('rel'),'noopener noreferrer');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await card.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  await p.evaluate(()=>{window.watch=id=>window.__watched=id;});
  await p.keyboard.press('Enter');
  assert.equal(await p.evaluate(()=>window.__watched),'j');
  await chat.focus();
  await p.evaluate(()=>loadWork());
  assert.equal(await p.evaluate(()=>document.activeElement.tagName),'A');
  assert.equal(await p.evaluate(()=>document.activeElement.getAttribute('href')),joined.items[0].url);
  await card.evaluate(e=>e.scrollIntoView({block:'start'}));
  await p.screenshot({path:CAPTURE+`/work-job-dedup-${theme}-${width}.png`,fullPage:true});
  assert.deepEqual(errors,[]);
  await p.close();
 }
} finally {await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('INITIAL', json.dumps(initial)).replace('JOINED', json.dumps(joined))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
