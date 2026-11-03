"""Saved meshes get the current object stage without rebuilding or rewriting their exports."""
import base64
import json
import struct
import subprocess
from pathlib import Path

import pytest

from kerf import studio, viewer
from test_studio import server  # isolated HTTP fixture; no Studio job runner


def stage_data():
    # A small tetrahedron is enough to exercise real WebGL without building CAD geometry.
    verts = base64.b64encode(struct.pack('<12f', 0, 0, 0, 30, 0, 0, 0, 30, 0, 0, 0, 30)).decode()
    tris = base64.b64encode(struct.pack('<12I', 0, 2, 1, 0, 1, 3, 1, 2, 3, 2, 0, 3)).decode()
    return {'viewer_schema': 1, 'items': [{'id': 'support', 'role': 'printed', 'color': '#a2e436', 'verts': verts,
            'tris': tris, 'nv': 4, 'nt': 4, 'explode': [1, 0, 0], 'joints': [], 'src': 'parts/support.py'}],
            'joints': [], 'bounds': [[0, 0, 0], [30, 30, 30]], 'params': {},
            'report': {'project': 'Fixture <script>object</script>', 'ok': False, 'problems': ['support: check failed'],
                       'warnings': ['Stress simulations PAUSED; strength is unproven'], 'parts': {}, 'purchased': {}}}


def test_current_saved_html_keeps_data_and_export(tmp_path):
    d = stage_data()
    d.pop('viewer_schema')  # compatible legacy files predate the schema tag
    f = tmp_path / 'viewer.html'
    original = '<h1>OLD TEMPLATE</h1><script type="application/json" id="kerf-data">' + json.dumps(d).replace('</', '<\\/') + '</script>'
    f.write_text(original)
    page = viewer.current_html(f)
    assert 'id="tool-tray"' in page and 'OLD TEMPLATE' not in page
    assert '<script>object</script>' not in page
    out = tmp_path / 'served.html'
    out.write_text(page)
    assert viewer.embedded(out) == d
    assert f.read_text() == original


@pytest.mark.parametrize('body', ['<p>legacy viewer</p>', '<script id="kerf-data">{broken</script>',
    '<script id="kerf-data">null</script>', '<script id="kerf-data">{"viewer_schema":2}</script>',
    '<script id="kerf-data">{"items":[],"joints":[],"report":{},"bounds":[[0,0,0],[1,"bad",1]]}</script>'])
def test_unsupported_saved_html_keeps_original_fallback(tmp_path, body):
    f = tmp_path / 'viewer.html'
    f.write_text(body)
    assert viewer.current_html(f) is None
    assert f.read_text() == body


@pytest.mark.parametrize('field,value', [('report', {'project': 7}), ('bounds', [[0, 0, 0], [10**400, 1, 1]]),
                                       ('items', [{'id': 'missing mesh'}]), ('joints', [{'name': 'missing axis'}])])
def test_incomplete_saved_contract_uses_fallback(tmp_path, field, value):
    d = stage_data()
    d[field] = value
    f = tmp_path / 'viewer.html'
    f.write_text('<script id="kerf-data">' + json.dumps(d).replace('</', '<\\/') + '</script>')
    assert viewer.current_html(f) is None


def test_saved_file_routes_refresh_only_compatible_viewers(tmp_path, monkeypatch, server):
    import urllib.request
    root = tmp_path / 'projects'
    out = root / 'demo' / 'out'
    out.mkdir(parents=True)
    monkeypatch.setattr(studio, 'PROJECTS', root)
    monkeypatch.setattr(studio, 'TRIALS', root)
    f = out / 'viewer.html'
    original = '<script id="kerf-data">' + json.dumps(stage_data()).replace('</', '<\\/') + '</script>'
    f.write_text(original)
    for prefix in ('files', 'trial'):
        with urllib.request.urlopen(f'{server}/{prefix}/demo/out/viewer.html') as response:
            assert response.headers['Content-Type'].startswith('text/html')
            assert b'id="tool-tray"' in response.read()
    assert f.read_text() == original
    f.write_text('old self-contained viewer')
    with urllib.request.urlopen(f'{server}/files/demo/out/viewer.html') as response:
        assert response.read() == b'old self-contained viewer'
    (out / 'part.stl').write_bytes(b'unchanged binary')
    with urllib.request.urlopen(f'{server}/files/demo/out/part.stl') as response:
        assert response.read() == b'unchanged binary'


