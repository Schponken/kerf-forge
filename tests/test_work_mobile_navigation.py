"""Mobile Work uses existing project navigation while keeping Activity and utility controls reachable."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_populated_mobile_work_navigation_restores_catalog_on_other_pages_and_resize(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_WORK_NAV_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "work-mobile-navigation.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(STUDIO_HTML_PATH,'utf8');
const browser=await openBrowser();
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[390,844],[390,1000],[320,568],[844,390]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  await p.emulateMedia({reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
  let projects=[],jobs=[],quotes=[];
  await p.route('**/*',route=>{const path=new URL(route.request().url()).pathname;
   if(path==='/') return route.fulfill({contentType:'text/html',body:html});
   if(path==='/api/projects') return route.fulfill({json:{projects,claude:false}});
   if(path==='/api/jobs') return route.fulfill({json:{jobs,sessions:[]}});
   if(path==='/api/quotes') return route.fulfill({json:{quotes}});
   if(path==='/api/claude') return route.fulfill({json:{ok:true,why:'Test fixture'}});
   if(path.startsWith('/api/project/')) {const name=path.split('/').pop();return route.fulfill({json:{name,title:'Fixture project 29',description:'Synthetic project',built:false,files:[],params:[],history:[],modes:[],live_on:false}});}
   if(path==='/api/work') return route.fulfill({json:{items:[{id:'fixture-task',provider:'Codex',state:'running',title:'Check the mounting bracket',activity:'Checking the bolt clearances before preparing the pull request.',remaining:['Review the result','Publish the pull request'],updated_at:Date.now()/1000}],sources:[]}});
   return route.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();await p.locator('.work-item').waitFor();
  projects=Array.from({length:30},(_,i)=>({name:'fixture_'+i,title:'Fixture project '+i,description:'',built:false}));
  jobs=Array.from({length:30},(_,i)=>({id:'fixture_job_'+i,kind:'check',project:'fixture_'+i,label:'Fixture check '+i,state:'running',seconds:30,tail:[]}));
  await p.evaluate(async()=>{await loadProjects();await pollJobs();});
  assert.equal(await p.locator('#search').isVisible(),false);
  assert.equal(await p.locator('#plist').isVisible(),false);
  assert.equal(await p.locator('#joblist .job').count(),30);
  assert.equal(await p.locator('#nav_grid').isVisible(),true);
  const side=await p.locator('#side').boundingBox(),main=await p.locator('#main').boundingBox();
  assert.ok(side.height<=height*.44+1,JSON.stringify(side));
  assert.ok(Math.abs(main.y-side.height)<1,JSON.stringify({side,main}));
  if(width===390) {
   assert.ok(side.height<=240,JSON.stringify(side));
   assert.ok(side.height<height*.44-140,JSON.stringify(side));
   assert.ok((await p.locator('.work-item').boundingBox()).y<height);
   await p.screenshot({path:CAPTURE+`/work-populated-${theme}-${width}-${height}.png`,fullPage:true});
  }
  // CSS responds to viewport changes without navigation or new route state.
  await p.setViewportSize({width:1440,height:900});
  await p.waitForFunction(()=>document.querySelector('#side').getBoundingClientRect().width===292);
  assert.equal(await p.locator('#plist').isVisible(),true);assert.equal(await p.locator('#search').isVisible(),true);
  assert.equal((await p.locator('#side').boundingBox()).width,292);
  assert.equal(await p.locator('.work-item').count(),1);
  await p.setViewportSize({width,height});
  await p.waitForFunction(w=>document.querySelector('#side').getBoundingClientRect().width===w,width);
  assert.equal(await p.locator('#plist').isVisible(),false);assert.equal(await p.locator('#search').isVisible(),false);
  // Existing All projects is keyboard-accessible and restores the full catalog and its search.
  await p.locator('#nav_grid').focus();await p.keyboard.press('Enter');
  assert.equal(await p.locator('#main h1').innerText(),'All projects');
  assert.equal(await p.locator('#plist').isVisible(),true);assert.equal(await p.locator('#search').isVisible(),true);
  assert.equal(await p.locator('.pcard').count(),30);
  await p.locator('#search').fill('Fixture project 29');
  assert.equal(await p.locator('#plist .pitem').count(),1);
  await p.locator('#plist .pitem').click();
  await p.waitForFunction(()=>S.detail?.name==='fixture_29');
  assert.equal(await p.locator('#main h1').innerText(),'Fixture project 29');
  assert.equal(await p.locator('#plist').isVisible(),true);assert.equal(await p.locator('#search').isVisible(),true);
  // Project content mentioning this class is not a top-level Work page.
  await p.locator('#tabbody').evaluate(e=>e.insertAdjacentHTML('beforeend','<div class="work-page">Example in project content</div>'));
  assert.equal(await p.locator('#plist').isVisible(),true);
  await p.locator('#nav_work').click();await p.locator('.work-item').waitFor();
  assert.equal(await p.locator('#plist').isVisible(),false);
  await p.waitForFunction(()=>!S.workLoading); // Navigation-race behavior is covered by the separate Work navigation fix.
  await p.locator('#newbtn').click();
  assert.equal(await p.locator('#main h1').innerText(),'New design');
  assert.equal(await p.locator('#plist').isVisible(),true);assert.equal(await p.locator('#search').isVisible(),true);
  await p.locator('#nav_work').click();await p.locator('.work-item').waitFor();
  // Options ready, global navigation, help, printer and notification controls are not hidden with the catalog.
  quotes=[{name:'fixture_options',options:2,description:'Synthetic saved options'}];
  await p.evaluate(()=>pollQuotes());
  assert.equal(await p.locator('#qbadge').isVisible(),true);
  for(const selector of ['#newbtn','#nav_grid','#nav_parts','#nav_work','#qbadge','#helpbtn','#themebtn','#printerbtn','#bellbtn']) {
   const control=p.locator(selector);assert.equal(await control.isVisible(),true);await control.focus();
   assert.ok(await control.evaluate(e=>{const r=e.getBoundingClientRect(),s=document.querySelector('#side').getBoundingClientRect();return r.top>=s.top-1 && r.bottom<=s.bottom+1;}),selector);
  }
  const lastJob=p.locator('#joblist .job').last();
  await p.evaluate(()=>{window.openJob=id=>window.__job=id;});
  await lastJob.scrollIntoViewIfNeeded();await lastJob.click();
  assert.equal(await p.evaluate(()=>window.__job),'fixture_job_29');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({theme,width,height,workSidebar:side.height,workContentTop:main.y}));
  await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('STUDIO_HTML_PATH', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
