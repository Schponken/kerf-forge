"""Synthetic boxes test the checked-path consumer without CAD builds or live jobs."""
import base64
import json
import struct
import subprocess
from pathlib import Path

from kerf import viewer


def assembly_motion_data():
    def box(name, lo, hi):
        vertices = [v for k in range(8) for v in [hi[0] if k & 1 else lo[0], hi[1] if k & 2 else lo[1], hi[2] if k & 4 else lo[2]]]
        triangles = [0, 2, 1, 1, 2, 3, 4, 5, 6, 5, 7, 6, 0, 1, 4, 1, 5, 4,
                     2, 6, 3, 3, 6, 7, 0, 4, 2, 2, 4, 6, 1, 3, 5, 3, 7, 5]
        return dict(id=name, label=name, role="printed", color="#a2c4df", verts=base64.b64encode(struct.pack('<24f', *vertices)).decode(),
                    tris=base64.b64encode(struct.pack('<36I', *triangles)).decode(), nv=8, nt=12, explode=[1, 0, 0], joints=[])
    def group(items, offset, phase=1):
        return dict(items=items, off=[-300, -300, -300], phase=phase, motion=dict(status="sampled_clear", source="guide_candidate",
                    offset_mm=offset, samples=31, max_step_mm=1, seat_checked=True, reason="Synthetic axis-aligned box path; sampled clear."))
    def step(n, title, groups, present):
        return dict(n=n, title=title, groups=groups, items=groups[0]["items"], present=present, inserts=[], screws=[], pins=[], demos=[], lines=[], bench_for=None)
    base = step(1, "Place the base", [group(["base"], [0, 0, 0])], ["base"])
    join = step(2, "Join the prepared parts", [group(["left", "cap"], [0, 0, 30]), group(["right"], [30, 0, 0], 2)], ["base", "left", "cap", "right"])
    join["inserts"] = [dict(item="right", at=[15, 10, 8], dir=[0, 0, -1], screw="M3", od=4, len=4,
                            motion=dict(status="unverified", reason="Tool clearance has not been checked."))]
    # A previously prepared insert must stay hidden while its incoming receiver is only a future ghost.
    base["inserts"] = [{**join["inserts"][0], "at": [15, 6, 8]}]
    return dict(viewer_schema=1, project_dir="synthetic-assembly-motion", items=[box("base", [0, 0, 0], [20, 20, 4]),
                box("left", [0, 0, 4], [8, 20, 8]), box("cap", [0, 0, 8], [8, 20, 10]), box("right", [12, 0, 4], [20, 20, 8])],
                joints=[], bounds=[[0, 0, 0], [20, 20, 10]], params={}, report=dict(project="Synthetic assembly motion fixture", parts={}, purchased={}, problems=[]),
                steps=dict(steps=[base, join], intro=[], outro=[]))


