"""Job failure recovery uses mocked processes; no builds or AI agents are started."""
from types import SimpleNamespace as NS

import pytest

from kerf import studio


@pytest.fixture
def failed_report(monkeypatch):
    monkeypatch.setattr(studio, "JOBS", {})
    monkeypatch.setattr(studio, "notify_job", lambda job: None)
    monkeypatch.setattr(studio, "AUTOFIXED", {})
    monkeypatch.setattr(studio, "settings", lambda: {"autofix": True})
    monkeypatch.setattr(studio, "budget_stop", lambda: "")
    monkeypatch.setattr(studio, "pick_agent", lambda: "codex")
    monkeypatch.setattr(studio, "_worked_on", lambda name: False)
    monkeypatch.setattr(studio, "_report", lambda path: {"ok": False, "fingerprint": "failed-design"})
    return NS(kind="build", project="demo", state="failed")


@pytest.mark.parametrize("kind", ["build", "check"])
def test_stop_does_not_start_auto_fix_from_an_old_failed_report(monkeypatch, failed_report, kind):
    failed_report.kind, failed_report.state = kind, "stopped"
    monkeypatch.setattr(studio, "fix_job", lambda name: pytest.fail("Stop launched an automatic fix"))
    studio.on_finished(failed_report)
    assert studio.AUTOFIXED == {}


def test_failed_auto_fix_launch_keeps_the_same_design_retryable(monkeypatch, failed_report):
    launches = []
    def launch(name):
        launches.append(name)
        if len(launches) == 1:
            raise OSError("agent executable disappeared")
        return NS(id="fix-job")
    monkeypatch.setattr(studio, "fix_job", launch)
    with pytest.raises(OSError, match="disappeared"):
        studio.auto_fix(failed_report)
    assert studio.AUTOFIXED == {}
    assert studio.auto_fix(failed_report).id == "fix-job"
    assert studio.auto_fix(failed_report) is None
    assert launches == ["demo", "demo"]


@pytest.mark.parametrize("failure", ["parser", "read"])
@pytest.mark.parametrize("group_exists", [True, False])
@pytest.mark.parametrize("stop_state", [None, "stopped"])
def test_output_failure_reaps_process_and_releases_project(monkeypatch, failure, group_exists, stop_state):
    calls = []
    class Output:
        def __iter__(self):
            yield "partial output\n"
            if failure == "read":
                raise UnicodeError("cannot decode output")
        def close(self):
            calls.append("close")
    class Process:
        pid, stdout, returncode = 123456, Output(), None
        def kill(self):
            calls.append("kill")
        def wait(self):
            assert job.state == "running" and studio.busy()
            with pytest.raises(ValueError, match="already running"):
                studio.require_idle("demo")
            calls.append("wait")
            self.returncode = -9
            return self.returncode
    def killpg(pid, sig):
        assert pid == Process.pid and sig == 9
        calls.append("killpg")
        if not group_exists:
            raise ProcessLookupError("process group already gone")
    def parse(raw):
        if failure == "parser":
            raise ValueError("invalid agent event")
        return [raw.rstrip("\n")]
    job = object.__new__(studio.Job)
    job.id, job.project, job.kind, job.label = "bad-output", "demo", "design", "Design demo"
    job.proc, job.parse = Process(), parse
    job.lines, job.events = [], []
    job.state, job._stop_state, job.usage, job.ended = "running", stop_state, {"until": 1}, None
    monkeypatch.setattr(studio, "JOBS", {job.id: job})
    monkeypatch.setattr(studio.os, "killpg", killpg)
    monkeypatch.setattr(studio, "on_finished", lambda completed: calls.append(completed.state))
    monkeypatch.setattr(studio, "schedule_resume", lambda completed: pytest.fail("output failure resumed a job"))
    job._pump()
    expected = stop_state or "failed"
    assert job.state == expected and job.ended is not None
    assert job.proc.returncode == -9
    assert calls == ["killpg", *([] if group_exists else ["kill"]), "wait", "close", expected]
    assert any("output" in line and "failed" in line for line in job.lines)
    assert not studio.busy()
    studio.require_idle("demo")


@pytest.mark.parametrize("outcome", ["done", "failed", "paused"])
def test_normal_output_still_finishes_and_preserves_usage_resume(monkeypatch, outcome):
    import io
    output = '@@{"k":"session","id":"saved-session"}\nplain output\n'
    if outcome == "paused":
        output += '@@{"k":"usage","until":1893456000,"text":"usage limit reached"}\n'
    stdout = io.StringIO(output)
    job = object.__new__(studio.Job)
    job.project, job.kind = "demo", "design"
    job.proc = NS(stdout=stdout, wait=lambda: 1 if outcome == "failed" else 0)
    job.parse, job.lines, job.events = None, [], []
    job.state, job._stop_state, job.usage, job.session, job.ended = "running", None, None, None, None
    monkeypatch.setattr(studio, "USAGE", {"until": 0, "text": ""})
    callbacks = []
    monkeypatch.setattr(studio, "schedule_resume", lambda completed: callbacks.append("resume"))
    monkeypatch.setattr(studio, "on_finished", lambda completed: callbacks.append(completed.state))
    job._pump()
    assert job.state == outcome and job.ended is not None
    assert stdout.closed and job.session == "saved-session" and job.lines[0] == "plain output"
    assert callbacks == (["resume", "paused"] if outcome == "paused" else [outcome])
    assert bool(studio.USAGE["until"]) == (outcome == "paused")
