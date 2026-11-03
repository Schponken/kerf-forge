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
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
REC = ROOT / "verify" / "BATCH.json"
LOCK = ROOT / "claims" / "batch-verify.json"
BATCH_ITEMS = 4          # PLAN check-offs since the last batch that make one due
MAX_AGE_H = 24           # or any feature commit older than this since the last batch
LOCK_STALE_MIN = 90
CHORE = re.compile(r"^(claim|claim heartbeat|release claims?|STATUS\b|batch verify|budget:|Merge )", re.I)


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)


def plan_done(text=None) -> int:
    text = text if text is not None else (ROOT / "PLAN.md").read_text(encoding="utf-8")
    return sum(l.strip().startswith("- [x]") for l in text.splitlines())


def load() -> dict:
    try:
        return json.loads(REC.read_text(encoding="utf-8"))
    except Exception:
        return {}


def feature_commits(since: str | None) -> list[tuple[str, int, str]]:
    """(hash, unix time, subject) of commits after `since` that are not claim/status chores, newest first."""
    rng = f"{since}..HEAD" if since and git("cat-file", "-e", since).returncode == 0 else "HEAD"
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
    sys.path.insert(0, str(ROOT / "tools"))
    import claims
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
    sys.path.insert(0, str(ROOT / "tools"))
    import claims
    return claims.session_id()


def push(msg: str, *paths) -> bool:
    for _ in range(4):
        git("add", *paths)
        if git("diff", "--cached", "--quiet").returncode != 0:
            git("-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com", "commit", "-q", "-m", msg)
        if git("push", "-q").returncode == 0:
            return True
        git("pull", "-q", "--rebase", "--autostash")
    return False


def others_working(sid: str | None = None) -> list[str]:
    """Sessions other than this one holding a fresh PLAN claim. Spencer, 2026-11-02: the full run waits until the
    other sessions are done, so it tests their finished work instead of being redone after it."""
    sys.path.insert(0, str(ROOT / "tools"))
    import claims
    sid = sid or claims.session_id()
    return sorted({c.get("session") for k, c in shared_claims().items()
                   if k not in (LOCK.stem, "budget") and c.get("session") != sid and claims.fresh(c)})


def hold_reason() -> str:
    """Why a due batch must not start now ('' = it may): the usage-budget switch, or other sessions still working."""
    sys.path.insert(0, str(ROOT / "tools"))
    import budget
    if why := budget.stopped():
        return f"budget stop ({why})"
    if who := others_working():
        return f"{len(who)} other session(s) still working ({', '.join(who)}); the last one to finish runs it"
    return ""


def cmd_status() -> int:
    rec = load()
    feats = feature_commits(rec.get("commit"))
    d, why = due(rec, feats, plan_done())
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


def cmd_run(force=False) -> int:
    git("pull", "-q", "--rebase", "--autostash")
    rec = load()
    feats = feature_commits(rec.get("commit"))
    d, why = due(rec, feats, plan_done())
    if not (d or force):
        print("not due: " + why)
        return 0
    if (held := hold_reason()) and (not force or held.startswith("budget stop")):
        print(f"due ({why}) but HELD: {held}")
        return 0
    sid = session_id()
    if lock_held_by_other(sid):
        print("another session is running the batch; skip")
        return 0
    LOCK.parent.mkdir(exist_ok=True)
    LOCK.write_text(json.dumps({"session": sid, "heartbeat": time.time(), "item": "batch verify"}), encoding="utf-8")
    if not push("batch verify: lock", str(LOCK.relative_to(ROOT))):
        print("could not push the batch lock; skip")
        return 1
    head = git("rev-parse", "--short", "HEAD").stdout.strip()
    kerf = ROOT / ".venv/bin/kerf"
    r = subprocess.run([str(kerf), "verify", "--all-failures"], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
    out = r.stdout + r.stderr
    fails = [l[5:] for l in out.splitlines() if l.startswith("FAIL ") and "PLAN.md has" not in l]
    if r.returncode not in (0, 1) and not fails:      # killed (e.g. out of memory): no verdict, don't record one
        LOCK.unlink(missing_ok=True)
        push("batch verify: unlock (run killed)", str(LOCK.relative_to(ROOT)))
        print(f"verify did not finish (exit {r.returncode}); nothing recorded. Tail:\n{out[-1500:]}")
        return 2
    new = {"commit": head, "time": time.strftime("%Y-%m-%d %H:%M"), "ok": not fails, "fails": fails[:60],
           "plan_done": plan_done(), "features": [f"{h} {s}" for h, _, s in feats][:80], "reason": why}
    REC.parent.mkdir(exist_ok=True)
    REC.write_text(json.dumps(new, indent=1), encoding="utf-8")
    LOCK.unlink(missing_ok=True)
    git("add", "-A", str(LOCK.relative_to(ROOT)))
    push(f"batch verify: {'PASS' if not fails else f'FAIL ({len(fails)})'} at {head}, {len(feats)} feature commits",
         str(REC.relative_to(ROOT)))
    print(("BATCH PASSED" if not fails else f"BATCH FAILED ({len(fails)})") + f" at {head}")
    for f in fails:
        print(f"  FAIL {f}")
    return 0 if not fails else 1


if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    sys.exit(cmd_status() if a[0] == "status" else cmd_run("--force" in a) if a[0] == "run" else 2)
