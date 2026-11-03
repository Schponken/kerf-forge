"""Follow live stays readable and operable; synthetic pages never start real live work."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_follow_live_label_status_and_errors_fit_and_toggle(tmp_path):
    root = Path(__file__).resolve().parents[1]
    captures = Path(os.environ.get("KERF_FOLLOW_SCREENSHOTS", str(tmp_path)))
    captures.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "follow-layout.mjs"
    script.write_text(r'''
import {chromium} from PLAYWRIGHT_PATH;
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(STUDIO_HTML_PATH,'utf8'),browser=await chromium.launch();
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[1440,900],[1024,768],[390,844],[320,568]]) {
  const p=await browser.newPage({viewport:{width,height}}),calls=[],errors=[];
  p.on('pageerror',e=>errors.push(e.message));await p.emulateMedia({reducedMotion:'reduce'});
  await p.route('**/*',r=>{const path=new URL(r.request().url()).pathname;
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path==='/api/live/follow'){const body=r.request().postDataJSON();calls.push(body);return r.fulfill({json:{on:body.on}});}
   if(path.endsWith('viewer.html'))return r.fulfill({contentType:'text/html',body:'<body style="background:#20262a;color:white;font:14px system-ui;padding:16px">Synthetic viewer fixture — no geometry</body>'});
   return r.fulfill({json:path==='/api/projects'?{projects:[],claude:false}:path==='/api/jobs'?{jobs:[],sessions:[]}:path==='/api/quotes'?{quotes:[]}:{}});
  });
  await p.goto('http://kerf.test/');
  await p.evaluate(t=>{
   setTheme(t);S.detail={name:'fixture',title:'Follow live layout fixture',description:'Synthetic project for control layout verification.',built:true,ok:true,files:[],viewer:'out/viewer.html',history:[],running:[],modes:[]};
   S.sel='fixture';S.tab='model';S.grid=false;
   // Preserve actual renderTab/setFollow behavior without loading a CAD renderer or polling a real project.
   window.viewerLoaded=()=>{};window.liveLoaded=()=>{};window.pollLive=()=>{};
   renderProject();
  },theme);
  const check=async(state)=>{
   await p.locator('.livebar').scrollIntoViewIfNeeded();
   const geometry=await p.locator('.livebar').evaluate(bar=>{
    const label=bar.querySelector('label'),input=label.querySelector('input'),helper=bar.querySelector(':scope>span'),range=document.createRange();
    range.selectNodeContents(label.lastChild);
    const rect=e=>e.getBoundingClientRect().toJSON();
    return {bar:rect(bar),label:rect(label),input:rect(input),text:range.getBoundingClientRect().toJSON(),helper:rect(helper),scroll:bar.scrollWidth,client:bar.clientWidth};
   });
   const {bar,label,input,text,helper}=geometry;
   assert.ok(input.width>0 && input.width<=24,JSON.stringify(geometry));
   assert.ok(text.left>=input.right+4 && text.right<=label.right+1,JSON.stringify(geometry));
   assert.ok(helper.left>=label.right+10 || helper.top>=label.bottom+4,JSON.stringify(geometry));
   assert.ok(helper.left>=bar.left-1 && helper.right<=bar.right+1,JSON.stringify(geometry));
   assert.ok(helper.bottom<=bar.bottom+1 && geometry.scroll<=geometry.client+1,JSON.stringify(geometry));
   if(width===1440 || width===390)await p.screenshot({path:CAPTURE_PATH+`/follow-${state}-${theme}-${width}.png`,fullPage:true});
  };
  const toggle=p.getByRole('checkbox',{name:'Follow live',exact:true});
  assert.equal(await toggle.isChecked(),false);await check('off');
  await p.locator('.livetog').click();
  await p.waitForFunction(()=>document.querySelector('.livebar>span').textContent.includes('watching origin'));
  assert.equal(await toggle.isChecked(),true);await check('on');
  await toggle.focus();assert.equal(await toggle.evaluate(e=>e===document.activeElement),true);
  await p.keyboard.press('Space');
  await p.waitForFunction(()=>document.querySelector('.livebar>span').textContent.includes('last build'));
  assert.equal(await toggle.isChecked(),false);
  assert.deepEqual(calls,[{project:'fixture',on:true},{project:'fixture',on:false}]);
  const error='Cannot update: local changes in '+('long_project_folder_'.repeat(12))+'/parts/arm.py. Save or commit your edits first.';
  await p.evaluate(message=>{S.live.fixture.error=message;renderTab();},error);
  assert.equal(await p.locator('.livebar>span').innerText(),error);await check('error');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);await p.close();
 }
}finally{await browser.close();}
'''.replace('PLAYWRIGHT_PATH', json.dumps(str(root / 'tools/render/node_modules/playwright/index.mjs')))
       .replace('STUDIO_HTML_PATH', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE_PATH', json.dumps(str(captures))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
