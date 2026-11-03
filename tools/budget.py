"""Usage-budget switch shared by every session (Spencer, 2026-11-02: "make sure everything runs aware of usage limits
and will pause before starting something that will be cut off by a limit").

No session can read the usage meter, so the switch is set by a person (or a session Spencer tells) and is shared
through git: claims/budget.json, pushed like a claim. A local .claude/state/BUDGET_STOP works too (this machine only).
While it is on: finish and push the item in hand, start nothing new (no `claims.py next/take`, no full batch run),
then stop; the Stop hook lets a session stop once its work is pushed and its claim released. With --until it switches
itself off at that time (e.g. the weekly reset).

  .venv/bin/python tools/budget.py status                        prints OK or STOPPED (exit 0 / 1)
  .venv/bin/python tools/budget.py stop "<reason>" [--until "YYYY-MM-DD HH:MM"]   (UTC) set it for everyone, push
  .venv/bin/python tools/budget.py resume                        clear it, push
"""
import calendar
import os
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parent.parent))
LOCAL = ROOT / ".claude" / "state" / "BUDGET_STOP"


def stopped(now: float | None = None, *, shared: dict | None = None) -> str:
    """The reason new work must not start, or '' when it may."""
    now = time.time() if now is None else now
    if LOCAL.exists():
        return "local BUDGET_STOP: " + (LOCAL.read_text(encoding="utf-8").strip() or "set on this machine")
    if shared is None:
        sys.path.insert(0, str(ROOT / "tools"))
        import claims
        shared = claims.load().get("budget", {})
    if not shared:
        return ""
    until = shared.get("until")
    if until and now >= float(until):
        return ""
    end = f" (until {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(float(until)))})" if until else ""
    return (shared.get("reason") or "usage budget near the cap") + end


def _push(msg: str, value: dict | None) -> bool:
    sys.path.insert(0, str(ROOT / "tools"))
    import claims
    return claims.publish(msg, lambda current: {"budget": value})


def main(argv) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        why = stopped()
        print(f"STOPPED: {why}. Finish and push the item in hand; start nothing new." if why else "OK: budget switch off")
        return 1 if why else 0
    if cmd == "stop":
        rest = argv[1:]
        until = None
        if "--until" in rest:
            i = rest.index("--until")
            until = calendar.timegm(time.strptime(rest[i + 1], "%Y-%m-%d %H:%M"))
            rest = rest[:i] + rest[i + 2:]
        value = {"reason": " ".join(rest) or "usage budget near the cap", "until": until,
                 "set": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
        return 0 if _push("budget: stop new work", value) else 1
    if cmd == "resume":
        return 0 if _push("budget: resume", None) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
