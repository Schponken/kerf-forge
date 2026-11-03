"""Compact object-stage navigation, contained trays and reachable controls on short screens."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_mobile_stage_trays_scroll_access_and_desktop_geometry(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_MOBILE_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "mobile-shell.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8');
const browser=await openBrowser();
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[390,844],[390,1000],[320,568],[844,390],[1440,900]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  await p.emulateMedia({reducedMotion:'reduce'});
  p.on('pageerror',e=>errors.push(e.message));
  let projects=[],jobs=[];
  await p.route('**/*',route=>{const path=new URL(route.request().url()).pathname;
   if(path==='/') return route.fulfill({contentType:'text/html',body:html});
   if(path==='/api/projects') return route.fulfill({json:{projects,claude:false}});
   if(path==='/api/jobs') return route.fulfill({json:{jobs,sessions:[]}});
   if(path==='/api/quotes') return route.fulfill({json:{quotes:[]}});
   if(path==='/api/work') return route.fulfill({json:{items:[{id:'fixture-task',provider:'Codex',state:'running',title:'Check the mounting bracket',activity:'Checking the bolt clearances before preparing the pull request.',remaining:['Review the result','Publish the pull request'],updated_at:Date.now()/1000}],sources:[]}});
   return route.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();await p.locator('.work-item').waitFor();
  const bounds=()=>p.evaluate(()=>Object.fromEntries(['side','main'].map(id=>{
   const r=document.getElementById(id).getBoundingClientRect();return[id,{top:r.top,bottom:r.bottom,left:r.left,width:r.width,height:r.height}];
  })));
  const empty=await bounds();
  assert.equal(empty.side.height,width<=900?108:72);
  assert.equal(empty.main.left,0);assert.equal(empty.main.width,width);
  assert.equal(empty.main.top,empty.side.bottom);assert.ok(empty.main.bottom<=height+1);
  assert.equal(await p.locator('#plist').isVisible(),false);assert.equal(await p.locator('#jobs').isVisible(),false);
  projects=Array.from({length:30},(_,i)=>({name:'fixture_'+i,title:'Fixture project '+i,description:'',built:false}));
  jobs=Array.from({length:30},(_,i)=>({id:'fixture_job_'+i,kind:'check',project:'fixture_'+i,label:'Fixture check '+i,state:'running',seconds:30,tail:[]}));
  await p.evaluate(async()=>{await loadProjects();await pollJobs();});
  await p.locator('#nav_grid').click(); // The mobile Work page uses this existing entry point for the catalog.
  const full=await bounds();
  assert.deepEqual(full,empty); // Adding projects/jobs cannot consume the object stage.
  if(width===390)await p.screenshot({path:CAPTURE+`/stage-${theme}-${width}-${height}.png`,fullPage:true});
  await p.evaluate(()=>{window.select=id=>window.__project=id;window.openJob=id=>window.__job=id;});
  await p.locator('#projecttray>summary').focus();await p.keyboard.press('Enter');
  await p.waitForFunction(()=>document.activeElement.id==='search');
  assert.ok(await p.locator('#plist').evaluate(e=>e.clientHeight>50&&e.scrollHeight>e.clientHeight));
  const lastProject=p.locator('#plist .pitem').last();
  await lastProject.focus();await p.keyboard.press('Enter');
  assert.equal(await p.evaluate(()=>window.__project),'fixture_29');
  assert.ok(await p.locator('#plist').evaluate(e=>e.scrollTop>0));
  await p.keyboard.press('Escape');assert.equal(await p.locator('#projecttray').getAttribute('open'),null);
  assert.equal(await p.evaluate(()=>document.activeElement.parentElement.id),'projecttray');
  await p.locator('#activitytray>summary').click();
  assert.ok(await p.locator('#jobs').evaluate(e=>e.scrollHeight>e.clientHeight));
  const lastJob=p.locator('#joblist .job').last();await lastJob.focus();
  const visible=await lastJob.evaluate(e=>{const r=e.getBoundingClientRect(),s=e.closest('.shell-panel').getBoundingClientRect();return r.top>=s.top-1&&r.bottom<=s.bottom+1&&r.right<=innerWidth;});
  assert.ok(visible);await p.keyboard.press('Space');
  assert.equal(await p.evaluate(()=>window.__job),'fixture_job_29');
  await p.locator('#toolstray>summary').click();
  assert.equal(await p.locator('#activitytray').getAttribute('open'),null);
  for(const control of await p.locator('#toolstray button').all()){
   await control.focus();assert.ok(await control.evaluate(e=>{const r=e.getBoundingClientRect(),s=e.closest('.shell-panel').getBoundingClientRect();return r.top>=s.top-1&&r.bottom<=s.bottom+1&&r.left>=0&&r.right<=innerWidth;}));
  }
  await p.keyboard.press('Escape');
  for(const control of await p.locator('#side button:visible,#side summary:visible').all()){
   await control.focus();assert.ok(await control.evaluate(e=>{const r=e.getBoundingClientRect(),s=document.querySelector('#side').getBoundingClientRect();return r.top>=s.top-1&&r.bottom<=s.bottom+1&&r.left>=0&&r.right<=innerWidth;}));
  }
  // Every visible header hit area remains separate, including the small landscape/320px cases.
  const overlap=await p.locator('#side').evaluate(e=>{const rows=[...e.querySelectorAll('button,summary')].filter(x=>x.getClientRects().length).map(x=>[x.textContent,x.getBoundingClientRect()]);return rows.flatMap(([a,x],i)=>rows.slice(i+1).filter(([b,y])=>Math.min(x.right,y.right)-Math.max(x.left,y.left)>1&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>1).map(([b])=>[a,b]));});
  assert.deepEqual(overlap,[]);
  await p.evaluate(()=>{window.showWork=()=>window.__nav='work';});
  await p.locator('#nav_grid').focus();await p.keyboard.press('Tab');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'nav_parts');
  await p.keyboard.press('Tab');assert.equal(await p.evaluate(()=>document.activeElement.id),'nav_work');
  await p.keyboard.press('Enter');assert.equal(await p.evaluate(()=>window.__nav),'work');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({theme,width,height,emptyHeader:empty.side.height,populatedHeader:full.side.height}));
  await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
