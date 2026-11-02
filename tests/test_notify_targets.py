"""Notifications go where they are about (Spencer, 2026-11-02: "notifications about processes or projects should snap
to the relevant view when clicked"): pop-ups and Mac desktop notifications carry a target that opens that project's
tab (Checks for a failure, Tune for a try, 3D for a build) or the job; Activity rows open their project too."""
import time
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

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


@pytest.mark.browser
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
    assert t[0].endswith(":model") and t[1].endswith(":results") and t[2].endswith(":tune") and t[3] == "job:j9" and t[4] == "new", t
    assert out["opened"][1] == "results" and out["toastGone"] == 0
    assert any(x.startswith("Build kit: ") for x in out["bg"]), out
