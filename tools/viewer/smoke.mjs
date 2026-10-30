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
    out.blank = await page.evaluate(() => { const cv = document.querySelector('canvas'), g = cv.getContext('webgl2') || cv.getContext('webgl'); const px = new Uint8Array(4 * 64); g.readPixels(Math.floor(cv.width / 2) - 32, Math.floor(cv.height / 2), 64, 1, g.RGBA, g.UNSIGNED_BYTE, px); return new Set(Array.from(px)).size < 4; });
  } else await page.screenshot({ path: `${prefix}-${name}.png`, fullPage: name === 'phone' });
  await ctx.close();
}
await browser.close();
console.log(JSON.stringify(out, null, 1));
