"""Studio Activity lists the Claude / Codex sessions working on a project (fresh claims), not only Studio's own jobs, and
the Checks tab shows what that session has saved lately."""
import time

from kerf import explain, studio
from test_studio import _browser, server  # noqa: F401  (fixture)


def _claim(monkeypatch):
    monkeypatch.setattr(studio, "_live_thread", lambda: None)
    fake = [{"item": "`servo_link` — fix the bracket", "provider": "Codex", "heartbeat": time.time() - 120}]
    monkeypatch.setattr(explain, "claims", lambda root=None: fake)
    studio.SESSIONS["at"] = 0.0


def test_sessions_and_recent_work(monkeypatch):
    _claim(monkeypatch)
    ss = studio.sessions(max_age=0)
    assert [x["project"] for x in ss] == ["servo_link"] and "2 min ago" in ss[0]["text"]
    assert ss[0]["last"] and ss[0]["last"]["subject"]          # its latest commit on projects/servo_link
    w = studio.explained("servo_link", {"problems": []}, {})["work"]
    assert w["state"] == "claimed" and 1 <= len(w["recent"]) <= 4 and all(c["time"] > 0 for c in w["recent"])
    monkeypatch.setattr(explain, "claims", lambda root=None: [])
    assert studio.explained("servo_link", {"problems": []}, {})["work"]["state"] == "idle"


def test_activity_shows_the_session(server, monkeypatch, tmp_path):  # noqa: F811
    _claim(monkeypatch)
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof pollJobs === 'function' && S.projects);
await p.evaluate(() => pollJobs());
await p.waitForSelector('#joblist .job.sess', {timeout: 10000});
out.row = await p.textContent('#joblist .job.sess');
out.tip = await p.getAttribute('#joblist .job.sess', 'title');
await p.click('#joblist .job.sess');
await p.waitForFunction(() => S.detail && S.detail.name === 'servo_link' && S.tab === 'results');""", tmp_path)
    assert out["errs"] == [], out
    assert "☁" in out["row"] and "min ago" in out["row"], out["row"]
    assert "Codex has claimed" in out["tip"] and "working" not in out["tip"], out["tip"]
