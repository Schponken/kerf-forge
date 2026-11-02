"""Batched full verification: one `kerf verify` covers many sessions' features instead of one run per change.

Spencer, 2026-11-02: "ship multiple sessions' features and then test them all at once", "pack as many testable
features into each suite run as you can verifiably test". Per change, a session runs only the tests and checks its
change touches (CLAUDE.md). The full suite runs here, once a batch is big enough or old enough, with pytest NOT
stopping at the first failure so one run reports every break in the batch.

  .venv/bin/python tools/batch_verify.py status   last batch result, features waiting, whether a batch is due
  .venv/bin/python tools/batch_verify.py run      if due (or --force) and nobody else is running one: lock, run the
                                                  full suite, record verify/BATCH.json with suspect commits, push
Record: verify/BATCH.json {commit, time, ok, fails, plan_done, features: [commit subjects in the batch]}.
A failed batch blocks new work until fixed: CLAUDE.md "Batched testing".
The runner requires a clean checkout exactly at shared main; it never updates/stashes caller files. Locks and
results publish independently of that checkout. SIGINT/SIGTERM stop the child group before unlocking; SIGKILL
or machine loss cannot guarantee cleanup and leave the lease to expire after 90 minutes.
"""
import json, os, re, signal, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(ROOT / "tools"))
import claims
LOCK = ROOT / "claims" / "batch-verify.json"
BATCH_ITEMS = 4          # PLAN check-offs since the last batch that make one due
MAX_AGE_H = 24           # or any feature commit older than this since the last batch
LOCK_STALE_MIN = 90
HEARTBEAT_SECONDS = 60
VERIFY_COMMAND = [str(ROOT / ".venv/bin/python"), "-m", "kerf.cli", "verify", "--all-failures"]
CHORE = re.compile(r"^(claim|claim heartbeat|release claims?|STATUS\b|batch verify|budget:|Merge )", re.I)


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})


def plan_done(text=None) -> int:
    text = text if text is not None else (ROOT / "PLAN.md").read_text(encoding="utf-8")
    return sum(l.strip().startswith("- [x]") for l in text.splitlines())


def load(ref=None) -> dict:
    ref = ref or claims.sync()
    path = "verify/BATCH.json"
    if not git("ls-tree", "--name-only", ref, "--", path).stdout.strip():
        return {}
    try:
        record = json.loads(git("show", f"{ref}:{path}").stdout)
        if not isinstance(record, dict):
            raise ValueError("expected an object")
        return record
    except ValueError as e:
        raise claims.GitBusy("batch: unreadable shared result; nothing started") from e


def feature_commits(since: str | None, ref="HEAD") -> list[tuple[str, int, str]]:
    """(hash, unix time, subject) of commits after `since` that are not claim/status chores, newest first."""
    rng = f"{since}..{ref}" if since and git("cat-file", "-e", since).returncode == 0 else ref
    lim = [] if since else ["-50"]
    out = git("log", *lim, "--format=%h\t%ct\t%s", rng).stdout.splitlines()
    rows = []
    for l in out:
        h, t, s = l.split("\t", 2)
        if not CHORE.match(s):
            rows.append((h, int(t), s))
    return rows


def due(rec: dict, feats: list, done_now: int, now: float | None = None) -> tuple[bool, str]:
    now = now or time.time()
    if not feats:
        return False, "no feature commits since the last batch"
    new_items = done_now - int(rec.get("plan_done", 0)) if rec else done_now
    if not rec:
        return True, "no batch recorded yet"
    if new_items >= BATCH_ITEMS:
        return True, f"{new_items} PLAN items checked off since the last batch"
    oldest = min(t for _, t, _ in feats)
    if (now - oldest) / 3600 >= MAX_AGE_H:
        return True, f"oldest untested feature commit is over {MAX_AGE_H} h old"
    return False, f"{len(feats)} feature commits / {new_items} items waiting (batch at {BATCH_ITEMS} items or {MAX_AGE_H} h)"


