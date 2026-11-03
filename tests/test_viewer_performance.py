"""Bounded browser checks for idle work, pointer coalescing and GPU resource ownership."""
import subprocess
from pathlib import Path

from kerf import viewer
from test_viewer_stage import stage_data


def test_viewer_idle_hover_and_compare_lifecycle(tmp_path):
    data = stage_data()
    data['items'][0]['joints'] = ['slide']
    data['joints'] = [dict(name='slide', kind='linear', home=0, range=[0, 20],
                           axis=[1, 0, 0], point=[0, 0, 0], moves=['support'])]
    data['steps'] = dict(intro=[], outro=[], steps=[dict(n=1, title='Synthetic insert fixture',
        lines=[], present=['support'], groups=[dict(items=['support'], off=[0, 0, 15], phase=1)],
        screws=[], pins=[], demos=[], inserts=[dict(item='support', at=[7, 7, 8],
        dir=[0, 0, -1], screw='M3', od=4.6, len=5)])])
    page = tmp_path / 'viewer.html'
    page.write_text(viewer.html(data))
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / 'performance.mjs'
    script.write_text(r'''import {chromium} from 'PLAYWRIGHT';
import assert from 'node:assert/strict';
const browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 const p=await browser.newPage({viewport:{width:1280,height:800}}), errors=[];
 p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{
  window.frameCalls=0; const raf=window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame=fn=>raf(t=>{window.frameCalls++;fn(t);});
 });
 await p.goto('file://PAGE'); await p.waitForFunction(()=>window.__kerf);
 await p.waitForTimeout(800);
 const start=await p.evaluate(()=>window.frameCalls); await p.waitForTimeout(300);
 const idleFrames=await p.evaluate(s=>window.frameCalls-s,start);
 // One browser event burst: each pick walks the actual Three meshes, not a mocked raycaster.
 await p.evaluate(()=>{
  const proto=window.KV3.Raycaster.prototype, original=proto.intersectObjects;
  window.raycasts=0; proto.intersectObjects=function(...args){window.raycasts++;return original.apply(this,args);};
  const c=document.querySelector('canvas'), r=c.getBoundingClientRect();
  const at=new window.KV3.Vector3(7.5,7.5,7.5).project(window.__kerf.camera);
  for(let i=0;i<80;i++)c.dispatchEvent(new PointerEvent('pointermove',{clientX:r.x+(at.x+1)*r.width/2+i/100,clientY:r.y+(1-at.y)*r.height/2}));
 });
 await p.waitForTimeout(100); const hoverRaycasts=await p.evaluate(()=>window.raycasts);
 const tip=await p.locator('#tip').innerText(); assert.match(tip,/support/);
 // Leaving before the queued pick must not resurrect the tooltip.
 await p.evaluate(()=>{const c=document.querySelector('canvas');c.dispatchEvent(new PointerEvent('pointermove',{clientX:20,clientY:20}));c.dispatchEvent(new PointerEvent('pointerleave'));});
 await p.waitForTimeout(50); const tipHidden=await p.locator('#tip').evaluate(e=>getComputedStyle(e).display==='none');
 // Explicit joint playback starts from idle and Home lets the scheduler settle again.
 await p.evaluate(()=>document.querySelector('[data-play="slide"]').click());
 await p.waitForTimeout(250);
 assert.ok(await p.evaluate(()=>window.__kerf.groups.get('support').matrix.elements[12]>0));
 await p.evaluate(()=>document.querySelector('[data-home="slide"]').click());
 assert.equal(await p.evaluate(()=>window.__kerf.groups.get('support').matrix.elements[12]),0);
 // A comparison focus uses the shared camera tween; it must wake an idle scheduler.
 await p.evaluate(()=>{const K=window.__kerf;K.compare({items:[K.D.items[0]],summary:[{id:'support',status:'changed',max_mm:1}]});});
 await p.evaluate(()=>document.querySelector('#clegend [data-f]').click());
 await p.waitForFunction(()=>!window.__kerf.asm.busy); await p.waitForTimeout(150);
 await p.locator('canvas').focus(); await p.keyboard.press('-'); await p.waitForTimeout(150);
 const cameraBefore=await p.evaluate(()=>window.__kerf.camera.position.toArray());
 await p.evaluate(()=>document.querySelector('#clegend [data-f]').click());
 await p.waitForFunction(()=>!window.__kerf.asm.busy);
 assert.notDeepEqual(await p.evaluate(()=>window.__kerf.camera.position.toArray()),cameraBefore);
 // Every comparison owns its surface and edge geometry/material, including replacement comparisons.
 const disposed=await p.evaluate(()=>{
  const K=window.__kerf, counts=[];
  for(let i=0;i<3;i++) {
   const ghost=K.groups.get('support').children.find(o=>o.userData.ghostOf), resources=new Set();
   ghost.traverse(o=>{if(o.geometry)resources.add(o.geometry);if(o.material)resources.add(o.material);});
   let n=0;for(const r of resources)r.addEventListener('dispose',()=>n++);
   if(i<2)K.compare({items:[K.D.items[0]],summary:[]});else K.clearCompare();
   if(ghost.parent)throw new Error('comparison ghost remained attached');
   counts.push([n,resources.size]);
  }
  return counts;
 });
 // A live mesh update and its delayed glow removal each wake the idle viewer.
 await p.waitForTimeout(150);
 await p.evaluate(()=>{const K=window.__kerf;K.liveSwap([{...K.D.items[0]}],[],180);});
 assert.equal(await p.evaluate(()=>window.__kerf.groups.get('support').userData.glow),true);
 await p.waitForTimeout(70);const glowStart=await p.evaluate(()=>window.frameCalls);await p.waitForTimeout(180);
 assert.ok(await p.evaluate(s=>window.frameCalls>s,glowStart));
 assert.equal(await p.evaluate(()=>window.__kerf.groups.get('support').userData.glow),false);
 // Orbit damping continues after a drag, then all frame work stops.
 const canvas=p.locator('canvas'), r=await canvas.boundingBox();
 await p.mouse.move(r.x+r.width*.5,r.y+r.height*.5);await p.mouse.down();
 await p.mouse.move(r.x+r.width*.5+65,r.y+r.height*.5+25,{steps:4});await p.mouse.up();
 const released=await p.evaluate(()=>window.__kerf.camera.position.toArray());await p.waitForTimeout(200);
 assert.notDeepEqual(await p.evaluate(()=>window.__kerf.camera.position.toArray()),released);
 await p.waitForTimeout(1400);const end=await p.evaluate(()=>window.frameCalls);await p.waitForTimeout(200);
 const settledFrames=await p.evaluate(s=>window.frameCalls-s,end);
 // Paused installation tweens preserve their clock without polling, then resume explicitly.
 await p.click('#tabAsm');
 await p.evaluate(()=>{const K=window.__kerf;K.asm.speed=4;return K.asm.show(1,false);});
 await p.click('#a_install_re');await p.waitForFunction(()=>window.__kerf.asm.demo?.contact);
 await p.click('#a_pause');await p.waitForTimeout(300);
 const paused=await p.evaluate(()=>({frames:window.frameCalls,tool:window.__kerf.asm.demo.tool.position.toArray()}));
 await p.waitForTimeout(150);
 const pausedFrames=await p.evaluate(s=>window.frameCalls-s,paused.frames);
 assert.deepEqual(await p.evaluate(()=>window.__kerf.asm.demo.tool.position.toArray()),paused.tool);
 await p.click('#a_pause');await p.waitForFunction(()=>!window.__kerf.asm.demo);
 console.log(JSON.stringify({idleFrames,hoverRaycasts,disposed,settledFrames,pausedFrames,tipHidden}));
 assert.deepEqual(errors,[]);
 assert.equal(idleFrames,0,'stationary viewer should schedule no frame callbacks');
 assert.equal(hoverRaycasts,1,'pointer burst should pick only the latest position once');
 assert.equal(tipHidden,true,'pointer leave cancels queued hover');
 assert.deepEqual(disposed,[[4,4],[4,4],[4,4]]);
 assert.equal(settledFrames,0,'damping must stop scheduling once settled');
 assert.equal(pausedFrames,0,'paused installation must not poll frames');
}finally{await browser.close();}
'''.replace('PLAYWRIGHT', str(root / 'tools/render/node_modules/playwright/index.mjs')).replace('PAGE', str(page)))
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=60)
    print(result.stdout.strip())
    assert result.returncode == 0, result.stdout + result.stderr
