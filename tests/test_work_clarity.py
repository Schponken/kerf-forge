"""Multi-job Work fixtures are synthetic; no real chats, jobs, project files or estimates are read."""
import json
import os
from pathlib import Path
import subprocess
import time

import pytest

from kerf import work


def work_fixture(now=None):
    now = now or time.time()
    def job(jid, label, **changes):
        return {"id": jid, "kind": "edit", "project": "demo_planter", "label": label,
                "agent": "codex", "state": "running", "started": now-1800, "events": [], **changes}
    sessions = [{"id": "demo-chat", "thread_id": "demo-chat", "provider": "Codex", "live": True,
                 "title": "Demo: choose a watering approach", "description": "Compare a passive reservoir with a small pump.",
                 "state": "waiting", "status_label": "Needs your answer", "updated_at": now-30,
                 "activity": "The passive reservoir fits the trip length. Confirm that it can sit above the pots.",
                 "projects": ["demo_planter"], "url": "codex://threads/demo-chat",
                 "steps": [{"title": "Compare watering approaches", "status": "completed"},
                           {"title": "Confirm the reservoir position", "status": "pending"},
                           {"title": "Check the hose routing", "status": "pending"}]}]
    claims = [{"id": "mount", "provider": "Codex", "session": "codex-mount-fit", "title": "Demo: refine the wall mount",
               "description": "Check fastener access and the mounting footprint.", "projects": ["demo_enclosure"],
               "updated_at": now-180, "activity": "Comparing the mounting holes with the bracket footprint.",
               "steps": [{"title": "Check driver access", "status": "pending"}]},
              {"id": "old", "provider": "Claude", "session": "claude-cable-route", "title": "Demo: route the cable",
               "description": "Keep the cable clear of the hinge.", "projects": ["demo_enclosure"], "stale": True,
               "updated_at": now-7200, "activity": "Reviewing the hinge sweep."}]
    jobs = [job("clearance", "Demo: check the pump clearance", events=[
                {"k": "note", "text": "Checking clearance around the tube connectors before saving the manifold.", "t": now-50},
                {"k": "tool", "phase": "check", "t": now-10}]),
            job("paused", "Demo: design the enclosure", agent="claude", state="paused", ended=now-300,
                usage={"until": now+3600}, auto_resume=True, resumable=True),
            job("build", "Demo: export the bracket kit", kind="build", project="demo_enclosure", started=now-120,
                estimate_seconds=300, events=[{"k": "start", "stages": ["build", "print", "bom"]},
                                             {"k": "stage", "stage": "print", "t": now-15}]),
            job("finished", "Demo: verify the valve mount", state="done", ended=now-600,
                events=[{"k": "done", "ok": True, "t": now-600}])]
    return work.overview({"cards": claims, "plan_done": 18, "plan_total": 26, "today": 3,
                          "feed": [{"time": now-600, "subject": "Check valve mount clearance", "done": ["clearance"]}]},
                         sessions, jobs, [{"name": "Synthetic fixture", "state": "ok",
                                            "detail": "Illustrative jobs and estimates for UI testing only."}], now)


