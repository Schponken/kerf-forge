"""Usage-out failsafes (Spencer, 2026-11-02: "add in failsafes throughout for in case usage runs out"): a Claude job
cut off by the usage limit is PAUSED (not failed), keeps its session, resumes by itself when usage is back (not with
the budget switch on) or now with Resume; no new Claude job starts while usage is out; every job is told to commit as
it goes; auto-fix waits too."""
import json
import sys
import time
from pathlib import Path

import pytest

from kerf import studio

FAKE = Path(__file__).resolve().parent / "fixtures" / "fake_claude_usage.py"


def test_reset_times_are_read_from_the_message():
    assert studio.usage_reset("Claude AI usage limit reached|1762126800") == 1762126800.0
    now = time.mktime((2026, 11, 2, 18, 0, 0, 0, 0, -1))
    t = time.localtime(studio.usage_reset("You've hit your limit · resets 7pm (America/New_York)", now))
    assert (t.tm_hour, t.tm_min) == (19, 0)
    assert studio.usage_reset("5-hour limit reached", now) == now + 3600
    assert studio.USAGE_RX.search("Claude AI usage limit reached|1762126800")
    assert not studio.USAGE_RX.search("checked the limit switch")


def test_cut_off_job_pauses_keeps_its_session_and_blocks_new_claude_work(monkeypatch, tmp_path):
    monkeypatch.setattr(studio, "USAGE", {"until": 0.0, "text": ""})
    monkeypatch.setattr(studio, "settings", lambda: {"notify": False, "sound": False, "autofix": True, "autoresume": False})
    j = studio.start_job("design", "zz_usage_demo", [sys.executable, str(FAKE)], "New design: demo", parse=studio._claude_lines)
    for _ in range(100):
        if j.state != "running":
            break
        time.sleep(0.05)
    assert j.state == "paused" and j.session == "sess-123" and j.usage and j.usage["until"] == 1893456000.0
    info = j.info()
    assert info["resumable"] and info["usage"]["until"] == 1893456000.0
    monkeypatch.setitem(studio.USAGE, "until", time.time() + 600)
    with pytest.raises(ValueError, match="usage is used up"):
        studio.start_job("edit", "zz_other", [sys.executable, "-c", "print(1)"], "Change: x")
    assert studio.claude_ready().get("code") in ("usage", "missing", "auth", "trust")
    monkeypatch.setattr(studio, "_report", lambda d: {"ok": False, "problems": ["x"], "fingerprint": "f"})
    from types import SimpleNamespace as NS
    assert studio.auto_fix(NS(kind="build", project="servo_link", state="failed")) is None   # no fix while usage is out
    studio.JOBS.pop(j.id, None)


def test_resume_uses_the_same_session_and_respects_the_budget_switch(monkeypatch):
    monkeypatch.setattr(studio, "USAGE", {"until": 0.0, "text": ""})
    started = []
    monkeypatch.setattr(studio, "start_job", lambda *a, **k: started.append(a) or type("J", (), {"id": "new1"})())
    monkeypatch.setattr(studio, "claude_bin", lambda: "claude")
    old = type("Old", (), {"state": "paused", "session": "sess-9", "resumed_by": None, "kind": "fix", "project": "p",
                           "label": "Fix p", "env": None, "lines": []})()
    monkeypatch.setitem(studio.JOBS, "o1", old)
    monkeypatch.setattr(studio, "budget_stop", lambda: "near the weekly cap")
    with pytest.raises(ValueError, match="budget switch"):
        studio.resume_job("o1", auto=True)
    j = studio.resume_job("o1")                                  # a person pressing Resume now is not blocked
    cmd = started[0][2]
    assert j.id == "new1" and old.resumed_by == "new1" and cmd[cmd.index("--resume") + 1] == "sess-9"
    with pytest.raises(ValueError, match="resumed already"):
        studio.resume_job("o1")


def test_every_claude_job_is_told_to_save_as_it_goes(monkeypatch):
    monkeypatch.setattr(studio, "USAGE", {"until": 0.0, "text": ""})
    cmd = [sys.executable, "-p", "do the thing"]
    j = studio.start_job("edit", "zz_note_demo", cmd, "Change: note")
    assert studio.CUTOFF_NOTE in cmd[2]
    j.stop(); studio.JOBS.pop(j.id, None)
