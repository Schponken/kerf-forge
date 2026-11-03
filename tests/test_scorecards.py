import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from kerf import lessons, scorecards, studio


def seed(tmp_path):
    (tmp_path / "learning").mkdir()
    (tmp_path / "learning" / "lessons.json").write_text(json.dumps({"lessons": [{"id": "fit", "lesson": "Check fit", "level": "note"}]}))
    return tmp_path


def record(repo, event_id="one", **kw):
    return scorecards.record("fit", repo=repo, event_id=event_id, outcome=kw.pop("outcome", "caught"), evidence=kw.pop("evidence", "Check found a collision"), **kw)


def test_evidence_idempotence_and_unknown_savings(tmp_path):
    repo = seed(tmp_path)
    assert scorecards.read(repo)["lessons"][0]["scorecard"]["times_applied"] == 0
    record(repo, project="arm")
    record(repo, project="arm")
    c = record(repo, "two", project="drone", saved_min=4, savings_source="Timed old and new workflow in log A")["scorecard"]
    assert c["times_applied"] == 2 and c["times_caught"] == 2
    assert c["saved_min"] is None and c["known_saved_min"] == 4
    assert c["promotion"] == "proposed gate"
    assert c["what_caught"] == ["Check found a collision"] * 2
    with pytest.raises(ValueError, match="different evidence"):
        record(repo, evidence="Changed")
    c = record(repo, "three", outcome="blocked_good_work", evidence="Independent fit check passed")["scorecard"]
    assert c["blocked_good_work"] == 1 and c["flag"] == "blocking" and c["promotion"] is None


@pytest.mark.parametrize("saved", [-1, float("nan"), float("inf"), True, "5"])
def test_reject_invalid_savings(tmp_path, saved):
    with pytest.raises(ValueError):
        record(seed(tmp_path), saved_min=saved)


def test_dead_lesson_and_rebuild_preserve_ledger(tmp_path):
    repo = seed(tmp_path)
    for i in range(3):
        row = record(repo, str(i), outcome="no_issue", evidence="Applied with no finding")
    assert row["scorecard"]["flag"] == "dead"
    (repo / "learning" / "diary").mkdir()
    rebuilt = lessons.run(repo=repo)["data"]["lessons"][0]
    assert rebuilt["historical_only"] and rebuilt["applications"] == row["applications"]
    assert scorecards.read(repo)["lessons"][0]["scorecard"]["times_applied"] == 3
    assert scorecards.preserve({"lessons": [{"id": "fit"}]}, {"lessons": [row]})["lessons"][0]["applications"] == row["applications"]


def test_scorecards_api_uses_real_records(tmp_path, monkeypatch):
    repo = seed(tmp_path)
    record(repo, saved_min=0, savings_source="No extra work avoided")
    monkeypatch.setattr(studio, "ROOT", repo)
    server = ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/scorecards") as response:
            row = json.load(response)["lessons"][0]
        assert row["scorecard"]["times_applied"] == 1 and row["scorecard"]["saved_min"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_missing_savings_source_rejected(tmp_path):
    with pytest.raises(ValueError, match="source"):
        record(seed(tmp_path), saved_min=2)


@pytest.mark.browser
def test_learning_panel_navigation_and_evidence(tmp_path):
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    fixture = scorecards.preserve({"lessons": [{"id": "fit", "lesson": "Illustrative fit lesson", "level": "note"}]}, {"lessons": []})
    fixture["lessons"][0]["applications"] = [{"id": "test", "outcome": "caught", "evidence": "<script>unsafe</script>", "saved_min": None, "project": "Illustrative fixture"}]
    fixture["lessons"][0]["scorecard"] = scorecards.summarize(fixture["lessons"][0]["applications"])
    script = tmp_path / "learning.mjs"
    script.write_text('''
import {browser as openBrowser} from BROWSER;
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const html=await fs.readFile(HTML,'utf8'), browser=await openBrowser(),fixture=FIXTURE;
try {
for (const width of [1440,390]) {
const p=await browser.newPage({viewport:{width,height:900}}), errors=[];
p.on('pageerror',e=>errors.push(e.message));
await p.route('**/*', r=>{const path=new URL(r.request().url()).pathname;
if(path==='/')return r.fulfill({contentType:'text/html',body:html});
if(path==='/api/projects')return r.fulfill({json:{projects:[]}});
if(path==='/api/scorecards')return r.fulfill({json:fixture});
if(path==='/api/jobs')return r.fulfill({json:{jobs:[],sessions:[]}});
return r.fulfill({json:{}});});
await p.goto('http://kerf.test/'); await p.locator('#nav_learning').click();
await p.getByRole('heading',{name:'Illustrative fit lesson'}).waitFor();
assert.equal(await p.locator('#nav_learning').getAttribute('aria-current'),'page');
assert.ok((await p.locator('#main').innerText()).includes('Applied 1 times'));
assert.ok((await p.locator('#main').innerText()).includes('Work saved: unknown'));
await p.getByText('Application evidence').click();
assert.ok((await p.locator('#main').innerText()).includes('<script>unsafe</script>'));
assert.equal(await p.locator('#main script').count(),0);
assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
await p.evaluate(()=>document.getAnimations().forEach(a=>a.finish()));
await p.screenshot({path:CAPTURE+'/learning-'+width+'.png'});
await p.locator('#nav_grid').click();
assert.equal(await p.locator('#nav_learning').getAttribute('aria-current'),null);
assert.deepEqual(errors,[]); await p.close();
}
}finally{await browser.close();}
'''.replace('BROWSER', json.dumps(str(root / 'tests/browser.mjs'))).replace('HTML', json.dumps(str(root / 'kerf/assets/studio.html'))).replace('FIXTURE', json.dumps(fixture)).replace('CAPTURE', json.dumps(str(tmp_path))))
    result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


def test_concurrent_records_and_rebuilds_keep_every_application(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    repo = seed(tmp_path)
    (repo / "learning" / "diary").mkdir()
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = []
        for i in range(12):
            futures.append(pool.submit(record, repo, str(i), outcome="no_issue"))
            futures.append(pool.submit(lessons.run, repo=repo))
        for future in futures:
            future.result()
    row = scorecards.read(repo)["lessons"][0]
    assert row["scorecard"]["times_applied"] == 12
    assert {e["id"] for e in row["applications"]} == {str(i) for i in range(12)}
