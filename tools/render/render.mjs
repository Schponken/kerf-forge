// Headless renderer: node render.mjs <in.glb> <out_prefix> [views=iso,front,right,top] [--sheet]
//   [--labels=a,b] (call out these nodes by name) [--focus=a,b] (frame these nodes, with context) [--title=text] (sheet)
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
const opt = k => (flags.find(f => f.startsWith(`--${k}=`)) || '').slice(k.length + 3);
const labels = opt('labels') ? opt('labels').split(',') : [];
const focus = opt('focus') ? opt('focus').split(',') : [];
const title = opt('title');
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
scene.add(new THREE.HemisphereLight(0xffffff, 0x777777, 1.3));
const sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(1, -1.5, 2.2); scene.add(sun);
const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(-1.4, 1.1, 0.5); scene.add(fill);
const cam = new THREE.PerspectiveCamera(30, W / H, 0.1, 1e6); cam.up.set(0, 0, 1);
window.go = async (b64, views, labels, focus) => {
  const buf = Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer;
  const gltf = await new GLTFLoader().parseAsync(buf, '');
  const root = gltf.scene;
  root.rotation.x = Math.PI / 2;   // glTF is Y-up; build123d exports Z-up as Y-up
  scene.add(root); root.updateMatrixWorld(true);
  root.traverse(o => { if (o.isMesh) {
    o.material.side = THREE.DoubleSide;
    // build123d writes no metallicFactor, and glTF's default is 1 (pure metal): with no environment map every part then
    // renders dark. Plastic and painted parts are dielectric.
    o.material.metalness = 0; o.material.roughness = 0.75;
    // a dark purchased part (black servo, PCB) disappears under black edges: lift it and draw light edges instead
    const col = o.material.color, lum = col ? 0.2126 * col.r + 0.7152 * col.g + 0.0722 * col.b : 1;
    if (col && lum < 0.18) col.lerp(new THREE.Color(0x8a9096), 0.5);
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry, 25),
      new THREE.LineBasicMaterial({ color: lum < 0.18 ? 0xc9ced2 : 0x1a1e21 }));
    o.add(e);
  } });
  const isNum = t => t.length > 0 && [...t].every(ch => ch >= '0' && ch <= '9');
  const named = n => { const out = []; root.traverse(o => { if (o.name === n || (o.name.startsWith(n + '_') && isNum(o.name.slice(n.length + 1)))) out.push(o); }); return out; };
  const boxOf = ns => { const b = new THREE.Box3(); for (const n of ns) for (const o of named(n)) b.expandByObject(o); return b; };
  const all = new THREE.Box3().setFromObject(root), rAll = all.getSize(new THREE.Vector3()).length() / 2;
  const fb = focus.length ? boxOf(focus) : null;
  const box = fb && !fb.isEmpty() ? fb : all;
  const c = box.getCenter(new THREE.Vector3());
  // framed on the focus with room for its neighbours, never wider than the whole scene
  const r = fb && !fb.isEmpty() ? Math.min(Math.max(box.getSize(new THREE.Vector3()).length() / 2 * 1.9, rAll * 0.35), rAll * 1.05) : rAll;
  // the floor: a plate with a 10 mm grid at the lowest point (for a part sheet, that is the print bed)
  const gsz = Math.ceil(r * 2.6 / 0.01) * 0.01;          // the model is in metres: 10 mm squares
  const grid = new THREE.GridHelper(gsz, Math.round(gsz / 0.01), 0x8f9793, 0xb9bfbb);
  grid.rotation.x = Math.PI / 2; grid.position.set(c.x, c.y, all.min.z - r * 0.002); scene.add(grid);
  const bed = new THREE.Mesh(new THREE.PlaneGeometry(gsz, gsz), new THREE.MeshBasicMaterial({ color: 0xdde1de, side: THREE.DoubleSide }));
  bed.position.set(c.x, c.y, all.min.z - r * 0.004); scene.add(bed);
  const dirs = { iso: [1, -1.25, 0.9], front: [0, -1, 0.0001], right: [1, 0, 0.0001], top: [0, -0.0001, 1], back: [0, 1, 0.0001], left: [-1, 0, 0.0001], under: [0.0001, 0, -1], iso2: [-1, 1.25, 0.9] };
  const out = {};
  for (const v of views) {
    const d = new THREE.Vector3(...dirs[v]).normalize();
    const dist = r / Math.sin(THREE.MathUtils.degToRad(15)) * 1.05;
    cam.position.copy(c).addScaledVector(d, dist); cam.near = dist / 100; cam.far = dist * 10; cam.updateProjectionMatrix(); cam.lookAt(c);
    grid.visible = bed.visible = v !== 'under';
    renderer.render(scene, cam);
    let url = renderer.domElement.toDataURL('image/png');
    if (labels.length) {                         // call-outs: a tag per labelled part with a leader to its centre
      const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const g = cv.getContext('2d');
      const im = new Image(); im.src = url; await im.decode(); g.drawImage(im, 0, 0);
      g.font = '600 20px sans-serif';
      const used = [];
      for (const n of labels) {
        const b = boxOf([n]); if (b.isEmpty()) continue;
        const p = b.getCenter(new THREE.Vector3()).project(cam);
        const px = (p.x + 1) / 2 * W, py = (1 - p.y) / 2 * H;
        const tw = g.measureText(n).width + 16;
        let tx = Math.min(W - tw - 8, px + 60), ty = Math.max(30, py - 70);
        while (used.some(u => Math.abs(u - ty) < 30)) ty += 32;
        used.push(ty);
        g.strokeStyle = '#1a1e21'; g.lineWidth = 2; g.beginPath(); g.moveTo(px, py); g.lineTo(tx, ty); g.stroke();
        g.fillStyle = '#1a1e21'; g.beginPath(); g.arc(px, py, 4, 0, 7); g.fill();
        g.fillStyle = 'rgba(255,255,255,0.92)'; g.fillRect(tx, ty - 22, tw, 30);
        g.strokeRect(tx, ty - 22, tw, 30); g.fillStyle = '#1a1e21'; g.fillText(n, tx + 8, ty);
      }
      url = cv.toDataURL('image/png');
    }
    out[v] = url;
  }
  return { out, size: all.getSize(new THREE.Vector3()).toArray() };
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
const { out, size } = await page.evaluate(([b, v, l, f]) => window.go(b, v, l, f), [b64, views, labels, focus]);
for (const [v, url] of Object.entries(out)) writeFileSync(`${prefix}_${v}.png`, Buffer.from(url.split(',')[1], 'base64'));
if (sheet) {
  const labels = { iso: 'ISO (front-right, above)', front: 'FRONT (looking +Y)', right: 'RIGHT (looking -X)', top: 'TOP (looking down)', back: 'BACK', left: 'LEFT', under: 'UNDERSIDE', iso2: 'ISO (back-left, above)' };
  const png = await page.evaluate(async ([imgs, labels, title]) => {
    const top = title ? 56 : 0;
    const c = document.createElement('canvas'); c.width = 2048; c.height = 1536 + top; const g = c.getContext('2d');
    g.fillStyle = '#ffffff'; g.fillRect(0, 0, 2048, 1536 + top);
    if (title) { g.fillStyle = '#1a1e21'; g.font = '700 32px sans-serif'; g.fillText(title, 18, 40); g.translate(0, top); }
    const keys = Object.keys(imgs).slice(0, 4);
    for (let i = 0; i < keys.length; i++) {
      const im = new Image(); im.src = imgs[keys[i]]; await im.decode();
      const x = (i % 2) * 1024, y = Math.floor(i / 2) * 768; g.drawImage(im, x, y);
      g.fillStyle = '#1a1e21'; g.font = '600 30px sans-serif'; g.fillText(labels[keys[i]] || keys[i], x + 18, y + 42);
      g.strokeStyle = '#9aa29e'; g.strokeRect(x + 0.5, y + 0.5, 1023, 767);
    }
    return c.toDataURL('image/png');
  }, [out, labels, title]);
  writeFileSync(`${prefix}_sheet.png`, Buffer.from(png.split(',')[1], 'base64'));
}
await browser.close();
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
console.log(JSON.stringify({ views: Object.keys(out), size_mm: size.map(x => +(x * 1000).toFixed(2)) }));
