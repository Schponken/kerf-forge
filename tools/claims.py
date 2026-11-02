"""Work claims, so several sessions can work on PLAN.md without doing the same item twice.

A claim is one small file, claims/<item-slug>.json, committed and pushed the moment it is made. One file per claim
means unrelated claims survive concurrent pushes. Claims live on origin/main, independent of the caller's
branch, index and working files. A claim is fresh while its heartbeat is younger than STALE_MIN; a stale claim
may be taken over. Reads require a reachable origin/main; unavailable shared state never means "free".

  .venv/bin/python tools/claims.py list            open PLAN items, who holds each, which are free
  .venv/bin/python tools/claims.py next            claim the first free open item (prints it), commit + push
  .venv/bin/python tools/claims.py take "<text>"   claim a specific open item (prefix of its text), commit + push
  .venv/bin/python tools/claims.py beat [activity] refresh + push claims, optionally say what is happening now
  .venv/bin/python tools/claims.py release         drop this session's claims (when the item is checked off), commit + push
  .venv/bin/python tools/claims.py mine            this session's claims
  .venv/bin/python tools/claims.py others-cover    exit 0 when every open item is freshly claimed by OTHER sessions

The session id lives in .claude/state/session_id (not committed), created on first use.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
STALE_MIN = 90


def git(*a, check=False, **kwargs):
    env = {**kwargs.pop("env", os.environ), "GIT_OPTIONAL_LOCKS": "0"}
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=check, env=env, **kwargs)


def session_id() -> str:
    if explicit := os.environ.get("KERF_SESSION_ID"):
        return explicit
    p = ROOT / ".claude/state/session_id"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(uuid.uuid4().hex[:10], encoding="utf-8")
    return p.read_text(encoding="utf-8").strip()


def session_source() -> dict:
    """Only explicit runtime identity labels a claim; old/unknown sessions stay unlabelled."""
    if os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDECODE") == "1":
        return {"provider": "Claude Code"}
    if thread := os.environ.get("CODEX_THREAD_ID"):
        return {"provider": "Codex", "thread_id": thread}
    return {}


def open_items() -> list[str]:
    """Unchecked PLAN.md items, in order. A parent item whose sub-items are listed counts through its sub-items."""
    lines = (ROOT / "PLAN.md").read_text(encoding="utf-8").splitlines()
    items = []
    for i, l in enumerate(lines):
        m = re.match(r"^(\s*)- \[ \] (.+)$", l)
        if not m:
            continue
        indent = len(m.group(1))
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        has_children = re.match(r"^(\s*)- \[", nxt) and len(re.match(r"^(\s*)", nxt).group(1)) > indent
        if not has_children:
            items.append(m.group(2).strip())
    return items


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def load(ref: str | None = None) -> dict[str, dict]:
    """Read an immutable shared snapshot, never the caller's stale or edited claim files."""
    ref = ref or sync()
    out = {}
    for name in git("ls-tree", "-r", "--name-only", ref, "--", "claims/", check=True).stdout.splitlines():
        f = Path(name)
        if f.parent != Path("claims") or f.suffix != ".json":
            continue
        try:
            c = json.loads(git("show", f"{ref}:{name}", check=True).stdout)
            if not isinstance(c, dict):
                raise ValueError("expected an object")
            out[f.stem] = c
        except (ValueError, subprocess.CalledProcessError) as e:
            raise GitBusy(f"claims: cannot read shared {name}; nothing published") from e
    return out


def fresh(c: dict) -> bool:
    return time.time() - float(c.get("heartbeat", 0)) < STALE_MIN * 60


class GitBusy(SystemExit):
    pass


class BudgetStop(Exception):
    pass


