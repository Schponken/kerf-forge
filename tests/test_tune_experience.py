"""Tune uses isolated API fixtures: no geometry, model jobs, or project writes."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_tune_drafts_validation_results_and_save_scopes(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_TUNE_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "tune.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
let html=await fs.readFile(__STUDIO_HTML__,'utf8');
if(process.env.KERF_TUNE_SHELL_HTML){
 const local=html;
 html=await fs.readFile(process.env.KERF_TUNE_SHELL_HTML,'utf8');
 // Integration preview uses the frozen shell plus this branch's scoped Tune implementation.
 const tuneStyle=local.slice(local.indexOf('/* Tune:'),local.indexOf('</style>'));
 html=html.replace('</style>',`${tuneStyle}</style>`);
 for(const [from,to,localFrom] of [
  ['function renderTune(el)', 'function plainChecks(ids)', 'function tuneState()'],
  ['function setParam(k, v, live)', '/* ---------- materials per printed part:', 'function updateTuneDraft()'],
  ['function matCard(d)', 'function massRow(d, tr)', 'function matCard(d)']]){
  assert.ok(html.includes(from),`Missing shell insertion: ${from}`);
  html=html.slice(0,html.indexOf(from))+local.slice(local.indexOf(localFrom),local.indexOf(to))+html.slice(html.indexOf(to));
 }
 html=html.replace('[".grid2 .primary", "Try these values:', '[".tune-actions .primary", "Try these values:');
}
const browser=await openBrowser();
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[1440,1000],[390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}),errors=[],posts=[];
  await p.emulateMedia({reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
  const requirement={id:'reach',check:'reach',value:100,unit:'mm',bound:'min',limit:80,ok:true};
  let d={name:'fixture',title:'Inspection arm · fixture',description:'Synthetic browser fixture. An adjustable desk inspection arm.',built:true,ok:true,stale:false,files:[],docs:[],history:[],viewer:null,live_on:false,summary_numbers:{filament_g:100},modes:[],
   report:{ok:true,requirements:[requirement],warnings:[],problems:[]},
   params:[{key:"arm'length",label:'Arm length',value:100,min:60,max:140,step:1,bounded:true,unit:'mm',unit_assumed:false,affects:{parts:['upper_arm','forearm'],checks:['reach'],layout:true}},
    {key:'depth',label:'Housing depth',value:12,min:6,max:18,step:0.1,bounded:false,unit:'mm',unit_assumed:true,affects:{parts:['housing'],checks:[],layout:false}}],
   part_materials:{upper_arm:'PLA'},materials:[{key:'PLA',xy_mpa:40,z_mpa:20,density:1.25,modulus_mpa:3000,usd_per_kg:20},{key:'PETG',xy_mpa:45,z_mpa:25,density:1.27,modulus_mpa:2200,usd_per_kg:24}],
   trial:{ok:true,params:{"arm'length":100,depth:12},materials:{upper_arm:'PLA'},requirements:[requirement],problems:[],mass:{printed_g:100}}};
  let failMaterial=false,slowSave=false;
  await p.route('**/*',async r=>{
   const path=new URL(r.request().url()).pathname;
   if(r.request().method()==='POST'){
    const body=r.request().postDataJSON();posts.push({path,body});
    if(path==='/api/run'){await new Promise(resolve=>setTimeout(resolve,50));return r.fulfill({json:{job:'trial-fixture'}});}
    if(path==='/api/save'){
     if(slowSave)await new Promise(resolve=>setTimeout(resolve,150));
     d.params.forEach(x=>{if(x.key in body.values)x.value=body.values[x.key];});d.stale=true;return r.fulfill({json:{changed:Object.keys(body.values)}});
    }
    if(path==='/api/save-materials'){
     if(failMaterial)return r.fulfill({status:400,json:{error:'Fixture material write failed.'}});
     Object.assign(d.part_materials,body.materials);return r.fulfill({json:{}});
    }
    throw new Error(`Unexpected POST: ${path}`);
   }
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path.endsWith('/viewer.html'))return r.fulfill({contentType:'text/html',body:'<html><body>Recorded model · isolated fixture<script>window.__kerf={setTheme(){},compare(){}};</script></body></html>'});
   if(path==='/api/projects')return r.fulfill({json:{projects:[d],claude:false}});
   if(path==='/api/project/fixture')return r.fulfill({json:d});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/glossary')return r.fulfill({json:{checks:{reach:{name:'Reach',means:'Fixture distance.'}},terms:{fixture_term:'A fixture-only glossary term.'}}});
   if(path.endsWith('.js'))return r.fulfill({contentType:'text/javascript',body:''});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.evaluate(async()=>{await select('fixture');setTab('tune');watch=id=>window.watchedTrial=id;});
  const arm=p.getByRole('textbox',{name:'Arm length',exact:true}),depth=p.getByRole('textbox',{name:'Housing depth',exact:true});
  const save=p.getByRole('button',{name:'Save to design',exact:true}),run=p.getByRole('button',{name:'Try these values',exact:true});
  assert.equal(await save.isDisabled(),true);assert.equal(await run.isDisabled(),true);
  assert.match(await p.locator('#tune-trial-match').innerText(),/Same parameter/);
  await arm.fill('');assert.equal(await arm.getAttribute('aria-invalid'),'true');
  assert.deepEqual(await p.evaluate(()=>S.edits),{});assert.equal(await save.isDisabled(),true);
  assert.match(await p.locator('#tune-param-0-error').innerText(),/from 60 to 140 mm/);
  await arm.fill('110,5');assert.equal(await arm.getAttribute('aria-invalid'),'false');
  assert.equal(await p.evaluate(()=>S.edits["arm'length"]),110.5);assert.equal(await arm.evaluate(e=>e===document.activeElement),true);
  assert.equal(await run.isDisabled(),false);assert.match(await p.locator('.tune-ledger').innerText(),/110.5 mm/);
  assert.match(await p.locator('#tune-trial-match').innerText(),/Different/);
  await arm.fill('141');assert.equal(await arm.getAttribute('aria-invalid'),'true');
  await p.getByLabel('upper arm',{exact:true}).selectOption('PETG');
  assert.equal(await arm.inputValue(),'141');assert.equal(await save.isDisabled(),true);
  await arm.fill('Infinity');assert.equal(await arm.getAttribute('aria-invalid'),'true');
  await arm.fill('NaN');assert.equal(await arm.getAttribute('aria-invalid'),'true');
  await arm.fill('0x64');assert.equal(await arm.getAttribute('aria-invalid'),'true');
  await p.getByRole('button',{name:'Undo Arm length',exact:true}).click();
  assert.equal(await arm.inputValue(),'100');assert.equal(await arm.getAttribute('aria-invalid'),'false');
  assert.equal(await arm.evaluate(e=>e===document.activeElement),true);
  assert.deepEqual(await p.evaluate(()=>S.medits),{upper_arm:'PETG'});
  await p.getByRole('button',{name:'Undo material for upper arm',exact:true}).click();
  assert.deepEqual(await p.evaluate(()=>S.medits),{});
  await depth.fill('22');assert.equal(await depth.getAttribute('aria-invalid'),'false');
  assert.equal(await p.getByRole('slider',{name:'Housing depth slider'}).getAttribute('max'),'22');
  await p.getByRole('button',{name:'Discard changes',exact:true}).click();
  assert.deepEqual(await p.evaluate(()=>[S.edits,S.medits]),[{},{}]);
  const slider=p.getByRole('slider',{name:'Arm length slider'});await slider.focus();await p.keyboard.press('ArrowRight');
  assert.equal(await p.evaluate(()=>S.edits["arm'length"]),101);assert.equal(await slider.evaluate(e=>e===document.activeElement),true);assert.equal(await run.isDisabled(),false);
  await arm.fill('112');await p.getByLabel('upper arm',{exact:true}).selectOption('PETG');
  assert.match(await p.locator('.tune-material-data').innerText(),/Density/);
  assert.match(await p.locator('.tune-limit').innerText(),/does not prove strength/);
  assert.equal(await p.locator('.tune-workbench').evaluate(e=>e.scrollWidth<=e.clientWidth+1),true);
  await p.locator('.tune-intro').scrollIntoViewIfNeeded();
  await p.screenshot({path:`${__CAPTURE_DIR__}/tune-${theme}-${width}-top.png`});
  await p.locator('.tune-controls').scrollIntoViewIfNeeded();
  await p.screenshot({path:`${__CAPTURE_DIR__}/tune-${theme}-${width}-controls.png`});
  await p.locator('.tune-trial-context').scrollIntoViewIfNeeded();
  await p.screenshot({path:`${__CAPTURE_DIR__}/tune-${theme}-${width}-trial.png`});
  await p.evaluate(()=>Promise.all([tryParams(),tryParams()]));
  assert.equal(posts.filter(x=>x.path==='/api/run').length,1);
  assert.deepEqual(posts.find(x=>x.path==='/api/run').body,{project:'fixture',action:'trial',values:{"arm'length":112},materials:{upper_arm:'PETG'}});
  assert.equal(await p.evaluate(()=>window.watchedTrial),'trial-fixture');
  p.on('dialog',dialog=>dialog.accept());failMaterial=true;
  await p.evaluate(()=>saveParams());
  assert.deepEqual(await p.evaluate(()=>S.edits),{});assert.deepEqual(await p.evaluate(()=>S.medits),{upper_arm:'PETG'});
  assert.match(await p.locator('.tune-notice').innerText(),/Some changes were saved/);
  assert.equal(await arm.inputValue(),'112');assert.equal(await save.isDisabled(),false);
  failMaterial=false;await p.evaluate(()=>saveParams());
  assert.equal(posts.filter(x=>x.path==='/api/save').length,1);
  assert.equal(posts.filter(x=>x.path==='/api/save-materials').length,2);
  assert.deepEqual(await p.evaluate(()=>[S.edits,S.medits]),[{},{}]);assert.equal(await save.isDisabled(),true);
  assert.match(await p.locator('.tune-notice').innerText(),/Changes saved/);
  // A response for a previous project cannot clear or write the next project's draft.
  await arm.fill('120');slowSave=true;
  await p.evaluate(()=>{window.pendingSave=saveParams();});
  await p.waitForFunction(()=>tuneState().busy==='save');
  await p.evaluate(()=>{S.sel='other';S.edits={other:8};S.medits={};S.detail={...S.detail,name:'other',params:[{key:'other',label:'Other length',value:4,min:0,max:10,step:1,unit:'mm',bounded:true}],trial:null};renderTab();});
  await p.evaluate(()=>window.pendingSave);
  assert.deepEqual(await p.evaluate(()=>({project:S.sel,edits:S.edits,detail:S.detail.name})),{project:'other',edits:{other:8},detail:'other'});
  assert.equal(posts.filter(x=>x.path==='/api/save').at(-1).body.project,'fixture');
  assert.equal(await p.evaluate(()=>better({bound:'min'},10,12)),1);assert.equal(await p.evaluate(()=>better({bound:'max'},10,12)),-1);
  assert.deepEqual(errors,[]);await p.close();
 }
} finally {await browser.close();}
'''.replace('BROWSER_HELPER',(root/'tests/browser.mjs').as_uri()).replace('__STUDIO_HTML__',json.dumps(str(root/'kerf/assets/studio.html'))).replace('__CAPTURE_DIR__',json.dumps(str(capture))),encoding='utf-8')
    result=subprocess.run(['node',str(script)],cwd=root,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
