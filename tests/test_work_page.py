"""Work overview: useful session states, stable controls, safe content and narrow-screen layout."""
import json
import os
from pathlib import Path
import subprocess
import time


def test_work_page_filters_progress_and_refresh_recovery(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "work-page.mjs"
    capture = Path(os.environ.get("KERF_WORK_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script.write_text(r'''
import { chromium } from "PLAYWRIGHT";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html = await fs.readFile(HTML, 'utf8'), now = Date.now()/1000;
const fixture = {
 updated_at:now, fetched:now, every:60, plan_done:18, plan_total:26, today:3,
 sources:[{name:'Codex',state:'available',detail:'Local sessions for this repository.'},
          {name:'Shared work',state:'available',detail:'Claims and commits from the team.'}],
 feed:[{time:now-100,subject:'Keep project locks until stopped processes exit',done:['Safe cancellation']},
       {time:now-600,subject:'Improve foldable wing clearances',done:[]}],
 items:[
  {id:'codex-work',provider:'Codex',session:'session-codex-1',title:'Make the Work page easier to follow',
   description:'Bring Codex and Claude work into one clear view, with useful next steps and honest estimates.',
   state:'running',status_label:'Working',activity:'Connecting local Codex sessions and checking how updates reach the page.',
   projects:[],updated_at:now-20,started_at:now-1200,source_label:'Local session',url:'codex://threads/example',
   progress:{done:2,total:4,label:'steps complete'},remaining:['Check the responsive layout','Run focused tests'],eta:null},
  {id:'wing',provider:'Claude Code',session:'session-claude-2',title:'Reinforce the folding wing pivot',
   description:'Improve the load path at the hub without changing the fold range.',state:'claimed',status_label:'Claimed',
   activity:'Claimed this task. No live activity is available from this computer.',projects:[{name:'wing',title:'Hawk-fold drone'}],
   updated_at:now-900,source_label:'Git claim',remaining:[],eta:null},
  {id:'approval',provider:'Codex',session:'session-codex-3',title:'Confirm the servo mounting holes',
   state:'waiting',status_label:'Waiting for input',activity:'The catalog and drawing disagree on the mounting-hole diameter.',
   attention:'Confirm the measured diameter before the mounting plate is changed.',projects:[{name:'arm',title:'Desk robot arm'}],
   updated_at:now-240,source_label:'Local session',remaining:['Use the confirmed diameter','Check the bolt pattern'],eta:null},
  {id:'build',provider:'Studio',job_id:'build-1',title:'Build the servo test kit',state:'running',status_label:'Working',
   activity:'Checking motion across the full joint range.',projects:[{name:'servo',title:'Servo test rig'}],updated_at:now-5,
   progress:{done:3,total:6,label:'build stages complete'},remaining:['Export the print plates','Render the assembly'],
   eta:{seconds:120,basis:'Based on previous builds of this project'},source_label:'Studio job'},
  {id:'done',provider:'Codex',session:'session-codex-4',title:'Fix project cancellation',state:'done',status_label:'Finished',
   activity:'68 targeted tests passed. The pull request is ready for review.',projects:[],updated_at:now-1800,
   source_label:'Local session',remaining:[],eta:null,url:'javascript:window.__unsafe=1'}
 ]
};
const browser = await chromium.launch();
try {
 for (const [theme,width,height] of [['dark',1440,1000],['light',1440,1000],['dark',390,844],['light',390,844]]) {
  const p = await browser.newPage({viewport:{width,height}}), errors=[];
  p.on('pageerror', e=>errors.push(e.message));
  let work=structuredClone(fixture), fail=false;
  await p.route('**/*', async route=>{
   const u=new URL(route.request().url());
   if(u.pathname==='/') return route.fulfill({contentType:'text/html',body:html});
   if(u.pathname==='/api/work') return route.fulfill(fail ? {status:503,json:{error:'Connection interrupted'}} : {json:work});
   if(u.pathname==='/api/projects') return route.fulfill({json:{projects:[],claude:false}});
   if(u.pathname==='/api/jobs') return route.fulfill({json:{jobs:[],sessions:[]}});
   if(u.pathname.startsWith('/api/')) return route.fulfill({json:{}});
   return route.fulfill({contentType:'text/javascript',body:''});
  });
  await p.goto('http://kerf.test/');
  await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();
  await p.waitForSelector('[data-work-item="approval"]');
  assert.equal(await p.locator('.work-item').count(),5);
  assert.match(await p.locator('.work-item').first().innerText(),/Confirm the servo/);
  assert.match(await p.locator('[data-work-item="build"]').innerText(),/About 2 min left/);
  assert.match(await p.locator('[data-work-item="wing"]').innerText(),/No time estimate yet/);
  assert.equal(await p.locator('.work-page a[href^="javascript:"]').count(),0);
  assert.equal(await p.locator('.work-page a[href^="codex:"]').count(),1);
  await p.locator('[data-work-item="codex-work"] summary').click();
  assert.equal(await p.locator('[data-work-item="codex-work"] details').getAttribute('open'),'');
  await p.evaluate(()=>renderWork());
  assert.equal(await p.locator('[data-work-item="codex-work"] details').getAttribute('open'),'');
  for (const id of ['work-item-codex-work-chat','work-item-build-job','work-item-codex-work-scope']) {
   await p.locator('#'+id).focus();
   await p.evaluate(()=>renderWork());
   assert.equal(await p.evaluate(()=>document.activeElement.id),id);
  }
  await p.locator('#work-search').fill('pivot');
  assert.equal(await p.locator('.work-item').count(),1);
  assert.equal(await p.locator('#work-search').evaluate(el=>document.activeElement===el),true);
  await p.evaluate(()=>renderWork());
  assert.equal(await p.locator('#work-search').inputValue(),'pivot');
  assert.equal(await p.locator('#work-search').evaluate(el=>document.activeElement===el),true);
  await p.locator('#work-search').fill('');
  await p.locator('#work-provider').selectOption('Codex');
  assert.equal(await p.locator('.work-item').count(),3);
  await p.locator('#work-filter-attention').click();
  assert.equal(await p.locator('.work-item').count(),1);
  assert.match(await p.locator('.work-item').innerText(),/Needs attention/);
  await p.locator('#work-filter-all').click();
  await p.locator('#work-provider').selectOption('all');
  await p.locator('[data-work-item="codex-work"] summary').click();
  fail=true;
  await p.evaluate(()=>loadWork());
  assert.equal(await p.locator('.work-item').count(),5);
  assert.match(await p.locator('.work-notice').innerText(),/last available information/);
  fail=false;
  await p.locator('.work-notice button').click();
  await p.waitForFunction(()=>!S.workLoading && !S.workError);
  assert.equal(await p.locator('.work-notice').count(),0);
  const overflow=await p.evaluate(()=>[...document.querySelectorAll('.work-page *')].filter(el=>{
   const r=el.getBoundingClientRect(),s=getComputedStyle(el);return s.display!=='none' && r.width>0 && (r.right>innerWidth+1 || r.left< -1);
  }).map(el=>el.className));
  assert.deepEqual(overflow,[],JSON.stringify(overflow));
  await p.locator('#main').evaluate(el=>el.scrollTop=0);
  assert.equal(await p.locator('.work-page .body').evaluate(el=>getComputedStyle(el).opacity),'1');
  if (theme==='light') {
   const ratios=await p.evaluate(()=>{
    const luminance=s=>s.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045 ? v/12.92 : ((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
    return ['.work-completed','.work-state.done'].map(selector=>{
     const el=document.querySelector(selector),fg=luminance(getComputedStyle(el).color);
     const bg=luminance(getComputedStyle(selector==='.work-completed' ? document.querySelector('.work-page') : el).backgroundColor);
     return (Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05);
    });
   });
   assert.ok(ratios.every(r=>r>=4.5),JSON.stringify(ratios));
  }
  await p.screenshot({path:CAPTURE+`/work-${theme}-${width}.png`,fullPage:true});
  work={...fixture,items:[],feed:[],sources:[{name:'Codex',state:'unavailable',detail:'Codex is not installed on this computer.'}]};
  await p.evaluate(()=>loadWork());
  assert.match(await p.locator('.work-empty').innerText(),/No work is being reported/);
  assert.match(await p.locator('.work-rail').innerText(),/not installed/);
  work={...fixture,items:[{...fixture.items[0],title:'<img src=x onerror="window.__unsafe=1">',activity:'<script>unsafe()</script>'}]};
  await p.evaluate(()=>loadWork());
  assert.equal(await p.locator('.work-item img').count(),0);
  assert.equal(await p.evaluate(()=>window.__unsafe),undefined);
  assert.deepEqual(errors,[],errors.join('\n'));
  await p.close();
 }
} finally { await browser.close(); }
'''.replace('"PLAYWRIGHT"', json.dumps(str(root / 'tools/render/node_modules/playwright/index.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE', json.dumps(str(capture))), encoding='utf-8')
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr


def test_linked_claim_owners_are_visible_searchable_and_preserved_on_refresh(tmp_path):
    from kerf import work
    root = Path(__file__).resolve().parents[1]
    now = time.time()
    long_owner = "codex-plate-clearance-worker-for-full-owner-identity-" + "ab12" * 25
    claims = [
        {"claim_id": "details", "thread_id": "shared-chat", "session": "codex-owner-details", "provider": "Codex",
         "item": "Clarify claimed tasks", "full": "Clarify claimed tasks: keep each owner's scope and updates visible.",
         "activity": "Checking ownership search and keyboard focus", "updated_at": now - 20,
         "steps": [{"title": "Preserve claim details", "status": "done"}, {"title": "Check phone layout", "status": "pending"}]},
        {"claim_id": "sources", "thread_id": "shared-chat", "session": long_owner, "provider": "Claude Code",
         "item": "Review source geometry", "full": "Review source geometry: compare the saved model with its vendor source.",
         "activity": "Waiting on vendor geometry measurements", "updated_at": now - 7200, "stale": True},
        {"claim_id": "notes", "thread_id": "shared-chat", "session": "legacy-owner-notes", "item": "Update assembly notes",
         "activity": "Checking the reported remaining work", "stale": True},
    ]
    session = {"id": "shared-chat", "provider": "Codex", "state": "working", "live": True, "title": "Sample shared chat",
               "activity": "Reviewing the combined changes", "updated_at": now - 5, "url": "codex://threads/example"}
    fixture = work.overview({"cards": claims, "plan_done": 12, "plan_total": 20, "feed": []}, sessions=[session,
        {"id": "other", "provider": "Studio", "state": "done", "title": "Sample completed job",
         "attention": "Review the completed output."},
    ], sources=[{"name": "Sample data", "state": "available", "detail": "Illustrative claims for interface verification."}], now=now)
    single = work.overview({"cards": [{**claims[0], "steps": None}]}, sessions=[{**session, "steps": [
        {"title": "Prepare", "status": "done"}, {"title": "Review the combined change", "status": "pending"}]}], now=now)
    known = work.overview({"cards": [claims[0], {**claims[1], "steps": [{"title": "Verify sources", "status": "pending"}]},
                                    {**claims[2], "steps": [{"title": "Finish notes", "status": "pending"}]}]},
                          sessions=[session], now=now)
    capture = Path(os.environ.get("KERF_WORK_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "work-owners.mjs"
    script.write_text(r'''
import { chromium } from "PLAYWRIGHT";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), fixture=FIXTURE, single=SINGLE_DATA, known=KNOWN_DATA;
const browser=await chromium.launch();
try {
 for(const [theme,width,height] of [['dark',1440,1200],['light',1440,1200],['dark',390,844],['light',390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  let data=structuredClone(fixture);
  p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/*',route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/') return route.fulfill({contentType:'text/html',body:html});
   if(path==='/api/work') return route.fulfill({json:data});
   if(path==='/api/projects') return route.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/jobs') return route.fulfill({json:{jobs:[],sessions:[]}});
   return route.fulfill({contentType:'text/javascript',body:path.startsWith('/api/') ? '{}' : ''});
  });
  await p.goto('http://kerf.test/');
  await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();
  const card=p.locator('[data-work-item="session:shared-chat"]'), detail=card.locator('details'), summary=card.locator('summary');
  await card.waitFor();
  assert.equal(await p.locator('.work-item').count(),2);
  assert.equal(await p.locator('#work-filter-active span').innerText(),'1');
  assert.equal(await p.locator('#work-filter-attention span').innerText(),'2');
  assert.equal(await p.locator('#work-filter-recent span').innerText(),'1');
  assert.equal(await card.locator(':scope > .work-item-top > .work-state').innerText(),'Working');
  assert.match(await card.locator(':scope > .work-attention').innerText(),/2 claimed tasks need attention/);
  await summary.click();
  assert.equal(await card.locator('.work-claim').count(),3);
  assert.deepEqual(await card.locator('.work-claim .work-state').allTextContents(),['Claimed','No recent update','No recent update']);
  assert.match(await card.innerText(),/1 of 2 reported steps complete/);
  assert.match(await card.innerText(),/Check phone layout/);
  assert.equal(await card.locator('.work-claim-progress').filter({hasText:'No checklist reported'}).count(),2);
  assert.equal(await card.locator('.work-claim-owner').nth(1).innerText(),'Owner: Claude Code · '+LONG_OWNER);
  assert.match(await card.locator('.work-claim').last().innerText(),/time unavailable/);
  assert.doesNotMatch(await card.locator('.work-claims').innerText(),/session may have stopped|About .* min left/);
  await p.locator('#work-filter-active').click();
  assert.equal(await p.locator('.work-item').count(),1);
  assert.equal(await card.count(),1);
  await p.locator('#work-filter-recent').click();
  assert.equal(await p.locator('.work-item').count(),1);
  assert.equal(await card.count(),0);
  await p.locator('#work-filter-all').click();
  for(const query of [LONG_OWNER,'vendor geometry measurements','legacy-owner-notes']) {
   await p.locator('#work-search').fill(query);
   assert.equal(await p.locator('.work-item').count(),1);
   assert.equal(await p.locator('#work-search').evaluate(el=>el===document.activeElement),true);
  }
  await p.locator('#work-search').fill('');
  for(const provider of ['Claude Code','Session']) {
   await p.locator('#work-provider').selectOption(provider);
   assert.equal(await p.locator('.work-item').count(),1);
   assert.equal(await card.locator(':scope > .work-item-top > .work-state').innerText(),'Working');
  }
  await p.locator('#work-provider').selectOption('all');
  await p.locator('#work-filter-attention').click();
  assert.equal(await p.locator('.work-item').count(),2);
  assert.equal(await card.count(),1);
  await summary.focus();
  const focused=await summary.getAttribute('id');
  data.items[0].claimed_tasks[0].activity='Ownership details remain visible after refresh';
  await p.evaluate(()=>loadWork());
  assert.equal(await detail.getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.activeElement.id),focused);
  assert.match(await card.locator('.work-claim').first().innerText(),/remain visible after refresh/);
  assert.equal(data.counts.running,1); assert.equal(data.counts.attention,2);
  const overflow=await p.evaluate(()=>[...document.querySelectorAll('.work-page *')].filter(el=>{
   const r=el.getBoundingClientRect();return r.width>0 && (r.right>innerWidth+1 || r.left< -1);
  }).map(el=>el.className));
  assert.deepEqual(overflow,[],JSON.stringify(overflow));
  const contrasts=await p.evaluate(()=>{
   const rgb=s=>s.match(/[\d.]+/g).map(Number), lum=a=>a.slice(0,3).map(v=>v/255).map(v=>v<=.04045 ? v/12.92 : ((v+.055)/1.055)**2.4).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
   const base=rgb(getComputedStyle(document.querySelector('.work-page')).backgroundColor);
   return ['.work-claim-owner','.work-claim-activity','.work-claim .work-attention','.work-claim .work-state.stale'].map(sel=>{
    const s=getComputedStyle(document.querySelector(sel)), fg=lum(rgb(s.color)), bg=rgb(s.backgroundColor), alpha=bg.length>3 ? bg[3] : 1;
    const back=lum(bg.slice(0,3).map((v,i)=>v*alpha+base[i]*(1-alpha)));
    return (Math.max(fg,back)+.05)/(Math.min(fg,back)+.05);
   });
  });
  assert.ok(contrasts.every(n=>n>=4.5),JSON.stringify(contrasts));
  await p.locator('#main').evaluate(el=>el.scrollTop=0);
  await p.screenshot({path:CAPTURE+`/work-owners-sample-${theme}-${width}-top.png`,fullPage:true});
  await card.locator('.work-claims').evaluate(el=>el.scrollIntoView({block:'start'}));
  await p.screenshot({path:CAPTURE+`/work-owners-sample-${theme}-${width}-details.png`,fullPage:true});
  // An older partial response must not imply that absent remaining-step text means completion.
  data.items[0].claimed_tasks[0].remaining=[];
  data.items[0].claimed_tasks[1].activity='<img src=x onerror="window.__unsafe=1">';
  await p.evaluate(()=>loadWork());
  assert.match(await card.locator('.work-claim').first().innerText(),/Remaining steps not reported/);
  assert.doesNotMatch(await card.locator('.work-claim').first().innerText(),/All reported checklist steps are complete/);
  assert.equal(await card.locator('.work-claims img').count(),0);
  assert.equal(await p.evaluate(()=>window.__unsafe),undefined);
  await p.locator('#work-filter-all').click();
  data=structuredClone(single);
  await p.evaluate(()=>loadWork());
  assert.match(await card.locator('.work-progress').innerText(),/1 of 2 chat steps complete/);
  assert.match(await card.locator('.work-claim-progress').innerText(),/No checklist reported/);
  assert.match(await card.locator('.work-chat-steps').innerText(),/Chat’s reported next steps.*Review the combined change/s);
  data.items[0].claimed_tasks[0].progress={...data.items[0].progress};
  data.items[0].claimed_tasks[0].remaining=[...data.items[0].remaining];
  await p.evaluate(()=>loadWork());
  assert.equal(await card.locator('.work-chat-steps').count(),0);
  assert.equal(await card.locator('li').filter({hasText:/^Review the combined change$/}).count(),1);
  data=structuredClone(known);
  await p.evaluate(()=>loadWork());
  assert.match(await card.locator('.work-progress').innerText(),/1 of 4 claimed task steps/);
  assert.deepEqual(await card.locator('.work-claim-progress').allTextContents(),[
   '1 of 2 reported steps complete','0 of 1 reported steps complete','0 of 1 reported steps complete']);
  assert.equal(await card.locator('.work-chat-steps').count(),0);
  assert.deepEqual(errors,[]);
  await p.close();
 }
} finally { await browser.close(); }
'''.replace('"PLAYWRIGHT"', json.dumps(str(root / 'tools/render/node_modules/playwright/index.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('FIXTURE', json.dumps(fixture)).replace('LONG_OWNER', json.dumps(long_owner))
       .replace('SINGLE_DATA', json.dumps(single)).replace('KNOWN_DATA', json.dumps(known))
       .replace('CAPTURE', json.dumps(str(capture))), encoding='utf-8')
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