def ensure_clean_git():
    """Keep the existing refusal during an unfinished Git operation; normal dirty work is safe."""
    gd = Path(git("rev-parse", "--git-dir").stdout.strip() or ".git")
    gd = gd if gd.is_absolute() else ROOT / gd
    busy = [n for n in ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD") if (gd / n).exists()]
    if busy or git("ls-files", "--unmerged").stdout.strip():
        raise GitBusy(f"claims: git is mid-{busy[0] if busy else 'conflict'}; finish or abort it first (nothing claimed)")


def sync():
    ensure_clean_git()
    # A private ref avoids FETCH_HEAD/origin-main races between worktrees sharing the same Git directory.
    ref = f"refs/kerf/claims/{uuid.uuid4().hex}"
    try:
        r = git("fetch", "-q", "--no-tags", "--no-write-fetch-head", "origin", f"refs/heads/main:{ref}")
        if r.returncode:
            raise GitBusy("claims: cannot fetch origin/main; nothing published\n" + r.stderr.strip())
        return git("rev-parse", "--verify", ref, check=True).stdout.strip()
    finally:
        git("update-ref", "-d", ref)


def publish(msg: str, change) -> bool:
    """Apply only explicit claim changes to current main, retrying ownership/budget decisions after races."""
    for _ in range(4):
        base = sync()
        changes = change(load(base))
        if changes is None:
            return False
        if not changes:
            return True
        with tempfile.TemporaryDirectory(prefix="kerf-claims-") as td:
            env = {**os.environ, "GIT_INDEX_FILE": str(Path(td) / "index")}
            git("read-tree", base, env=env, check=True)
            for key, value in changes.items():
                if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", key):
                    raise GitBusy(f"claims: invalid claim name {key!r}; nothing published")
                if value is None:
                    entry = f"0 {'0' * 40}\tclaims/{key}.json\n"
                else:
                    blob = git("hash-object", "-w", "--stdin", input=json.dumps(value, indent=1) + "\n", check=True).stdout.strip()
                    entry = f"100644 {blob}\tclaims/{key}.json\n"
                git("update-index", "--index-info", input=entry, env=env, check=True)
            tree = git("write-tree", env=env, check=True).stdout.strip()
        if tree == git("rev-parse", f"{base}^{{tree}}", check=True).stdout.strip():
            return True
        commit = git("-c", "user.name=Kerf claims", "-c", "user.email=noreply@kerf.local", "commit-tree", tree,
                     "-p", base, "-m", msg, check=True).stdout.strip()
        r = git("push", "-q", "origin", f"{commit}:refs/heads/main")
        if r.returncode == 0:
            return True
    raise GitBusy(f"claims: could not publish '{msg}' after 4 tries; caller work is unchanged\n" + r.stderr.strip())


def check_budget(current=None):
    import budget
    why = budget.stopped() if current is None else budget.stopped(shared=current.get("budget", {}))
    if why:
        raise BudgetStop(why)


def _claim(item: str) -> bool:
    s = slug(item)
    if s in ("budget", "batch-verify"):
        raise GitBusy(f"claims: {s!r} is reserved for shared controls; nothing claimed")
    sid = session_id()
    def change(current):
        check_budget(current)
        cur = current.get(s)
        if cur and fresh(cur) and cur.get("session") != sid:
            return None
        now = time.time()
        return {s: {"item": item, "session": sid, "since": now, "heartbeat": now, **session_source(),
                    "since_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(now))}}
    return publish(f"claim: {item[:70]}", change)


def cmd_list():
    claims = load()
    for it in open_items():
        c = claims.get(slug(it))
        who = "FREE" if not c or not fresh(c) else ("MINE" if c["session"] == session_id() else f"taken by {c['session']} since {c.get('since_utc')}")
        print(f"[{who}] {it[:110]}")


def workable_items() -> list[str]:
    """Open items a session may start: items Spencer paused (text contains "PAUSED:") wait until the marker is
    removed. `take` can still claim one explicitly."""
    return [it for it in open_items() if "PAUSED:" not in it]


def cmd_next():
    claims = load()
    for it in workable_items():
        c = claims.get(slug(it))
        if c and fresh(c):
            continue
        if _claim(it):
            print(it)
            return 0
    print("NO FREE ITEM: every open PLAN item is claimed by an active session", file=sys.stderr)
    return 1


def cmd_take(prefix: str):
    for it in open_items():
        if it.lower().startswith(prefix.lower()):
            ok = _claim(it)
            print(("claimed: " if ok else "already claimed by another session: ") + it)
            return 0 if ok else 1
    print(f"no open PLAN item starts with: {prefix}", file=sys.stderr)
    return 1


def mine(current=None) -> list[str]:
    return [k for k, c in (load() if current is None else current).items()
            if k not in ("budget", "batch-verify") and c.get("session") == session_id()]


def cmd_beat(activity: str = ""):
    def change(current):
        changes = {}
        for k in mine(current):
            c = dict(current[k], heartbeat=time.time())
            source = session_source()
            if source.get("provider") == "Claude Code":
                c.pop("thread_id", None)
            c.update(source)
            if activity.strip():
                c["activity"] = " ".join(activity.split())[:500]
            changes[k] = c
        return changes
    return 0 if publish("claim heartbeat", change) else 1


def cmd_release():
    return 0 if publish("release claims", lambda current: dict.fromkeys(mine(current))) else 1


def others_cover() -> bool:
    items = workable_items()
    claims = load()
    return bool(items) and all((c := claims.get(slug(it))) and fresh(c) and c.get("session") != session_id() for it in items)


def dispatch(argv):
    if not argv or argv[0] == "list":
        return cmd_list() or 0
    cmd = argv[0]
    if cmd in ("next", "take"):
        check_budget()
    if cmd == "next":
        return cmd_next()
    if cmd == "take":
        return cmd_take(" ".join(argv[1:]))
    if cmd == "beat":
        return cmd_beat(" ".join(argv[1:]))
    if cmd == "release":
        return cmd_release()
    if cmd == "mine":
        current = load()
        print("\n".join(current[k]["item"] for k in mine(current)))
        return 0
    if cmd == "others-cover":
        return 0 if others_cover() else 1
    print(__doc__)
    return 2


def main(argv):
    try:
        return dispatch(argv)
    except BudgetStop as e:
        print(f"budget stop: {e}. Not claiming anything; push your work and stop.")
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
