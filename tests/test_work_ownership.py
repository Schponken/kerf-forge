"""Ownership joins require one exact identity; owner updates never imply live activity."""
import json
import os
from pathlib import Path
import subprocess
import time

import pytest

from kerf import work


def claim(**changes):
    return {"claim_id": "scope", "thread_id": "chat", "item": "Review mounting bracket",
            "session": "fixture-owner", "provider": "Codex", "updated_at": 950,
            "activity": "Comparing the mounting holes with the contract.", **changes}


def test_claim_uses_explicit_chat_identity_instead_of_observation_storage_id():
    session = {"id": "observation", "thread_id": "chat", "provider": "Codex", "state": "working",
               "live": True, "activity": "Inspecting the recorded fit results.", "updated_at": 990}
    item, = work.overview({"cards": [claim()]}, sessions=[session], now=1000)["items"]
    assert item["id"] == "session:observation" and item["chat_id"] == "chat"
    assert item["claimed_tasks"][0]["session"] == "fixture-owner"
    assert item["activity"] == session["activity"] and item["activity_source"] == "session"
    # A storage ID matching a different explicit identity is not evidence of ownership.
    session.update(id="chat", thread_id="other")
    separate = work.overview({"cards": [claim()]}, sessions=[session], now=1000)["items"]
    assert len(separate) == 2 and all(not i.get("claimed_tasks") for i in separate)


@pytest.mark.parametrize("identity", ["chat", "explicit"])
def test_ambiguous_identity_keeps_claim_separate_from_every_session(identity):
    sessions = [{"id": f"observation-{n}" if identity == "explicit" else "chat",
                 "thread_id": "chat" if identity == "explicit" else None,
                 "provider": "Codex", "state": "working"} for n in range(2)]
    result = work.overview({"cards": [claim()]}, sessions=sessions, now=1000)
    assert result["counts"]["total"] == 3 and result["counts"]["claimed"] == 1
    assert all(not item.get("claimed_tasks") for item in result["items"])
    owned, = [item for item in result["items"] if item["source"] == "claim"]
    assert owned["session"] == "fixture-owner" and owned["activity_source"] == "claim"


@pytest.mark.parametrize("identity", [None, 12, [], {}])
def test_missing_or_malformed_thread_identity_never_links_by_string_coercion(identity):
    result = work.overview({"cards": [claim(thread_id=identity)]}, sessions=[
        {"id": str(identity), "state": "idle"}], now=1000)
    assert result["counts"]["total"] == 2


def test_saved_chat_overlay_labels_the_activitys_own_source_and_timestamp():
    session = {"id": "chat", "state": "idle", "live": False, "updated_at": 990,
               "activity": "Previous turn completed."}
    item, = work.overview({"cards": [claim()]}, sessions=[session], now=1000)["items"]
    assert item["state"] == "claimed" and item["activity_source"] == "claim"
    assert item["activity"] == claim()["activity"] and item["updated_at"] == 950
    assert not item["action"] and item["eta"] is None and item["progress"] is None


@pytest.mark.parametrize("local_note", [None, "Recorded local job update."])
def test_joined_job_preserves_the_source_of_the_activity_it_actually_displays(local_note):
    # Exercise the join boundary with normalized ownership context and fresh runtime evidence separately.
    session, = work.overview({"cards": [claim()]}, sessions=[
        {"id": "chat", "thread_id": "chat", "state": "idle", "live": False}], now=1000)["items"]
    assert session["activity_source"] == "claim"
    source = {"id": "job", "kind": "edit", "agent": "codex", "state": "running", "started": 900,
              "events": [{"k": "note", "text": local_note, "t": 990}] if local_note else []}
    job = work._job(source, 1000)
    work._join_active_job(job, source, session, {"live": True, "updated_at": 995})
    assert job["activity"] == (local_note or claim()["activity"])
    assert job["activity_source"] == ("job" if local_note else "claim")
    assert job["state"] == "running" and job["job_id"] == "job"


@pytest.mark.browser
def test_owner_update_cues_and_unknown_time_remain_clear_on_desktop_and_phone(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_WORK_OWNERSHIP_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    now = time.time()
    fixture = work.overview({"cards": [claim(item="Demo: review mounting bracket", updated_at=now-50),
                                       claim(claim_id="unlinked", thread_id=None,
                                             item="Demo: unlinked owner update", updated_at=None)]},
                            sessions=[{"id": "chat", "provider": "Codex", "live": False, "state": "idle"},
                                      {"id": "live", "provider": "Codex", "live": True, "state": "working",
                                       "title": "Demo: observed session", "activity": "Reading the fixture report.",
                                       "updated_at": now-10}], now=now)
    script = tmp_path / "work-ownership.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'),fixture=FIXTURE,browser=await openBrowser();
try {
 for(const [theme,width,height] of [['dark',1440,1000],['light',1440,1000],['dark',390,844],['light',390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}),errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/*',r=>{const path=new URL(r.request().url()).pathname;
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path==='/api/work')return r.fulfill({json:fixture});
   if(path==='/api/projects')return r.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();await p.waitForFunction(()=>S.workData&&!S.workLoading);
  const owned=p.locator('[data-work-item="session:chat"]'),live=p.locator('[data-work-item="session:live"]');
  assert.match(await owned.locator('.work-activity').innerText(),/^Owner update: Comparing/);
  assert.match(await owned.locator('.work-item-footer .work-stamp').innerText(),/^Owner update /);
  assert.equal(await owned.locator('.work-state').first().innerText(),'Assigned');
  assert.equal(await live.locator('.work-activity').innerText(),'Reading the fixture report.');
  assert.match(await live.locator('.work-stamp').innerText(),/^Updated /);
  assert.equal(await p.locator('[data-work-item="claim:unlinked"] .work-item-footer .work-stamp').innerText(),'Update time unavailable');
  assert.match(await owned.locator('.work-measures').innerText(),/Progress not reported/);
  await owned.locator('summary').focus();await p.keyboard.press('Enter');
  assert.match(await owned.locator('.work-detail').innerText(),/current execution is not confirmed/);
  await p.evaluate(()=>loadWork());
  assert.equal(await owned.locator('.work-detail').getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'work-item-session%3Achat-scope');
  const note=await p.evaluate(()=>{const el=document.createElement('p');el.className='note';el.textContent='Illustrative ownership fixture; no real sessions or jobs started.';document.querySelector('.work-page .body').prepend(el);return el.textContent;});
  assert.ok(note.includes('fixture'));
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  await p.screenshot({path:CAPTURE+`/work-ownership-${theme}-${width}.png`,fullPage:true});
  await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root/'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(root/'kerf/assets/studio.html')))
       .replace('FIXTURE', json.dumps(fixture)).replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
