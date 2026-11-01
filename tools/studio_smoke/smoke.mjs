import { chromium } from '../render/node_modules/playwright/index.mjs';
// End-to-end Studio check in a real browser (run.sh starts Studio with a stand-in Claude Code): picture capture, viewer "Do it" -> edit job,
// duplicate, materials + params Try with the saved design as a ghost, notifications switch, all-projects grid. Needs servo_link built.
const [base, prefix] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage(); const errors = [];
page.on('pageerror', e => errors.push(e.message)); page.on('console', m => m.type() === 'error' && !/marked|cdnjs|ERR_/.test(m.text()) && errors.push(m.text()));
const log = (...a) => console.log(...a);
await page.goto(base); await page.waitForSelector('.pitem'); await page.click('.pitem >> text=Servo test rig'); await page.waitForSelector('#mainviewer');
const fr = page.frameLocator('#mainviewer');
await page.waitForFunction(() => { const f = document.querySelector('#mainviewer'); return f && f.contentWindow.__kerf; }, null, { timeout: 30000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: `${prefix}-model.png` });
// picture captured for the card
await page.waitForFunction(async () => (await (await fetch('/api/projects')).json()).projects.find(p => p.name === 'servo_link').picture, null, { timeout: 20000 });
log('picture saved');
// Do it from the viewer: click the arm, describe a change, Do it
const pt = await page.evaluate(() => { const w = document.querySelector('#mainviewer').contentWindow, K = w.__kerf, T = w.KV3, g = K.groups.get('arm'); const c = g.userData.box.getCenter(new T.Vector3()).project(K.camera); const fr = document.querySelector('#mainviewer').getBoundingClientRect(), cv = w.document.querySelector('canvas').getBoundingClientRect(); return [fr.left + cv.left + (c.x + 1) / 2 * cv.width, fr.top + cv.top + (1 - c.y) / 2 * cv.height]; });
await page.mouse.click(pt[0], pt[1]); await page.waitForTimeout(400);
log('do-it buttons in viewer:', await fr.locator('#dof').count(), await fr.locator('[data-do]').count());
await fr.locator('#free').fill('round the tip of the arm with a 9 mm radius');
await fr.locator('#dof').click(); await page.waitForSelector('#modal.open');
await page.screenshot({ path: `${prefix}-doit-modal.png` });
await page.click('#edgo'); await page.waitForSelector('#mc.open');
await page.waitForFunction(() => document.querySelector('#tricon').textContent === '✓', null, { timeout: 30000 });
await page.screenshot({ path: `${prefix}-edit-done.png` });
// duplicate with no change
await page.click('button:has-text("⧉ Duplicate")'); await page.waitForSelector('#modal.open');
await page.fill('#dname', 'zz_studio_test_copy'); await page.screenshot({ path: `${prefix}-dup-modal.png` });
await page.click('#dgo'); await page.waitForFunction(() => document.querySelector('.head h1') && document.querySelector('.head h1').textContent.includes('(copy)'), null, { timeout: 15000 });
log('duplicated:', await page.textContent('.head h1'));
await page.click('.pitem >> text=Servo test rig'); await page.waitForSelector('#mainviewer');
// Tune: arm to PLA and arm_len 120, Try
await page.click('.tab[data-t="tune"]'); await page.waitForSelector('.mats');
await page.selectOption('.mats tr:has(td:text-is("base")) select', 'ASA');
await page.fill('#r_foot_d', '44'); await page.dispatchEvent('#r_foot_d', 'input'); await page.dispatchEvent('#r_foot_d', 'change');
await page.screenshot({ path: `${prefix}-tune.png` });
await page.click('text=▶ Try these values'); await page.waitForSelector('#mc.open');
await page.waitForTimeout(1500); for (let k = 0; k < 200 && await page.evaluate(async () => (await (await fetch('/api/jobs')).json()).jobs.some(j => j.state === 'running')); k++) await page.waitForTimeout(2000); await page.waitForTimeout(2500);
await page.screenshot({ path: `${prefix}-trial-mc.png` }); await page.click('#mc button[title=Close]');
await page.waitForSelector('#trialviewer'); await page.waitForFunction(() => { const f = document.querySelector('#trialviewer'); return f && f.contentWindow.__kerf && f.contentWindow.__kerf.colorMode === 'compare'; }, null, { timeout: 60000 });
await page.waitForTimeout(800); await page.screenshot({ path: `${prefix}-trial-compare.png`, fullPage: false });
log('trial banner:', (await page.textContent('.banner')).replace(/\s+/g, ' '));
// bell
await page.click('#bellbtn'); await page.waitForTimeout(300); log('bell after click:', await page.textContent('#bellbtn'));
await page.click('#bellbtn'); await page.waitForTimeout(300); log('bell after 2nd click:', await page.textContent('#bellbtn'));
// grid
await page.click('text=▦ All projects'); await page.waitForTimeout(1200); await page.screenshot({ path: `${prefix}-grid.png` });
log('errors', JSON.stringify(errors)); await browser.close();
