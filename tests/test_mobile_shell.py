"""Content-sized phone sidebar, contained long lists and reachable controls on short screens."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_mobile_sidebar_content_size_scroll_access_and_desktop_geometry(tmp_path):
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
  const bounds=()=>p.evaluate(()=>Object.fromEntries(['side','plist','jobs','main'].map(id=>{
   const e=document.getElementById(id),r=e.getBoundingClientRect();
   return[id,{top:r.top,bottom:r.bottom,left:r.left,width:r.width,height:r.height,scroll:e.scrollHeight,client:e.clientHeight}];
  })));
  const empty=await bounds();
  if(width<=900) {
   assert.ok(empty.side.height<=height*.44+1,JSON.stringify(empty));
   assert.ok(Math.abs(empty.main.top-empty.side.bottom)<1,JSON.stringify(empty));
   assert.ok(empty.main.bottom<=height+1,JSON.stringify(empty));
   if(width===390) {
    assert.ok(empty.plist.height<=60,JSON.stringify(empty));
    assert.ok(empty.main.top<height*.44-100,JSON.stringify(empty));
    await p.screenshot({path:CAPTURE+`/work-${theme}-${width}-${height}.png`,fullPage:true});
   }
  } else {
   assert.equal(empty.side.width,292);assert.equal(empty.side.height,height);
   assert.equal(empty.main.left,292);assert.equal(empty.main.top,0);assert.equal(empty.main.height,height);
  }
  projects=Array.from({length:30},(_,i)=>({name:'fixture_'+i,title:'Fixture project '+i,description:'',built:false}));
  jobs=Array.from({length:30},(_,i)=>({id:'fixture_job_'+i,kind:'check',project:'fixture_'+i,label:'Fixture check '+i,state:'running',seconds:30,tail:[]}));
  await p.evaluate(async()=>{await loadProjects();await pollJobs();});
  await p.locator('#nav_grid').click(); // The mobile Work page uses this existing entry point for the catalog.
  const full=await bounds();
  assert.ok(full.plist.client>=50 && full.plist.scroll>full.plist.client,JSON.stringify(full));
  assert.ok(full.jobs.scroll>full.jobs.client,JSON.stringify(full));
  if(width<=900) {
   assert.ok(full.side.height<=height*.44+1,JSON.stringify(full));
   assert.ok(full.jobs.height<=80,JSON.stringify(full));
   assert.ok(Math.abs(full.main.top-full.side.bottom)<1,JSON.stringify(full));
   assert.equal(await p.locator('#side').evaluate(e=>getComputedStyle(e).overflowY),'auto');
   if(height<600) assert.ok(full.side.scroll>full.side.client,JSON.stringify(full));
  } else {
   assert.equal(full.side.width,empty.side.width);assert.equal(full.side.height,empty.side.height);
   assert.equal(full.main.left,empty.main.left);assert.equal(full.main.top,empty.main.top);
  }
  if(width===390) await p.screenshot({path:CAPTURE+`/catalog-populated-${theme}-${width}-${height}.png`,fullPage:true});
  // Reach the last project/job through their own scroll panes and the short-screen outer fallback.
  await p.evaluate(()=>{window.select=id=>window.__project=id;window.openJob=id=>window.__job=id;});
  const lastProject=p.locator('#plist .pitem').last(),lastJob=p.locator('#joblist .job').last();
  await lastProject.scrollIntoViewIfNeeded();await lastProject.click();
  assert.equal(await p.evaluate(()=>window.__project),'fixture_29');
  await lastJob.scrollIntoViewIfNeeded();await lastJob.click();
  assert.equal(await p.evaluate(()=>window.__job),'fixture_job_29');
  assert.ok(await p.locator('#plist').evaluate(e=>e.scrollTop>0));
  assert.ok(await p.locator('#jobs').evaluate(e=>e.scrollTop>0));
  if(width<=900 && height<600) assert.ok(await p.locator('#side').evaluate(e=>e.scrollTop>0));
  // Native focus scrolling must expose every header, navigation and Activity button, not clip it.
  for(const control of await p.locator('#side button:visible').all()) {
   await control.focus();
   const visible=await control.evaluate(e=>{const r=e.getBoundingClientRect(),s=document.querySelector('#side').getBoundingClientRect();
    return r.top>=s.top-1 && r.bottom<=s.bottom+1 && r.left>=0 && r.right<=innerWidth+1;});
   assert.ok(visible,await control.innerText());
  }
  await p.evaluate(()=>{window.showWork=()=>window.__nav='work';});
  await p.locator('#nav_grid').focus();await p.keyboard.press('Tab');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'nav_parts');
  await p.keyboard.press('Tab');assert.equal(await p.evaluate(()=>document.activeElement.id),'nav_work');
  await p.keyboard.press('Enter');assert.equal(await p.evaluate(()=>window.__nav),'work');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({theme,width,height,emptySidebar:empty.side.height,populatedSidebar:full.side.height}));
  await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
