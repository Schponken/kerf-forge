"""Delayed/failing mocked requests must not move people away from their current task."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_navigation_keeps_current_screen_and_recovers_failed_loading(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_JOURNEY_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "journey-quality.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8');
const browser=await openBrowser();
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[1512,982],[390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[], requests=[], held=new Map();
  await p.emulateMedia({reducedMotion:'reduce'});
  await p.addInitScript(()=>{window.setInterval=()=>0;localStorage.setItem('kerf-tour','1');});
  p.on('pageerror',e=>errors.push(e.message));
  let d={name:'fixture',title:'Folding inspection arm',description:'Isolated navigation fixture.',built:false,ok:false,problems:0,review:null,files:[],docs:['out/ASSEMBLY.md','DESIGN.md'],params:[],history:[],modes:[],report:null};
  let projects=[d],inventoryFailure=false,guideFailure=false;
  const hold=path=>{
   let receive;const request=new Promise(resolve=>receive=resolve);held.set(path,receive);
   return {request,reply:async response=>(await request).fulfill(response)};
  };
  await p.route('**/*',r=>{
   const path=new URL(r.request().url()).pathname;requests.push([r.request().method(),path]);
   if(held.has(path)){const receive=held.get(path);held.delete(path);receive(r);return;}
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path==='/api/projects')return r.fulfill({json:{projects,claude:false}});
   if(path==='/api/project/fixture')return r.fulfill({json:d});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/work')return r.fulfill({json:{items:[],warnings:[],sources:[],plan:{done:0,total:0},commits:[]}});
   if(path==='/api/inventory')return r.fulfill(inventoryFailure?{status:503,json:{error:'Inventory unavailable'}}:{json:{items:{},keys:[]}});
   if(path.startsWith('/files/fixture/'))return r.fulfill(guideFailure?{status:503,body:'server error'}:{contentType:'text/plain',body:path.endsWith('DESIGN.md')?'Current design guide':'Assembly guide loaded'});
   if(path.endsWith('.js'))return r.fulfill({contentType:'text/javascript',body:''});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.locator('.project-workspace').waitFor();
  await p.evaluate(t=>setTheme(t),theme);
  // A rejected Tune entry is still a draft, even when it has no valid value yet.
  await p.evaluate(()=>{S.tune={edits:S.edits,invalid:{length:{raw:'',message:'Enter a value'}}};S.tab='tune'});
  await p.evaluate(()=>select('fixture'));
  assert.equal(await p.evaluate(()=>S.tab),'tune');
  let prompt='';p.once('dialog',dialog=>{prompt=dialog.message();return dialog.dismiss()});
  await p.evaluate(()=>select('other'));
  assert.match(prompt,/1 unsaved Tune change/);assert.equal(await p.evaluate(()=>S.sel),'fixture');
  // Every global exit asks before changing route state. Blank/whitespace and zero are drafts.
  await p.evaluate(()=>{S.edits={length:0};S.tune={edits:S.edits,invalid:{length:{raw:'   ',message:'Enter a value'}}}});
  assert.equal(await p.evaluate(()=>tuneDraftCount()),1);
  for(const navigate of ['showGrid','showNew','showParts','showWork','openQuotesPage']){
   const before=await p.evaluate(()=>JSON.stringify({sel:S.sel,tab:S.tab,ticket:S.ticket,grid:S.grid,work:S.work,parts:S.parts,newOpen:S.newOpen,edits:S.edits,invalid:S.tune.invalid}));
   prompt='';p.once('dialog',dialog=>{prompt=dialog.message();return dialog.dismiss()});
   await p.evaluate(name=>window[name](),navigate);
   assert.match(prompt,/1 unsaved Tune change/,navigate);
   assert.equal(await p.evaluate(()=>JSON.stringify({sel:S.sel,tab:S.tab,ticket:S.ticket,grid:S.grid,work:S.work,parts:S.parts,newOpen:S.newOpen,edits:S.edits,invalid:S.tune.invalid})),before,navigate);
  }
  p.once('dialog',dialog=>dialog.dismiss());await p.evaluate(()=>openSession('other'));
  assert.equal(await p.evaluate(()=>S.tab),'tune');
  p.once('dialog',dialog=>dialog.accept());await p.locator('#nav_grid').click();
  assert.equal(await p.locator('#main h1').innerText(),'All projects');assert.equal(await p.evaluate(()=>tuneDraftCount()),0);
  await p.evaluate(()=>select('fixture'));
  // A pending project load, including its failure, cannot replace All projects.
  for(const failure of [false,true]){
   const pending=hold('/api/project/fixture');
   await p.evaluate(()=>{window.__pending=select('fixture')});await pending.request;
   await p.locator('#nav_grid').click();
   await pending.reply(failure?{status:503,json:{error:'Project unavailable'}}:{json:d});
   await p.evaluate(()=>window.__pending);
   assert.equal(await p.locator('#main h1').innerText(),'All projects');
  }
  // Reopening the same project starts a new visit; an old refresh is no longer current.
  await p.evaluate(()=>select('fixture'));
  const refresh=hold('/api/project/fixture'),old={...d,title:'Obsolete project response'};
  await p.evaluate(()=>{window.__refresh=refreshDetail()});await refresh.request;
  await p.locator('#nav_grid').click();await p.evaluate(()=>select('fixture'));
  await refresh.reply({json:old});await p.evaluate(()=>window.__refresh);
  assert.equal(await p.locator('#main h1').innerText(),d.title);
  // Loading inventory gives immediate feedback and late replies cannot steal another screen.
  for(const failure of [false,true]){
   const pending=hold('/api/inventory');
   await p.evaluate(()=>{window.__parts=showParts()});await pending.request;
   assert.equal(await p.getByRole('status').innerText(),'Loading your parts…');
   await p.locator('#nav_grid').click();
   await pending.reply(failure?{status:503,json:{error:'Inventory unavailable'}}:{json:{items:{},keys:[]}});
   await p.evaluate(()=>window.__parts);
   assert.equal(await p.locator('#main h1').innerText(),'All projects');
  }
  inventoryFailure=true;await p.locator('#nav_parts').click();
  await p.getByRole('alert').waitFor();assert.match(await p.getByRole('alert').innerText(),/Couldn’t load your parts/);
  const retry=p.getByRole('button',{name:'Try again',exact:true});
  await retry.focus();assert.equal(await retry.evaluate(e=>e===document.activeElement),true);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await p.screenshot({path:CAPTURE+`/inventory-retry-${theme}-${width}.png`,fullPage:true});
  inventoryFailure=false;await p.keyboard.press('Enter');await p.getByRole('heading',{name:'My parts',exact:true}).waitFor();
  const saving=hold('/api/inventory');
  await p.evaluate(()=>{window.__saving=saveParts()});await saving.request;
  await p.locator('#nav_grid').click();await saving.reply({json:{items:{}}});await p.evaluate(()=>window.__saving);
  assert.equal(await p.locator('#main h1').innerText(),'All projects');
  // Empty-list polling must preserve explicitly opened Work and All projects screens.
  projects=[];await p.locator('#nav_work').click();await p.evaluate(()=>loadProjects());
  assert.equal(await p.locator('#main h1').innerText(),'Work');
  await p.locator('#nav_grid').click();await p.evaluate(()=>loadProjects());
  assert.equal(await p.locator('#main h1').innerText(),'All projects');
  projects=[d];await p.evaluate(()=>loadProjects());await p.evaluate(()=>select('fixture'));
  // The later guide selection wins even when an earlier response arrives last.
  const older=hold('/files/fixture/out/ASSEMBLY.md');
  await p.evaluate(()=>{S.doc='out/ASSEMBLY.md';setTab('docs')});await older.request;
  assert.equal(await p.getByRole('status').innerText(),'Loading guide…');
  await p.locator('.docnav').getByRole('button',{name:'Design',exact:true}).click();
  await p.waitForFunction(()=>$('#docbody').textContent.includes('Current design guide'));
  await older.reply({contentType:'text/plain',body:'Obsolete assembly guide'});
  await p.waitForLoadState('networkidle');
  assert.equal(await p.locator('#docbody').innerText(),'Current design guide');
  assert.equal(await p.locator('.docnav [aria-pressed="true"]').innerText(),'Design');
  // An HTTP failure is a recoverable state, never rendered as guide content.
  guideFailure=true;await p.locator('.docnav').getByRole('button',{name:'Assembly guide',exact:true}).click();
  await p.getByRole('alert').waitFor();assert.match(await p.locator('#docbody').innerText(),/Couldn’t load this guide/);
  assert.doesNotMatch(await p.locator('#docbody').innerText(),/server error/);
  assert.equal(await p.locator('.docnav').getByRole('button',{name:'← Files & guides'}).isVisible(),true);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await p.screenshot({path:CAPTURE+`/guide-retry-${theme}-${width}.png`,fullPage:true});
  guideFailure=false;await p.getByRole('button',{name:'Try again',exact:true}).focus();await p.keyboard.press('Enter');
  await p.waitForFunction(()=>$('#docbody').textContent.includes('Assembly guide loaded'));
  // A guide that completes after leaving Files cannot fill a different project's page.
  const departed=hold('/files/fixture/DESIGN.md');
  await p.locator('.docnav').getByRole('button',{name:'Design',exact:true}).click();await departed.request;
  await p.locator('#nav_grid').click();await departed.reply({status:503,body:'server error'});
  await p.waitForLoadState('networkidle');assert.equal(await p.locator('#main h1').innerText(),'All projects');
  assert.deepEqual(errors,[]);assert.deepEqual(requests.filter(([method])=>method!=='GET'),[['POST','/api/inventory']]);
  console.log(JSON.stringify({theme,width,journeys:'project, refresh, inventory, empty polling, guides'}));await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / "tests/browser.mjs")))
       .replace('HTML', json.dumps(str(root / "kerf/assets/studio.html")))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
