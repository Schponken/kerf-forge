"""SessionStart: make sure the environment exists, then show where the work stands."""
import json, os, subprocess, sys
root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
msgs = []
if not os.path.exists(os.path.join(root, ".venv/bin/kerf")):
    r = subprocess.run(["bash", "setup.sh"], cwd=root, capture_output=True, text=True)
    msgs.append("setup.sh: " + ("ok" if r.returncode == 0 else "FAILED\n" + (r.stdout + r.stderr)[-1500:]))
status = open(os.path.join(root, "STATUS.md")).read()[-3000:] if os.path.exists(os.path.join(root, "STATUS.md")) else ""
plan = open(os.path.join(root, "PLAN.md")).read()
todo = [l.strip() for l in plan.splitlines() if l.strip().startswith("- [ ]")]
msgs.append(f"PLAN.md: {len(todo)} unchecked items. Next: {todo[0] if todo else 'none'}")
msgs.append("STATUS.md (tail):\n" + status)
msgs.append("Read CLAUDE.md now. Work until `.venv/bin/kerf verify` passes and everything is pushed.")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n\n".join(msgs)}}))
