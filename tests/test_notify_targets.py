"""Notifications go where they are about (Spencer, 2026-11-02: "notifications about processes or projects should snap
to the relevant view when clicked"): pop-ups and Mac desktop notifications carry a target that opens that project's
tab (Checks for a failure, Tune for a try, 3D for a build) or the job; Activity rows open their project too."""
import time
from pathlib import Path
from types import SimpleNamespace as NS

from kerf import studio
from test_studio import _browser, server  # noqa: F401  (fixture)


def test_server_leaves_notifications_to_the_mac_app_while_it_is_open(monkeypatch):
    sent = []
    monkeypatch.setattr(studio, "notify", lambda *a: sent.append(a) or True)
    monkeypatch.setattr(studio, "settings", lambda: {"notify": True})
    job = NS(kind="design", state="done", started=time.time() - 600, ended=time.time(), label="New design", lines=[], events=[])
    monkeypatch.setitem(studio.LIFE, "native", time.time())
    assert studio.notify_job(job) is False and sent == []
    monkeypatch.setitem(studio.LIFE, "native", 0.0)
    monkeypatch.setattr(studio, "job_outcome", lambda j: (True, "done"))
    assert studio.notify_job(job) is True and len(sent) == 1


def test_swift_app_posts_clickable_notifications():
    src = (Path(__file__).resolve().parent.parent / "tools" / "mac" / "KerfStudio.swift").read_text()
    assert "UNUserNotificationCenterDelegate" in src and "window.kerfOpen" in src and "didReceive response" in src
    inst = (Path(__file__).resolve().parent.parent / "tools" / "mac" / "install_app.sh").read_text()
    assert "-framework UserNotifications" in inst


def test_page_targets_and_click_through(server, tmp_path):  # noqa: F811
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof kerfOpen === 'function' && S.projects.length > 1);
const names = await p.evaluate(() => S.projects.map(x => x.name));
out.targets = await p.evaluate(n => [jobTarget({kind: 'build', project: n, state: 'done'}, true), jobTarget({kind: 'build', project: n}, false),
  jobTarget({kind: 'trial', project: n}, true), jobTarget({kind: 'check', project: '*', id: 'j9'}, true), jobTarget({kind: 'quote', project: 'x'}, true)], names[1]);
await p.evaluate(n => toast('Build done', '3 problems', 'bad', 'project:' + n + ':results'), names[1]);
await p.click('.toast.go');
await p.waitForFunction(n => S.detail && S.detail.name === n && S.tab === 'results', names[1]);
out.opened = await p.evaluate(() => [S.sel, S.tab]);
out.toastGone = await p.$$eval('.toast.go', e => e.length);
// a job that finishes while you aren't watching it still tells you, with a target
await p.evaluate(n => { S.jobStates = {jx: 'running'}; S.seenDone.delete('jx'); const f = window.fetch;
  window.fetch = (u, o) => String(u).startsWith('/api/jobs') ? Promise.resolve(new Response(JSON.stringify({jobs: [{id: 'jx', kind: 'build',
    project: n, state: 'failed', label: 'Build kit: ' + n, tail: [], seconds: 30}], sessions: []}), {headers: {'Content-Type': 'application/json'}})) : f(u, o);
  return pollJobs().then(() => { window.fetch = f; }); }, names[0]);
out.bg = await p.$$eval('.toast.go b', e => e.map(x => x.textContent));""", tmp_path)
    assert out["errs"] == [], out
    t = out["targets"]
    assert t[0].endswith(":model") and t[1].endswith(":results") and t[2].endswith(":tune") and t[3] == "job:j9" and t[4] == "quote:x", t
    assert out["opened"][1] == "results" and out["toastGone"] == 0
    assert any(x.startswith("Build kit: ") for x in out["bg"]), out


def test_two_option_runs_each_open_with_their_own_request(server, tmp_path, monkeypatch):  # noqa: F811
    import json
    qd = tmp_path / "quotes"; qd.mkdir()
    monkeypatch.setattr(studio, "QUOTES", qd)
    good = {"title": "A", "summary": "s", "parts_printed": 5, "cost_usd": 21.5, "print_hours": 6, "risks": []}
    for name, desc, titles in (("hawk_v2", "a folding hawk drone", ["Pivot root", "Swing arm"]),
                               ("launcher", "a reusable drone launcher", ["Bungee rail", "Spring sled"])):
        (qd / f"{name}.json").write_text(json.dumps({"options": [good | {"title": t} for t in titles], "recommended": 0}))
        (qd / f"{name}.request.json").write_text(json.dumps({"description": desc, "intake": {}}))
    assert [q["name"] for q in studio.list_quotes()] and {q["name"] for q in studio.list_quotes()} == {"hawk_v2", "launcher"}
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof openQuote === 'function' && S.projects.length > 0);
await p.evaluate(() => showNew()); await p.waitForSelector('#quotesready .qrow');
out.rows = await p.$$eval('#quotesready .qrow b', e => e.map(x => x.textContent));
await p.click('#quotesready .qrow:has-text("launcher")'); await p.waitForSelector('.qopt');
out.l = await p.evaluate(() => [$('#ndesc').value, [...document.querySelectorAll('.qopt b')].map(x => x.textContent), document.querySelectorAll('.qopt button.primary:not([disabled])').length]);
await p.evaluate(() => kerfOpen('quote:hawk_v2')); await p.waitForFunction(() => $('#ndesc').value === 'a folding hawk drone');
await p.waitForFunction(() => [...document.querySelectorAll('.qopt b')].some(x => x.textContent === 'Pivot root'));
out.h = await p.evaluate(() => [$('#nname').value, document.querySelectorAll('.qopt button.primary:not([disabled])').length]);""", tmp_path)
    assert out["errs"] == [], out
    assert set(out["rows"]) == {"hawk v2", "launcher"}
    assert out["l"][0] == "a reusable drone launcher" and out["l"][1][:2] == ["Bungee rail", "Spring sled"] and out["l"][2] == 2, out
    assert out["h"] == ["hawk_v2", 2], out                                      # each one's buttons are live, not blocked


def test_paused_card_and_options_badge(server, tmp_path, monkeypatch):  # noqa: F811
    import json
    qd = tmp_path / "quotes"; qd.mkdir()
    monkeypatch.setattr(studio, "QUOTES", qd)
    good = {"title": "A", "summary": "s", "parts_printed": 5, "cost_usd": 21.5, "print_hours": 6, "risks": []}
    (qd / "launcher.json").write_text(json.dumps({"options": [good, good | {"title": "B"}], "recommended": 0}))
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof pollQuotes === 'function');
await p.evaluate(() => pollQuotes()); await p.waitForSelector('#qbadge:not([hidden])');
out.badge = await p.textContent('#qbadge');
out.card = await p.evaluate(() => { const d = document.createElement('div');
  d.innerHTML = pausedCard({id: 'j1', state: 'paused', resumable: true, usage: {until: 1893456000}}); return d.textContent; });
out.target = await p.evaluate(() => jobTarget({id: 'j1', state: 'paused', kind: 'design', project: 'x'}, false));
await p.click('#qbadge'); await p.waitForSelector('#quotesready .qrow');
out.rows = await p.$$eval('#quotesready .qrow b', e => e.map(x => x.textContent));""", tmp_path)
    assert out["errs"] == [], out
    assert "launcher" in out["badge"] and "Resume now" in out["card"] and "Paused" in out["card"] and out["target"] == "job:j1"
    assert out["rows"] == ["launcher"]


def test_design_this_needs_no_typing(server, tmp_path, monkeypatch):  # noqa: F811
    import json
    qd = tmp_path / "quotes"; qd.mkdir()
    monkeypatch.setattr(studio, "QUOTES", qd)
    good = {"title": "A", "summary": "s", "parts_printed": 5, "cost_usd": 21.5, "print_hours": 6, "risks": []}
    (qd / "launcher_x.json").write_text(json.dumps({"request": "a reusable drone launcher", "options": [good, good | {"title": "B"}], "recommended": 0}))
    seen = {}
    def fake_new(name, description, intake=None, option=None, option_index=None):
        seen.update(name=name, description=description, option=option if option is not None else option_index)
        return type("J", (), {"id": "j1"})()
    monkeypatch.setattr(studio, "new_design", fake_new)
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof openQuote === 'function');
await p.evaluate(() => openQuote('launcher_x')); await p.waitForSelector('.qopt button.primary');
await p.evaluate(() => { $('#ndesc').value = ''; window.watch = () => {}; });   // the box emptied: still starts
await p.click('.qopt button.primary');
await p.waitForTimeout(800);
out.toasts = await p.$$eval('.toast b', e => e.map(x => x.textContent));""", tmp_path)
    assert out["errs"] == [], out
    assert seen.get("name") == "launcher_x" and seen.get("description") == "a reusable drone launcher" and seen["option"], (seen, out)
    assert "Design started" in out["toasts"], out


def test_server_uses_the_options_request_when_none_is_sent(monkeypatch, tmp_path):
    import json
    import pytest
    monkeypatch.setattr(studio, "QUOTES", tmp_path)
    good = {"title": "A", "summary": "s", "parts_printed": 5, "cost_usd": 21.5, "print_hours": 6, "risks": []}
    (tmp_path / "hawk_q.json").write_text(json.dumps({"options": [good, good | {"title": "B"}], "recommended": 0}))
    (tmp_path / "hawk_q.request.json").write_text(json.dumps({"description": "a folding hawk drone", "intake": {}}))
    got = {}
    def stop(n, d):
        got.update(n=n, d=d)
        raise ValueError("stop")
    monkeypatch.setattr(studio, "_check_new", stop)
    with pytest.raises(ValueError, match="stop"):
        studio.new_design("hawk_q", "", {}, None, 0)
    assert got == {"n": "hawk_q", "d": "a folding hawk drone"}
