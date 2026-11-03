"""Briefing interactions exercise real Studio HTML against isolated, synthetic API responses."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_design_briefing_intake_clarification_evidence_and_navigation(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get('KERF_BRIEFING_SCREENSHOTS', str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / 'briefing.mjs'
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(process.env.KERF_BRIEFING_HTML || __HTML_FILE__,'utf8');
const browser=await openBrowser();
const source={title:'Illustrative research source',url:'https://example.com/fixture',finding:'Synthetic fixture; no product research or measurements are claimed.'};
const comparison={request_kind:'scenario',recommended:0,recommendation_reason:'The ready-made route asks less of the user if its capacity is sufficient.',questions:[],assumptions:['Indoor use; water demand is still unmeasured.'],options:[
 {title:'Ready-made watering kit',summary:'A complete kit to evaluate for six plants while you travel.',route:'buy',parts_printed:0,cost_usd:null,print_hours:0,cost_note:'A current delivered price has not been checked.',print_note:'No printed parts.',fit:'Confirm its capacity covers six plants for ten days.',effort:'Set up a trial before travelling.',risks:['A leak could damage the floor.'],next_steps:['Check capacity and availability.'],sources:[source]},
 {title:'Adapt a reservoir mount',summary:'Fit an existing reservoir design to the shelf you already have.',route:'adapt',parts_printed:1,cost_usd:24,print_hours:null,print_note:'Geometry is not sized or sliced.',fit:'A tailored mount could fit the shelf; water demand still needs measuring.',effort:'Measure the shelf and assemble the mount.',risks:['The reservoir may not last the full trip.'],next_steps:['Measure daily water use.'],sources:[source]},
 {title:'Build a custom watering system',summary:'Design a reservoir, mount and control arrangement around this space.',route:'build',parts_printed:3,cost_usd:null,print_hours:null,cost_note:'Parts have not been selected.',print_note:'No print estimate yet.',fit:'More freedom to fit the space, with more setup and maintenance.',effort:'Assembly and calibration needed.',risks:['Additional electronics need protection from water.'],next_steps:['Choose a water capacity after measuring use.'],sources:[source]}
]};
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[1440,1000],[390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}),errors=[],posts=[];
  await p.emulateMedia({reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
  let quote=structuredClone(comparison),delayed=null,quoteReads=0;
  await p.route('**/*',async r=>{
   const path=new URL(r.request().url()).pathname;
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(r.request().method()==='POST'){posts.push({path,...r.request().postDataJSON()});return r.fulfill({status:400,json:{error:'Synthetic request recorded; no job starts in this fixture.'}});}
   if(path==='/api/projects')return r.fulfill({json:{projects:[],claude:true}});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/quote/plants'){quoteReads++;if(delayed)await delayed.promise;return r.fulfill({json:quote});}
   if(path==='/api/claude')return r.fulfill({json:{ok:true}});
   if(path==='/api/glossary')return r.fulfill({json:{checks:{},terms:{}}});
   if(path.endsWith('.js'))return r.fulfill({contentType:'text/javascript',body:''});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);await p.evaluate(()=>showNew());
  await p.waitForFunction(()=>!$('#nquote').disabled);
  assert.equal(await p.locator('.briefing-details[open]').count(),0);
  assert.equal(await p.locator('#ndesc').getAttribute('aria-describedby'),'briefing-hint');
  await p.locator('#ndesc').fill('A camera arm for my desk');
  assert.equal(await p.locator('#nname').inputValue(),'camera_arm_desk');
  assert.equal(await p.locator('#nstart').isVisible(),true);
  assert.doesNotMatch(await p.locator('.briefing').innerText(),/1–4 hours|strength simulation/);
  await p.locator('.briefing-examples summary').focus();await p.keyboard.press('Enter');
  await p.locator('.examples button').first().click();assert.equal(await p.evaluate(()=>document.activeElement.id),'ndesc');
  assert.match(await p.locator('#ndesc').inputValue(),/wall mount/);
  await p.locator('.briefing-examples summary').click();
  // Optional controls keep every original intake field and value, with keyboard disclosure access.
  const use=p.locator('.briefing-details summary').filter({hasText:'Use & constraints'}),prefs=p.locator('.briefing-details summary').filter({hasText:'Build preferences'});
  await use.focus();await p.keyboard.press('Enter');
  await p.locator('#i_budget').fill('60');await p.locator('#i_mounting').fill('Shelf');await p.locator('#i_who').fill('Me');
  await p.locator('#i_how_often').fill('When travelling');await p.locator('#i_goes_wrong').fill('A leak');
  await p.locator('#i_environment').selectOption('Wet / splashes');await p.locator('#i_power').selectOption('USB');await p.locator('#i_notes').fill('Keep the floor dry.');
  await prefs.focus();await p.keyboard.press('Enter');await p.locator('#nname').fill('plants');
  await p.locator('#ndesc').fill('my plants die when I travel');assert.equal(await p.locator('#nname').inputValue(),'plants');
  await use.click();await prefs.click();
  await p.locator('#i_request_kind').selectOption('scenario');assert.equal(await p.locator('#nstart').isVisible(),false);
  await p.locator('#i_success').fill('Six plants watered for ten days');await p.locator('#i_priority').selectOption('Reliability and low maintenance');await p.locator('#i_effort').fill('One evening; no soldering');
  await p.locator('#nquote').click();await p.waitForFunction(()=>document.querySelector('.toast'));
  assert.equal(posts.length,1);assert.equal(posts[0].path,'/api/quote');assert.equal(posts[0].name,'plants');
  assert.deepEqual(posts[0].intake,{request_kind:'scenario',budget:'60',power:'USB',mounting:'Shelf',environment:'Wet / splashes',printer:'Bambu Lab A2L',material:'PETG',notes:'Keep the floor dry.',who:'Me',how_often:'When travelling',goes_wrong:'A leak',success:'Six plants watered for ten days',priority:'Reliability and low maintenance',effort:'One evening; no soldering'});
  // A synthetic label is present in every saved screenshot, not in production UI.
  await p.evaluate(()=>{const l=document.createElement('div');l.id='fixture-label';l.textContent='SYNTHETIC BROWSER FIXTURE · no jobs or researched results';l.style.cssText='position:fixed;bottom:0;left:0;right:0;padding:4px 12px;z-index:9999;background:#202832;color:#fff;font:11px system-ui;text-align:center';document.body.append(l);document.querySelectorAll('.toast').forEach(e=>e.remove());$('#main').scrollTop=0;});
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await p.locator('#main').evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  await p.screenshot({path:CAPTURE+`/briefing-${theme}-${width}.png`,fullPage:true});
  quote.context={description:posts[0].description,intake:posts[0].intake};
  await p.evaluate(()=>showQuote('plants'));await p.locator('.qopt').first().waitFor();
  assert.equal(await p.locator('.qopt').count(),3);assert.equal(await p.locator('.qopt').first().locator('button').count(),0);
  assert.match(await p.locator('.qopt').first().innerText(),/Cost not yet known/);assert.doesNotMatch(await p.locator('.qopt').first().innerText(),/\$0/);
  assert.equal(await p.locator('.qopt').nth(1).locator('button').isEnabled(),true);
  assert.equal(await p.locator('.qopt a').first().getAttribute('rel'),'noopener noreferrer');
  await p.locator('.qopt a').first().focus();assert.equal(await p.evaluate(()=>document.activeElement.tagName),'A');
  await p.locator('.briefing-tradeoffs summary').nth(1).focus();await p.keyboard.press('Enter');
  assert.match(await p.locator('.qopt').nth(1).innerText(),/The reservoir may not last the full trip/);
  await p.locator('.briefing-tradeoffs summary').nth(1).click();
  await p.locator('#quote').evaluate(e=>e.scrollIntoView({block:'start'}));
  assert.equal(await p.locator('#main').evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  await p.screenshot({path:CAPTURE+`/options-${theme}-${width}.png`,fullPage:true});
  await p.locator('.qopt').nth(1).locator('button').click();assert.equal(posts.at(-1).path,'/api/new');assert.equal(posts.at(-1).option_index,1);assert.equal(posts.at(-1).option.route,'adapt');
  quote.questions=['How much water do the plants use each day?','Will the shelf hold a full reservoir?'];
  await p.evaluate(()=>showQuote('plants'));
  assert.equal(await p.locator('.qopt button:disabled').count(),2);
  assert.equal(await p.locator('#quote-refine').isDisabled(),true);
  await p.locator('#quote-answers').fill('About 120 ml per plant per day. I will check the shelf load before choosing.');
  assert.equal(await p.locator('#quote-refine').isEnabled(),true);
  await p.locator('#quote').evaluate(e=>e.scrollIntoView({block:'start'}));
  await p.screenshot({path:CAPTURE+`/clarify-${theme}-${width}.png`,fullPage:true});
  await p.locator('#quote-refine').click();assert.equal(posts.at(-1).path,'/api/quote');
  assert.match(posts.at(-1).intake.notes,/Keep the floor dry\.[\s\S]*How much water[\s\S]*120 ml/);
  assert.match(await p.locator('#quote').innerText(),/Your request changed/);
  assert.equal(await p.locator('#i_success').inputValue(),'Six plants watered for ten days');
  // Earlier options never overwrite newer edits or enable their design actions.
  quote.questions=[];await p.evaluate(()=>showQuote('plants'));
  assert.equal(await p.locator('.qopt button:disabled').count(),2);
  assert.match(await p.locator('#quote').innerText(),/earlier answers/);
  // Restoring a saved brief restores all fields, including hidden options; exact context unlocks its option.
  await p.evaluate(()=>openQuote('plants'));assert.equal(await p.locator('#i_notes').inputValue(),'Keep the floor dry.');
  assert.equal(await p.locator('.qopt button:enabled').count(),2);
  // A delayed quote or saved request cannot mutate a replacement New screen.
  for(const open of [false,true]){
   delayed={};delayed.promise=new Promise(resolve=>delayed.resolve=resolve);
   const requested=p.waitForRequest(r=>new URL(r.url()).pathname==='/api/quote/plants');
   await p.evaluate(open=>{window.pendingQuote=open?openQuote('plants'):showQuote('plants');},open);
   await requested;
   await p.evaluate(()=>showNew());await p.locator('#ndesc').fill('A fresh, different brief');delayed.resolve();delayed=null;
   await p.evaluate(()=>window.pendingQuote);
   assert.equal(await p.locator('#ndesc').inputValue(),'A fresh, different brief');assert.equal(await p.locator('.qopt').count(),0);
  }
  const beforeCancel=quoteReads;
  await p.evaluate(async()=>{const original=showNew;window.showNew=()=>{};S.newOpen=false;$('#main').innerHTML='<p id="cancelled">Project kept open</p>';await openQuote('plants');window.showNew=original;});
  assert.equal(quoteReads,beforeCancel);assert.equal(await p.locator('#cancelled').innerText(),'Project kept open');
  assert.deepEqual(errors,[]);console.log(JSON.stringify({theme,width,posts:posts.length}));await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('__HTML_FILE__', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE', json.dumps(str(capture))), encoding='utf-8')
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
