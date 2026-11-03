"""A stop request must not unlock a project before its process exits."""
import sys
import threading

import pytest

from kerf import studio


@pytest.mark.parametrize("outcome,usage", [("stopped", False), ("failed", False),
                                           ("stopped", True), ("failed", True), ("paused", True)])
def test_stopping_job_holds_project_until_process_exits(tmp_path, monkeypatch, outcome, usage):
    release = tmp_path / "release"
    script = tmp_path / "child.py"
    script.write_text("""import signal, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, lambda *_: print('terminating', flush=True))
if sys.argv[3] == 'True':
    print('{"type":"system","subtype":"init","session_id":"test-session"}', flush=True)
    print('Claude AI usage limit reached|1893456000', flush=True)
print('ready', flush=True)
if sys.argv[2] == 'failed':
    print('Failed to authenticate: OAuth session expired and could not be refreshed', flush=True)
while not Path(sys.argv[1]).exists():
    time.sleep(0.01)
print('cleanup complete', flush=True)
""", encoding="utf-8")
    ready, terminating, finished = (threading.Event() for _ in range(3))

    def parse(raw):
        if raw.strip() == "ready":
            ready.set()
        if raw.strip() == "terminating":
            terminating.set()
        return studio._claude_lines(raw)

    monkeypatch.setattr(studio, "JOBS", {})
    monkeypatch.setattr(studio, "USAGE", {"until": 0.0, "text": ""})
    scheduled = []
    def schedule(job):
        assert job.proc.poll() == 0 and "cleanup complete" in job.lines
        scheduled.append(job)
    monkeypatch.setattr(studio, "schedule_resume", schedule)
    monkeypatch.setattr(studio, "on_finished", lambda job: finished.set())
    job = studio.start_job("design", "demo", [sys.executable, str(script), str(release), outcome, str(usage)],
                           "Design demo", parse=parse)
    try:
        assert ready.wait(5), "child did not start"
        if outcome == "stopped":
            job.stop()
        if outcome != "paused":
            assert terminating.wait(5), "child did not receive the stop signal"
        assert job.proc.poll() is None
        assert job.state == "running" and job.ended is None
        assert studio.busy()
        for project in ("demo", "*"):
            with pytest.raises(ValueError, match="Activity"):
                studio.start_job("trial", project, [], "Try again",
                                 prepare=lambda: pytest.fail("active trial overwritten"))
        studio.require_idle("another_project")
        if outcome != "paused":
            job.stop()  # Repeated stops must not replace an authentication failure with "stopped".
        release.touch()
        assert finished.wait(5), "child did not finish"
        assert job.state == outcome and job.ended is not None
        assert job.proc.returncode == 0  # Even a graceful exit must retain the requested outcome.
        assert "cleanup complete" in job.lines
        assert scheduled == ([job] if outcome == "paused" else [])
        if usage:
            assert job.usage and job.session == "test-session"
        assert not studio.busy()
        studio.require_idle("demo")
        studio.require_idle("*")
    finally:
        release.touch()
        if not finished.wait(5):
            job.proc.kill()
            job.proc.wait(timeout=5)


@pytest.fixture
def paused_job(monkeypatch):
    job = object.__new__(studio.Job)
    job.id, job.kind, job.project, job.label = "old", "design", "demo", "Design demo"
    job.state, job._stop_state, job.session = "paused", None, "saved-session"
    job.resumed_by, job.env, job.agent, job.lines = None, None, "claude", []
    job.usage = {"until": 1893456000}
    monkeypatch.setattr(studio, "JOBS", {job.id: job})
    monkeypatch.setattr(studio, "USAGE", {"until": 0.0, "text": ""})
    monkeypatch.setattr(studio, "settings", lambda: {"autoresume": True})
    monkeypatch.setattr(studio, "budget_stop", lambda: "")
    monkeypatch.setattr(studio.agent, "can_take_over", lambda: False)
    return job


@pytest.fixture
def queued_resume(monkeypatch, paused_job):
    options, callbacks, launches = {"autoresume": True}, [], []
    class Timer:
        def __init__(self, delay, callback):
            callbacks.append(callback)
        def start(self):
            pass
    class Successor:
        id = "new"
    def launch(*a, **k):
        launches.append(k)
        return Successor()
    monkeypatch.setattr(studio, "settings", lambda: options)
    monkeypatch.setattr(studio.threading, "Timer", Timer)
    monkeypatch.setattr(studio, "agent_job", launch)
    studio.USAGE["until"] = paused_job.usage["until"]
    studio.schedule_resume(paused_job, delay=1)
    assert len(callbacks) == 1
    return options, callbacks[0], launches


