"""Plain-English glossary (kerf/glossary.py): every requirement check is explained, Studio serves it, failed-requirement
cards and the requirement table use the plain names, and jargon in a tab gets an explaining underline."""
import json

from kerf import explain, glossary, requirements
from test_studio import _browser, _get, server  # noqa: F401  (fixture)


def test_every_check_has_a_plain_name_and_meaning():
    missing = sorted(set(requirements.REGISTRY) - set(glossary.CHECKS))
    assert not missing, f"add these checks to kerf/glossary.py CHECKS: {missing}"
    for k, (name, means) in glossary.CHECKS.items():
        assert name and means.endswith(".") and len(means) < 200, k
    for k, v in glossary.TERMS.items():
        assert v.endswith(".") and len(v) < 220, k


def test_failed_requirement_card_uses_the_plain_name():
    card = explain.explain_requirement({"id": "arm_resonance", "check": "natural_freq", "value": 186.0, "limit": 200, "unit": "Hz", "bound": "min"})
    assert card["title"].startswith("Doesn't shake itself apart")
    assert glossary.name("not_a_check") == "not_a_check"


def test_studio_serves_it_and_underlines_jargon(server, tmp_path):  # noqa: F811
    code, body = _get(server + "/api/glossary")
    g = json.loads(body)
    assert code == 200 and g["checks"]["fea_static"]["name"] == "Strength under load" and "FEA" in g["terms"]
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof glossify === 'function' && GL.rx);
out.n = await p.evaluate(() => { const d = document.createElement('div');
  d.innerHTML = '<p>The FEA shows high stress in the arm; FEA again. <code>FEA</code> PLAnet heat-set insert done.</p>';
  document.body.appendChild(d); glossify(d); return [...d.querySelectorAll('abbr.gl')].map(a => a.textContent + '=' + !!a.title); });
out.name = await p.evaluate(() => glossCheck('natural_freq').name);
await p.evaluate(() => showGlossary());
out.rows = await p.$$eval('.glmodal .glrow', e => e.length);
await p.fill('.glmodal input', 'infill');
out.shown = await p.$$eval('.glmodal .glrow', e => e.filter(x => x.style.display !== 'none').length);""", tmp_path)
    assert out["errs"] == [], out
    assert out["n"] == ["FEA=true", "stress=true", "heat-set insert=true"], out["n"]   # first use only; not in code or inside words
    assert out["name"] == "Doesn't shake itself apart"
    assert out["rows"] == len(glossary.CHECKS) + len(glossary.TERMS) and 1 <= out["shown"] < 5


def test_tune_compare_says_better_or_worse_in_plain_words(server, tmp_path):  # noqa: F811
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof compareTable === 'function' && GL.rx);
out.html = await p.evaluate(() => { S.detail = {report: {requirements: []}};
  const saved = [{id: 'w', check: 'mass_max', value: 300, ok: true, bound: 'max', limit: 350, unit: 'g'},
                 {id: 't', check: 'thrust_to_weight', value: 6.4, ok: true, bound: 'min', limit: 6, unit: ':1'},
                 {id: 'c', check: 'static_margin', value: 0.05, ok: true, bound: 'range', limit: [0.05, 0.15], unit: 'x MAC'}];
  const tried = [{...saved[0], value: 280}, {...saved[1], value: 5.8, ok: false}, {...saved[2], value: 0.09}];
  const d = document.createElement('div'); d.innerHTML = compareTable(saved, tried);
  return [...d.querySelectorAll('tr')].slice(1).map(r => [r.querySelector('b').textContent, r.querySelector('.fxs').textContent, r.querySelector('.fxa').className]); });""", tmp_path)
    assert out["errs"] == [], out
    assert out["html"] == [["Total weight", "better", "fxa up"], ["Thrust vs weight", "now fails", "fxa down"],
                           ["Flies stable (balance)", "better", "fxa up"]], out["html"]
