"""First-use guidance uses isolated API fixtures, never agents, builds or geometry."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from kerf import glossary


@pytest.mark.browser
def test_guidance_glossary_tour_welcome_and_readiness(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_FIRST_USE_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "first-use.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML_PATH,'utf8'), glossary=GLOSSARY;
const browser=await openBrowser();
try {
 for(const theme of ['light','dark']) for(const [width,height] of [[1440,960],[390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[], requests=[];
  await p.emulateMedia({reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/*',r=>{
   const path=new URL(r.request().url()).pathname;requests.push([r.request().method(),path]);
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path==='/api/projects')return r.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/glossary')return r.fulfill({json:glossary});
   if(path==='/api/claude')return r.fulfill({json:{ok:true}});
   if(path.endsWith('.js'))return r.fulfill({contentType:'text/javascript',body:''});
   return r.fulfill({json:{}});
  });
  const shot=name=>p.screenshot({path:CAPTURE+`/${name}-${theme}-${width}.png`,fullPage:true,animations:'disabled'});
  const fits=async selector=>{const r=await p.locator(selector).boundingBox();assert.ok(r.x>=0&&r.y>=0&&r.x+r.width<=width+1&&r.y+r.height<=height+1,JSON.stringify({selector,r,width,height}));};
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.waitForFunction(()=>GL.rx && document.querySelector('.welcome-studio'));
  await p.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  assert.equal(await p.locator('.guide-popover,.tourlay').count(),0);
  assert.match(await p.locator('.welcome-studio').innerText(),/Paused strength checks leave strength unproven/);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await shot('welcome');
  const how=p.getByRole('button',{name:'How Kerf works'});await how.focus();await p.keyboard.press('Enter');
  assert.equal(await p.locator('[role=dialog][aria-label="Explain this page"]').count(),1);
  assert.match(await p.locator('.guide-popover').innerText(),/research options/);
  assert.equal(await p.locator('.guide-popover').evaluate(e=>getComputedStyle(e).animationName),'none');
  await fits('.guide-popover');await shot('help');
  await p.keyboard.press('Escape');assert.equal(await p.locator('.guide-popover').count(),0);
  assert.equal(await how.evaluate(e=>e===document.activeElement),true);
  await how.click();await p.getByRole('button',{name:'Show me around this page'}).click();
  assert.equal(await p.locator('.tourlay .note').innerText(),'1 of 3');
  assert.equal(await p.locator('.tourlay').evaluate(e=>getComputedStyle(e).pointerEvents),'none');
  await fits('.tourlay .bub');await shot('tour');
  await p.locator('[data-a=n]').click();assert.equal(await p.locator('.tourlay .note').innerText(),'2 of 3');
  await p.getByRole('button',{name:'Back',exact:true}).click();assert.equal(await p.locator('.tourlay .note').innerText(),'1 of 3');
  await p.keyboard.press('Escape');assert.equal(await how.evaluate(e=>e===document.activeElement),true);
  await how.click();await p.getByRole('button',{name:'Words, explained',exact:true}).click();
  const dialog=p.getByRole('dialog',{name:'Words, explained'}), input=dialog.getByRole('searchbox',{name:'Find a word or check'});
  await input.fill('infill');assert.match(await dialog.locator('.glrow:visible').innerText(),/infill/i);
  await input.fill('not-a-real-word');assert.equal(await dialog.getByText('No matching words',{exact:true}).isVisible(),true);
  await dialog.getByRole('button',{name:'Clear search'}).click();assert.equal(await input.inputValue(),'');
  assert.equal(await input.evaluate(e=>e===document.activeElement),true);
  assert.equal(await dialog.locator('.glrow:visible').count(),Object.keys(glossary.terms).length+Object.keys(glossary.checks).length);
  await input.fill('strength');await fits('.glmodal');await shot('glossary');
  // Native modal focus cannot escape to the page; closing returns to the actual guide opener.
  await dialog.getByRole('button',{name:'Close',exact:true}).focus();await p.keyboard.press('Shift+Tab');
  assert.equal(await p.evaluate(()=>document.querySelector('dialog.glmodal').contains(document.activeElement)),true);
  await p.keyboard.press('Escape');await p.locator('.glmodal').waitFor({state:'detached'});assert.equal(await p.locator('.glmodal').count(),0);
  assert.equal(await how.evaluate(e=>e===document.activeElement),true);
  await p.evaluate(()=>{const e=document.createElement('section');e.id='term-fixture';e.innerHTML='<p>FEA and stress. FEA again. <code>FEA</code> PLAnet heat-set insert.</p>';document.querySelector('.welcome-studio').prepend(e);glossify(e);});
  assert.deepEqual(await p.locator('#term-fixture abbr').allTextContents(),['FEA','stress','heat-set insert']);
  const term=p.getByRole('button',{name:'Explain FEA',exact:true});await term.focus();await p.keyboard.press('Space');
  assert.match(await p.getByRole('dialog',{name:'Word explained'}).innerText(),/FEA/);await fits('.guide-popover');
  await p.keyboard.press('Escape');assert.equal(await term.evaluate(e=>e===document.activeElement),true);
  await term.click();await p.getByRole('button',{name:'Close guidance'}).click();assert.equal(await term.evaluate(e=>e===document.activeElement),true);
  await how.click();await p.locator('#welcome-title').click();assert.equal(await p.locator('.guide-popover').count(),0);
  await p.getByRole('button',{name:'Start a design',exact:true}).click();
  await p.getByText('Design assistant is ready',{exact:true}).waitFor();
  assert.equal(await p.locator('#ready .banner.ok').count(),0);
  await p.locator('.ready-status summary').focus();await p.keyboard.press('Enter');
  assert.match(await p.locator('.ready-detail').innerText(),/installed, trusts this folder and is signed in/);
  assert.match(await p.locator('.ready-status time').getAttribute('datetime'),/^\d{4}-/);
  await p.evaluate(()=>showReady({ok:false,code:'auth',why:'Fixture: sign-in required'}));
  assert.match(await p.locator('#ready').innerText(),/Fixture: sign-in required/);assert.match(await p.locator('#ready').innerText(),/\/login/);
  assert.equal(await p.locator('#nstart').isDisabled(),true);assert.equal(await p.locator('#nquote').isDisabled(),true);
  await p.evaluate(()=>showReady({ok:false,code:'usage',why:'Fixture: usage paused'}));assert.match(await p.locator('#ready').innerText(),/Fixture: usage paused/);
  await p.evaluate(()=>showReady({ok:true}));assert.equal(await p.locator('#nstart').isDisabled(),false);
  assert.deepEqual(errors,[]);assert.ok(requests.every(([method])=>method==='GET'),JSON.stringify(requests));
  console.log(JSON.stringify({theme,width,height,requests:requests.length}));await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / "tests/browser.mjs")))
       .replace('HTML_PATH', json.dumps(str(root / "kerf/assets/studio.html")))
       .replace('GLOSSARY', json.dumps(glossary.as_json()))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