def test_checked_paths_sequence_and_static_fallback(tmp_path):
    page = tmp_path / "motion.html"
    page.write_text(viewer.html(assembly_motion_data()), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "motion.mjs"
    script.write_text(r'''import {chromium} from PLAYWRIGHT;
import assert from 'node:assert/strict';
const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 const p=await b.newPage({viewport:{width:1440,height:960}}),errors=[];
 p.on('pageerror',e=>errors.push(e.message));
 await p.goto(PAGE);await p.waitForFunction(()=>window.__kerf);
 await p.click('#tabAsm');await p.evaluate(()=>{window.__kerf.asm.speed=4;return window.__kerf.asm.show(2,false);});
 await p.evaluate(()=>{
  const K=window.__kerf;window.samples=[];window.watch=true;
  const sample=()=>{if(!window.watch)return;const row={};
   for(const id of ['base','left','cap','right']){const g=K.groups.get(id);row[id]={at:g.matrix.elements.slice(12,15),solid:g.visible&&g.userData.mesh.material.opacity>0.5};}
   row.hardware=K.groups.get('right').children.some(o=>o.userData.hardware&&o.visible);
   row.demo=!!K.asm.demo;window.samples.push(row);requestAnimationFrame(sample);};requestAnimationFrame(sample);
  window.play=K.asm.show(2,true,null,true);
 });
 await p.evaluate(()=>window.play);await p.evaluate(()=>{window.watch=false;});
 const samples=await p.evaluate(()=>window.samples);
 assert.ok(samples.some(s=>s.left.at[2]>0)&&samples.some(s=>s.right.at[0]>0),'both checked paths really animate');
 const bounds={base:[[0,0,0],[20,20,4]],left:[[0,0,4],[8,20,8]],cap:[[0,0,8],[8,20,10]],right:[[12,0,4],[20,20,8]]};
 let sawInsertStaged=false;
 for(const row of samples){
  assert.deepEqual(row.left.at,row.cap.at,'a prepared rigid group keeps its relative pose');
  assert.ok(Math.abs(row.left.at[0])<1e-6&&Math.abs(row.left.at[1])<1e-6&&row.left.at[2]>=0&&row.left.at[2]<=30,JSON.stringify(row));
  assert.ok(row.right.at[0]>=0&&row.right.at[0]<=30&&Math.abs(row.right.at[1])<1e-6&&Math.abs(row.right.at[2])<1e-6);
  if(row.right.at[0]>0)assert.deepEqual(row.left.at,[0,0,0],'second group starts after first seats');
  if(row.hardware){assert.equal(row.right.solid,true,'insert never appears before its receiver');if(row.right.at[0]>0)sawInsertStaged=true;}
  assert.equal(row.demo,false,'checked assembly does not autoplay an unverified tool');
  const ids=Object.keys(bounds).filter(id=>row[id].solid);
  for(let a=0;a<ids.length;a++)for(let c=a+1;c<ids.length;c++){
   const x=ids[a],y=ids[c],dx=row[x].at,dy=row[y].at;
   const overlap=[0,1,2].map(k=>Math.min(bounds[x][1][k]+dx[k],bounds[y][1][k]+dy[k])-Math.max(bounds[x][0][k]+dx[k],bounds[y][0][k]+dy[k]));
   assert.ok(overlap.some(v=>v<=1e-6),`${x}/${y} pass through each other: ${overlap}`);
  }
 }
 assert.ok(sawInsertStaged,'phase-two insert belongs to the staged receiver before it mates');
 assert.deepEqual(await p.evaluate(()=>['left','cap','right'].map(id=>window.__kerf.groups.get(id).matrix.elements.slice(12,15))),[[0,0,0],[0,0,0],[0,0,0]]);
 assert.match(await p.textContent('#asm'),/checked at sampled positions/);
 assert.match(await p.textContent('.sites'),/Technique illustration — tool clearance not checked/);
 await p.click('#a_install_re');await p.waitForFunction(()=>window.__kerf.asm.demo?.contact);
 assert.equal(await p.evaluate(()=>window.__kerf.asm.demo.kind),'iron','an explicit manual technique remains available');
 await p.click('#a_locate');
 // Blocked, missing, and malformed proof never reuse the old display explode offset.
 for(const proof of [{status:'blocked',reason:'Fixture blocker crosses the path.'},null,{status:'sampled_clear',offset_mm:[0,0,30],samples:0,max_step_mm:1}]){
  await p.evaluate(m=>{window.__kerf.D.steps.steps[1].groups[1].motion=m;return window.__kerf.asm.show(2,true,null,true);},proof);
  assert.match(await p.textContent('#asm'),/Static assembly reference; part motion is not shown/);
  assert.deepEqual(await p.evaluate(()=>['left','cap','right'].map(id=>window.__kerf.groups.get(id).matrix.elements.slice(12,15))),[[0,0,0],[0,0,0],[0,0,0]]);
  assert.equal(await p.evaluate(()=>window.__kerf.asm.busy||!!window.__kerf.asm.demo),false);
  assert.equal(await p.evaluate(()=>window.__kerf.groups.get('base').parent.children.some(o=>o.userData.before)),false);
 }
 await p.screenshot({path:DESKTOP});
 assert.deepEqual(errors,[]);
 const phone=await b.newPage({viewport:{width:390,height:844},reducedMotion:'reduce',colorScheme:'dark'});
 const phoneErrors=[];phone.on('pageerror',e=>phoneErrors.push(e.message));await phone.goto(PAGE);await phone.waitForFunction(()=>window.__kerf);
 await phone.click('#tabAsm');await phone.evaluate(()=>window.__kerf.asm.show(2,true,null,true));
 assert.deepEqual(await phone.evaluate(()=>['left','cap','right'].map(id=>window.__kerf.groups.get(id).matrix.elements.slice(12,15))),[[0,0,0],[0,0,0],[0,0,0]]);
 assert.equal(await phone.evaluate(()=>window.__kerf.asm.busy||!!window.__kerf.asm.demo),false);
 assert.equal(await phone.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await phone.screenshot({path:PHONE});assert.deepEqual(phoneErrors,[]);
}finally{await b.close();}
'''.replace('PLAYWRIGHT', json.dumps(str(root / 'tools/render/node_modules/playwright/index.mjs')))
       .replace('PAGE', json.dumps(page.as_uri())).replace('DESKTOP', json.dumps(str(tmp_path / 'motion-desktop.png')))
       .replace('PHONE', json.dumps(str(tmp_path / 'motion-phone.png'))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr


def test_tween_clock_cannot_extend_a_checked_path_before_its_start(tmp_path):
    source = (Path(viewer.__file__).parent / 'assets/viewer.html').read_text(encoding='utf-8')
    clock = source[source.index('function stepTweens(now) {'):source.index('function camTo(')]
    script = tmp_path / 'clock.cjs'
    script.write_text("const assert=require('node:assert/strict');const AS={demo:null};const redraw=()=>{};const values=[];let ended=0;"
                      "const TW=[{t0:100,dur:100,ease:x=>x,fn:x=>values.push(x),res:()=>ended++}];\n" + clock +
                      "stepTweens(99);stepTweens(150);stepTweens(210);assert.deepEqual(values,[0,0.5,1]);"
                      "assert.equal(ended,1);assert.equal(TW.length,0);", encoding='utf-8')
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
