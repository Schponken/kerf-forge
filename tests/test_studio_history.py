"""Saved-build history navigation uses isolated API fixtures: no build, job, or project writes."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_saved_history_story_comparison_restore_and_navigation(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_HISTORY_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "history.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8');
const image=process.env.KERF_HISTORY_IMAGE ? await fs.readFile(process.env.KERF_HISTORY_IMAGE) : null;
const browser=await openBrowser();
try {
for(const theme of ['dark','light']) for(const [width,height] of [[1512,982],[390,844]]) {
 const page=await browser.newPage({viewport:{width,height}}), errors=[], writes=[];
 await page.emulateMedia({reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
 const H=[
  {stamp:'20261102-160000',time:1793653200,fingerprint:'c',ok:false,problems:1,params:{arm_len:120.125,offset:0},requirements:{reach:{ok:true,value:120.125,unit:'mm'},clearance:{ok:false,value:0.4,unit:'mm'},new_check:{ok:true,value:2}},cost:48.25,mass:{device_g:320.25},commit:'abc123',geom:true,thumb:image?'20261102-160000/thumb.png':null},
  {stamp:'20261102-150000',time:1793649600,fingerprint:'b',ok:false,problems:1,params:{arm_len:100.125,offset:0},requirements:{reach:{ok:false,value:100.125,unit:'mm'},clearance:{ok:true,value:1.2,unit:'mm'},old_check:{ok:true,value:3}},cost:45.5,mass:{device_g:300.25},commit:'def456',dirty:true},
  {stamp:'20261102-140000',time:1793646000,fingerprint:'a',ok:null,params:{arm_len:90,retired_param:5},requirements:{},commit:'<script>alert(1)</script>'}
 ];
 let d={name:'fixture',title:'History interaction fixture',description:'Synthetic build records for interface verification. Any supplied picture is a read-only existing model image.',built:true,ok:false,problems:1,stale:true,files:[],docs:[],params:[{key:'arm_len',label:'Arm length',value:130.375,min:60,max:150,unit:'mm'},{key:'offset',label:'Offset',value:0,min:0,max:10}],history:H,modes:[],viewer:null,report:{fingerprint:'c',ok:false,params:{arm_len:120.125,offset:0},requirements:[{id:'reach',ok:true,value:120.125,unit:'mm'},{id:'clearance',ok:false,value:0.4,unit:'mm'}],problems:['Fixture clearance failure'],mass:{device_g:320.25},files:{ship:{bom:{total_usd:48.25}}}},summary_numbers:null};
 let failRestore=false, previewFixture=false, delayRestore=false, pendingRestore, restoreArrived;
 const restoreSeen=new Promise(resolve=>restoreArrived=resolve);
 await page.route('**/*',route=>{
  const req=route.request(),path=new URL(req.url()).pathname;
  if(req.method()==='POST'){
   writes.push([path,req.postDataJSON()]);
   if(path==='/api/restore'){
    if(failRestore)return route.fulfill({status:409,json:{error:'This project has a running job. Wait for it to finish.'}});
    d={...d,params:d.params.map(p=>({...p,value:H.find(h=>h.stamp===req.postDataJSON().stamp).params[p.key]??p.value}))};
    if(delayRestore){pendingRestore=()=>route.fulfill({json:{changed:['arm_len']}});restoreArrived();return;}
    return route.fulfill({json:{changed:['arm_len']}});
   }
   throw Error('Unexpected write: '+path);
  }
  if(path==='/')return route.fulfill({contentType:'text/html',body:html});
  if(path==='/api/projects')return route.fulfill({json:{projects:[d],claude:false}});
  if(path==='/api/project/fixture')return route.fulfill({json:d});
  if(path==='/api/jobs')return route.fulfill({json:{jobs:[],sessions:[]}});
  if(path==='/api/quotes')return route.fulfill({json:{quotes:[]}});
  if(path==='/api/glossary')return route.fulfill({json:{checks:{},terms:{fixture_term:'A fixture-only entry.'}}});
  if(path.endsWith('/thumb.png'))return (image||previewFixture)?route.fulfill({contentType:'image/png',body:image||Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==','base64')}):route.fulfill({status:404});
  if(path.endsWith('.js'))return route.fulfill({contentType:'text/javascript',body:''});
  return route.fulfill({json:{}});
 });
 await page.goto('http://kerf.test/');await page.evaluate(t=>setTheme(t),theme);
 await page.evaluate(async()=>{await select('fixture');setTab('history');});
 const story=page.locator('.history-story');
 await story.waitFor();
 assert.equal(await page.locator('.history-moment').count(),3);
 assert.deepEqual(await page.locator('.history-moment').evaluateAll(es=>es.map(e=>e.id)),H.map(h=>'history-build-'+h.stamp).reverse());
 assert.equal(await page.locator('[aria-pressed=true].history-moment').getAttribute('id'),'history-build-'+H[0].stamp);
 assert.match(await story.innerText(),/1 check now passes/);assert.match(await story.innerText(),/1 check now fails/);
 assert.equal(await story.locator('script').count(),0);
 // Native disclosures are keyboard reachable and preserve exact values rather than rounded restore values.
 await page.locator('#history-params').focus();await page.keyboard.press('Enter');
 assert.match(await page.locator('.history-table').allTextContents().then(x=>x.join(' ')),/100.125.*120.125/s);
 await page.locator('#history-checks').click();
 const checks=await page.locator('.history-table').allTextContents();
 assert.match(checks.join(' '),/new_check.*Not recorded.*Passed/s);
 assert.match(checks.join(' '),/old_check.*Passed.*Not recorded/s);
 await page.evaluate(()=>{S.edits={arm_len:140};renderHistory($('#tabbody'));});
 await page.locator('#history-restore').click();
 assert.match(await story.innerText(),/unsaved Tune edits/);
 assert.match(await story.innerText(),/130.375/);assert.match(await story.innerText(),/120.125/);
 assert.match(await story.innerText(),/Part code and materials stay as they are/);
 await page.locator('#history-restore-button').focus();await page.evaluate(()=>refreshDetail());
 assert.equal(await page.evaluate(()=>document.activeElement.id),'history-restore-button');
 assert.equal(await page.locator('#history-restore').locator('..').getAttribute('open'),'');
 // Cancelling confirmation cannot post or mutate anything.
 page.once('dialog',dialog=>dialog.dismiss());await page.locator('#history-restore-button').click();assert.equal(writes.length,0);
 // A running-job rejection stays a visible error; the restore button is available for recovery.
 failRestore=true;page.once('dialog',dialog=>dialog.accept());await page.locator('#history-restore-button').click();
 await page.waitForFunction(()=>document.querySelector('#toasts').textContent.includes('running job'));
 assert.equal(await page.locator('#history-restore-button').isEnabled(),true);failRestore=false;
 // Older selections compare saved values with the current BUILT report, never current edited parameter values.
 await page.locator('#history-build-'+H[1].stamp).focus();await page.keyboard.press('Space');
 await page.locator('#history-compare').selectOption('current');
 assert.match(await story.innerText(),/current design has newer, unbuilt edits/);
 await page.locator('#history-params').click();
 const paramTable=page.locator('table').filter({has:page.locator('caption',{hasText:'Recorded parameter changes'})});
 assert.match(await paramTable.innerText(),/100.125.*120.125/s);assert.doesNotMatch(await paramTable.innerText(),/130.375/);
 await page.evaluate(()=>refreshDetail());assert.equal(await page.locator('#history-compare').inputValue(),'current');
 assert.equal(await page.locator('[aria-pressed=true].history-moment').getAttribute('id'),'history-build-'+H[1].stamp);
 // The earliest unknown build is not labelled as a pass, and missing measurements are explicit.
 await page.locator('#history-build-'+H[2].stamp).click();await page.locator('#history-compare').selectOption('previous');
 assert.match(await story.innerText(),/Check result not recorded/);assert.match(await story.innerText(),/no earlier snapshot/);
 await page.locator('#history-saved').focus();await page.keyboard.press('Enter');assert.match(await story.innerText(),/retired_param/);
 await page.keyboard.press('Escape');assert.equal(await page.locator('#history-saved').locator('..').getAttribute('open'),null);
 await page.locator('#history-source').click();assert.equal(await story.locator('script').count(),0);
 assert.match(await story.innerText(),/<script>alert\(1\)<\/script>/);
 await page.locator('#history-restore').click();assert.match(await story.innerText(),/no longer in this design/);
 // Returning to the latest build gives a bounded visual capture in both themes and sizes.
 await page.locator('#history-build-'+H[0].stamp).click();
 await page.evaluate(()=>{document.activeElement.blur();$('#toasts').replaceChildren();$('#main').scrollTop=0;});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.screenshot({path:CAPTURE+`/history-${theme}-${width}.png`,fullPage:true});
 await page.locator('#history-checks').click();await page.locator('#history-checks').scrollIntoViewIfNeeded();
 await page.screenshot({path:CAPTURE+`/history-comparison-${theme}-${width}.png`,fullPage:true});
 // The one-pixel PNG is an interaction sentinel, never shown in visual evidence as a design image.
 previewFixture=true;d={...d,history:d.history.map((h,i)=>i? h : {...h,thumb:h.stamp+'/thumb.png'})};await page.evaluate(()=>refreshDetail());
 await page.locator('#history-picture-button').focus();await page.keyboard.press('Enter');
 assert.equal(await page.locator('#history-picture-dialog').evaluate(e=>e.open),true);
 await page.keyboard.press('Escape');assert.equal(await page.locator('#history-picture-dialog').evaluate(e=>e.open),false);
 assert.equal(await page.evaluate(()=>document.activeElement.id),'history-picture-button');
 // Confirming restore posts only the chosen project/stamp to the existing guarded API.
 await page.locator('#history-restore').click();delayRestore=true;page.once('dialog',dialog=>dialog.accept());await page.locator('#history-restore-button').click();
 await restoreSeen;await page.evaluate(()=>setTab('files'));await pendingRestore();
 await page.waitForFunction(()=>S.detail.params.find(p=>p.key==='arm_len').value===120.125);
 assert.equal(await page.evaluate(()=>S.tab),'files');await page.evaluate(()=>setTab('history'));
 await page.waitForFunction(()=>!document.querySelector('#history-restore-button'));
 assert.equal(await page.evaluate(()=>S.edits.arm_len),140);
 assert.deepEqual(writes,[['/api/restore',{project:'fixture',stamp:H[0].stamp}],['/api/restore',{project:'fixture',stamp:H[0].stamp}]]);
 // No history is an honest empty state, with no implied older versions or restore action.
 d={...d,history:[]};await page.evaluate(()=>refreshDetail());assert.match(await page.locator('#tabbody').innerText(),/no saved snapshots/i);
 assert.equal(await page.locator('#history-restore-button').count(),0);
 assert.deepEqual(errors,[]);console.log(JSON.stringify({theme,width,writes:writes.length}));await page.close();
}
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / "tests/browser.mjs")))
       .replace('HTML', json.dumps(str(root / "kerf/assets/studio.html")))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
