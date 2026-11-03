"""Exact installation sites and schematic tool demonstrations in a real browser."""
import subprocess
from pathlib import Path

from kerf import assembly as A, viewer
from test_viewer import proj


def test_installation_sites_tools_and_reduced_motion(proj, tmp_path):
    data = viewer.data(proj, A.plan(proj), {"project": "t", "problems": []})
    steps = data["steps"]["steps"]
    # Legacy saved paths have no clearance proof; manual site technique still works.
    for step in steps:
        for group in step["groups"]:
            group.pop("motion", None)
    s = steps[0]
    s["demos"] = ["slide"]
    s["inserts"] = [dict(item="base", at=[x, 0, 10], dir=[0, 0, -1], screw="M3", od=4.6, len=5) for x in [20, 80]]
    s["screws"] = [dict(male="carriage", female="base", at=[30, 0, 10], dir=[0, 0, -1], screw="M3", len=10, phase=1, head="socket")]
    s["pins"] = [dict(id="base:pin:0", item="base", items=["base", "carriage"], pin="shoulder4", screw="M3", kind="shoulder", at=[10, -15, 5], dir=[0, 1, 0], len=12, od=4, shoulder_len=8, thread_len=4, thread_d=3, head_d=6, head_h=2, phase=1),
                 dict(id="unknown", item="base", items=["base", "carriage"], pin="dowel4", kind="dowel", at=None, dir=None, len=12, od=4, warning="Axial seat is not recorded.")]
    steps[1]["title"] = "Press heat-set inserts into carriage"
    steps[1]["inserts"] = [dict(item="carriage", at=None, dir=None, screw="M3", od=4.6, len=5)]
    steps[2]["inserts"] = [dict(item="flap", at=[10, 0, 20], dir=[0, -1, 0], screw="M3", od=None, len=None, warning="Catalog dimensions unavailable.")]
    page = tmp_path / "v.html"
    page.write_text(viewer.html(data), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "check.mjs"
    script.write_text(r"""import {chromium} from 'PLAYWRIGHT';
import assert from 'node:assert/strict';
const b = await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
  const p = await b.newPage({viewport:{width:1280,height:800}}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.goto('file://PAGE'); await p.waitForFunction(()=>window.__kerf);
  await p.click('#tabAsm'); await p.evaluate(()=>window.__kerf.asm.show(1));
  assert.equal(await p.locator('#a_site option').count(),4);
  assert.match(await p.textContent('#asm'),/Axial seat is not recorded/);
  const first=await p.evaluate(()=>{const K=window.__kerf,t=K.asm.target;return {at:t.at,dir:t.dir,item:t.item,marker:t.marker.position.toArray(),visible:K.groups.get(t.item).visible,demo:!!K.asm.demo};});
  assert.deepEqual(first,{at:[20,0,10],dir:[0,0,-1],item:'base',marker:[20,0,10],visible:true,demo:false});
  await p.waitForFunction(()=>document.querySelector('.site-leader line')?.getAttribute('x1'));
  const leader=await p.evaluate(()=>{const K=window.__kerf,v=K.asm.target.marker.getWorldPosition(K.camera.position.clone()).project(K.camera),c=document.querySelector('canvas'),line=document.querySelector('.site-leader line');return {x:+line.getAttribute('x1'),expected:(v.x+1)*c.clientWidth/2,opacity:+document.querySelector('.lab.target').style.opacity};});
  assert.ok(Math.abs(leader.x-leader.expected)<1); assert.equal(leader.opacity,1);
  await p.click('#a_site_next'); assert.deepEqual(await p.evaluate(()=>window.__kerf.asm.target.at),[80,0,10]);
  await p.click('#a_site_prev');
  await p.click('#a_install_re'); await p.waitForFunction(()=>window.__kerf.asm.demo?.contact);
  const contact=await p.evaluate(()=>{const d=window.__kerf.asm.demo;const a=d.tool.position.clone().sub(d.hardware.position);const y=d.tool.position.clone().set(0,1,0).applyQuaternion(d.tool.quaternion);return {gap:a.length(),axis:y.dot(d.hardware.userData.dir),smoke:d.smoke.children.some(w=>w.material.opacity>0),kind:d.kind};});
  assert.equal(contact.kind,'iron'); assert.ok(contact.gap<1e-6 && contact.axis>0.999 && contact.smoke);
  await p.click('#a_pause'); const frozen=await p.evaluate(()=>window.__kerf.asm.demo.tool.position.toArray());
  await p.waitForTimeout(180); assert.deepEqual(await p.evaluate(()=>window.__kerf.asm.demo.tool.position.toArray()),frozen);
  await p.click('#a_pause'); await p.waitForFunction(()=>window.__kerf.asm.demo?.phase==='withdraw');
  assert.ok(await p.evaluate(()=>window.__kerf.asm.demo.smoke.children.every(w=>w.material.opacity===0)));
  await p.waitForFunction(()=>!window.__kerf.asm.demo); assert.ok(await p.isDisabled('#a_pause'));
  // Replaying then changing site disposes tool geometry/materials and cannot mutate the next scene.
  await p.click('#a_install_re'); await p.waitForFunction(()=>window.__kerf.asm.demo?.tool.parent);
  await p.evaluate(()=>{window.disposed=0;window.oldTool=window.__kerf.asm.demo.tool;window.oldTool.traverse(o=>{o.geometry?.addEventListener('dispose',()=>window.disposed++);o.material?.addEventListener('dispose',()=>window.disposed++);});});
  await p.selectOption('#a_site','2');
  assert.ok(await p.evaluate(()=>window.disposed>0 && !window.oldTool.parent && !window.__kerf.asm.demo));
  await p.click('#a_install_re'); await p.waitForFunction(()=>window.__kerf.asm.demo?.contact);
  const driver=await p.evaluate(()=>{const d=window.__kerf.asm.demo;return {kind:d.kind,headGap:d.tool.position.distanceTo(d.hardware.position),angle:d.tool.quaternion.angleTo(d.hardware.quaternion),smoke:d.smoke.children.length};});
  assert.equal(driver.kind,'driver'); assert.ok(Math.abs(driver.headGap-3)<1e-6 && driver.angle<1e-6); assert.equal(driver.smoke,0);
  await p.selectOption('#a_site','0'); await p.click('#a_install_re'); await p.waitForFunction(()=>window.__kerf.asm.demo?.contact);
  await p.click('[data-demo="slide"]'); assert.ok(await p.evaluate(()=>!window.__kerf.asm.demo && !!window.__kerf.asm.target));
  await p.selectOption('#a_site','3');
  const pivot=await p.evaluate(()=>[...window.__kerf.groups.get('base').children].find(o=>o.userData.siteIndex===3).children.map(m=>[m.geometry.parameters.radiusTop,m.geometry.parameters.height]));
  assert.deepEqual(pivot,[[2,8],[1.5,4],[3,2]]);
  await p.click('#a_install_re'); await p.waitForFunction(()=>window.__kerf.asm.demo?.contact);
  assert.equal(await p.evaluate(()=>window.__kerf.asm.demo.kind),'driver');
  assert.deepEqual(await p.evaluate(()=>window.__kerf.asm.target.dir),[0,1,0]);
  await p.click('#a_overview'); assert.ok(await p.evaluate(()=>window.__kerf.asm.demo.paused));
  await p.click('#a_locate'); assert.ok(await p.evaluate(()=>!window.__kerf.asm.demo));
  await p.evaluate(()=>window.__kerf.asm.show(2,false));
  assert.match(await p.textContent('#asm'),/Exact installation locations are unavailable/);
  assert.match(await p.textContent('#asm'),/Static assembly reference; part motion is not shown/);
  assert.ok(await p.evaluate(()=>window.__kerf.groups.get('base').parent.children.filter(o=>o.userData.before && o.visible).length===0),'unverified explode offsets must not suggest an insertion path');
  await p.uncheck('#a_ghost');
  assert.ok(await p.evaluate(()=>window.__kerf.groups.get('base').parent.children.filter(o=>o.userData.before).every(o=>!o.visible)));
  await p.evaluate(()=>window.__kerf.asm.show(3,false));
  assert.match(await p.textContent('#asm'),/Hardware dimensions unavailable; location marker only/);
  await p.click('#a_install_re'); assert.ok(await p.evaluate(()=>!window.__kerf.asm.demo && !!window.__kerf.asm.target));
  await p.click('#tray-close'); assert.equal(await p.locator('.site-leader').count(),0);
  assert.deepEqual(errors,[]);
  const r=await b.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});const re=[];r.on('pageerror',e=>re.push(e.message));
  await r.goto('file://PAGE'); await r.waitForFunction(()=>window.__kerf);await r.click('#tabAsm');await r.evaluate(()=>window.__kerf.asm.show(1));
  await r.click('#a_install_re');await r.waitForTimeout(100);
  assert.ok(await r.evaluate(()=>!window.__kerf.asm.demo && !!window.__kerf.asm.target));
  assert.equal(await r.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await r.locator('#a_site_next').focus(); await r.keyboard.press('Enter');
  assert.equal(await r.evaluate(()=>window.__kerf.asm.site),1);
  await r.click('[data-demo="slide"]'); assert.ok(await r.evaluate(()=>!window.__kerf.asm.demo && !window.__kerf.asm.busy));
  assert.deepEqual(re,[]);
} finally { await b.close(); }
""".replace("PLAYWRIGHT", str(root / "tools/render/node_modules/playwright/index.mjs")).replace("PAGE", str(page)), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
