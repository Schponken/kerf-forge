// Drive a built viewer.html headlessly: node viewer_check.mjs <viewer.html> <shot_prefix> '<json poses>'
// poses: [{"name":"home","joints":{},"explode":0,"theme":"light","width":1280,"height":800}, ...]
// Prints JSON {errors, poses:{name:{world:{id:[16 col-major]}}}} and writes <shot_prefix>_<name>.png per pose.
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
const [file, prefix, posesArg] = process.argv.slice(2);
const poses = JSON.parse(posesArg || '[{"name":"home"}]');
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const errors = [], out = {};
for (const p of poses) {
  const page = await browser.newPage({ viewport: { width: p.width || 1280, height: p.height || 800 }, colorScheme: p.theme || 'light' });
  page.on('pageerror', e => errors.push(`${p.name}: ${e}`));
  page.on('console', m => { if (m.type() === 'error') errors.push(`${p.name}: console: ${m.text()}`); });
  page.on('request', r => { if (!r.url().startsWith('file:') && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) errors.push(`${p.name}: network request ${r.url()}`); });
  await page.goto(pathToFileURL(file).href);
  await page.waitForFunction(() => window.kerfViewer?.ready === true, null, { timeout: 30000 });
  if (p.tab) await page.click(`nav button[data-t="${p.tab}"]`);
  const world = await page.evaluate(([j, e, sel]) => {
    for (const [n, v] of Object.entries(j || {})) window.kerfViewer.setJoint(n, v);
    window.kerfViewer.setExplode(e || 0);
    if (sel) window.kerfViewer.select(sel, false);
    return window.kerfViewer.world();
  }, [p.joints, p.explode, p.select]);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${prefix}_${p.name}.png` });
  out[p.name] = { world };
  await page.close();
}
await browser.close();
console.log(JSON.stringify({ errors, poses: out }));
