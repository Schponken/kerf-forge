"""Assembly order, independent replays and keyboard completion in the saved viewer."""
import json
import subprocess
from pathlib import Path

from kerf import assembly as A, viewer
from test_viewer import proj


def test_assembly_reading_replays_and_keyboard(proj, tmp_path):
    data = viewer.data(proj, A.plan(proj), {"project": "Assembly flow fixture", "problems": []})
    step = data["steps"]["steps"][0]
    step["lines"] = ["1. Press the inserts into base before joining the carriage.",
                     "2. Align the carriage, then fasten it to base.",
                     "3. Check that the carriage can move freely."]
    step["demos"] = []
    # Synthetic path proof exercises the consumer; producer clearance is tested separately.
    for group in step["groups"]:
        group["motion"] = dict(status="sampled_clear", offset_mm=[0, 0, 20], samples=21, max_step_mm=1, seat_checked=True)
    step["inserts"] = [dict(item="base", at=[x, 0, 10], dir=[0, 0, -1],
                            screw="M3", od=4.6, len=5) for x in [20, 80]]
    page = tmp_path / "viewer.html"
    page.write_text(viewer.html(data), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "assembly.mjs"
    script.write_text(r"""import {chromium} from PLAYWRIGHT;
import assert from 'node:assert/strict';
const browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
  const p=await browser.newPage({viewport:{width:1440,height:960}}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.goto(PAGE); await p.waitForFunction(()=>window.__kerf);
  await p.click('#tabAsm'); await p.evaluate(()=>{window.__kerf.asm.speed=4;return window.__kerf.asm.show(1,false);});
  assert.ok(await p.evaluate(()=>!!(document.querySelector('#asm .txt').compareDocumentPosition(document.querySelector('.sites')) & Node.DOCUMENT_POSITION_FOLLOWING)), 'written order precedes site tools');
  assert.match(await p.textContent('.sites'),/threaded metal sleeve/);
  assert.equal(await p.locator('.tl button:not([aria-label])').count(),0);
  assert.equal(await p.locator('.tl [aria-current="step"]').getAttribute('data-go'),'1');
  await p.screenshot({path:DESKTOP});
  await p.locator('#a_site_next').focus(); await p.keyboard.press('Enter');
  assert.equal(await p.evaluate(()=>window.__kerf.asm.site),1);
  assert.equal(await p.evaluate(()=>document.activeElement.id),'a_site', 'last site transfers focus to its selector');
  await p.locator('#dbx').focus(); await p.keyboard.press('Space');
  assert.equal(await p.locator('#dbx').getAttribute('aria-pressed'),'true');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'dbx');
  assert.equal(await p.textContent('#a_play'),'Play all', 'Space activates the focused completion button');
  await p.keyboard.press('Space');
  assert.equal(await p.locator('#dbx').getAttribute('aria-pressed'),'false');
  await p.locator('.tl [data-go="1"]').focus(); await p.keyboard.press('Space');
  assert.equal(await p.locator('.tl [data-go="1"]').evaluate(el=>el===document.activeElement),true);
  assert.equal(await p.textContent('#a_play'),'Play all');
  // A local technique stays on its site; a whole-step replay moves checked parts and keeps hardware static.
  await p.click('#a_install_re'); await p.waitForFunction(()=>window.__kerf.asm.demo?.contact);
  assert.deepEqual(await p.evaluate(()=>window.__kerf.asm.target.at),[80,0,10]);
  await p.locator('#a_pause').focus(); await p.keyboard.press('Space');
  const paused=await p.evaluate(()=>window.__kerf.asm.demo.tool.position.toArray());
  await p.waitForTimeout(180);
  assert.deepEqual(await p.evaluate(()=>window.__kerf.asm.demo.tool.position.toArray()),paused);
  await p.keyboard.press('Space');
  await p.waitForFunction(()=>window.__kerf.asm.demo?.phase==='withdraw');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'a_pause');
  await p.click('#a_re'); await p.waitForFunction(()=>window.__kerf.groups.get('base').matrix.elements[14]>0);
  assert.equal(await p.evaluate(()=>!!window.__kerf.asm.demo),false,'whole-step replay does not animate unverified tools');
  await p.waitForFunction(()=>!window.__kerf.asm.busy);
  assert.equal(await p.textContent('#a_play'),'Play all');
  await p.click('#a_locate');
  await p.click('#a_play'); await p.waitForFunction(()=>window.__kerf.groups.get('base').matrix.elements[14]>0);
  assert.equal(await p.textContent('#ab_play'),'Stop walkthrough');
  await p.click('#ab_play');
  const stopped=await p.evaluate(()=>({i:window.__kerf.asm.i,t:window.__kerf.asm.target.at}));
  await p.waitForTimeout(1500);
  assert.deepEqual(await p.evaluate(()=>({i:window.__kerf.asm.i,t:window.__kerf.asm.target.at})),stopped);
  assert.equal(await p.evaluate(()=>!!window.__kerf.asm.demo || window.__kerf.asm.busy),false);
  await p.evaluate(()=>window.__kerf.asm.show(window.__kerf.asm.cards.length-1,false));
  assert.match(await p.textContent('#asm'),/does not confirm your physical assembly/);
  assert.doesNotMatch(await p.textContent('#asm'),/it's built/);
  assert.deepEqual(errors,[]);
  const phone=await browser.newPage({viewport:{width:390,height:844},colorScheme:'dark',reducedMotion:'reduce'}), phoneErrors=[];
  phone.on('pageerror',e=>phoneErrors.push(e.message));
  await phone.goto(PAGE); await phone.waitForFunction(()=>window.__kerf);
  await phone.click('#tabAsm'); await phone.evaluate(()=>window.__kerf.asm.show(1,false));
  assert.match(await phone.textContent('.sites'),/Reduced motion is on/);
  assert.equal(await phone.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.ok(await phone.locator('#dbx').evaluate(el=>el.getBoundingClientRect().height>=44));
  await phone.screenshot({path:PHONE});
  await phone.locator('#dbx').focus(); await phone.keyboard.press('Space');
  assert.equal(await phone.locator('#dbx').getAttribute('aria-pressed'),'true');
  assert.equal(await phone.evaluate(()=>document.activeElement.id),'dbx');
  assert.deepEqual(phoneErrors,[]);
} finally { await browser.close(); }
""".replace("PLAYWRIGHT", json.dumps(str(root / "tools/render/node_modules/playwright/index.mjs")))
       .replace("PAGE", json.dumps(page.as_uri()))
       .replace("DESKTOP", json.dumps(str(tmp_path / "desktop.png")))
       .replace("PHONE", json.dumps(str(tmp_path / "phone.png"))), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
