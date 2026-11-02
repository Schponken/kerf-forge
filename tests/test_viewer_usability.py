"""A preview is not a passing check; the finished viewer exposes usable outputs."""
import json
import subprocess
from pathlib import Path

from kerf import assembly as A, viewer
from test_viewer import proj  # shared three-part moving assembly fixture


def test_viewer_keeps_device_and_off_board_mass(proj):
    mass = {'printed_g': 20, 'on_board_g': 5, 'device_g': 25, 'off_board_g': 317}
    d = viewer.data(proj, A.plan(proj), {'project':'Example', 'problems':[], 'mass':mass}, preview=True)
    assert d['report']['mass'] == mass


def test_preview_outputs_and_copy_recovery_in_browser(proj, tmp_path):
    mass = {'device_g':25, 'off_board_g':317}
    rep = {'project':'LongProjectName' * 12 + ' <mount> & camera', 'ok':False, 'problems':['base: exported mesh is not watertight'], 'mass':mass,
           'bom':[{'type':'purchased','item':'Servo','spec':'servos.MG996R','qty':1,'buy':'https://shop.example/servo?a=1&b=2'},
                  {'type':'hardware','item':'Untrusted link','qty':1,'buy':'javascript:alert(1)'}],
           'files':{'plates':[{'file':'plate_1.3mf','parts':['base #1']}]},
           'assembly':{'sweeps':[{'joint':'tilt','range':[-30,60],'clear':False,'samples':9,'collisions':[{'a':'base','b':'flap'}]}, {'joint':'corners','clear':False,'samples':2,'collisions':[{'a':'base','b':'flap'}]}]},
           'requirements':[{'id':'strength','skipped':True,'ok':False,'value':None,'detail':'skipped in quick mode'}]}
    d = viewer.data(proj, A.plan(proj), rep)
    d['report']['preview'] = False
    ready = tmp_path / 'ready.html'
    ready.write_text(viewer.html(d), encoding='utf-8')
    d['report'] = {'project':'Example','preview':True,'ok':False,'problems':rep['problems'], 'problem_cards':d['report']['problem_cards']}
    preview = tmp_path / 'preview.html'
    preview.write_text(viewer.html(d), encoding='utf-8')
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / 'check.mjs'
    script.write_text('''import {chromium} from 'PLAYWRIGHT';
import assert from 'node:assert/strict';
const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 for(const viewport of [{width:1280,height:800},{width:390,height:844}])for(const theme of ['light','dark']) {
 const p=await b.newPage({viewport});const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('file://PREVIEW');await p.waitForFunction(()=>window.__kerf);
 await p.evaluate(t=>{document.documentElement.dataset.theme=t;window.__kerf.restyle()},theme);
 assert.match(await p.locator('#meta').innerText(),/weight not calculated/);
 await p.click('[data-tab="checks"]');assert.match(await p.locator('#checks').innerText(),/Checks are still running/);
 assert.equal(await p.locator('#checks .i.ok').count(),0);assert.equal(await p.locator('#checks .note.bad').count(),1);
 assert.equal(await p.locator('#checks .note.bad details').getAttribute('open'),null);
 await p.locator('#checks .note.bad summary').click();assert.match(await p.locator('#checks .note.bad').innerText(),/exported mesh is not watertight/);assert.doesNotMatch(await p.locator('#checks').innerText(),/No parts overlap/);
 await p.click('[data-tab="print"]');assert.match(await p.locator('#print').innerText(),/still being prepared/);
 await p.click('[data-tab="bom"]');assert.match(await p.locator('#bom').innerText(),/still being prepared/);
 await p.goto('file://READY');await p.waitForFunction(()=>window.__kerf);
 await p.evaluate(t=>{document.documentElement.dataset.theme=t;window.__kerf.restyle()},theme);
 assert.match(await p.locator('#meta').innerText(),/~25 g.*317 g off the device/);
 assert.equal(await p.locator('#title').innerText(),'LongProjectName'.repeat(12)+' <mount> & camera');
 assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await p.click('[data-tab="checks"]');assert.match(await p.locator('#checks').innerText(),/Joint tilt collides while moving/);assert.match(await p.locator('#checks').innerText(),/Combined motion.*has a collision/);
 const skipped=p.locator('#checks .chk').filter({hasText:'strength: not checked in this run'});assert.equal(await skipped.count(),1);assert.equal(await skipped.locator('.i.ok,.i.bad').count(),0);
 await p.click('[data-tab="bom"]');assert.equal(await p.locator('#bom details summary').innerText(),'Part reference');assert.equal(await p.locator('#bom details').getAttribute('open'),null);await p.locator('#bom details summary').click();assert.match(await p.locator('#bom').innerText(),/servos.MG996R/);const shop=p.locator('#bom a');assert.equal(await shop.count(),1);
 assert.equal(await shop.getAttribute('href'),'https://shop.example/servo?a=1&b=2');assert.match(await shop.getAttribute('rel'),/noopener/);
 await p.click('[data-tab="print"]');assert.equal(await p.locator('#print a').getAttribute('href'),'plates/plate_1.3mf');
 assert.match(await p.locator('#print').innerText(),/slice and review/);
 const prompts=[];p.on('dialog',async d=>{prompts.push(d.defaultValue());await d.dismiss()});
 await p.evaluate(()=>{
  Object.defineProperty(navigator,'clipboard',{value:{writeText:async()=>{throw Error('denied')}},configurable:true});document.execCommand=()=>false;
  window.__kerf.inspect('base',0);
 });
 const expected=await p.locator('#insp .loc code').innerText();
 await p.click('#cpw');assert.deepEqual(prompts,[expected]);assert.equal(await p.locator('#cpw').innerText(),'Copy manually');
 assert.equal(await p.locator('body > textarea').count(),0);
 await p.evaluate(()=>{document.execCommand=()=>true});await p.click('#cpw');
 assert.equal(await p.locator('#cpw').innerText(),'Copied');assert.deepEqual(errors,[]);
 await p.close();
 }
} finally {await b.close();}
'''.replace('PLAYWRIGHT',str(root / 'tools/render/node_modules/playwright/index.mjs'))
        .replace('PREVIEW',str(preview)).replace('READY',str(ready)), encoding='utf-8')
    r = subprocess.run(['node',str(script)],capture_output=True,text=True,timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr


def test_viewer_reuses_explanations_without_losing_original_diagnostics(proj):
    message = 'base: exported mesh is not watertight'
    d = viewer.data(proj, A.plan(proj), {'project':'Example','problems':[message],'warnings':[message]}, preview=True)
    card = d['report']['problem_cards'][0]
    assert card['part'] == 'base' and card['title'] != message
    assert card['why'] and card['fix'] and card['detail'] == message
    assert d['report']['design_notes'][0]['detail'] == message
