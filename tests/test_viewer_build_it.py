"""Viewer "Build it" tab (Spencer, 2026-11-02): a label sits beside the part it names, never on it; a small part gets a
close-up instead of the whole build; a bench step keeps the build it joins on screen (faint) instead of the parts
floating alone. Checked in a real browser on a big base, a bracket and a tiny nub built on the bench."""
import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from kerf import assembly as A, project as P, viewer

pytestmark = pytest.mark.browser

YAML = """
name: Build it test
params: {}
parts:
  base: {file: parts/base.py}
  bracket: {file: parts/bracket.py}
  nub: {file: parts/nub.py}
assembly:
  root: base
  joints:
    - {parent: base.top, child: bracket.bottom}
    - {parent: bracket.side, child: nub.back}
  order: [base, nub, bracket]
"""
BASE = """
from build123d import *
def build(ctx):
    ctx.rigid("top", Location((0, 0, 10)))
    return ctx.finish(Box(300, 300, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
BRACKET = """
from build123d import *
def build(ctx):
    ctx.rigid("bottom", Location((0, 0, 0)))
    ctx.rigid("side", Location((20, 0, 20)))
    return ctx.finish(Box(40, 40, 40, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
NUB = """
from build123d import *
def build(ctx):
    ctx.rigid("back", Location((0, 0, 0)))
    return ctx.finish(Box(6, 6, 6, align=(Align.MIN, Align.CENTER, Align.CENTER)))
"""


def test_build_it_labels_closeups_and_bench_context(tmp_path):
    d = tmp_path / "p"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    for n, src in {"base": BASE, "bracket": BRACKET, "nub": NUB}.items():
        (d / "parts" / f"{n}.py").write_text(textwrap.dedent(src))
    pr = P.build(P.load(str(d)))
    assert not {k: v.error for k, v in pr.items.items() if v.error}
    asm = A.plan(pr)
    data = viewer.data(pr, asm, {"assembly": {"fasteners": [], "pins": []}})
    steps = data["steps"]["steps"]
    nub = next(s for s in steps if "nub" in s["items"])
    assert nub.get("bench_for")                                  # the nub is built on the bench, joined later
    page = tmp_path / "v.html"
    page.write_text(viewer.html(data), encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    script = tmp_path / "check.mjs"
    script.write_text("""import {browser} from 'PLAYWRIGHT';
import assert from 'node:assert/strict';
const b = await browser();
try {
  const p = await b.newPage({viewport: {width: 1280, height: 800}}); const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto('file://PAGE'); await p.waitForFunction(() => window.__kerf);
  await p.click('#tabAsm');
  const k = await p.evaluate(n => window.__kerf.asm.cards.findIndex(c => c.kind === 'step' && c.s.n === n), NUBSTEP);
  await p.evaluate(k => { window.__kerf.asm.speed = 4; window.__kerf.asm.show(k); }, k);
  await p.waitForFunction(() => !window.__kerf.asm.busy, null, {timeout: 30000}); await p.waitForTimeout(300);
  const r = await p.evaluate(() => {
    const K = window.__kerf, s = K.asm.cards[K.asm.i].s, g = K.groups.get('nub');
    const box = g.userData.box.clone().applyMatrix4(g.matrix), sr = K.asm.screenRect(box);
    const fb = K.asm.focusBox(s, new Map()), all = new (box.constructor)();
    for (const id of ['base', 'bracket', 'nub']) { const h = K.groups.get(id); all.union(h.userData.box.clone().applyMatrix4(h.matrix)); }
    const stage = document.querySelector('#labels').getBoundingClientRect();
    return { ctx: K.asm.ctx, labels: K.asm.labels(), sr, stage: {x: stage.x, y: stage.y},
             focus: fb.getSize(box.min.clone()).length(), whole: all.getSize(box.min.clone()).length(),
             baseVisible: K.groups.get('base').visible };
  });
  assert.ok(r.ctx.includes('base') && r.baseVisible, 'the build the bench part joins stays on screen');
  assert.ok(r.focus < 0.4 * r.whole, `close-up on the small part: ${r.focus} vs ${r.whole}`);
  const L = r.labels.find(l => l.id === 'nub'); assert.ok(L && L.opacity === 1, 'the nub is labelled');
  const lr = {x0: L.el.left - r.stage.x, x1: L.el.right - r.stage.x, y0: L.el.top - r.stage.y, y1: L.el.bottom - r.stage.y};
  const overlap = Math.max(0, Math.min(lr.x1, r.sr.x1) - Math.max(lr.x0, r.sr.x0)) * Math.max(0, Math.min(lr.y1, r.sr.y1) - Math.max(lr.y0, r.sr.y0));
  const area = (r.sr.x1 - r.sr.x0) * (r.sr.y1 - r.sr.y0);
  assert.ok(overlap < 0.05 * area, `the label must not cover its part (${overlap} of ${area} px2)`);
  assert.deepEqual(errors, []);
} finally { await b.close(); }
""".replace("PLAYWRIGHT", str(root / "tests/browser.mjs")).replace("PAGE", str(page))
       .replace("NUBSTEP", json.dumps(nub["n"])), encoding="utf-8")
    r = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