@pytest.mark.parametrize("reenabled", [False, True])
def test_queued_resume_reads_current_setting(paused_job, queued_resume, reenabled):
    options, callback, launches = queued_resume
    options["autoresume"] = False
    if reenabled:
        options["autoresume"] = True
    callback()
    assert paused_job.state == "paused"
    if reenabled:
        assert len(launches) == 1 and paused_job.resumed_by == "new"
        assert launches[0]["resume"] == paused_job.session
        assert not paused_job.lines and studio.USAGE["until"] == 0
    else:
        assert not launches and paused_job.resumed_by is None
        assert paused_job.lines == ["(not resumed automatically: automatic resume is off)"]
        assert studio.USAGE["until"] == paused_job.usage["until"]


def test_queued_resume_reads_setting_after_budget_check(monkeypatch, paused_job, queued_resume):
    options, callback, launches = queued_resume
    entered, release = threading.Event(), threading.Event()
    def budget():
        entered.set()
        assert release.wait(5)
        return ""
    monkeypatch.setattr(studio, "budget_stop", budget)
    runner = threading.Thread(target=callback)
    runner.start()
    try:
        assert entered.wait(5)
        options["autoresume"] = False
    finally:
        release.set()
        runner.join(5)
    assert not runner.is_alive() and not launches
    assert paused_job.state == "paused" and paused_job.resumed_by is None
    assert paused_job.lines == ["(not resumed automatically: automatic resume is off)"]
    assert studio.USAGE["until"] == paused_job.usage["until"]


def test_manual_resume_works_with_automatic_resume_off(paused_job, queued_resume):
    options, callback, launches = queued_resume
    options["autoresume"] = False
    successor = studio.resume_job(paused_job.id)
    assert successor.id == paused_job.resumed_by == "new"
    assert len(launches) == 1 and launches[0]["resume"] == paused_job.session
    callback()  # The old timer must not launch a second successor after manual Resume.
    assert len(launches) == 1 and not paused_job.lines


def test_stop_cancels_already_started_resume_callback(monkeypatch, paused_job):
    callbacks = []
    class Timer:
        def __init__(self, delay, callback):
            callbacks.append(callback)
        def start(self):
            pass
    monkeypatch.setattr(studio.threading, "Timer", Timer)
    monkeypatch.setattr(studio, "agent_job", lambda *a, **k: pytest.fail("stopped job launched an agent"))
    studio.schedule_resume(paused_job, delay=1)
    assert len(callbacks) == 1
    entered, release = threading.Event(), threading.Event()
    def budget():
        entered.set()
        assert release.wait(5)
        return ""
    monkeypatch.setattr(studio, "budget_stop", budget)
    callback = threading.Thread(target=callbacks[0])
    callback.start()
    try:
        assert entered.wait(5)
        paused_job.stop()
    finally:
        release.set()
        callback.join(5)
    assert not callback.is_alive() and paused_job.state == "stopped"
    assert paused_job.resumed_by is None
    with pytest.raises(ValueError, match="nothing to resume"):
        studio.resume_job(paused_job.id)
    with pytest.raises(ValueError, match="nothing to take over"):
        studio.codex_takeover(paused_job)
    monkeypatch.setattr(studio.agent, "can_take_over", lambda: True)
    studio.schedule_resume(paused_job)
    assert len(callbacks) == 1


@pytest.mark.parametrize("handoff", ["resume", "codex"])
def test_delayed_stop_reaches_successor_registered_during_launch(monkeypatch, paused_job, handoff):
    entered, release, stopping = (threading.Event() for _ in range(3))
    errors = []
    class Successor:
        id, state = "new", "running"
        def stop(self):
            with studio.JOB_LOCK:
                self.state = "stopped"
    successor = Successor()
    def launch(*a, **k):
        entered.set()
        assert release.wait(5)
        with studio.JOB_LOCK:  # start_job already re-enters this lock while registering the process.
            studio.JOBS[successor.id] = successor
        return successor
    monkeypatch.setattr(studio, "agent_job", launch)
    def resume():
        try:
            studio.resume_job(paused_job.id) if handoff == "resume" else studio.codex_takeover(paused_job)
        except Exception as exc:
            errors.append(exc)
    def stop():
        stopping.set()
        paused_job.stop()
    resumer = threading.Thread(target=resume)
    stopper = threading.Thread(target=stop)
    resumer.start()
    try:
        assert entered.wait(5)
        stopper.start()
        assert stopping.wait(5)
    finally:
        release.set()
        resumer.join(5)
        if stopper.ident is not None:
            stopper.join(5)
    assert not resumer.is_alive() and not stopper.is_alive() and not errors
    assert paused_job.state == successor.state == "stopped"
    assert paused_job.resumed_by == successor.id