def shared_claims() -> dict:
    return claims.load()


def running_now() -> str | None:
    """'session S, started/heartbeat N min ago' while a fresh lock says a full run is going (any machine), else None."""
    c = shared_claims().get(LOCK.stem)
    if not c:
        return None
    age = (time.time() - float(c.get("heartbeat", 0))) / 60
    return f"session {c.get('session')}, last heartbeat {age:.0f} min ago" if age < LOCK_STALE_MIN else None


def lock_held_by_other(sid: str) -> bool:
    c = shared_claims().get(LOCK.stem)
    if not c:
        return False
    return c.get("session") != sid and time.time() - float(c.get("heartbeat", 0)) < LOCK_STALE_MIN * 60


def session_id() -> str:
    return claims.session_id()


def others_working(sid: str | None = None, current=None) -> list[str]:
    """Sessions other than this one holding a fresh PLAN claim. Spencer, 2026-11-02: the full run waits until the
    other sessions are done, so it tests their finished work instead of being redone after it."""
    sid = sid or claims.session_id()
    return sorted({c.get("session") for k, c in (shared_claims() if current is None else current).items()
                   if k not in (LOCK.stem, "budget") and c.get("session") != sid and claims.fresh(c)})


def hold_reason(current=None) -> str:
    """Why a due batch must not start now ('' = it may): the usage-budget switch, or other sessions still working."""
    import budget
    why = budget.stopped() if current is None else budget.stopped(shared=current.get("budget", {}))
    if why:
        return f"budget stop ({why})"
    who = others_working() if current is None else others_working(current=current)
    if who:
        return f"{len(who)} other session(s) still working ({', '.join(who)}); the last one to finish runs it"
    return ""


def cmd_status() -> int:
    ref = claims.sync()
    rec = load(ref)
    feats = feature_commits(rec.get("commit"), ref)
    done = plan_done(git("show", f"{ref}:PLAN.md").stdout)
    d, why = due(rec, feats, done)
    if rec:
        print(f"last batch: {'PASS' if rec.get('ok') else 'FAIL'} at {rec.get('commit')} ({rec.get('time')}), "
              f"{len(rec.get('features', []))} features")
        for f in rec.get("fails", [])[:10]:
            print(f"  FAIL {f}")
    else:
        print("last batch: none recorded")
    run = running_now()
    if run:      # Spencer, 2026-11-02: check for a running full suite before starting one
        print(f"RUNNING NOW: a full batch is in progress ({run}); do not start another, wait for its result")
    else:
        held = hold_reason() if d else ""
        print(f"HELD (due: {why}): {held}" if held else ("DUE: " if d else "not due: ") + why)
    return 0


def runner_ready(head):
    claims.ensure_clean_git()
    if git("rev-parse", "HEAD").stdout.strip() != head or git("status", "--porcelain").stdout.strip():
        raise claims.GitBusy("batch: use a clean checkout at the tested main revision; caller files were left untouched")


def owned(current, token):
    lock = current.get(LOCK.stem, {})
    return lock.get("session") == session_id() and lock.get("run") == token


def renew(token):
    def change(current):
        if not owned(current, token):
            return None
        return {LOCK.stem: dict(current[LOCK.stem], heartbeat=time.time())}
    return claims.publish("batch verify: heartbeat", change)


def release(token, record=None):
    return claims.publish("batch verify: result" if record is not None else "batch verify: unlock",
                          lambda current: {LOCK.stem: None} if owned(current, token) else None, record=record)


def stop_child(proc):
    """A child and its test workers must be gone before another session may acquire the lock."""
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # A descendant may have closed its pipes while staying alive after the direct child exited.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.communicate()


