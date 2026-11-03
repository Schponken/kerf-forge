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
  assert.deepEqual(await p.locator('#term-fixture abbr').allTextContents(),['FEA','stress','FEA','heat-set insert']);
  const term=p.getByRole('button',{name:'Explain FEA',exact:true}).first();await term.focus();await p.keyboard.press('Space');
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


@pytest.mark.browser
def test_definitions_at_the_word(tmp_path):
    """Hover, focus and one tap reveal the definition without opening a menu or searching."""
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "word-definitions.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML_PATH,'utf8'), glossary=GLOSSARY, browser=await openBrowser();
try {
 for (const touch of [false,true]) {
  const width=touch?390:1440,height=touch?844:960;
  const p=await browser.newPage({viewport:{width,height},hasTouch:touch}),errors=[],requests=[];
  p.on('pageerror',e=>errors.push(e.message));await p.emulateMedia({reducedMotion:'reduce'});
  await p.route('**/*',r=>{
   const path=new URL(r.request().url()).pathname;requests.push([r.request().method(),path]);
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path==='/api/projects')return r.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/glossary')return r.fulfill({json:glossary});
   if(path.endsWith('.js'))return r.fulfill({contentType:'text/javascript',body:''});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.waitForFunction(()=>GL.rx&&document.querySelector('.welcome-studio'));
  await p.evaluate(()=>{
   const e=document.createElement('section');e.id='words';e.style='position:fixed;right:16px;bottom:16px;z-index:50';
   e.innerHTML='<p>FEA and stress. FEA again. <code>FEA</code></p><button id="word-after">After terms</button>';
   document.body.append(e);glossify(e);glossify(e);
  });
  const term=p.getByRole('button',{name:'Explain FEA',exact:true}).first(),popup=p.getByRole('dialog',{name:'Word explained'});
  assert.deepEqual(await p.locator('#words abbr').allTextContents(),['FEA','stress','FEA']);
  assert.equal(await term.getAttribute('title'),null);
  await p.locator('#word-after').focus();
  if(touch) await term.tap(); else await term.hover();
  await popup.waitFor();assert.match(await popup.innerText(),/Finite element analysis/);
  assert.equal(await term.getAttribute('aria-describedby'),'guide-description');
  assert.equal(await p.locator('dialog.glmodal').count(),0);
  const box=await popup.boundingBox(),anchor=await term.boundingBox();
  assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=height,JSON.stringify(box));
  assert.ok(box.y+box.height<=anchor.y,'near bottom: definition appears above the word');
  assert.equal(await popup.evaluate(e=>getComputedStyle(e).animationName),'none');
  if(!touch){
   assert.equal(await p.locator('#word-after').evaluate(e=>e===document.activeElement),true,'hover must not steal focus');
   await p.mouse.move(anchor.x+anchor.width/2,anchor.y-6);await p.waitForTimeout(100);
   await p.mouse.move(box.x+box.width/2,box.y+box.height/2);await p.waitForTimeout(300);
   assert.equal(await popup.isVisible(),true,'pointer can cross the gap and read the definition');
   await p.keyboard.press('Escape');assert.equal(await popup.count(),0);
   assert.equal(await p.locator('#word-after').evaluate(e=>e===document.activeElement),true);
   await p.mouse.move(1,1);await term.focus();await popup.waitFor();
   assert.equal(await term.evaluate(e=>e===document.activeElement),true,'focus reveals definition without an extra key');
   await p.keyboard.press('Escape');assert.equal(await popup.count(),0);
   await p.keyboard.press('Enter');await popup.waitFor();
   await p.keyboard.press('Escape');assert.equal(await popup.count(),0);
   assert.equal(await term.evaluate(e=>e===document.activeElement),true,'Escape returns to the term without reopening');
   await p.locator('#word-after').focus();await term.hover();await popup.waitFor();
   await p.mouse.move(1,1);await popup.waitFor({state:'detached'});
   await term.focus();await popup.waitFor();await p.locator('#word-after').focus();await popup.waitFor({state:'detached'});
  }else{
   await popup.getByRole('button',{name:'Close guidance'}).tap();assert.equal(await popup.count(),0);
   await term.tap();await popup.waitFor();await p.locator('#word-after').tap();assert.equal(await popup.count(),0);
  }
  assert.equal(await term.getAttribute('aria-describedby'),null);
  assert.deepEqual(errors,[]);assert.ok(requests.every(([method])=>method==='GET'));
  console.log(JSON.stringify({touch,width,height}));await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / "tests/browser.mjs")))
       .replace('HTML_PATH', json.dumps(str(root / "kerf/assets/studio.html")))
       .replace('GLOSSARY', json.dumps(glossary.as_json())), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
