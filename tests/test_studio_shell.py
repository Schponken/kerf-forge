"""Studio's shared navigation, theme and keyboard controls, using synthetic API data."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.browser
def test_studio_shell_themes_navigation_and_keyboard(tmp_path):
    root = Path(__file__).resolve().parents[1]
    capture = Path(os.environ.get("KERF_SHELL_SCREENSHOTS", str(tmp_path)))
    capture.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "studio-shell.mjs"
    script.write_text(r'''
import {browser as openBrowser} from BROWSER_HELPER;
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(STUDIO_HTML_PATH,'utf8'),browser=await openBrowser();
const previewDir=process.env.KERF_SHELL_PREVIEW_DIR;
const previews=previewDir?JSON.parse(await fs.readFile(previewDir+'/projects.json','utf8')):[];
try {
 for(const theme of ['light','dark']) for(const width of [1440,390]) {
  const p=await browser.newPage({viewport:{width,height:900},colorScheme:theme}),errors=[];
  p.on('pageerror',e=>errors.push(e.message));await p.emulateMedia({reducedMotion:'reduce'});
  let projects=[],jobs=[],settings={notify:true,sound:false};
  await p.route('**/*',r=>{const path=new URL(r.request().url()).pathname;
   if(path==='/')return r.fulfill({contentType:'text/html',body:html});
   if(previewDir && path.startsWith('/preview/'))return fs.readFile(previewDir+'/'+path.split('/').pop()).then(body=>r.fulfill({contentType:'image/png',body}));
   if(path==='/fixture-preview.svg')return r.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><path d="M80 270V90H150V200H390V270Z" fill="#305f86"/></svg>'});
   if(path==='/api/projects')return r.fulfill({json:{projects,claude:false}});
   if(path==='/api/jobs')return r.fulfill({json:{jobs,sessions:[]}});
   if(path==='/api/quotes')return r.fulfill({json:{quotes:[]}});
   if(path==='/api/settings'){if(r.request().method()==='POST')settings={...settings,...r.request().postDataJSON()};return r.fulfill({json:settings});}
   if(path==='/api/work')return r.fulfill({json:{items:[{id:'fixture-work',provider:'Codex',state:'running',title:'Check the mounting bracket',activity:'Comparing bolt clearances with the design requirements.',remaining:['Inspect the result','Prepare the pull request'],source_label:'Illustrative fixture'}],sources:[]}});
   if(path.startsWith('/api/project/'))return r.fulfill({json:{name:path.split('/').pop(),title:'Illustrative project',built:false,files:[],params:[],history:[],modes:[],live_on:false}});
   return r.fulfill({json:{}});
  });
  await p.goto('http://kerf.test/');
  assert.equal(await p.locator('html').getAttribute('data-theme'),theme); // OS preference is the initial default.
  projects=Array.from({length:12},(_,i)=>({name:'fixture_'+i,title:['Workshop shelf bracket','Desk cable guide','Camera pan mount'][i%3]+` ${i+1}`,description:'Illustrative fixture',built:false}));
  projects[0].picture='/fixture-preview.svg';
  previews.forEach((row,i)=>{projects[i]={...projects[i],...row};});
  jobs=[{id:'fixture-check',kind:'check',project:'fixture_0',label:'Check mounting clearances',state:'running',seconds:35,tail:[]}];
  await p.evaluate(async()=>{S.grid=true;await loadProjects();await pollJobs();showGrid();});
  assert.equal(await p.locator('#nav_grid').getAttribute('aria-current'),'page');
  assert.equal(await p.locator('#search').getAttribute('aria-label'),'Search projects');
  assert.equal(await p.locator('#plist button.pitem').count(),12);
  assert.equal(await p.locator('.pcard').count(),12);
  assert.equal(await p.locator('.pgrid .pcard').count(),previews.length||1);
  assert.equal(await p.locator('.project-index .pcard').count(),12-(previews.length||1));
  assert.equal(await p.locator('.project-index .pic').count(),0); // Missing pictures never reserve empty model tiles.
  assert.equal(await p.locator('.pgrid .pic').first().evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');
  assert.equal(await p.locator('#joblist button.job').count(),1);
  const nav=await p.locator('.sidenav').evaluate(e=>getComputedStyle(e).flexDirection);
  assert.equal(nav,'row');
  assert.equal((await p.locator('#main').boundingBox()).x,0);
  assert.equal(await p.locator('#plist').isVisible(),false);
  assert.equal(await p.locator('#main').evaluate(e=>getComputedStyle(e).backgroundImage),'none');
  assert.equal(await p.locator('#newbtn').evaluate(e=>getComputedStyle(e).backgroundImage),'none');
  assert.equal(await p.locator('.logo').evaluate(e=>getComputedStyle(e).animationName),'none');
  // Measure actual theme text/control colors, not the declaration spelling.
  await p.evaluate(()=>{
   const style=getComputedStyle(document.documentElement),rgb=v=>v.match(/[\d.]+/g).slice(0,3).map(Number);
   const color=name=>{const x=document.createElement('span');x.style.color=style.getPropertyValue(name);document.body.append(x);const c=rgb(getComputedStyle(x).color);x.remove();return c;};
   const luminance=c=>c.map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
   const ratio=(a,b)=>{const x=[luminance(color(a)),luminance(color(b))].sort((a,b)=>a-b);return(x[1]+.05)/(x[0]+.05);};
   for(const surface of ['--bg','--bg2','--panel','--panel2'])for(const text of ['--ink','--muted'])if(ratio(text,surface)<4.5)throw Error(`${text}/${surface} contrast`);
   if(ratio('--accent','--accent-ink')<4.5 || ratio('--control-line','--panel')<3)throw Error('Control contrast');
  });
  await p.waitForFunction(()=>[...document.querySelectorAll('#main .head,#main .body,#main .pcard')].every(e=>getComputedStyle(e).opacity==='1'));
  await p.evaluate(saved=>{const note=document.createElement('p');note.className='note';note.textContent=saved?'Saved models in an illustrative workspace. Status comes from saved reports; no new checks ran.':'Illustrative workspace: synthetic project data for UI testing.';document.querySelector('#main .body').prepend(note);},!!previewDir);
  await p.waitForFunction(()=>[...document.querySelectorAll('.pcard img')].every(i=>i.complete&&i.naturalWidth>0));
  await p.screenshot({path:CAPTURE_PATH+`/shell-projects-${theme}-${width}.png`,fullPage:true});
  // The sidebar destinations and project rows are real keyboard controls.
  await p.locator('#nav_work').focus();await p.keyboard.press('Enter');await p.locator('.work-item').waitFor();await p.waitForFunction(()=>!S.workLoading);
  assert.equal(await p.locator('#nav_work').getAttribute('aria-current'),'page');
  assert.equal(await p.locator('#nav_grid').getAttribute('aria-current'),null);
  if(width===390)assert.equal(await p.locator('#plist').isVisible(),false);
  await p.screenshot({path:CAPTURE_PATH+`/shell-work-${theme}-${width}.png`,fullPage:true});
  await p.locator('#nav_grid').click();
  await p.locator('#projecttray>summary').click();await p.locator('#search').waitFor();
  await p.locator('#search').fill('no-such-project');assert.equal(await p.locator('#plist').innerText(),'No matching projects. Try another name.');
  await p.locator('#search').fill('');
  await p.locator('#plist button').last().focus();
  await p.evaluate(()=>renderList());assert.equal(await p.evaluate(()=>document.activeElement.dataset.project),'fixture_11');
  await p.keyboard.press('Enter');
  await p.waitForFunction(()=>S.detail?.name==='fixture_11');
  assert.equal(await p.locator('#plist button').last().getAttribute('aria-current'),'page');
  await p.evaluate(()=>{window.openJob=id=>window.__selectedJob=id;});
  await p.locator('#activitytray>summary').click();
  await p.locator('#joblist button.job').focus();await p.keyboard.press('Space');
  assert.equal(await p.evaluate(()=>window.__selectedJob),'fixture-check');
  await p.locator('#toolstray>summary').click();
  await p.locator('#bellbtn').click();await p.waitForFunction(()=>document.querySelector('#bellbtn').getAttribute('aria-label')==='Turn notifications on');
  assert.equal(await p.locator('#bellbtn .muted-line').isVisible(),true);
  await p.locator('#themebtn').click();
  const changed=theme==='light'?'dark':'light';
  assert.equal(await p.locator('html').getAttribute('data-theme'),changed);
  await p.reload();assert.equal(await p.locator('html').getAttribute('data-theme'),changed); // Explicit choice survives reload.
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);await p.close();
 }
}finally{await browser.close();}
'''.replace('BROWSER_HELPER', json.dumps(str(root / 'tests/browser.mjs')))
       .replace('STUDIO_HTML_PATH', json.dumps(str(root / 'kerf/assets/studio.html')))
       .replace('CAPTURE_PATH', json.dumps(str(capture))), encoding="utf-8")
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
