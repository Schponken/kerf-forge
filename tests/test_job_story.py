"""Active job and decision trail contracts; static fixtures, no jobs or geometry."""
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from kerf import studio


def test_job_info_preserves_authoritative_provider_and_state():
    fields = dict(id="fixture", kind="design", project="fixture", label="Fixture", state="paused", usage=None,
                  session="s", resumed_by=None, started=10, ended=20, lines=[], events=[])
    j = SimpleNamespace(**fields, agent="codex")
    assert studio.Job.info(j)["agent"] == "codex"
    assert studio.Job.info(j)["state"] == "paused"
    del j.agent
    assert studio.Job.info(j)["agent"] == "claude"  # Existing Work API's historical fallback.
    j.agent = None
    assert studio.Job.info(j)["agent"] is None


@pytest.mark.parametrize("state", ["running", "paused", "failed", "stopped", "done"])
def test_thoughtweb_reports_job_state_without_reinterpreting_events(monkeypatch, state):
    from kerf import steer
    j = SimpleNamespace(events=[], request="Fixture", label="Fixture", state=state, kind="design", project="fixture")
    monkeypatch.setattr(studio, "JOBS", {"fixture": j})
    monkeypatch.setattr(steer, "read", lambda _: [])
    handler = studio.Handler.__new__(studio.Handler)
    handler.path = "/api/thoughtweb?job=fixture"
    result = []
    handler._json = lambda data, *args: result.append(data)
    handler.do_GET()
    assert result[0]["state"] == state
    assert result[0]["live"] is (state == "running")
    assert result[0]["steerable"] is (state == "running")


@pytest.mark.browser
def test_job_story_focus_evidence_steering_and_layout(tmp_path):
    root = Path(__file__).resolve().parents[1]
    captures = Path(os.environ.get("KERF_JOB_SCREENSHOTS", str(tmp_path)))
    captures.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "job-story.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), js=await fs.readFile(TRAIL,'utf8');
const browser=await openBrowser();
const node=(id,parent,kind,label,t,extra={})=>({id,parent,kind,label,t,touched:t,state:'active',notes:[],...extra});
const fixture={live:true,state:'running',steerable:true,steer:[],steps:4,nodes:[
 node('c',null,'core','A folding desk lamp',0,{detail:'Fixture: a lamp that folds flat and uses screws I already own.'}),
 node('q','c','idea','Can the hinge hold the light without drifting?',1,{notes:['A clamped joint allows the tension to be adjusted.']}),
 node('s','q','source','Supplier hinge datasheet',2,{url:'https://example.com/hinge'}),
 node('q2','c','idea','Which power supply fits inside the base?',3),
 node('s2','q2','source','Unsafe source stays text',4,{url:'javascript:alert(1)'})]};
