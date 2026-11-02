"""Real shared Git locks, with harmless children only: these tests never launch kerf verify."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from test_claims import repos, sh, shared, snapshot, push_claim, race_once, dirty_feature, run_tool


PASS = "print('VERIFY PASSED in 0.1 s')"
DRIVER = """import batch_verify as b, sys, signal
b.VERIFY_COMMAND = [sys.executable, '-c', sys.argv[1]]
b.HEARTBEAT_SECONDS = 1
# instrumentation
before = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
try:
    result = b.cmd_run(force=sys.argv[2] == 'force')
finally:
    assert all(signal.getsignal(sig) == handler for sig, handler in before.items())
sys.exit(result)
"""


def batch(repo, code=PASS, *, force=True, wait=True, instrument=""):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo), "KERF_SESSION_ID": repo.name,
           "PYTHONPATH": str(repo / "tools"), "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.Popen([sys.executable, "-c", DRIVER.replace("# instrumentation", instrument), code, "force" if force else "due"], cwd=repo,
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return finished(proc) if wait else proc


def finished(proc):
    stdout, stderr = proc.communicate(timeout=30)
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


def record(remote):
    r = sh(remote, "git", "show", "main:verify/BATCH.json")
    return json.loads(r.stdout) if r.returncode == 0 else None


def until(predicate):
    end = time.monotonic() + 15
    while time.monotonic() < end:
        if result := predicate():
            return result
        time.sleep(.03)
    raise AssertionError("condition did not become true")


def stopped(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


@pytest.mark.parametrize("code,expected,ok", [
    (PASS, 0, True),
    ("print('FAIL project servo: broken'); print('VERIFY FAILED (1) in 0.1 s'); exit(1)", 1, False),
    ("print('FAIL PLAN.md has 2 unchecked items, first: - [ ] todo'); print('VERIFY FAILED (1) in 0.1 s'); exit(1)", 0, True),
])
def test_result_and_unlock_are_atomic_and_bind_exact_tested_revision(repos, code, expected, ok):
    a, _, remote = repos
    before = snapshot(a)
    head = sh(a, "git", "rev-parse", "HEAD").stdout.strip()
    result = batch(a, code)
    assert result.returncode == expected, result.stdout + result.stderr
    saved = record(remote)
    assert saved["commit"] == head and saved["ok"] is ok and len(saved["commit"]) == 40
    assert shared(remote, "batch-verify") is None and snapshot(a) == before
    assert not (a / "verify/BATCH.json").exists()
    files = sh(remote, "git", "diff-tree", "--no-commit-id", "--name-only", "-r", "main").stdout.splitlines()
    assert set(files) == {"claims/batch-verify.json", "verify/BATCH.json"}
    assert bool(saved["excluded_plan_failures"]) == ("PLAN.md has" in code)
    if saved["excluded_plan_failures"]:
        assert "open PLAN items excluded" in result.stdout


@pytest.mark.parametrize("code", ["exit(1)", "print('VERIFY PASSED in 0.1 s'); exit(2)",
                                  "import os, signal; os.kill(os.getpid(), signal.SIGTERM)",
                                  "print('FAIL project: failed'); exit(1)"])
def test_incomplete_child_never_replaces_prior_record(repos, code):
    a, _, remote = repos
    old = {"commit": sh(a, "git", "rev-parse", "HEAD").stdout.strip(), "ok": False, "fails": ["earlier failure"]}
    (a / "verify").mkdir()
    (a / "verify/BATCH.json").write_text(json.dumps(old))
    sh(a, "git", "add", "verify/BATCH.json"); sh(a, "git", "commit", "-qm", "earlier batch result")
    assert sh(a, "git", "push", "-q").returncode == 0
    before = snapshot(a)
    result = batch(a, code)
    assert result.returncode == 2 and "nothing recorded" in result.stdout
    assert record(remote) == old and shared(remote, "batch-verify") is None and snapshot(a) == before


@pytest.mark.parametrize("context", ["dirty", "feature"])
def test_unsafe_runner_context_is_refused_without_any_publication(repos, context):
    a, _, remote = repos
    if context == "dirty":
        dirty_feature(a)
    else:
        sh(a, "git", "checkout", "-qb", "codex/feature")
        (a / "feature.py").write_text("unmerged work")
        sh(a, "git", "add", "feature.py"); sh(a, "git", "commit", "-qm", "feature")
    before = snapshot(a)
    remote_head = sh(remote, "git", "rev-parse", "main").stdout
    result = batch(a)
    assert result.returncode != 0 and "checkout" in result.stderr
    assert snapshot(a) == before and sh(remote, "git", "rev-parse", "main").stdout == remote_head


@pytest.mark.parametrize("owner", ["a", "other"])
def test_fresh_lock_blocks_even_the_same_session_and_force(repos, owner):
    a, b, remote = repos
    lock = {"session": owner, "run": "existing", "heartbeat": time.time()}
    push_claim(b, "batch-verify", lock)
    assert sh(a, "git", "pull", "-q", "--ff-only").returncode == 0
    result = batch(a)
    assert result.returncode == 0 and "already running" in result.stdout
    assert shared(remote, "batch-verify") == lock and record(remote) is None


def test_abandoned_lock_expires_and_detached_clean_main_can_run(repos):
    a, b, remote = repos
    push_claim(b, "batch-verify", {"session": "dead", "run": "old", "heartbeat": time.time() - 91 * 60})
    assert sh(a, "git", "pull", "-q", "--ff-only").returncode == 0
    assert sh(a, "git", "checkout", "--detach", "-q").returncode == 0
    result = batch(a)
    assert result.returncode == 0, result.stderr
    assert shared(remote, "batch-verify") is None and record(remote)["ok"]


@pytest.mark.parametrize("racer", ["budget", "lock", "unrelated"])
def test_push_race_rechecks_holds_and_never_launches_a_stale_snapshot(repos, racer):
    a, b, remote = repos
    if racer == "budget":
        key, value = "budget", {"reason": "weekly cap", "until": None}
    else:
        key = "batch-verify" if racer == "lock" else "sub-a"
        value = {"session": "b", "run": "winner", "heartbeat": time.time()}
    race_once(a, b, key, value)
    result = batch(a)
    assert "BATCH PASSED" not in result.stdout and record(remote) is None
    assert shared(remote, key) == value
    assert "budget stop" in result.stdout if racer == "budget" else "already running" in result.stdout if racer == "lock" else "main advanced" in result.stderr


def test_heartbeat_keeps_lock_fresh_and_later_main_code_stays_untested(repos, tmp_path):
    a, b, remote = repos
    ready = tmp_path / "ready"
    finish = tmp_path / "finish"
    code = f"""from pathlib import Path
import time
Path({str(ready)!r}).write_text('ready')
while not Path({str(finish)!r}).exists(): time.sleep(.03)
{PASS}
"""
    head = sh(a, "git", "rev-parse", "HEAD").stdout.strip()
    proc = batch(a, code, wait=False)
    try:
        until(ready.exists)
        first = shared(remote, "batch-verify")
        until(lambda: shared(remote, "batch-verify")["heartbeat"] > first["heartbeat"])
        sh(b, "git", "pull", "-q", "--ff-only")
        (b / "later.py").write_text("later main code\n")
        sh(b, "git", "add", "later.py"); sh(b, "git", "commit", "-qm", "later feature")
        assert sh(b, "git", "push", "-q").returncode == 0
        finish.write_text("done")
        result = finished(proc)
        assert result.returncode == 0, result.stdout + result.stderr
        assert record(remote)["commit"] == head and shared(remote, "batch-verify") is None
        assert sh(remote, "git", "show", "main:later.py").stdout == "later main code\n"
        assert "later feature" in sh(remote, "git", "log", "--format=%s", f"{head}..main").stdout
        status = run_tool(a, "batch_verify.py", "status")
        assert "last batch: PASS" in status.stdout and "1 feature commits" in status.stdout
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT); finished(proc)


def test_parent_sigterm_stops_child_group_before_releasing_lock(repos, tmp_path):
    a, _, remote = repos
    ready = tmp_path / "pids.json"
    descendant_ready = tmp_path / "descendant_ready"
    descendant = ("import signal, time; from pathlib import Path; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                  f"Path({str(descendant_ready)!r}).write_text('ready'); time.sleep(60)")
    code = f"""import os, sys, subprocess, json, time
