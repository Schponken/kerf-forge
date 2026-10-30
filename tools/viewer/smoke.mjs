// Smoke test for a generated viewer.html: node tools/viewer/smoke.mjs <viewer.html> <out_prefix>
// Loads the page offline (all network blocked), checks it renders, the joints move the right items, and screenshots.
import { chromium } from '../render/node_modules/playwright/index.mjs';
const [file, prefix] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const out = { errors: [], requests: [] };
for (const [name, opts] of [['desktop', { viewport: { width: 1280, height: 800 } }], ['dark', { viewport: { width: 1280, height: 800 }, colorScheme: 'dark' }], ['phone', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 }]]) {
  const ctx = await browser.newContext(opts);
  ctx.on('request', r => { if (!r.url().startsWith('file:')) out.requests.push(r.url()); });  // must stay empty: the page is offline-only
  const page = await ctx.newPage(); page.setDefaultTimeout(60000);
  page.on('pageerror', e => out.errors.push(`${name}: ${e.message}`));
  page.on('console', m => m.type() === 'error' && out.errors.push(`${name}: ${m.text()}`));
  await page.goto('file://' + file);
  await page.waitForFunction(() => window.__kerf, null, { timeout: 30000 });
  await page.waitForTimeout(600);
  if (name === 'desktop') {
    out.info = await page.evaluate(() => {
      const K = window.__kerf, D = K.D;
      const pos = id => { const g = K.groups.get(id); g.updateMatrixWorld(true); const v = g.matrixWorld.elements; return [v[12], v[13], v[14]]; };
      const res = { items: D.items.map(i => i.id), joints: D.joints.map(j => ({ name: j.name, axis: j.axis, point: j.point, moves: j.moves })) };
      // move every joint to its max: items in its subtree must move, others must not
      res.moveCheck = D.joints.map(j => {
        const before = Object.fromEntries(D.items.map(i => [i.id, JSON.stringify(K.groups.get(i.id).matrix.elements.map(x => +x.toFixed(4)))]));
        K.setJ(j.name, j.range[1]);
        const changed = D.items.filter(i => JSON.stringify(K.groups.get(i.id).matrix.elements.map(x => +x.toFixed(4))) !== before[i.id]).map(i => i.id).sort();
        K.setJ(j.name, j.home);
        return { joint: j.name, changed, expected: [...j.moves].sort() };
      });
      return res;
    });
    await page.screenshot({ path: `${prefix}-desktop.png` });
    const j = out.info.joints[0];
    if (j) { await page.evaluate(n => window.__kerf.setJ(n, window.__kerf.D.joints[0].range[1]), j.name); await page.waitForTimeout(200); await page.screenshot({ path: `${prefix}-joint-max.png` }); await page.evaluate(n => window.__kerf.setJ(n, window.__kerf.D.joints[0].home), j.name); }
    await page.fill('#ex', '50'); await page.dispatchEvent('#ex', 'input'); await page.dispatchEvent('#ex', 'change'); await page.waitForTimeout(200);
    out.fitAfterExplode = await page.evaluate(() => { const K = window.__kerf, T = window.KV3, b = new T.Box3(); for (const g of K.groups.values()) if (g.visible) { g.updateMatrixWorld(true); b.expandByObject(g.userData.mesh); } return b.isEmpty() ? null : b.getSize(new T.Vector3()).toArray().map(x => +x.toFixed(1)); });
    await page.screenshot({ path: `${prefix}-exploded.png` });
    for (const t of ['parts', 'bom', 'print', 'checks']) { await page.click(`[data-tab="${t}"]`); await page.waitForTimeout(100); await page.screenshot({ path: `${prefix}-tab-${t}.png`, clip: await page.locator('aside').boundingBox() }); }
    // click-select from the canvas centre; hover tooltip
    const c = await page.locator('canvas').boundingBox();
    await page.mouse.move(c.x + c.width / 2, c.y + c.height / 2); await page.waitForTimeout(150);
    out.tooltip = await page.$eval('#tip', e => e.style.display === 'block' ? e.textContent : null);
    // click-to-edit: click the middle of each printed part's largest face, check the card, copy an edit request
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.evaluate(() => { window.__kerf.explode = 0; window.__kerf.view('iso'); window.__kerf.fit(); });
    out.inspect = [];
    for (const it of out.info.items) {
      const pt = await page.evaluate(id => {
        const K = window.__kerf, T = window.KV3, g = K.groups.get(id), item = g.userData.it;
        if (item.role !== 'printed') return null;
        g.updateMatrixWorld(true);
        const geo = g.userData.mesh.geometry, pos = geo.getAttribute('position'), idx = geo.index.array, cv = document.querySelector('canvas');
        const cam = [...document.querySelectorAll('canvas')].length && window.__kerfCam;
        // pick a triangle whose centre is visible: test candidates with a raycast from the camera
        const r = cv.getBoundingClientRect(), ray = new T.Raycaster(), cands = [];
        for (let t = 0; t < idx.length / 3; t += Math.max(1, Math.floor(idx.length / 3 / 400))) {
          const c = new T.Vector3(); for (let k = 0; k < 3; k++) c.add(new T.Vector3().fromBufferAttribute(pos, idx[3 * t + k])); c.divideScalar(3).applyMatrix4(g.matrixWorld);
          const s = c.clone().project(K.camera); if (Math.abs(s.x) > 0.95 || Math.abs(s.y) > 0.95) continue;
          ray.setFromCamera(new T.Vector2(s.x, s.y), K.camera);
          const hit = ray.intersectObjects([...K.groups.values()].filter(x => x.visible).map(x => x.userData.mesh), false)[0];
          if (hit && hit.object === g.userData.mesh && hit.faceIndex === t) return { x: r.left + (s.x + 1) / 2 * r.width, y: r.top + (1 - s.y) / 2 * r.height, tri: t, face: K.faceOf(item, t) };
        }
        return null;
      }, it);
      if (!pt) continue;
      await page.mouse.click(pt.x, pt.y); await page.waitForTimeout(150);
      const card = await page.evaluate(() => { const b = document.getElementById('insp'); return !b.classList.contains('on') || !b.querySelector('.hd') ? null : { text: b.innerText.slice(0, 400), params: [...b.querySelectorAll('[data-p]')].map(i => i.dataset.p), hasCode: !!b.querySelector('pre') }; });
      const rec = { item: it, face: pt.face, card };
      if (card && card.params.length) {
        const n = card.params[0];
        await page.evaluate(n => { const i = document.querySelector(`#insp [data-p="${CSS.escape(n)}"]`); i.value = String(+i.value + 2 * (+i.step || 1)); }, n);
        await page.click(`#insp [data-cp="${n}"]`); await page.waitForTimeout(150);
        rec.clipboard = await page.evaluate(() => navigator.clipboard.readText());
      }
      out.inspect.push(rec);
      if (out.inspect.length === 1) await page.screenshot({ path: `${prefix}-inspect.png` });
    }
    out.blank = await page.evaluate(() => { const cv = document.querySelector('canvas'), g = cv.getContext('webgl2') || cv.getContext('webgl'); const px = new Uint8Array(4 * 64); g.readPixels(Math.floor(cv.width / 2) - 32, Math.floor(cv.height / 2), 64, 1, g.RGBA, g.UNSIGNED_BYTE, px); return new Set(Array.from(px)).size < 4; });
  } else await page.screenshot({ path: `${prefix}-${name}.png`, fullPage: name === 'phone' });
  await ctx.close();
}
await browser.close();
console.log(JSON.stringify(out, null, 1));