def test_stage_disclosures_identity_and_keyboard(tmp_path):
    page = tmp_path / 'viewer.html'
    page.write_text(viewer.html(stage_data()))
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / 'stage.mjs'
    script.write_text(r'''import {chromium} from 'PLAYWRIGHT';
import assert from 'node:assert/strict';
const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 for(const viewport of [{width:1512,height:982},{width:390,height:844}]) for(const theme of ['light','dark']) {
  const p=await b.newPage({viewport,colorScheme:theme,reducedMotion:'reduce'}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.goto('file://PAGE'); await p.waitForFunction(()=>window.__kerf);
  assert.equal(await p.locator('#tool-tray').isVisible(),false);
  assert.match(await p.locator('#notice').innerText(),/1 problem/);
  const stage=await p.locator('#stage').boundingBox(); assert.ok(stage.width>=viewport.width-2);
  const material=await p.evaluate(()=>window.__kerf.groups.get('support').userData.mesh.material.color.getHexString());
  await p.locator('#viewb').click(); assert.equal(await p.locator('#viewb').getAttribute('aria-expanded'),'true');
  await p.locator('#part-colors').click();
  assert.equal(await p.locator('#part-colors').getAttribute('aria-pressed'),'true');
  const identity=await p.evaluate(()=>window.__kerf.groups.get('support').userData.mesh.material.color.getHexString());
  assert.notEqual(material,identity); assert.equal(identity,'a2e436');
  await p.keyboard.press('Escape'); assert.equal(await p.locator('#viewb').getAttribute('aria-expanded'),'false');
  await p.locator('[data-tab="parts"]').click();
  assert.equal(await p.locator('[data-tab="parts"]').getAttribute('aria-expanded'),'true');
  await p.locator('[data-part="support"]').focus(); await p.keyboard.press('Enter');
  assert.equal(await p.locator('[data-part="support"]').getAttribute('aria-pressed'),'true');
  await p.locator('#inspect-part').click(); assert.match(await p.locator('#insp').innerText(),/support.py/);
  await p.keyboard.press('Escape'); assert.equal(await p.locator('#tool-tray').isVisible(),false);
  await p.locator('#notice').click(); assert.match(await p.locator('#checks').innerText(),/strength is unproven/);
  const tray=await p.locator('#tool-tray').boundingBox(); assert.ok(tray.x>=0 && tray.x+tray.width<=viewport.width && tray.y>=stage.y);
  assert.ok(tray.y+tray.height<=viewport.height-65);
  const model=await p.locator('canvas').boundingBox();
  if(viewport.width<760) assert.ok(model.y+model.height<=tray.y+1); else assert.ok(model.x+model.width<=tray.x+1);
  const projected=await p.evaluate(()=>window.__kerf.asm.screenRect(window.__kerf.groups.get('support').userData.box));
  assert.ok(projected.x0>=0 && projected.x1<=model.width && projected.y0>=0 && projected.y1<=model.height);
  await p.locator('#tray-close').click();
  const canvas=p.locator('canvas'); await canvas.focus();
  const before=await p.evaluate(()=>window.__kerf.camera.position.toArray());
  await p.keyboard.press('ArrowRight');
  const after=await p.evaluate(()=>window.__kerf.camera.position.toArray()); assert.notDeepEqual(before,after);
  await p.locator('#cutb').click(); assert.equal(await p.locator('#cutb').getAttribute('aria-pressed'),'true');
  await p.keyboard.press('Escape'); assert.equal(await p.locator('#cutp').isVisible(),false);
  assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]); await p.close();
 }
}finally{await b.close()}
'''.replace('PLAYWRIGHT', str(root / 'tools/render/node_modules/playwright/index.mjs')).replace('PAGE', str(page)))
    r = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
