"""A stop request must not unlock a project before its process exits."""
import sys
import threading

import pytest

from kerf import studio


@pytest.mark.parametrize("outcome", ["stopped", "failed"])
def test_stopping_job_holds_project_until_process_exits(tmp_path, monkeypatch, outcome):
    release = tmp_path / "release"
    script = tmp_path / "child.py"
    script.write_text("""import signal, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, lambda *_: print('terminating', flush=True))
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
    monkeypatch.setattr(studio, "on_finished", lambda job: finished.set())
    job = studio.start_job("design", "demo", [sys.executable, str(script), str(release), outcome],
                           "Design demo", parse=parse)
    try:
        assert ready.wait(5), "child did not start"
        if outcome == "stopped":
            job.stop()
        assert terminating.wait(5), "child did not receive the stop signal"
        assert job.proc.poll() is None
        assert job.state == "running" and job.ended is None
        assert studio.busy()
        for project in ("demo", "*"):
            with pytest.raises(ValueError, match="Activity"):
                studio.start_job("trial", project, [], "Try again",
                                 prepare=lambda: pytest.fail("active trial overwritten"))
        studio.require_idle("another_project")
        job.stop()  # Repeated stops must not replace an authentication failure with "stopped".
        release.touch()
        assert finished.wait(5), "child did not finish"
        assert job.state == outcome and job.ended is not None
        assert job.proc.returncode == 0  # Even a graceful exit must retain the requested outcome.
        assert "cleanup complete" in job.lines
        assert not studio.busy()
        studio.require_idle("demo")
        studio.require_idle("*")
    finally:
        release.touch()
        if not finished.wait(5):
            job.proc.kill()
            job.proc.wait(timeout=5)
