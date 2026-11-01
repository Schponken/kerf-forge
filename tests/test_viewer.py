"""The assembly viewer reproduces the engine's kinematics: each moving joint's axis is measured from solve(), and moving
it in the page must move exactly the items the engine moves, to the same place."""
import base64
import json
import re
import textwrap

import numpy as np
import pytest

from kerf import assembly as A, project as P, viewer

YAML = """
name: Slide and hinge
parts:
  base: {file: parts/base.py}
  carriage: {file: parts/carriage.py}
  flap: {file: parts/flap.py}
assembly:
  root: base
  joints:
    - {parent: base.rail, child: carriage.mount, name: slide, range: [0, 40]}
    - {parent: carriage.hinge, child: flap.pin, name: tilt, range: [-30, 60], home: 10}
"""
BASE = """
from build123d import *
def build(ctx):
    ctx.linear("rail", Axis((0, 0, 10), (1, 0, 0)), range=(0, 40))
    return ctx.finish(Box(100, 30, 10, align=(Align.MIN, Align.CENTER, Align.MIN)))
"""
CARRIAGE = """
from build123d import *
def build(ctx):
    ctx.rigid("mount", Location((0, 0, 0)))
    ctx.revolute("hinge", Axis((10, 0, 20), (0, 1, 0)), range=(-30, 60))
    return ctx.finish(Box(20, 30, 20, align=(Align.MIN, Align.CENTER, Align.MIN)))
"""
FLAP = """
from build123d import *
def build(ctx):
    ctx.rigid("pin", Location((0, 0, 0)))
    return ctx.finish(Pos(0, 0, 1) * Box(4, 20, 30, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""


@pytest.fixture()
def proj(tmp_path):
    d = tmp_path / "p"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent(YAML))
    for n, src in {"base": BASE, "carriage": CARRIAGE, "flap": FLAP}.items():
        (d / "parts" / f"{n}.py").write_text(textwrap.dedent(src))
    pr = P.build(P.load(str(d)))
    assert not {k: v.error for k, v in pr.items.items() if v.error}
    return pr


def _apply(j, v, pts):
    """The page's joint motion (kerf/assets/viewer.html jointMatrix), in numpy."""
    d = v - j["home"]
    if j["kind"] == "linear":
        return pts + np.array(j["axis"]) * d * j.get("scale", 1)
    a, p, th = np.array(j["axis"]), np.array(j["point"]), np.radians(d)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K
    return (pts - p) @ R.T + p


def _verts(item):
    return np.frombuffer(base64.b64decode(item["verts"]), dtype=np.float32).reshape(-1, 3).astype(float)


def test_page_kinematics_match_engine(proj):
    asm = A.plan(proj)
    d = viewer.data(proj, asm, {"project": "t", "problems": []})
    J = {j["name"]: j for j in d["joints"]}
    assert J["slide"]["kind"] == "linear" and J["tilt"]["kind"] == "revolute"
    assert sorted(J["slide"]["moves"]) == ["carriage", "flap"] and J["tilt"]["moves"] == ["flap"]
    items = {i["id"]: i for i in d["items"]}
    assert items["flap"]["joints"] == ["slide", "tilt"] and items["base"]["joints"] == []
    # pose the engine and the page the same way and compare every flap vertex
    pose = {"slide": 25.0, "tilt": 45.0}
    page = _apply(J["slide"], pose["slide"], _apply(J["tilt"], pose["tilt"], _verts(items["flap"])))
    A.solve(asm, pose)
    eng, _ = viewer.mesh(proj.items["flap"].shape)
    assert page.shape == eng.shape
    assert np.abs(page - eng).max() < 1e-3
    A.solve(asm)


def test_html_is_self_contained(proj, tmp_path):
    asm = A.plan(proj)
    out = viewer.write(proj, asm, {"project": "t </script> & <b>", "problems": []}, tmp_path / "v.html")
    s = out.read_text()
    assert "/*KV3*/" not in s and "/*DATA*/" not in s and "{{TITLE}}" not in s
    assert not re.search(r"""(src|href)=["']https?://""", s)          # no network resources
    data = s.split('id="kerf-data">', 1)[1].split("</script>", 1)[0]  # the data block ends at the real tag
    assert json.loads(data)["report"]["project"] == "t </script> & <b>"


