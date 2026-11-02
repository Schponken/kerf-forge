"""Work overview: useful session states, stable controls, safe content and narrow-screen layout."""
import json
import os
from pathlib import Path
import subprocess


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