def verdict(code, output):
    """Only a completed verify summary is a verdict; the existing PLAN-only exclusion stays explicit."""
    raw = [line[5:] for line in output.splitlines() if line.startswith("FAIL ")]
    summary = re.search(r"^VERIFY (PASSED|FAILED \((\d+)\)) in [\d.]+ s$", output, re.M)
    complete = summary and ((code == 0 and summary[1] == "PASSED" and not raw)
                            or (code == 1 and summary[2] and int(summary[2]) == len(raw) and raw))
    if not complete:
        return None
    return ([line for line in raw if not line.startswith("PLAN.md has ")],
            [line for line in raw if line.startswith("PLAN.md has ")])


def cmd_run(force=False) -> int:
    head = git("rev-parse", "HEAD").stdout.strip()
    runner_ready(head)
    ref = claims.sync()
    if ref != head:
        raise claims.GitBusy("batch: checkout must match origin/main; update it explicitly and retry (nothing started)")
    rec = load(ref)
    feats = feature_commits(rec.get("commit"), ref)
    done = plan_done()
    d, why = due(rec, feats, done)
    if not (d or force):
        print("not due: " + why)
        return 0
    sid = session_id()
    token = uuid.uuid4().hex
    def acquire(current):
        runner_ready(head)
        if (held := hold_reason(current)) and (not force or held.startswith("budget stop")):
            print(f"due ({why}) but HELD: {held}")
            return None
        lock = current.get(LOCK.stem)
        if owned(current, token):
            return {}  # A push acknowledgement may be lost after the remote acquired our unique token.
        if lock and time.time() - float(lock.get("heartbeat", 0)) < LOCK_STALE_MIN * 60:
            print(f"batch already running for {lock.get('session')}; skip")
            return None
        return {LOCK.stem: {"session": sid, "run": token, "heartbeat": time.time(),
                            "item": "batch verify", "commit": head}}
    proc = None
    locked = False
    critical = True
    cancellation = None
    def terminate(signum, frame):
        nonlocal cancellation
        cancellation = signum
        if not critical:
            raise SystemExit(128 + signum)
    def cancelled():
        if cancellation is not None:
            raise SystemExit(128 + cancellation)
    previous = {sig: signal.signal(sig, terminate) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        locked = True  # Cleanup checks the token even if publication succeeds before its acknowledgement arrives.
        acquired = claims.publish("batch verify: lock", acquire, expected_head=head)
        critical = False
        cancelled()
        if not acquired:
            return 0
        runner_ready(head)
        if not renew(token):
            raise claims.GitBusy("batch: lost lock before starting; nothing run")
        critical = True
        proc = subprocess.Popen(VERIFY_COMMAND, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"}, start_new_session=True)
        critical = False
        cancelled()
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=HEARTBEAT_SECONDS)
                break
            except subprocess.TimeoutExpired:
                if not renew(token):
                    raise claims.GitBusy("batch: lost shared lock; stopping child, no result published")
        out = stdout + stderr
        result = verdict(proc.returncode, out)
        if result is None:
            print(f"verify did not finish (exit {proc.returncode}); nothing recorded. Tail:\n{out[-1500:]}")
            return 2
        stop_child(proc)
        proc = None
        runner_ready(head)
        fails, excluded = result
        record = {"commit": head, "time": time.strftime("%Y-%m-%d %H:%M"), "ok": not fails, "fails": fails[:60],
                  "plan_done": done, "features": [f"{h} {s}" for h, _, s in feats][:80], "reason": why,
                  "excluded_plan_failures": excluded}
        if not release(token, record):
            raise claims.GitBusy("batch: lost shared lock; no result published")
        locked = False
        print(("BATCH PASSED" if not fails else f"BATCH FAILED ({len(fails)})") + f" at {head}"
              + (" (open PLAN items excluded)" if excluded else ""))
        for f in fails:
            print(f"  FAIL {f}")
        return 0 if not fails else 1
    finally:
        critical = True
        try:
            stop_child(proc)
            if locked:
                release(token)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            cancelled()


if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    sys.exit(cmd_status() if a[0] == "status" else cmd_run("--force" in a) if a[0] == "run" else 2)