def test_page_renders_with_a_combined_pose_sweep(proj, tmp_path):
    """Regression: a coupled-pose sweep (no 'range') crashed the side panel and left the 3D view blank, silently."""
    import subprocess
    from pathlib import Path
    asm = A.plan(proj)
    rep = {"project": "t", "problems": [], "assembly": {"sweeps": [
        {"joint": "corners", "poses": [{"slide": 0, "tilt": 0}, {"slide": 40, "tilt": 60}], "clear": True, "samples": 2},
        {"joint": "slide", "range": [0, 40], "clear": True, "samples": 9}]}}
    page = viewer.write(proj, asm, rep, tmp_path / "v.html")
    root = Path(__file__).resolve().parent.parent
    js = tmp_path / "check.mjs"
    js.write_text(f"""import {{ chromium }} from '{root}/tools/render/node_modules/playwright/index.mjs';
const b = await chromium.launch({{ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] }});
const p = await b.newPage({{ viewport: {{ width: 1000, height: 700 }} }}); const errs = [];
p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
await p.goto('file://{page}'); await p.waitForFunction(() => window.__kerf, null, {{ timeout: 30000 }}); await p.waitForTimeout(500);
const lit = await p.evaluate(() => {{ const c = document.querySelector('canvas'); const g = c.getContext('webgl2') || c.getContext('webgl');
  const px = new Uint8Array(4 * 64 * 64); g.readPixels(c.width / 2 - 32, c.height / 2 - 32, 64, 64, g.RGBA, g.UNSIGNED_BYTE, px);
  let n = 0; for (let i = 0; i < px.length; i += 4) if (px[i] + px[i + 1] + px[i + 2] > 0) n++; return n; }});
const text = await p.evaluate(() => document.body.textContent);
console.log(JSON.stringify({{ errs, lit, combined: text.includes('Combined motion') }})); await b.close();""")
    r = subprocess.run(["node", str(js)], capture_output=True, text=True, timeout=120)
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errs"] == [] and out["combined"], out


def _fea_for(proj, part, allow=10.0):
    """A synthetic FEA surface field for one part (part frame), stress rising along +X: what pipeline passes as fea_viz."""
    from build123d import Location
    import trimesh
    v, t = viewer.mesh(proj.items[part].shape.located(Location()))
    v, t = trimesh.remesh.subdivide_to_size(v, t, max_edge=2.0)      # FEA surfaces are fine meshes
    tris = v[t]
    vm = (tris.mean(axis=1)[:, 0] - v[:, 0].min()) / (np.ptp(v[:, 0]) or 1) * allow
    return {f"{part}_fea": {"tris": tris, "vm": vm, "allow": allow, "p999": float(vm.max()), "peak": float(vm.max()), "part": part}}


def test_stress_steps_and_sections_data(proj):
    asm = A.plan(proj)
    md = "# Assembly\n\n## Before you start\n\n- Tools: none\n\n## Step 0 — test-fit\n\n- print a coupon\n\n" \
         "## Step 1 — base\n\n![step 1](x.png)\n\n- Start with **base**.\n\n## Step 2 — carriage\n\n- Fit it.\n\n" \
         "## Step 3 — flap\n\n- Fit the flap.\n\n## Electrical — wire it\n\n1. Cut a wire.\n"
    d = viewer.data(proj, asm, {"project": "t", "problems": []}, fea=_fea_for(proj, "carriage"), assembly_md=md)
    st = d["steps"]
    assert [c["title"] for c in st["intro"]] == ["Before you start", "Step 0 — test-fit"]   # step 0 is a preparation card
    assert [c["title"] for c in st["outro"]] == ["Electrical — wire it"]
    assert [s["items"] for s in st["steps"]] == [["base"], ["carriage"], ["flap"]]
    assert st["steps"][0]["lines"] == ["- Start with **base**."]                             # pictures dropped
    assert st["steps"][2]["present"] == ["base", "carriage", "flap"] and st["steps"][2]["demos"] == ["tilt"]
    assert np.linalg.norm(st["steps"][1]["groups"][0]["off"]) > 10                           # comes in from somewhere
    car = next(i for i in d["items"] if i["id"] == "carriage")
    u = np.frombuffer(base64.b64decode(car["stress"]["u"]), np.uint8) / car["stress"]["scale"]
    x = _verts(car)[:, 0]
    assert u.max() == pytest.approx(1.0, abs=0.1) and u.min() < 0.1 and np.corrcoef(x, u)[0, 1] > 0.95   # the field, in place
    assert car["stress"]["cases"][0]["use"] == pytest.approx(1.0) and "stress" not in next(i for i in d["items"] if i["id"] == "flap")
    assert viewer.data(proj, asm, {"project": "t", "problems": []})["steps"]["intro"] == []    # no ASSEMBLY.md: steps, no text


