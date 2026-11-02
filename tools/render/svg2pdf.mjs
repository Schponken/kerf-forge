// SVG -> one-page PDF at the drawing's own size (kerf/circuit.py: out/schematic.pdf). Usage: node svg2pdf.mjs in.svg out.pdf
import { chromium } from 'playwright';
import { readFileSync } from 'fs';
const [, , src, dst] = process.argv;
const svg = readFileSync(src, 'utf8');
const m = svg.match(/<svg[^>]*\swidth="([\d.]+)mm"[^>]*\sheight="([\d.]+)mm"/);
const [w, h] = m ? [m[1], m[2]] : ['420', '297'];
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setContent(`<!doctype html><html><head><style>@page{size:${w}mm ${h}mm;margin:0}html,body{margin:0}svg{display:block;width:${w}mm;height:${h}mm}</style></head><body>${svg}</body></html>`);
await page.pdf({ path: dst, width: `${w}mm`, height: `${h}mm`, printBackground: true, pageRanges: '1' });
await browser.close();
