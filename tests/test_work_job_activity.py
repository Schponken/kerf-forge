"""Public Studio progress notes survive tool updates; raw tool data stays out of Work."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from test_work_job_states import NOW, job, paused, snapshot  # noqa: F401

NOTE = "Checking hinge clearance before designing the next part."


def events(text=NOTE):
    return [{"k": "note", "text": text, "t": NOW-10},
            {"k": "tool", "phase": "check", "name": "private-tool-name", "cmd": "private-command",
             "what": "private-tool-output", "t": NOW-1},
            {"k": "reasoning", "text": "private-reasoning", "t": NOW-1}]


@pytest.mark.parametrize("kind", ["design", "edit", "fix", "quote"])
@pytest.mark.parametrize("agent", ["claude", "codex"])
def test_serialized_agent_note_survives_tool_update(snapshot, kind, agent):
    item, = snapshot(job("j", kind=kind, agent=agent, events=events()))["items"]
    assert item["activity"] == NOTE and item["action"] == "Checking the design"
    assert item["updated_at"] == NOW-1 and item["state"] == "running"
    assert item["eta"] is None and item["progress"] is None
    assert "private-" not in repr(item)


def test_new_public_note_replaces_description_and_clears_action(snapshot):
    rows = events() + [{"k": "note", "text": "  Clearances checked.\nPreparing the next part.  ", "t": NOW}]
    item, = snapshot(job("j", events=rows))["items"]
    assert item["activity"] == "Clearances checked. Preparing the next part."
    assert not item["action"] and item["updated_at"] == NOW


def test_empty_notes_do_not_hide_public_note_or_phase(snapshot):
    rows = events() + [{"k": "note", "text": " \n ", "t": NOW}]
    item, = snapshot(job("j", events=rows))["items"]
    assert item["activity"] == NOTE and item["action"] == "Checking the design"
    fallback, = snapshot(job("j", events=rows[1:]))["items"]
    assert fallback["activity"] == "Checking the design" and not fallback["action"]


@pytest.mark.parametrize("phase,expected", [("research", "Researching options"), ("unknown-private-phase", "Working on the task")])
def test_action_uses_bounded_phase_labels(snapshot, phase, expected):
    rows = events(); rows[1]["phase"] = phase
    item, = snapshot(job("j", events=rows))["items"]
    assert item["activity"] == NOTE and item["action"] == expected
    assert "private-" not in repr(item)


def test_stage_action_and_duplicate_description(snapshot):
    rows = events()[:1] + [{"k": "stage", "stage": "print", "t": NOW}]
    item, = snapshot(job("j", events=rows))["items"]
    assert item["activity"] == NOTE and item["action"] == "Print checks"
    rows[0]["text"] = "Print checks"
    same, = snapshot(job("j", events=rows))["items"]
    assert same["activity"] == "Print checks" and not same["action"]
    build, = snapshot(job("j", kind="build", events=rows))["items"]
    assert build["activity"] == "Print checks" and not build["action"]


@pytest.mark.parametrize("boundary,expected", [({"k": "hint", "code": "auth"}, "Waiting for the process to stop."),
                                              ({"k": "done", "ok": True}, "Checks completed."),
                                              ({"k": "done", "ok": False}, "Checks found problems to fix.")])
def test_hint_and_result_boundaries_keep_status_authoritative(snapshot, boundary, expected):
    item, = snapshot(job("j", events=events()+[boundary]))["items"]
    assert item["activity"] == expected and not item["action"]
    if boundary["k"] == "hint":
        assert item["attention"] == "Claude needs you to sign in again."
    later, = snapshot(job("j", events=events()+[boundary, {"k": "tool", "phase": "check"}]))["items"]
    assert later["activity"] == expected and not later["action"]
    assert later["attention"] == item["attention"]  # Cleanup cannot conceal an authentication failure.


@pytest.mark.parametrize("state", ["done", "failed", "stopped"])
def test_ended_jobs_do_not_get_current_action(snapshot, state):
    item, = snapshot(job("j", state=state, ended=NOW, events=events()))["items"]
    assert item["state"] == state and not item["action"]


@pytest.mark.parametrize("state", ["failed", "stopped"])
@pytest.mark.parametrize("cleanup", [False, True])
def test_ended_setup_failure_does_not_claim_process_is_still_stopping(snapshot, state, cleanup):
    rows = events()+[{"k": "hint", "code": "trust"}]
    if cleanup:
        rows.append({"k": "tool", "phase": "build"})
    item, = snapshot(job("j", agent="codex", state=state, ended=NOW, events=rows))["items"]
    assert item["activity"] == "The process stopped after a setup problem."
    assert item["attention"] == "Codex needs this project folder to be trusted."
    assert item["state"] == state and not item["action"]


def test_pause_and_continuation_replace_note_and_action(snapshot):
    items = {i["job_id"]: i for i in snapshot(paused(events=events()),
             paused("old", events=events(), resumed_by="next"), job("next", agent="codex"))["items"]}
    assert items["paused"]["activity"] == "Usage limit reached; this run is paused."
    assert items["old"]["activity"] == "Codex continued this task in another job."
    assert items["paused"]["action"] is items["old"]["action"] is None
    assert NOTE not in repr(items)


def test_terminal_build_keeps_result_and_reported_progress(snapshot):
    rows = [{"k": "start", "stages": ["build", "print"]}, *events(), {"k": "done", "ok": True, "t": NOW}]
    item, = snapshot(job("j", kind="build", state="done", ended=NOW, events=rows))["items"]
    assert item["activity"] == "Checks completed." and not item["action"]
    assert item["progress"] == {"done": 2, "total": 2, "label": "build stages"}
    assert item["remaining"] == [] and item["eta"] is None


@pytest.mark.browser
def test_serialized_job_note_and_action_reach_work_page(snapshot, tmp_path):
    root = Path(__file__).resolve().parents[1]
    note = NOTE + " <img src=x onerror=alert(1)> " + "clearance-reference-"*10
    initial = snapshot(job("j", agent="codex", label="Check the hinge fit", events=events(note)))
    updated = snapshot(job("j", agent="codex", label="Check the hinge fit",
                           events=events(note)+[{"k": "note", "text": "Clearance check complete; reviewing the result.", "t": NOW}]))
    capture = Path(os.environ.get("KERF_WORK_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "work-job-activity.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), initial=INITIAL, updated=UPDATED;
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
  assert.equal(await card.locator('.work-activity').innerText(),initial.items[0].activity);
  assert.equal(await card.locator('.work-action').innerText(),'Checking the design');
  assert.equal(await card.locator('img').count(),0);
  assert.doesNotMatch(await card.innerText(),/private-|About \d+ min left/);
  for(const text of ['hinge clearance','Checking the design']) {
   await p.locator('#work-search').fill(text);
   assert.equal(await card.count(),1);
   assert.equal(await p.locator('.work-item').count(),1);
  }
  await p.locator('#work-search').fill('');
  await card.locator('summary').click();
  const watch=card.getByRole('button',{name:'Watch job',exact:true});
  await watch.focus();
  const focusId=await watch.getAttribute('id');
  await p.evaluate(()=>renderWork());
  assert.equal(await p.evaluate(()=>document.activeElement.id),focusId);
  assert.equal(await card.locator('details').getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await card.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  await card.evaluate(e=>e.scrollIntoView({block:'start'}));
  await p.screenshot({path:CAPTURE+`/work-job-activity-${theme}-${width}.png`,fullPage:true});
  fixture=updated;
  await p.evaluate(()=>loadWork());
  assert.equal(await card.locator('.work-activity').innerText(),updated.items[0].activity);
  assert.equal(await card.locator('.work-action').count(),0);
  assert.equal(await p.evaluate(()=>document.activeElement.id),focusId);
  assert.equal(await card.locator('details').getAttribute('open'),'');
  await p.evaluate(()=>{window.watch=id=>window.__watched=id;});
  await p.keyboard.press('Enter');
  assert.equal(await p.evaluate(()=>window.__watched),'j');
  assert.deepEqual(errors,[]);
  await p.close();
 }
} finally {await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('INITIAL', json.dumps(initial)).replace('UPDATED', json.dumps(updated))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
