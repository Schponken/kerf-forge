"""Making handoff uses synthetic saved-file data and mocked GETs, never a build or printer."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_files_handoff_preserves_downloads_context_and_keyboard(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_HANDOFF_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "making-handoff.mjs"
    script.write_text(r'''
import {browser as openBrowser} from "BROWSER_HELPER";
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML_PATH,'utf8'), browser=await openBrowser();
const files=['out/plates/plate_1.3mf','out/parts/bracket_left.stl','out/parts/bracket_left.3mf','out/drawings/bracket_left.pdf','out/assembly.step','out/bom.csv','out/bom.md','out/viewer.html','out/ASSEMBLY.md','out/WIRING.md','out/plates/PRINT_SETTINGS.md','out/firmware/BRINGUP.md','out/firmware/controller/controller.ino','out/fixture_urdf.zip','out/manufacturing/ORDER.md','out/manufacturing/mount.dxf','out/unexpected <part> "export".txt'];
const docs=['DESIGN.md','REFERENCES.md','out/ASSEMBLY.md','out/WIRING.md','out/firmware/BRINGUP.md','out/bom.md','out/plates/PRINT_SETTINGS.md','out/OPTIMISE.md','out/manufacturing/ORDER.md'];
try {
 for(const theme of ['dark','light']) for(const [width,height] of [[1512,982],[390,844]]) {
  const p=await browser.newPage({viewport:{width,height}}), errors=[], requests=[];
  await p.emulateMedia({reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
  const base={name:'fixture',title:'Desk inspection arm · fixture',description:'Synthetic saved-output fixture. No build, hardware or print operation is performed.',built:true,ok:true,problems:0,stale:false,review:{ok:false},files,docs,params:[],history:[],renders:[],modes:[],viewer:null,report:{ok:true,fingerprint:'fixture-build-0123456789abcdef',problems:[],requirements:[{id:'strength',paused:true}],warnings:['Stress simulations PAUSED: strength unproven.']},built_at:1793664000};
  let d=structuredClone(base);
  await p.route('**/*',r=>{
   const path=new URL(r.request().url()).pathname;requests.push([r.request().method(),path]);
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(path==='/api/projects')return r.fulfill({json:{projects:[d],claude:false}});
   if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/glossary')return r.fulfill({json:{checks:{},terms:{fixture:'Fixture'}}});
   if(path==='/api/project/fixture')return r.fulfill({json:d});
   if(path.startsWith('/files/'))return r.fulfill({contentType:'text/plain',body:'# Fixture guide\nSupplier source: https://example.test/source'});
   if(path.endsWith('.js'))return r.fulfill({contentType:'text/javascript',body:''});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');await p.evaluate(t=>setTheme(t),theme);
  await p.evaluate(async()=>{await select('fixture');setTab('files')});
  const scope=p.locator('.files-handoff');await scope.waitFor();
  assert.equal(await p.evaluate(()=>TOUR.files.every(([selector])=>document.querySelector(selector)!==null)),true);
  assert.match(await scope.innerText(),/Review still needed/);
  assert.match(await scope.innerText(),/Strength is unproven/);
  assert.match(await scope.innerText(),/components to buy or supply/);
  assert.deepEqual(await scope.locator('[data-doc]').evaluateAll(es=>es.slice(0,3).map(e=>e.textContent)),['Assembly guide','Shopping list','Print settings']);
  assert.equal(await scope.getByRole('link',{name:'Download project ZIP'}).getAttribute('href'),'/export/fixture.zip');
  // Every API-listed output and source document remains a genuine download, including future/unknown formats.
  const actual=await scope.locator('a[download]').evaluateAll(es=>es.map(e=>e.getAttribute('href')));
  for(const f of new Set([...files,...docs]))assert.ok(actual.includes('/files/fixture/'+f.split('/').map(encodeURIComponent).join('/')),f);
  assert.equal(await scope.locator('img').count(),0); // adversarial filename cannot become markup
  assert.equal(await p.locator('#handoff-plates').getAttribute('open'),'');
  assert.equal(await p.locator('#handoff-parts').getAttribute('open'),null);
  assert.equal(await p.locator('#handoff-summary-parts').evaluate(e=>getComputedStyle(e,'::after').transitionDuration),'0s');
  await p.locator('#handoff-summary-guides-extra').focus();await p.keyboard.press('Space');
  assert.equal(await scope.getByRole('button',{name:'References',exact:true}).isVisible(),true);
  await p.keyboard.press('Escape');assert.equal(await p.locator('#handoff-guides-extra').getAttribute('open'),null);
  const parts=p.locator('#handoff-summary-parts');await parts.focus();await p.keyboard.press('Enter');
  assert.equal(await p.locator('#handoff-parts').getAttribute('open'),'');
  await p.evaluate(()=>refreshDetail());
  assert.equal(await p.locator('#handoff-parts').getAttribute('open'),'');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'handoff-summary-parts');
  await p.keyboard.press('Escape');assert.equal(await p.locator('#handoff-parts').getAttribute('open'),null);
  assert.equal(await p.evaluate(()=>document.activeElement.id),'handoff-summary-parts');
  await p.locator('#handoff-summary-provenance').click();
  assert.match(await p.locator('#handoff-provenance').innerText(),/does not verify a build fingerprint for each file/);
  assert.match(await p.locator('#handoff-provenance').innerText(),/fixture-build-0123456789abcdef/);
  await p.locator('#handoff-summary-provenance').focus();await p.keyboard.press('Escape');
  await scope.getByRole('button',{name:'Assembly guide',exact:true}).click();
  assert.equal(await p.evaluate(()=>S.doc),'out/ASSEMBLY.md');
  await p.locator('#docbody').getByText('Supplier source:',{exact:false}).waitFor();
  await p.evaluate(()=>setTab('files'));
  await scope.getByRole('button',{name:'Review checks',exact:true}).click();assert.equal(await p.evaluate(()=>S.tab),'results');
  // Saved guides remain available with no exports; unbuilt does not discard design sources.
  d={...base,built:false,report:null,review:null,files:[],docs:['DESIGN.md','REFERENCES.md'],built_at:null};
  await p.evaluate(()=>{S.tab='files';return refreshDetail()});
  assert.match(await scope.innerText(),/No downloadable build files/);assert.match(await scope.innerText(),/Shopping list unavailable/);
  assert.equal(await scope.getByRole('button',{name:'Design notes',exact:true}).count(),1);
  assert.equal(await scope.getByRole('button',{name:'Build kit',exact:true}).count(),1);
  // Existing handlers are intercepted to avoid any actual work dispatch.
  await p.evaluate(()=>{window.runMode=m=>window.__handoffMode=m});await scope.getByRole('button',{name:'Build kit',exact:true}).click();
  assert.equal(await p.evaluate(()=>window.__handoffMode),'kit');
  d={...base,stale:true};await p.evaluate(()=>refreshDetail());
  assert.match(await scope.innerText(),/earlier version/);assert.equal(await scope.getByRole('button',{name:'Review previous checks'}).count(),1);
  d={...base,ok:false,problems:2};await p.evaluate(()=>refreshDetail());assert.match(await scope.innerText(),/2 problems to review/);
  d={...base,running:['Build kit']};await p.evaluate(()=>refreshDetail());assert.match(await scope.innerText(),/Work in progress/);
  d={...base,review:{ok:true},report:{...base.report,requirements:[{id:'motion',skipped:true}]}};await p.evaluate(()=>refreshDetail());
  assert.match(await scope.innerText(),/Some checks were not run/);assert.doesNotMatch(await scope.innerText(),/Strength is unproven/);
  // Long names, render inspection, and a source-only project preserve the same routes.
  d={...base,renders:['out/renders/assembly.png'],files:[...files,'out/parts/'+('long_part_name_'.repeat(12))+'.stl']};await p.evaluate(()=>refreshDetail());
  await p.locator('#handoff-summary-parts').click();
  assert.equal(await scope.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  await p.locator('#handoff-summary-renders').click();
  assert.equal(await p.locator('#handoff-renders a').getAttribute('href'),'/files/fixture/out/renders/assembly.png');
  await p.locator('#handoff-renders a').click();assert.equal(await p.locator('#lb').isVisible(),true);
  await p.locator('#lb').click();
  // Capture representative paused/review-needed evidence in both themes, including unfolded files.
  d=structuredClone(base);await p.evaluate(()=>refreshDetail());
  if(await p.locator('#handoff-parts').getAttribute('open')===null)await p.locator('#handoff-summary-parts').click();
  await scope.scrollIntoViewIfNeeded();
  await p.evaluate(()=>{document.activeElement.blur();$('#main').scrollTop=$('.files-handoff').offsetTop-$('#main').offsetTop-20;});
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.equal(await scope.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  await p.screenshot({path:CAPTURE_PATH+`/handoff-${theme}-${width}.png`,fullPage:true});
  await p.locator('#handoff-summary-parts').scrollIntoViewIfNeeded();
  await p.screenshot({path:CAPTURE_PATH+`/handoff-files-${theme}-${width}.png`,fullPage:true});
  assert.deepEqual(errors,[]);assert.ok(requests.every(([method])=>method==='GET'),JSON.stringify(requests));
  console.log(JSON.stringify({theme,width,downloads:actual.length,errors}));await p.close();
 }
}finally{await browser.close();}
'''.replace('"BROWSER_HELPER"', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('HTML_PATH', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE_PATH', json.dumps(str(capture))), encoding='utf-8')
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
