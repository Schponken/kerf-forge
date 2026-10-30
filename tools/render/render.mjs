// Headless renderer: node render.mjs <in.glb> <out_prefix> [views=iso,front,right,top] [--sheet]
// Writes <out_prefix>_<view>.png for each view and <out_prefix>_sheet.png (2x2 labelled) with --sheet.
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const [glbPath, prefix, viewsArg = 'iso,front,right,top', ...flags] = process.argv.slice(2);
if (!glbPath || !prefix) { console.error('usage: render.mjs in.glb out_prefix [views] [--sheet]'); process.exit(2); }
const views = viewsArg.split(',');
const sheet = flags.includes('--sheet');
const three = join(here, 'node_modules/three');

const html = `<!doctype html><html><body style="margin:0;background:#eef0ef">
<script type="importmap">{"imports":{"three":"https://r/three/build/three.module.js","three/addons/":"https://r/three/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
const W = 1024, H = 768;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, H); renderer.setClearColor(0xeef0ef); document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x777777, 1.8));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(1, -1.5, 2.2); scene.add(sun);
const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(-1.4, 1.1, 0.5); scene.add(fill);
const cam = new THREE.PerspectiveCamera(30, W / H, 0.1, 1e6); cam.up.set(0, 0, 1);
window.go = async (b64, views) => {
  const buf = Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer;
  const gltf = await new GLTFLoader().parseAsync(buf, '');
  const root = gltf.scene;
  root.rotation.x = Math.PI / 2;   // glTF is Y-up; build123d exports Z-up as Y-up
  scene.add(root); root.updateMatrixWorld(true);
  root.traverse(o => { if (o.isMesh) {
    o.material.side = THREE.DoubleSide;
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry, 25), new THREE.LineBasicMaterial({ color: 0x1a1e21 }));
    o.add(e);
  } });
  const box = new THREE.Box3().setFromObject(root), c = box.getCenter(new THREE.Vector3()), r = box.getSize(new THREE.Vector3()).length() / 2;
  const grid = new THREE.GridHelper(Math.ceil(r * 3 / 10) * 10, Math.ceil(r * 3 / 10), 0xb7bdb9, 0xd2d6d3);
  grid.rotation.x = Math.PI / 2; grid.position.set(c.x, c.y, box.min.z); scene.add(grid);
  const dirs = { iso: [1, -1.25, 0.9], front: [0, -1, 0.0001], right: [1, 0, 0.0001], top: [0, -0.0001, 1], back: [0, 1, 0.0001], left: [-1, 0, 0.0001], under: [0.0001, 0, -1], iso2: [-1, 1.25, 0.9] };
  const out = {};
  for (const v of views) {
    const d = new THREE.Vector3(...dirs[v]).normalize();
    const dist = r / Math.sin(THREE.MathUtils.degToRad(15)) * 1.05;
    cam.position.copy(c).addScaledVector(d, dist); cam.near = dist / 100; cam.far = dist * 10; cam.updateProjectionMatrix(); cam.lookAt(c);
    grid.visible = v !== 'under';
    renderer.render(scene, cam);
    out[v] = renderer.domElement.toDataURL('image/png');
  }
  return { out, size: box.getSize(new THREE.Vector3()).toArray() };
};
window.ready = true;
</script></body></html>`;

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1024, height: 768 } });
await page.route('**/*', route => {
  const u = route.request().url();
  if (u === 'https://r/') return route.fulfill({ body: html, contentType: 'text/html' });
  if (u.startsWith('https://r/three/')) return route.fulfill({ path: join(three, u.slice('https://r/three/'.length)), contentType: 'application/javascript' });
  return route.abort();
});
const errs = [];
page.on('pageerror', e => errs.push(String(e)));
await page.goto('https://r/');
await page.waitForFunction(() => window.ready === true, null, { timeout: 30000 });
const b64 = readFileSync(glbPath).toString('base64');
const { out, size } = await page.evaluate(([b, v]) => window.go(b, v), [b64, views]);
for (const [v, url] of Object.entries(out)) writeFileSync(`${prefix}_${v}.png`, Buffer.from(url.split(',')[1], 'base64'));
if (sheet) {
  const labels = { iso: 'ISO (front-right, above)', front: 'FRONT (looking +Y)', right: 'RIGHT (looking -X)', top: 'TOP (looking down)', back: 'BACK', left: 'LEFT', under: 'UNDERSIDE', iso2: 'ISO (back-left, above)' };
  const png = await page.evaluate(async ([imgs, labels]) => {
    const c = document.createElement('canvas'); c.width = 2048; c.height = 1536; const g = c.getContext('2d');
    const keys = Object.keys(imgs).slice(0, 4);
    for (let i = 0; i < keys.length; i++) {
      const im = new Image(); im.src = imgs[keys[i]]; await im.decode();
      const x = (i % 2) * 1024, y = Math.floor(i / 2) * 768; g.drawImage(im, x, y);
      g.fillStyle = '#1a1e21'; g.font = '600 30px sans-serif'; g.fillText(labels[keys[i]] || keys[i], x + 18, y + 42);
      g.strokeStyle = '#9aa29e'; g.strokeRect(x + 0.5, y + 0.5, 1023, 767);
    }
    return c.toDataURL('image/png');
  }, [out, labels]);
  writeFileSync(`${prefix}_sheet.png`, Buffer.from(png.split(',')[1], 'base64'));
}
await browser.close();
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
console.log(JSON.stringify({ views: Object.keys(out), size_mm: size.map(x => +(x * 1000).toFixed(2)) }));
