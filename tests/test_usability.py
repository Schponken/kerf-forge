"""First-use failures: invalid edits, conflicting jobs, and phone navigation/recovery."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from kerf import studio


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), -1, 21])
def test_invalid_param_never_changes_design(tmp_path, value):
    p = tmp_path / 'project.yaml'
    original = 'params:\n  length: {value: 10, min: 0, max: 20}\n'
    p.write_text(original, encoding='utf-8')
    with pytest.raises(ValueError):
        studio.write_params(p, {'length': value})
    assert p.read_text(encoding='utf-8') == original


@pytest.mark.parametrize('existing,requested', [('demo','demo'), ('*','demo'), ('demo','*')])
def test_conflicting_job_does_not_launch(monkeypatch, existing, requested):
    monkeypatch.setattr(studio, 'JOBS', {'old': SimpleNamespace(project=existing, state='running', label='Build demo')})
    def unexpected(*a, **kw):
        pytest.fail('a conflicting process was launched')
    monkeypatch.setattr(studio, 'Job', unexpected)
    with pytest.raises(ValueError, match='Activity'):
        studio.start_job('build', requested, [], 'Build again')


def test_finished_job_does_not_block_next_job(monkeypatch):
    monkeypatch.setattr(studio, 'JOBS', {'old': SimpleNamespace(project='demo', state='done', label='Build demo')})
    new = SimpleNamespace(id='new')
    monkeypatch.setattr(studio, 'Job', lambda *a, **kw: new)
    assert studio.start_job('build', 'demo', [], 'Build again') is new


def test_phone_tune_and_connection_recovery(tmp_path):
    root = Path(__file__).resolve().parents[1]
    page = tmp_path / 'studio.html'
    page.write_text((root / 'kerf/assets/studio.html').read_text())
    script = tmp_path / 'check.mjs'
    script.write_text('''import { chromium } from "PLAYWRIGHT";
import assert from 'node:assert/strict';
const b=await chromium.launch();
try {
 for(const theme of ['light','dark']) {
 const p=await b.newPage({viewport:{width:390,height:844}});
 await p.route('**/api/**',r=>r.fulfill({json:r.request().url().includes('/projects')?{projects:[],claude:false}:r.request().url().includes('/jobs')?{jobs:[]}:{}}));
 await p.goto('file://PAGE');
 await p.evaluate(t=>{
 setTheme(t); S.projects=Array.from({length:7},(_,i)=>({name:'p'+i,title:'Project '+i,description:'',built:false,review:null}));renderList(); S.detail={params:[{key:'length',label:'Arm length',value:10,min:0,max:20,step:1,bounded:true,unit:'mm'}],part_materials:{},trial:null};
 document.querySelector('#main').innerHTML='<div class="body" id="tabbody"></div>';S.tab='tune';renderTune(document.querySelector('#tabbody'));
 },theme);
 await p.waitForTimeout(500);
 const list=await p.locator('#plist').boundingBox();assert.ok(list.height>=50, JSON.stringify(list));
 assert.match(await p.evaluate(()=>statusPill({built:true,ok:true,problems:0})),/checks pass/);
 const rect=await p.locator('.param .rng').boundingBox();assert.ok(rect.x>=0 && rect.x+rect.width<=390, JSON.stringify(rect));
 await p.evaluate(()=>{setParam('length','12',true);setParam('length','999',false)});
 assert.equal(await p.evaluate(()=>S.edits.length),12);
 assert.match(await p.locator('#toasts').innerText(),/from 0 to 20/);
 await p.evaluate(()=>closedScreen());
 assert.match(await p.locator('h2').innerText(),/Connection/);assert.equal(await p.getByRole('button',{name:'Reconnect',exact:true}).count(),1);
 await p.close();
 }
} finally {await b.close();}
'''.replace('PLAYWRIGHT', str(root / 'tools/render/node_modules/playwright/index.mjs')).replace('PAGE',str(page)))
    r = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=90)
    assert r.returncode == 0, r.stdout + r.stderr


def test_trial_prepare_is_not_run_for_a_busy_project(monkeypatch):
    monkeypatch.setattr(studio, 'JOBS', {'old': SimpleNamespace(project='demo', state='running', label='Try demo')})
    with pytest.raises(ValueError, match='Activity'):
        studio.start_job('trial', 'demo', [], 'Try again', prepare=lambda: pytest.fail('active trial overwritten'))


@pytest.mark.parametrize('spec,value', [('10', float('nan')), ('{value: 10, min: 0}', -1), ('{value: 10, max: 20}', 21)])
def test_unbounded_and_one_sided_params_are_validated(tmp_path, spec, value):
    p = tmp_path / 'project.yaml'
    original = f'params:\n  length: {spec}\n'
    p.write_text(original, encoding='utf-8')
    with pytest.raises(ValueError):
        studio.write_params(p, {'length': value})
    assert p.read_text(encoding='utf-8') == original


def test_port_exhaustion_stays_in_valid_range(monkeypatch, capsys):
    tried = []
    def occupied(address, handler):
        tried.append(address[1])
        raise OSError('occupied')
    monkeypatch.setattr(studio, 'ThreadingHTTPServer', occupied)
    assert studio.serve(65535, open_browser=False) == 1
    assert tried == [65535]
    assert 'no free port' in capsys.readouterr().out


@pytest.mark.parametrize('path', ['save', 'save-materials', 'restore'])
def test_saves_cannot_change_a_running_project(monkeypatch, path):
    import threading
    import urllib.request
    import urllib.error
    from http.server import ThreadingHTTPServer
    monkeypatch.setattr(studio, 'JOBS', {'old': SimpleNamespace(project='servo_link', state='running', label='Build servo_link')})
    srv = ThreadingHTTPServer(('127.0.0.1', 0), studio.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{srv.server_address[1]}/api/{path}',
            data=json.dumps({'project':'servo_link'}).encode(), headers={'Content-Type':'application/json'})
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 400
        assert 'Activity' in json.load(e.value)['error']
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)