def test_page_cut_stress_build_it_compare_and_picture(proj, tmp_path):
    """Every new mode runs in a real browser without a page error and does what it says."""
    import subprocess
    from pathlib import Path
    asm = A.plan(proj)
    md = "## Step 1 — base\n\n- Start.\n\n## Step 2 — carriage\n\n- Fit.\n\n## Step 3 — flap\n\n- Fit the flap.\n"
    (tmp_path / "ASSEMBLY.md").write_text(md)
    page = viewer.write(proj, asm, {"project": "t", "problems": [], "fingerprint": "f"}, tmp_path / "viewer.html", fea=_fea_for(proj, "carriage"))
    root = Path(__file__).resolve().parent.parent
    js = tmp_path / "check.mjs"
    js.write_text(f"""import {{ chromium }} from '{root}/tools/render/node_modules/playwright/index.mjs';
const b = await chromium.launch({{ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] }});
const p = await b.newPage({{ viewport: {{ width: 1100, height: 750 }} }}); const errs = [], out = {{}};
p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
await p.goto('file://{page}'); await p.waitForFunction(() => window.__kerf, null, {{ timeout: 30000 }}); await p.waitForTimeout(300);
const lit = () => p.evaluate(() => {{ const c = document.querySelector('canvas'), g = c.getContext('webgl2') || c.getContext('webgl');
  const px = new Uint8Array(4 * c.width * c.height); g.readPixels(0, 0, c.width, c.height, g.RGBA, g.UNSIGNED_BYTE, px);
  let n = 0; for (let i = 0; i < px.length; i += 4) if (Math.abs(px[i] - px[0]) + Math.abs(px[i + 1] - px[1]) + Math.abs(px[i + 2] - px[2]) > 30) n++; return n; }});
out.full = await lit();
await p.click('#cutb'); await p.click('#cutax [data-ax="x"]'); await p.waitForTimeout(150); out.cut = await lit();
out.cutPanel = await p.isVisible('#cutp'); await p.click('#cutb'); out.cutOff = await p.isHidden('#cutp');
out.stressBtn = await p.isVisible('#stressb'); await p.click('#stressb'); out.stressMode = await p.evaluate(() => window.__kerf.colorMode);
out.legend = await p.textContent('#slegend'); await p.click('#stressb');
const png = await p.evaluate(() => window.__kerf.snapshot(320, 240)); out.png = png.startsWith('data:image/png;base64,') && png.length > 2000;
out.after = await lit();
await p.click('[data-tab="asm"]'); out.cards = await p.evaluate(() => window.__kerf.asm.cards.length);
await p.evaluate(() => {{ window.__kerf.asm.speed = 8; }});
out.steps = [];
for (let i = 0; i < out.cards; i++) {{
  await p.evaluate(i => window.__kerf.asm.show(i), i); await p.waitForFunction(() => !window.__kerf.asm.busy, null, {{ timeout: 30000 }}); await p.waitForTimeout(100);
  out.steps.push(await p.evaluate(() => [...window.__kerf.groups.values()].filter(g => g.visible && g.userData.mesh.material.opacity > 0.5).map(g => g.userData.it.id).sort()));
}}
await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(50); out.keyBack = await p.evaluate(() => window.__kerf.asm.i);
await p.click('[data-tab="motion"]'); out.exited = await p.evaluate(() => !window.__kerf.asm.on && [...window.__kerf.groups.values()].every(g => g.userData.it.role === 'keepout' || g.visible));
const K = 'window.__kerf';
const items = await p.evaluate(() => window.__kerf.D.items.filter(i => i.id === 'flap').map(i => ({{ id: i.id, role: i.role, verts: i.verts, tris: i.tris }})));
await p.evaluate(items => window.__kerf.compare({{ label: 'v1', items, dist: {{}}, gdist: {{}}, summary: [{{ id: 'flap', status: 'changed', max_mm: 1.5 }}, {{ id: 'base', status: 'same', max_mm: 0 }}] }}), items);
out.compare = await p.evaluate(() => [window.__kerf.colorMode, document.querySelector('#clegend').textContent.includes('changed, up to 1.5 mm')]);
await p.click('#cx'); out.compareOff = await p.evaluate(() => window.__kerf.colorMode);
console.log(JSON.stringify({{ errs, ...out }})); await b.close();""")
    r = subprocess.run(["node", str(js)], capture_output=True, text=True, timeout=240)
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errs"] == [], out["errs"]
    assert out["cutPanel"] and out["cutOff"] and 0 < out["cut"] < out["full"]          # the cut removes part of the picture
    assert out["stressBtn"] and out["stressMode"] == "stress" and "carriage" in out["legend"] and "base" in out["legend"]
    assert out["png"] and out["after"] > 0.8 * out["full"]                             # the picture leaves the view as it was
    assert out["cards"] == 5                                                           # before you start, 3 steps, finished
    assert out["steps"][1:4] == [["base"], ["base", "carriage"], ["base", "carriage", "flap"]]
    assert out["keyBack"] == 3 and out["exited"]
    assert out["compare"] == ["compare", True] and out["compareOff"] == "normal"
