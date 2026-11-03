"""Source coverage and project navigation use synthetic work; no real sessions or jobs are opened."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from test_work_clarity import work_fixture


@pytest.mark.browser
def test_work_exposes_partial_sources_and_project_shortcuts_clear_conflicting_filters(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_WORK_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    html = Path(os.environ.get("KERF_WORK_HTML", str(root / "kerf/assets/studio.html")))
    script = tmp_path / "work-source-visibility.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), initial=FIXTURE;
const browser=await openBrowser();
try {
 for(const [theme,width,height] of [['dark',1440,1000],['light',1440,1000],['dark',390,844],['light',390,844]]) {
  let fixture=structuredClone(initial), respond=null, delay=false;
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/*',async route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/')return route.fulfill({contentType:'text/html',body:html});
   if(path==='/api/work') {
    if(delay)await new Promise(resolve=>respond=resolve);
    return route.fulfill({json:fixture});
   }
   if(path==='/api/projects')return route.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/quotes')return route.fulfill({json:{quotes:[]}});
   if(path==='/api/jobs')return route.fulfill({json:{jobs:[],sessions:[]}});
   return route.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();await p.locator('.work-item').first().waitFor();
  assert.equal(await p.locator('#work-coverage').count(),0);
  await p.locator('#work-filter-recent').click();
  await p.locator('#work-provider').selectOption('Studio');
  assert.equal(await p.locator('.work-item').count(),0);
  await p.locator('#work-project-demo_planter').click();
  assert.equal(await p.locator('#work-provider').inputValue(),'all');
  assert.equal(await p.locator('#work-filter-all').getAttribute('aria-pressed'),'true');
  assert.equal(await p.locator('#work-search').inputValue(),'demo_planter');
  assert.equal(await p.locator('.work-item').count(),4);
  assert.equal(await p.evaluate(()=>document.activeElement.id),'work-search');
  await p.locator('#work-search').fill('');
  // The backend reports stale observations explicitly; a limited source can also omit sessions entirely.
  fixture.items=fixture.items.filter(i=>i.source!=='session');
  fixture.sources=[{name:'Codex',state:'unavailable',detail:'Synthetic UI fixture: could not refresh sessions <img src=x onerror=alert(1)>.'},
   {name:'Shared claims',state:'ok',detail:'Synthetic shared claims.'},{name:'Studio jobs',state:'ok',detail:'Synthetic local jobs.'}];
  await p.evaluate(()=>loadWork());
  assert.match(await p.locator('.work-summary').innerText(),/2 working · 1 assigned · 1 paused/);
  const summary=p.locator('#work-coverage-summary');
  assert.equal(await summary.innerText(),'Partial view · 1 source limited');
  assert.equal(await p.locator('#work-coverage').getAttribute('open'),null);
  await summary.focus();await p.keyboard.press('Enter');
  assert.equal(await p.locator('#work-coverage').getAttribute('open'),'');
  assert.match(await p.locator('#work-coverage').innerText(),/Codex · unavailable/);
  assert.match(await p.locator('#work-coverage').innerText(),/Counts cover the work currently reported/);
  assert.equal(await p.locator('#work-coverage img').count(),0);
  await p.evaluate(()=>loadWork());
  assert.equal(await p.locator('#work-coverage').getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'work-coverage-summary');
  await p.evaluate(()=>document.querySelector('#main').scrollTop=0);
  await p.screenshot({path:CAPTURE+`/work-sources-${theme}-${width}.png`});
  await summary.click();
  for(const state of ['partial','loading']) {
   fixture.sources[0].state=state;await p.evaluate(()=>loadWork());
   assert.equal(await summary.innerText(),'Partial view · 1 source limited');
  }
  fixture.sources[1].state='partial';await p.evaluate(()=>loadWork());
  assert.equal(await summary.innerText(),'Partial view · 2 sources limited');
  fixture.items=[];await p.evaluate(()=>loadWork());
  assert.match(await p.locator('.work-empty h2').innerText(),/No work visible from available sources/);
  fixture.sources.forEach(s=>s.state='ok');await p.evaluate(()=>loadWork());
  assert.equal(await p.locator('#work-coverage').count(),0);
  assert.equal(await p.locator('.work-empty h2').innerText(),'No work is being reported yet');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  // A late Work request must not replace the destination after navigation.
  delay=true;await p.evaluate(()=>{loadWork();});
  await p.waitForFunction(()=>S.workLoading);
  await p.evaluate(()=>showGrid());
  const destination=await p.locator('#main').innerText();
  while(!respond)await new Promise(resolve=>setTimeout(resolve,10));
  respond();await p.waitForFunction(()=>!S.workLoading);
  assert.equal(await p.locator('#main').innerText(),destination);
  assert.equal(await p.locator('.work-page').count(),0);
  assert.deepEqual(errors,[]);await p.close();
 }
} finally {await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(html))).replace('FIXTURE', json.dumps(work_fixture()))
       .replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
