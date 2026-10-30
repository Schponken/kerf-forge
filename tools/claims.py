"""Work claims, so several Claude sessions can work on PLAN.md at the same time without doing the same item twice.

A claim is one small file, claims/<item-slug>.json, committed and pushed the moment it is made. One file per claim
means two sessions never edit the same file, so claims never cause merge conflicts. A claim is fresh while the
claiming session keeps pushing (its newest commit touching anything, or the claim's own `heartbeat`, is younger
than STALE_MIN); a stale claim may be taken over.

  .venv/bin/python tools/claims.py list            open PLAN items, who holds each, which are free
  .venv/bin/python tools/claims.py next            claim the first free open item (prints it), commit + push
  .venv/bin/python tools/claims.py take "<text>"   claim a specific open item (prefix of its text), commit + push
  .venv/bin/python tools/claims.py beat            refresh this session's claims (run before each push)
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
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
DIR = ROOT / "claims"
STALE_MIN = 90


def git(*a, check=False):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=check)


def session_id() -> str:
    p = ROOT / ".claude/state/session_id"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(os.environ.get("KERF_SESSION_ID") or uuid.uuid4().hex[:10])
    return p.read_text().strip()


def open_items() -> list[str]:
    """Unchecked PLAN.md items, in order. A parent item whose sub-items are listed counts through its sub-items."""
    lines = (ROOT / "PLAN.md").read_text().splitlines()
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


def load() -> dict[str, dict]:
    out = {}
    for f in sorted(DIR.glob("*.json")):
        try:
            out[f.stem] = json.loads(f.read_text())
        except Exception:  # noqa: BLE001 - a broken claim file is treated as no claim
            pass
    return out


def fresh(c: dict) -> bool:
    return time.time() - float(c.get("heartbeat", 0)) < STALE_MIN * 60


def sync():
    git("pull", "-q", "--rebase", "--autostash")


def push(msg: str) -> bool:
    for _ in range(4):
        git("add", "claims")
        if git("diff", "--cached", "--quiet", "--", "claims").returncode != 0:
            git("-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com", "commit", "-q", "-m", msg, "--", "claims")
        if git("push", "-q").returncode == 0:
            return True
        git("pull", "-q", "--rebase", "--autostash")
    return False


def _claim(item: str) -> bool:
    sync()
    s = slug(item)
    cur = load().get(s)
    if cur and fresh(cur) and cur.get("session") != session_id():
        return False
    DIR.mkdir(exist_ok=True)
    now = time.time()
    (DIR / f"{s}.json").write_text(json.dumps({"item": item, "session": session_id(), "since": now, "heartbeat": now,
                                                "since_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(now))}, indent=1) + "\n")
    if not push(f"claim: {item[:70]}"):
        return False
    # someone may have pushed the same claim first; the pushed tree is the truth
    sync()
    return load().get(s, {}).get("session") == session_id()


def cmd_list():
    sync()
    claims = load()
    for it in open_items():
        c = claims.get(slug(it))
        who = "FREE" if not c or not fresh(c) else ("MINE" if c["session"] == session_id() else f"taken by {c['session']} since {c.get('since_utc')}")
        print(f"[{who}] {it[:110]}")


def cmd_next():
    sync()
    claims = load()
    for it in open_items():
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


def mine() -> list[str]:
    return [k for k, c in load().items() if c.get("session") == session_id()]


def cmd_beat():
    now = time.time()
    for k in mine():
        p = DIR / f"{k}.json"
        c = json.loads(p.read_text()); c["heartbeat"] = now
        p.write_text(json.dumps(c, indent=1) + "\n")
    return 0


def cmd_release():
    sync()
    for k in mine():
        (DIR / f"{k}.json").unlink()
        git("rm", "-q", "--cached", "--ignore-unmatch", f"claims/{k}.json")
    return 0 if push("release claims") else 1


def others_cover() -> bool:
    items = open_items()
    claims = load()
    return bool(items) and all((c := claims.get(slug(it))) and fresh(c) and c.get("session") != session_id() for it in items)


def main(argv):
    if not argv or argv[0] == "list":
        return cmd_list() or 0
    cmd = argv[0]
    if cmd == "next":
        return cmd_next()
    if cmd == "take":
        return cmd_take(" ".join(argv[1:]))
    if cmd == "beat":
        return cmd_beat()
    if cmd == "release":
        return cmd_release()
    if cmd == "mine":
        print("\n".join(load()[k]["item"] for k in mine()))
        return 0
    if cmd == "others-cover":
        return 0 if others_cover() else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