def test_local_changes_are_observations_not_invented_history(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "work-observations.mjs"
    script.write_text(r'''
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), fixture=FIXTURE;
const c=vm.createContext({S:{},Date,Map,Set,JSON,Number,URL});
vm.runInContext(html.slice(html.indexOf('const WORK_STATES'),html.indexOf('async function openLive')),c);
const copy=x=>JSON.parse(JSON.stringify(x));
c.workRecordChanges(fixture);
assert.equal(c.S.workUpdates.length,0,'initial snapshot is not history');
const heartbeat=copy(fixture);heartbeat.updated_at+=60;
for(const i of heartbeat.items)i.updated_at+=60;
c.workRecordChanges(heartbeat);
assert.equal(c.S.workUpdates.length,0,'timestamp-only refresh is not a new action');
for(const [failure,id] of [[{fetch_error:'offline'},'claim:mount'],
 [{sources:[{name:'Codex',state:'stale'}]},'session:demo-chat'],
 [{sources:[{name:'Codex',state:'unavailable'}]},'session:demo-chat'],
 [{sources:[{name:'Studio jobs',state:'error'}]},'job:clearance']]) {
 c.S={};c.workRecordChanges(fixture);
 const stale=copy(fixture);Object.assign(stale,failure);stale.items.find(i=>i.id===id).activity='untrustworthy change';
 c.workRecordChanges(stale);
 assert.equal(c.S.workUpdates.length,0);
 c.workRecordChanges(fixture);
 assert.equal(c.S.workUpdates.length,0,'source recovery does not invent changes across the gap');
}
for(const failedSource of ['Codex','Shared claims']) {
 c.S={};const mixed=copy(fixture);
 mixed.sources=[{name:'Codex',state:'ok'},{name:'Shared claims',state:'ok'},{name:'Studio jobs',state:'ok'}];
 mixed.sources.find(s=>s.name===failedSource).state='unavailable';
 if(failedSource==='Shared claims')mixed.fetch_error='shared fetch failed';
 c.workRecordChanges(mixed);
 mixed.items.find(i=>i.id==='job:clearance').activity='Local checks completed; reviewing the report.';
 const untrusted=mixed.items.find(i=>i.id===(failedSource==='Codex' ? 'session:demo-chat' : 'claim:mount'));
 untrusted.state='done';untrusted.status_label='Finished';
 c.workRecordChanges(mixed);
 assert.equal(c.S.workUpdates.length,1);assert.equal(c.S.workUpdates[0].id,'job:clearance');
}
c.S={};const joined=copy(fixture), joinedJob=joined.items.find(i=>i.id==='job:clearance');
joinedJob.chat_id='linked-chat';joinedJob.claimed_tasks=[copy(joined.items.find(i=>i.id==='claim:mount'))];
joined.sources=[{name:'Codex',state:'unavailable'},{name:'Shared claims',state:'ok'},{name:'Studio jobs',state:'ok'}];
joinedJob.state='waiting';joinedJob.status_label='Needs approval';c.workRecordChanges(joined);
joinedJob.state='running';joinedJob.status_label='Working';joinedJob.activity='stale derived context';
c.workRecordChanges(joined);assert.equal(c.S.workUpdates.length,0,'lost chat state cannot become an observed resume');
joinedJob.state='done';joinedJob.status_label='Finished';c.workRecordChanges(joined);
assert.equal(c.S.workUpdates.length,1);assert.equal(c.S.workUpdates[0].detail,'Observed job status: Finished','actual local result remains visible even with an unavailable chat source');
c.S={};joined.sources[0].state='ok';joined.fetch_error='shared fetch failed';c.workRecordChanges(joined);
joinedJob.activity='Actual local result';joinedJob.claimed_tasks[0].activity='stale ownership';
c.workRecordChanges(joined);assert.equal(c.S.workUpdates.length,1);assert.equal(c.S.workUpdates[0].detail,'Actual local result');
c.S={};c.workRecordChanges(fixture);
const updated=copy(fixture), changed=updated.items.find(i=>i.id==='job:clearance');
changed.activity='Connector clearance checked; preparing the report.';
c.workRecordChanges(updated);
assert.equal(c.S.workUpdates.length,1);assert.equal(c.S.workUpdates[0].id,changed.id);
assert.equal(c.S.workUpdates[0].detail,changed.activity);
const key=c.S.workUpdates[0].key;
const missing=copy(updated);missing.items=missing.items.filter(i=>i.id!=='job:finished');
c.workRecordChanges(missing);
assert.equal(c.S.workUpdates.length,1,'disappearance is not a completion event');
const newItem=copy(missing);newItem.items.push({...changed,id:'new-job',title:'Newly observed task'});
c.workRecordChanges(newItem);
assert.match(c.S.workUpdates[0].detail,/Newly visible/);
assert.equal(c.S.workUpdates[1].key,key,'retained observations keep stable identity');
for(let n=0;n<9;n++) {newItem.items[0].activity='Public update '+n;c.workRecordChanges(newItem);}
assert.equal(c.S.workUpdates.length,6);
assert.equal(new Set(c.S.workUpdates.map(u=>u.key)).size,6);
assert.ok(c.S.workUpdates.every(u=>u.at>0 && !/finished|completed/i.test(u.detail)));
const zero={...fixture,items:[]};c.S={};c.workRecordChanges(zero);assert.equal(c.S.workUpdates.length,0);
'''.replace('HTML', json.dumps(str(root/'kerf/assets/studio.html'))).replace('FIXTURE', json.dumps(work_fixture())), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.browser
def test_work_queue_answers_actions_ownership_next_steps_and_refresh_changes(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_WORK_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    html = Path(os.environ.get("KERF_WORK_HTML", str(root/'kerf/assets/studio.html')))
    fixture = work_fixture()
    script = tmp_path / "work-clarity.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), initial=FIXTURE;
const browser=await openBrowser();
try {
 for(const [theme,width,height] of [['dark',1440,1000],['light',1440,1000],['dark',390,844],['light',390,844]]) {
  let fixture=structuredClone(initial);
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/*',route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/')return route.fulfill({contentType:'text/html',body:html});
   if(path==='/api/work')return route.fulfill({json:fixture});
   if(path==='/api/projects')return route.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/quotes')return route.fulfill({json:{quotes:[]}});
   if(path==='/api/jobs')return route.fulfill({json:{jobs:[],sessions:[]}});
   return route.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();await p.locator('.work-item').first().waitFor();
  assert.match(await p.locator('.work-summary').innerText(),/2 working · 1 assigned · 1 paused/);
  assert.equal(await p.locator('#work-updates').count(),0);
  assert.equal(await p.locator('.work-item').count(),7);
  assert.deepEqual(await p.locator('.work-queue').evaluateAll(es=>es.map(e=>[e.getAttribute('aria-label'),e.querySelectorAll('.work-item').length])),[['Waiting for your input',1],['Working now',2],['Assigned work',1],['Paused runs',1],['Updates to review',1],['Recent runs & saved chats',1]]);
  const waiting=p.locator('[data-work-item="session:demo-chat"]');
  assert.match(await waiting.locator('.work-next').innerText(),/Confirm the reservoir position/);
  assert.equal(await waiting.locator(':scope > .work-attention').count(),0);
  const inputAction=waiting.getByRole('link',{name:'Open chat',exact:true});
  const actionBox=await inputAction.boundingBox();assert.ok(actionBox.y>=0 && actionBox.y+actionBox.height<=height,'waiting action visible in first viewport');
  assert.equal(await waiting.locator('.work-next').getByRole('button').innerText(),'All 2 remaining steps');
  await waiting.locator('.work-next button').click();
  assert.equal(await waiting.locator('details').getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.activeElement.tagName),'SUMMARY');
  await waiting.locator('summary').click();
  await p.locator('#work-filter-input').click();
  assert.equal(await p.locator('.work-item').count(),1);
  assert.equal(await waiting.getByRole('link',{name:'Open chat',exact:true}).getAttribute('href'),'codex://threads/demo-chat');
  await p.locator('#work-filter-all').click();
  assert.match(await p.locator('[data-work-item="claim:mount"] .work-owner').innerText(),/Owner codex-mount-fit/);
  assert.doesNotMatch(await p.locator('[data-work-item="job:clearance"] .work-owner').innerText(),/Session|Job clearance/);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await p.locator('.work-item').evaluateAll(es=>es.every(e=>e.scrollWidth<=e.clientWidth)),true);
  await p.evaluate(()=>document.querySelector('#main').scrollTop=0);
  await p.screenshot({path:CAPTURE+`/work-clarity-${theme}-${width}-queue.png`});
  const card=p.locator('[data-work-item="job:clearance"]');
  await card.locator('summary').click();
  const watch=card.getByRole('button',{name:'Watch job',exact:true});await watch.focus();
  const focusId=await watch.getAttribute('id');
  fixture.items.find(i=>i.id==='job:clearance').activity='Connector clearance checked <img src=x onerror=alert(1)>; preparing the report.';
  await p.evaluate(()=>loadWork());
  assert.equal(await p.evaluate(()=>document.activeElement.id),focusId);
  assert.equal(await card.locator('details').getAttribute('open'),'');
  await p.locator('#work-updates-summary').click();
  assert.match(await p.locator('#work-updates').innerText(),/Connector clearance checked/);
  assert.match(await p.locator('#work-updates').innerText(),/Observed/);
  assert.equal(await p.locator('#work-updates img').count(),0);
  const update=p.locator('#work-updates button').first();await update.focus();
  const updateId=await update.getAttribute('id');
  fixture.items.find(i=>i.id==='job:build').activity='Preparing the kit files.';
  await p.evaluate(()=>loadWork());
  assert.equal(await p.evaluate(()=>document.activeElement.id),updateId);
  await p.keyboard.press('Enter');
  assert.equal(await p.evaluate(()=>document.activeElement.dataset.workItem),'job:clearance');
  await p.locator('#work-updates-summary').scrollIntoViewIfNeeded();
  await p.screenshot({path:CAPTURE+`/work-clarity-${theme}-${width}-changes.png`});
  assert.deepEqual(errors,[]);
  await p.close();
 }
} finally {await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root/'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(html))).replace('FIXTURE', json.dumps(fixture))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