from pathlib import Path
child = subprocess.Popen([sys.executable, '-c', {descendant!r}],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
while not Path({str(descendant_ready)!r}).exists(): time.sleep(.01)
Path({str(ready)!r}).write_text(json.dumps([os.getpid(), child.pid]))
time.sleep(60)
"""
    proc = batch(a, code, wait=False)
    try:
        pids = json.loads(until(lambda: ready.read_text() if ready.exists() else ""))
        assert shared(remote, "batch-verify") is not None
        proc.terminate()
        result = finished(proc)
        assert result.returncode == 128 + signal.SIGTERM, result.stdout + result.stderr
        for pid in pids:
            until(lambda: stopped(pid))
        assert shared(remote, "batch-verify") is None and record(remote) is None
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT); finished(proc)


def test_clean_run_does_not_refresh_caller_index_metadata(repos):
    a, _, _ = repos
    index = a / ".git/index"
    before = index.read_bytes()
    os.utime(a / "PLAN.md", (time.time() + 60, time.time() + 60))
    result = batch(a)
    assert result.returncode == 0, result.stderr
    assert index.read_bytes() == before


@pytest.mark.parametrize("boundary", ["published_lock", "spawned_child"])
@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT])
def test_cancellation_waits_until_acquisition_or_spawn_is_tracked(repos, tmp_path, boundary, signum):
    a, _, remote = repos
    child_pid = tmp_path / "spawned_pid"
    if boundary == "published_lock":
        instrument = f"""import os
publish = b.claims.publish
def interrupt_publish(msg, change, **kw):
    result = publish(msg, change, **kw)
    if msg == 'batch verify: lock': os.kill(os.getpid(), {int(signum)})
    return result
b.claims.publish = interrupt_publish
"""
    else:
        instrument = f"""import os
from pathlib import Path
popen = b.subprocess.Popen
def interrupt_popen(command, **kw):
    proc = popen(command, **kw)
    if command == b.VERIFY_COMMAND:
        Path({str(child_pid)!r}).write_text(str(proc.pid))
        os.kill(os.getpid(), {int(signum)})
    return proc
b.subprocess.Popen = interrupt_popen
"""
    result = batch(a, "import time; time.sleep(60)", instrument=instrument)
    assert result.returncode == 128 + signum, result.stdout + result.stderr
    assert record(remote) is None and shared(remote, "batch-verify") is None
    if boundary == "spawned_child":
        until(lambda: stopped(int(child_pid.read_text())))


def test_lost_push_acknowledgement_recognizes_own_token(repos):
    a, _, remote = repos
    instrument = """import subprocess
git = b.claims.git
lost = False
def lose_ack(*args, **kw):
    global lost
    result = git(*args, **kw)
    if args[0] == 'push' and not lost and result.returncode == 0:
        lost = True
        return subprocess.CompletedProcess(result.args, 1, result.stdout, 'lost acknowledgement')
    return result
b.claims.git = lose_ack
"""
    result = batch(a, instrument=instrument)
    assert result.returncode == 0, result.stdout + result.stderr
    assert record(remote)["ok"] and shared(remote, "batch-verify") is None


@pytest.mark.parametrize("event", ["lost_lock", "interrupt", "edited_checkout"])
def test_live_child_is_stopped_before_unlock_and_unsafe_result_is_not_published(repos, tmp_path, event):
    a, b, remote = repos
    ready = tmp_path / "child_pid"
    finish = tmp_path / "finish"
    code = f"""import os, time
from pathlib import Path
Path({str(ready)!r}).write_text(str(os.getpid()))
while not Path({str(finish)!r}).exists(): time.sleep(.03)
{PASS}
"""
    proc = batch(a, code, wait=False)
    try:
        pid = int(until(lambda: ready.read_text() if ready.exists() else ""))
        other = {"session": "b", "run": "replacement", "heartbeat": time.time()}
        if event == "lost_lock":
            push_claim(b, "batch-verify", other)
        elif event == "interrupt":
            proc.send_signal(signal.SIGINT)
        else:
            (a / "PLAN.md").write_text("user edits during verification\n")
            finish.write_text("done")
        result = finished(proc)
        assert result.returncode != 0 and record(remote) is None
        until(lambda: stopped(pid))
        assert shared(remote, "batch-verify") == (other if event == "lost_lock" else None)
        if event == "edited_checkout":
            assert (a / "PLAN.md").read_text() == "user edits during verification\n"
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT); finished(proc)