const job={id:'fixture',kind:'design',project:'fixture',label:'Fixture: folding desk lamp',agent:'codex',state:'running',seconds:126,lines:[],events:[]};
try {
 for(const [theme,width,height] of [['dark',1440,1000],['light',1440,1000],['dark',390,844],['light',390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  let data=structuredClone(fixture), fail=false, posts=[];
  await p.route('**/*',async route=>{
   const u=new URL(route.request().url());
   if(u.pathname==='/') return route.fulfill({contentType:'text/html',body:html});
   if(u.pathname==='/ui/thoughtweb.js') return route.fulfill({contentType:'text/javascript',body:js});
   if(u.pathname==='/api/thoughtweb') return route.fulfill(fail?{status:503,json:{error:'offline'}}:{json:data});
   if(u.pathname==='/api/steer') {const b=route.request().postDataJSON(); posts.push(b); data.steer.push({...b,delivered:false}); return route.fulfill({json:b});}
   if(u.pathname==='/api/projects') return route.fulfill({json:{projects:[],claude:false}});
   if(u.pathname==='/api/jobs') return route.fulfill({json:{jobs:[],sessions:[]}});
   if(u.pathname==='/api/quotes') return route.fulfill({json:{quotes:[]}});
   if(u.pathname==='/api/work') return route.fulfill({json:{items:[],counts:{},sources:[],feed:[]}});
   if(u.pathname.startsWith('/api/')) return route.fulfill({json:{}});
   return route.fulfill({contentType:'text/javascript',body:''});
  });
  await p.goto('http://kerf.test/');
  await p.evaluate(({theme,job})=>{
   setTheme(theme); S.tw={stop(){}}; S.job=job.id; S.settings={autoresume:false};
   S.ev=[{k:'tool',name:'Write',path:'/project/parts/hinge.py',phase:'parts'}]; S.lines=['The hinge uses a replaceable screw.'];
   $('#mc').classList.add('open'); renderMc(job);
  },{theme,job});
  assert.match(await p.locator('.job-current').innerText(),/Drawing the hinge/);
  assert.match(await p.locator('#mcsub').innerText(),/Codex · Working · 2:06 elapsed/);
  assert.equal(await p.locator('#pbar').count(),0);
  assert.equal(await p.locator('details.job-detail[open]').count(),0);
  await p.getByText('Design stages',{exact:true}).click();
  assert.match(await p.locator('[data-detail=phases]').innerText(),/Research\s+Not reported/);
  assert.equal(await p.locator('#mc .step.done').count(),0);
  await p.locator('[data-detail=phases] summary').focus();
  await p.evaluate(job=>renderMc(job),job);
  assert.equal(await p.evaluate(()=>document.activeElement.parentElement.dataset.detail),'phases');
  assert.equal(await p.locator('[data-detail=phases]').getAttribute('open'),'');
  await p.getByText('Design stages',{exact:true}).click();
  await p.screenshot({path:CAPTURE+`/job-${theme}-${width}.png`,fullPage:true});
  for(const state of ['paused','failed','stopped','done']) {
   await p.evaluate(({job,state})=>renderMc({...job,state}),{job,state});
   assert.equal(await p.locator('#mc .step.active').count(),0);
   assert.doesNotMatch(await p.locator('.job-current').innerText(),/Drawing the hinge/);
  }
  await p.evaluate(job=>{renderMc({...job,kind:'build',agent:'codex'});},job);
  assert.match(await p.locator('#mcsub').innerText(),/^Kerf/);
  assert.match(await p.locator('.job-next').innerText(),/not been reported/);
  await p.evaluate(()=>{
   closeMc(); const b=document.createElement('button'); b.id='story-open'; b.textContent='Read the story';
   b.onclick=()=>showDecided(null,'fixture','Fixture: folding desk lamp'); document.body.appendChild(b); b.focus(); b.click();
  });
  await p.waitForSelector('.twmodal .twc.q');
  assert.equal(await p.locator('.twmodal').getAttribute('role'),'dialog');
  assert.equal(await p.locator('.twmodal a[href^="javascript:"]').count(),0);
  assert.equal(await p.locator('.twmodal a[href="https://example.com/hinge"]').count(),1);
  const focus=p.locator('[data-key="focus-q"]');
  await focus.click();
  await p.waitForFunction(()=>document.querySelector('[data-key="focus-q"]').getAttribute('aria-pressed')==='true');
  assert.equal(posts[0].action,'focus');
  assert.equal(await p.evaluate(()=>document.activeElement.dataset.key),'focus-q');
  await p.locator('#tw-note').fill('Keep the base compact.');
  await p.locator('.tell .send').click();
  await p.waitForFunction(()=>document.querySelector('.receipts').textContent.includes('Waiting for receipt'));
  data.steer.forEach(x=>x.delivered=true);
  await p.waitForFunction(()=>document.querySelector('.receipts').textContent.includes('Received by Kerf'));
  await p.locator('#tw-note').fill('Keep this draft while updates arrive.');
  data.nodes.push(node('s3','q','source','Second supplier source',5,{url:'https://example.com/second'}));
  await p.waitForSelector('a[href="https://example.com/second"]');
  assert.equal(await p.locator('#tw-note').inputValue(),'Keep this draft while updates arrive.');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'tw-note');
  await p.locator('[data-key="section-research"]').click();
  data.nodes.push(node('s4','q','source','Third supplier source',6,{url:'https://example.com/third'}));
  await p.waitForSelector('a[href="https://example.com/third"]',{state:'attached'});
  assert.equal(await p.locator('[data-section=research]').getAttribute('open'),null);
  await p.locator('[data-key="section-research"]').click();
  fail=true;
  await p.waitForSelector('.load-error:not([hidden])');
  assert.match(await p.locator('.load-error').innerText(),/last recorded update/);
  assert.equal(await p.locator('a[href="https://example.com/hinge"]').count(),1);
  fail=false;
  data.live=false; data.state='paused'; data.steerable=false;
  data.nodes.push(node('d','c','decision','Plan',7),node('o','d','option','Clamp the hinge with a screw',8,{state:'chosen',reason:'The tension can be adjusted.',based_on:'q'}));
  await p.waitForFunction(()=>document.querySelector('.nowt').textContent.includes('Work paused'));
  assert.equal(await p.locator('.twmodal .st.done').count(),0);
  assert.equal(await p.locator('.twmodal [data-steer]').count(),0);
  if(await p.locator('[data-section=decide]').getAttribute('open')===null) await p.locator('[data-key="section-decide"]').click();
  assert.match(await p.locator('.twc.opt').innerText(),/Chosen.*Clamp the hinge.*tension/s);
  await p.locator('[data-key="goto-o"]').click();
  assert.equal(await p.locator('[data-section=research]').getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await p.locator('.twmodal .card').evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  assert.equal(await p.locator('.twv .scroll').evaluate(e=>e.scrollWidth<=e.clientWidth+1),true);
  await p.screenshot({path:CAPTURE+`/trail-${theme}-${width}.png`,fullPage:true});
  await p.keyboard.press('Escape');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'story-open');
  assert.deepEqual(errors,[]);
  await p.close();
 }
} finally {await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('TRAIL', json.dumps(str(root / 'kerf/assets/thoughtweb.js')))
       .replace('CAPTURE', json.dumps(str(captures))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr
