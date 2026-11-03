"""PostToolUse (Studio jobs only): hand steering from Studio's "How Kerf decided" to the running job as extra context.
Costs nothing when there is no steering: settings.json only starts this when KERF_STUDIO_JOB is set and the steering
file exists, and it prints nothing unless there is something new (kerf/steer.py)."""
import json, os, sys
root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
project = os.environ.get("KERF_STUDIO_JOB", "")
if not project:
    sys.exit(0)
sys.path.insert(0, root)
try:
    from kerf import steer
    msg = steer.deliver(project)
except Exception:
    sys.exit(0)
if msg:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
sys.exit(0)
