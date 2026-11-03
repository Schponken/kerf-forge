"""Project navigation and layout use mocked APIs; no build, agent, or geometry work."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_project_workspace_description_tabs_context_and_viewport(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_WORKSPACE_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "project-workspace.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8');
const saved=process.env.KERF_WORKSPACE_SAVED_VIEWER ? await fs.readFile(process.env.KERF_WORKSPACE_SAVED_VIEWER,'utf8') : null;
const savedContext=process.env.KERF_WORKSPACE_SAVED_CONTEXT ? JSON.parse(await fs.readFile(process.env.KERF_WORKSPACE_SAVED_CONTEXT,'utf8')) : null;
const viewer='<html><body><button>Fit model</button><p>Isolated viewer layout fixture</p><script>window.__kerf={setTheme(){}};</script></body></html>';
const browser=await openBrowser();
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[1512,982],[390,844],[844,390]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[], requests=[];
  await p.emulateMedia({reducedMotion:'reduce'});
  p.on('pageerror',e=>errors.push(e.message));
  let d={name:'fixture',title:'Folding inspection arm',description:'A compact inspection arm for reaching behind a desk. '+('This fixture describes mounting, access, cable routing and assembly tradeoffs. '.repeat(8))+'<img src=x onerror=alert(1)>',built:true,ok:false,problems:2,stale:false,review:null,files:[],docs:[],params:[],history:[],modes:[{mode:'kit',label:'Build kit',gives:'Checks and files',cost:'No agent usage'}],viewer:'out/viewer.html',live_on:false,report:{ok:false,problems:['Fixture clearance problem','Fixture fastener problem'],requirements:[],warnings:[]},summary_numbers:{cost_usd:48,packs_usd:61,unpriced:1,device_g:320,print_s:7200,print_sliced:false,plates:2},picture:'/fixture.png'};
  d.can_optimise=true;d.last_mode='check';
  let viewingSaved=false;
  await p.route('**/*',r=>{
   const path=new URL(r.request().url()).pathname;requests.push([r.request().method(),path]);
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path.endsWith('/viewer.html'))return r.fulfill({contentType:'text/html',body:viewingSaved?saved:viewer});
   if(path==='/api/projects')return r.fulfill({json:{projects:[d],claude:false}});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/glossary')return r.fulfill({json:{checks:{},terms:{fixture_term:'A fixture-only glossary entry.'}}});
   if(path==='/api/project/fixture')return r.fulfill({json:d});
   if(path.endsWith('.js'))return r.fulfill({contentType:'text/javascript',body:''});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.evaluate(()=>select('fixture'));await p.locator('#mainviewer').waitFor();
  if(width>900)await p.waitForFunction(()=>$('#mainviewer').getBoundingClientRect().bottom>=innerHeight-25);
  const geometry=()=>p.evaluate(()=>Object.fromEntries(['main','tabs','tabbody','mainviewer'].map(id=>{
   const e=document.getElementById(id),r=e.getBoundingClientRect();return[id,{top:r.top,bottom:r.bottom,height:r.height,left:r.left,right:r.right,scroll:e.scrollHeight,client:e.clientHeight}];
  })));
  const initial=await geometry();
  assert.equal(initial.tabs.scroll,initial.tabs.client,JSON.stringify(initial));
  assert.ok(initial.mainviewer.height>=360,JSON.stringify(initial));
  if(width>900) {assert.ok(initial.mainviewer.bottom>=height-25 && initial.mainviewer.bottom<=height-20,JSON.stringify(initial));assert.ok(initial.main.scroll<=initial.main.client+1,JSON.stringify(initial));}
  assert.equal(await p.locator('#project-description img').count(),0);
  assert.equal(await p.evaluate(()=>document.querySelector(TOUR.head[1][0]).id),'project-build');
  assert.equal(await p.getByRole('group',{name:'Build and options'}).getByRole('button').count(),2);
  assert.equal(await p.locator('.actions > button,.actions > .more,.actions > .project-build-group').count(),4);
  const details=p.locator('#project-build-details'),summary=p.locator('#project-build-summary');
  assert.equal(await details.getAttribute('open'),null);
  await summary.focus();await p.keyboard.press('Enter');
  assert.equal(await details.getAttribute('open'),'');assert.match(await p.locator('.facts').innerText(),/320 g/);
  await p.evaluate(()=>refreshDetail());assert.equal(await details.getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'project-build-summary');
  assert.equal(await p.locator('.project-context').evaluate(e=>getComputedStyle(e).animationName),'none');
  await p.keyboard.press('Escape');assert.equal(await details.getAttribute('open'),null);
  await summary.click();await p.locator('.titlerow h1').click();assert.equal(await details.getAttribute('open'),null);
  const brief=p.locator('#project-brief-toggle');await brief.focus();await p.keyboard.press('Enter');
  assert.equal(await brief.getAttribute('aria-expanded'),'true');
  assert.equal(await p.locator('#project-description').evaluate(e=>e.scrollHeight<=e.clientHeight),true);
  await p.evaluate(()=>refreshDetail());
  assert.equal(await brief.getAttribute('aria-expanded'),'true');assert.equal(await p.evaluate(()=>document.activeElement.id),'project-brief-toggle');
  await p.keyboard.press('Space');assert.equal(await brief.getAttribute('aria-expanded'),'false');
  // Arrow/Home/End selection, one tab stop, accessible panel association, and no vertical tab scroll.
  await p.locator('#project-tab-model').focus();await p.keyboard.press('ArrowRight');
  assert.equal(await p.evaluate(()=>S.tab),'tune');assert.equal(await p.locator('[role=tab][tabindex="0"]').count(),1);
  assert.equal(await p.locator('#tabbody').getAttribute('aria-labelledby'),'project-tab-tune');
  await p.keyboard.press('End');assert.equal(await p.evaluate(()=>S.tab),'history');
  const tabScroll=await p.locator('#tabs').evaluate(e=>e.scrollLeft);
  await p.evaluate(()=>refreshDetail());
  assert.equal(await p.evaluate(()=>document.activeElement.id),'project-tab-history');
  assert.equal(await p.locator('#tabs').evaluate(e=>e.scrollLeft),tabScroll);
  await p.keyboard.press('Home');assert.equal(await p.evaluate(()=>S.tab),'model');
  await p.evaluate(()=>refreshDetail());assert.equal(await p.evaluate(()=>document.activeElement.id),'project-tab-model');
  await p.getByRole('button',{name:'Review checks',exact:true}).click();
  assert.equal(await p.evaluate(()=>S.tab),'results');assert.match(await p.locator('#tabbody').innerText(),/Fixture clearance problem/);
  // Explicit historical context cannot present an old pass as readiness of the changed design.
  d={...d,ok:true,stale:true,report:{...d.report,ok:true,problems:[]}};
  await p.evaluate(()=>refreshDetail());
  await summary.click();
  assert.match(await p.locator('.project-context').innerText(),/earlier version/);
  assert.match(await p.locator('#tabbody').innerText(),/previous build/i);
  assert.doesNotMatch(await p.locator('#tabbody').innerText(),/Ready to print/);
  assert.equal(await p.getByRole('button',{name:'Review last build’s checks'}).count(),1);
  d={...d,stale:false};await p.evaluate(()=>refreshDetail());
  assert.match(await p.locator('.project-context').innerText(),/current design review is still missing/);
  assert.match(await p.locator('#cert').innerText(),/Build check summary/);
  assert.match(await p.locator('#cert').innerText(),/not done yet/);
  assert.doesNotMatch(await p.locator('#tabbody').innerText(),/Ready to print/);
  d={...d,review:{ok:true}};await p.evaluate(()=>refreshDetail());
  assert.match(await p.locator('.titlerow').innerText(),/Checks and review current/);
  d={...d,running:['Build kit']};await p.evaluate(()=>refreshDetail());
  assert.match(await p.locator('.project-context').innerText(),/still running/);
  d={...d,running:[],built:false,viewer:null,report:null,description:'A short description.'};
  await p.evaluate(()=>{S.tab='model';S.briefOpen=null;return refreshDetail()});
  assert.equal(await brief.isVisible(),false);assert.match(await p.locator('.project-context').innerText(),/Build this design/);
  await p.getByRole('button',{name:'Close',exact:true}).click();
  // Existing action dispatch is preserved without starting any process.
  await p.evaluate(()=>{window.runMode=m=>window.__mode=m;window.openEdit=()=>window.__edit=true;window.run=a=>window.__action=a;});
  await p.getByRole('button',{name:'Build kit',exact:true}).first().click();assert.equal(await p.evaluate(()=>window.__mode),'kit');
  await p.getByRole('button',{name:'Change something',exact:true}).click();assert.equal(await p.evaluate(()=>window.__edit),true);
  await p.getByRole('button',{name:'Depth',exact:false}).click();assert.equal(await p.locator('#modemenu').isVisible(),true);
  await p.locator('#modemenu button').first().focus();await p.keyboard.press('Enter');assert.equal(await p.evaluate(()=>window.__mode),'kit');
  await p.getByRole('button',{name:'More',exact:false}).click();
  await p.locator('#moremenu').getByRole('button',{name:'Optimise',exact:false}).click();assert.equal(await p.evaluate(()=>window.__action),'optimise');
  await p.getByRole('button',{name:'More',exact:false}).click();
  await p.locator('#moremenu').getByRole('button',{name:'Upgrade to Build kit',exact:false}).click();assert.equal(await p.evaluate(()=>window.__mode),'kit');
  // Long titles/briefs and portrait/short-landscape screens keep navigation and model controls reachable.
  d={...d,built:true,ok:false,problems:2,review:null,report:{ok:false,problems:['Fixture problem'],requirements:[],warnings:[]},viewer:'out/viewer.html',title:'Long_unbroken_project_name_'.repeat(5),description:'Long_unbroken_description_'.repeat(15)};
  await p.evaluate(()=>refreshDetail());
  for(const id of ['project-brief-toggle','project-tab-history']){await p.locator('#'+id).focus();assert.equal(await p.evaluate(()=>document.activeElement.id),id);}
  await p.locator('#mainviewer').scrollIntoViewIfNeeded();
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await p.locator('#tabs').evaluate(e=>e.scrollHeight===e.clientHeight),true);
  assert.ok((await geometry()).mainviewer.height>=360);
  assert.equal(await p.locator('#mainviewer').getAttribute('title'),'3D model of '+d.title);
  // Optional visual evidence uses a read-only saved viewer, retaining its actual report and explicit fixture label.
  if(saved){
   const data=JSON.parse(saved.split('id="kerf-data">')[1].split('</script>')[0]);
   d={...d,title:data.report.project,description:savedContext?.description || 'Saved model in a mocked Studio workspace. No build or live project changes were made for this layout preview.',report:data.report,ok:data.report.ok,problems:data.report.problems.length,summary_numbers:savedContext?.summary_numbers || d.summary_numbers,review:null};viewingSaved=true;
  }else d={...d,title:'Folding inspection arm',description:'Workspace fixture: inspect the model, read its checks, then prepare the files.'};
  await p.evaluate(()=>{S.tab='model';return refreshDetail()});
  if(saved)await p.frameLocator('#mainviewer').locator('canvas').waitFor();
  await p.evaluate(()=>{closeBuildDetails();document.activeElement.blur();$('#tabs').scrollLeft=0;$('#main').scrollTop=0;});
  await p.waitForFunction(()=>$('#main').scrollTop===0 && $('.titlerow h1').getBoundingClientRect().top >= $('#main').getBoundingClientRect().top);
  await p.screenshot({path:CAPTURE+`/project-${theme}-${width}.png`,fullPage:true});
  await summary.click();
  const popover=await p.locator('.project-context').boundingBox();assert.ok(popover.x>=0 && popover.x+popover.width<=width,JSON.stringify(popover));
  await p.screenshot({path:CAPTURE+`/project-details-${theme}-${width}.png`,fullPage:true});
  await p.getByRole('button',{name:'Close',exact:true}).click();assert.equal(await p.evaluate(()=>document.activeElement.id),'project-build-summary');
  if(width<=900){await p.locator('#mainviewer').scrollIntoViewIfNeeded();await p.screenshot({path:CAPTURE+`/project-model-${theme}-${width}.png`,fullPage:true});}
  assert.deepEqual(errors,[]);assert.ok(requests.every(([method])=>method==='GET'),JSON.stringify(requests.filter(([method])=>method!=='GET')));
  console.log(JSON.stringify({theme,width,height,initial}));await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / "tests/browser.mjs")))
       .replace('HTML', json.dumps(str(root / "kerf/assets/studio.html")))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
