"""Selected viewer terms explain themselves offline without opening a menu or searching."""
import json
import re
import subprocess
from pathlib import Path

from kerf import glossary, viewer
from test_viewer_stage import stage_data


def definition_data():
    d = stage_data()
    d['report']['parts'] = {'support': {'material': 'PLA', 'mass_est_g': 4, 'size_mm': [30, 30, 30], 'infill': .2}}
    d['joints'] = [{'name': 'hinge', 'kind': 'revolute', 'home': 0, 'range': [0, 90], 'axis': [0, 0, 1],
                    'point': [0, 0, 0], 'child': 'support', 'moves': ['support']}]
    d['items'][0]['joints'] = ['hinge']
    d['report']['assembly'] = {'sweeps': [{'joint': 'hinge', 'clear': True}]}
    d['items'].append({**d['items'][0], 'id': 'clear_space', 'role': 'keepout', 'joints': []})
    return d


def test_viewer_embeds_selected_glossary_without_changing_saved_data(tmp_path, monkeypatch):
    d = definition_data()
    malicious = '</script><script>window.injected=true</script>'
    monkeypatch.setitem(glossary.TERMS, 'PLA', malicious)
    html = viewer.html(d)
    block = re.search(r'<script type="application/json" id="kerf-terms">(.*?)</script>', html, re.S).group(1)
    terms = json.loads(block)
    expected = {'revolute', 'sweep', 'keep-out', 'stress', 'safety factor', 'infill', 'overhang',
                'PLA', 'PETG', 'ASA', 'PA-CF', 'TPU'}
    assert set(terms) == expected
    assert terms == {key: glossary.TERMS[key] for key in expected}
    assert malicious not in html
    assert '/*TERMS*/' not in html and '/api/glossary' not in html
    page = tmp_path / 'viewer.html'
    page.write_text(html)
    assert viewer.embedded(page) == d


def test_viewer_definitions_hover_focus_and_touch_offline(tmp_path):
    page = tmp_path / 'viewer.html'
    page.write_text(viewer.html(definition_data()))
    root = Path(__file__).resolve().parents[1]
    capture = Path('/tmp/kerf-viewer-definitions')
    capture.mkdir(exist_ok=True)
    script = tmp_path / 'definitions.mjs'
    script.write_text(r'''import {chromium} from 'PLAYWRIGHT';
import assert from 'node:assert/strict';
const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 for(const touch of [false,true]) {
  const width=touch?390:1440,height=touch?844:960;
  const p=await b.newPage({viewport:{width,height},hasTouch:touch,colorScheme:touch?'dark':'light',reducedMotion:'reduce'}),errors=[],network=[];
  p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  await p.goto('file://PAGE');await p.waitForFunction(()=>window.__kerf);
  const popup=p.getByRole('dialog');
  await p.locator('[data-tab=motion]').click();
  const rotating=p.getByRole('button',{name:'Explain rotating joint',exact:true});
  assert.equal(await rotating.isVisible(),true);
  assert.equal(await p.locator('[data-play=hinge]').innerText(),'Move through range');
  if(touch) await rotating.tap();else await rotating.hover();
  await popup.waitFor();assert.match(await popup.innerText(),/joint that turns around an axis/);
  assert.equal(await rotating.getAttribute('aria-describedby'),'word-meaning');
  const fits=async()=>{const r=await popup.boundingBox();assert.ok(r.x>=0&&r.y>=0&&r.x+r.width<=width&&r.y+r.height<=height,JSON.stringify(r));};
  await fits();assert.equal(await popup.evaluate(e=>getComputedStyle(e).animationName),'none');
  if(!touch){
   assert.equal(await p.locator('[data-tab=motion]').evaluate(e=>e===document.activeElement),true,'hover preserves focus');
   const r=await rotating.boundingBox(),q=await popup.boundingBox(),gap=q.y>r.y?r.y+r.height+6:r.y-6;
   await p.mouse.move(r.x+r.width/2,gap);await p.waitForTimeout(100);
   await p.mouse.move(q.x+q.width/2,q.y+q.height/2);await p.waitForTimeout(300);
   assert.equal(await popup.isVisible(),true,'pointer can cross into the popup');
   await p.keyboard.press('Escape');assert.equal(await popup.count(),0);
   assert.equal(await p.locator('#tool-tray').isVisible(),true,'Escape only dismisses the definition');
   await p.mouse.move(1,1);await rotating.focus();await popup.waitFor();
   assert.equal(await rotating.evaluate(e=>e===document.activeElement),true,'focus reveals the definition immediately');
   await p.keyboard.press('Enter');await p.keyboard.press('Escape');
   assert.equal(await popup.count(),0);assert.equal(await rotating.evaluate(e=>e===document.activeElement),true);
  }else{
   await popup.getByRole('button',{name:'Close definition'}).tap();assert.equal(await popup.count(),0);
   assert.equal(await rotating.evaluate(e=>e===document.activeElement),true);
  }
  await p.locator('[data-tab=parts]').click();
  const material=p.locator('#parts').getByRole('button',{name:'Explain PLA',exact:true});
  if(touch)await material.tap();else await material.hover();
  await popup.waitFor();assert.match(await popup.innerText(),/easiest, most common printing plastic/);await fits();
  assert.equal(await p.locator('[data-part=support]').getAttribute('aria-pressed'),'false','reading material does not select its part');
  await p.screenshot({path:'CAPTURE/'+(touch?'phone-dark':'desktop-light')+'.png',animations:'disabled'});
  await p.keyboard.press('Escape');assert.equal(await popup.count(),0);
  const keep=p.locator('#parts').getByRole('button',{name:'Explain Space to keep clear',exact:true});
  await keep.focus();await popup.waitFor();assert.match(await popup.innerText(),/space that must stay empty/);
  await p.keyboard.press('Escape');
  await p.locator('[data-tab=print]').click();
  const infill=p.getByRole('button',{name:'Explain infill',exact:true});
  await infill.focus();await popup.waitFor();assert.match(await popup.innerText(),/pattern printed inside a part/);
  await p.locator('#theme').click();assert.equal(await popup.count(),0,'outside click dismisses definition');
  assert.deepEqual(network,[],'offline exported HTML fetches no glossary or other network resource');
  assert.deepEqual(errors,[]);console.log(JSON.stringify({touch,width,height}));await p.close();
 }
}finally{await b.close();}
'''.replace('PLAYWRIGHT', str(root / 'tools/render/node_modules/playwright/index.mjs'))
       .replace('PAGE', str(page)).replace('CAPTURE', str(capture)))
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
