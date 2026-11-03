"""Studio serialization -> Work DOM for agent providers, usage pauses and continuation controls."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from test_work_job_states import job, paused, snapshot  # noqa: F401


@pytest.mark.browser
def test_serialized_job_states_reach_work_filters_and_controls(snapshot, tmp_path):
    root = Path(__file__).resolve().parents[1]
    data = snapshot(paused(label="Pause while checking the fixture"),
                    paused("old", resumed_by="next", label="Previous design run"),
                    job("next", agent="codex", label="Continue the design <img src=x onerror=alert(1)>"),
                    paused("missing", resumed_by="unavailable", label="Older continuation"))
    capture = Path(os.environ.get("KERF_WORK_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "work-job-page.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), fixture=FIXTURE;
const browser=await openBrowser();
try {
 for(const [theme,width,height] of [['dark',1440,1100],['light',1440,1100],['dark',390,1000],['light',390,1000]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/*', route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/') return route.fulfill({contentType:'text/html',body:html});
   if(path==='/api/work') return route.fulfill({json:fixture});
   if(path==='/api/projects') return route.fulfill({json:{projects:[],claude:false}});
   if(path==='/api/quotes') return route.fulfill({json:{quotes:[]}});
   if(path==='/api/jobs') return route.fulfill({json:{jobs:[],sessions:[]}});
   return route.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');
  await p.evaluate(t=>setTheme(t),theme);
  await p.locator('#nav_work').click();
  const paused=p.locator('[data-work-item="job:paused"]'), old=p.locator('[data-work-item="job:old"]');
  await paused.waitFor();
  assert.equal(await p.locator('.work-item').count(),4);
  assert.equal(await paused.locator('.work-state').innerText(),'Paused · usage limit');
  assert.match(await paused.innerText(),/Pause details:.*Automatic retry is enabled/s);
  assert.match(await paused.innerText(),/retry timing is unavailable/);
  assert.match(await paused.innerText(),/Usage resets.*This is not a finish estimate/s);
  assert.doesNotMatch(await paused.innerText(),/Needs your input|Designing the next part|About \d+ min left|raw private usage log/);
  assert.equal(await p.locator('[data-work-item="job:next"] .work-owner b').innerText(),'Codex');
  assert.equal(await p.locator('.work-item img').count(),0);
  assert.match(await old.innerText(),/Continued in another job/);
  assert.match(await old.innerText(),/Continuing job: Codex · Working/);
  assert.equal(await old.locator('.work-attention').count(),0);
  assert.equal(await p.locator('[data-work-item="job:missing"]').getByRole('button',{name:'Watch continuing job'}).count(),0);
  await p.locator('#work-filter-attention').click();
  assert.equal(await p.locator('.work-item').count(),1);
  assert.equal(await paused.count(),1);
  await p.locator('#work-filter-active').click();
  assert.equal(await p.locator('.work-item').count(),1);
  assert.equal(await p.locator('[data-work-item="job:next"]').count(),1);
  await p.locator('#work-filter-recent').click();
  assert.equal(await p.locator('.work-item').count(),2);
  assert.equal(await old.count(),1);
  await p.evaluate(()=>{window.watch=id=>window.__watched=id;});
  const action=old.getByRole('button',{name:'Watch continuing job'});
  await action.focus();
  const id=await action.getAttribute('id');
  await p.evaluate(()=>renderWork());
  assert.equal(await p.evaluate(()=>document.activeElement.id),id);
  await p.keyboard.press('Enter');
  assert.equal(await p.evaluate(()=>window.__watched),'next');
  await old.getByRole('button',{name:'View previous run'}).click();
  assert.equal(await p.evaluate(()=>window.__watched),'old');
  await p.screenshot({path:CAPTURE+`/work-job-continuation-${theme}-${width}.png`,fullPage:true});
  await p.locator('#work-filter-all').click();
  await p.evaluate(()=>{$('#main').scrollTop=0;});
  assert.deepEqual(await p.evaluate(()=>[null,-1,Infinity,1e99].map(workReset)),Array(4).fill('Usage reset time is not reported.'));
  assert.match(await p.evaluate(()=>workReset(1)),/Reported usage reset/);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await p.locator('.work-page').evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  assert.deepEqual(errors,[]);
  await p.screenshot({path:CAPTURE+`/work-job-paused-${theme}-${width}.png`,fullPage:true});
  await p.close();
 }
} finally {await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('FIXTURE', json.dumps(data)).replace('CAPTURE', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
