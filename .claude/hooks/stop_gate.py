"""Stop gate: the session may only end when the definition of done is met.

Done = `kerf verify` passes (tests, every project, every review current, every eval, PLAN.md fully checked)
       AND the working tree is clean AND every commit is pushed.
Escape: .claude/state/BLOCKED (external blocker) is honoured only when verify's sole failures are PLAN items
that depend on the blocker; it is reported, never silent. A runaway guard allows a stop after 60 consecutive blocks.
"""
import json, os, subprocess, sys, time
root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
state = os.path.join(root, ".claude/state"); os.makedirs(state, exist_ok=True)
counter = os.path.join(state, "stop_blocks")
try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

def block(reason):
    n = int(open(counter).read()) + 1 if os.path.exists(counter) else 1
    open(counter, "w").write(str(n))
    if n > 60:
        print(json.dumps({"systemMessage": f"Stop gate: allowing stop after {n} blocks (runaway guard). Work is NOT done: {reason[:500]}"}))
        os.remove(counter); sys.exit(0)
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)

def git(*a):
    return subprocess.run(["git", *a], cwd=root, capture_output=True, text=True)

# A scheduled run that found another session actively working yields without touching anything.
yield_f = os.path.join(state, "YIELD")
if os.path.exists(yield_f) and not git("status", "--porcelain").stdout.strip():
    os.remove(yield_f)
    print(json.dumps({"systemMessage": "Stop allowed: yielded to another active session (no local changes)."}))
    sys.exit(0)

kerf = os.path.join(root, ".venv/bin/kerf")
if not os.path.exists(kerf):
    block("The environment is not set up (.venv/bin/kerf missing). Run ./setup.sh and continue the work in PLAN.md.")
r = subprocess.run([kerf, "verify"], cwd=root, capture_output=True, text=True, timeout=3500)
out = (r.stdout + r.stderr)[-6000:]
blocked = os.path.exists(os.path.join(state, "BLOCKED"))
if r.returncode != 0:
    if blocked:
        note = open(os.path.join(state, "BLOCKED")).read()[:800]
        fails = [l for l in out.splitlines() if l.startswith("FAIL ")]
        if fails and all("PLAN.md" in l for l in fails):
            print(json.dumps({"systemMessage": f"Stop allowed on a recorded external blocker: {note}"}))
            sys.exit(0)
    block("kerf verify is not passing, so the work is not finished. Fix these and keep going "
          "(update STATUS.md, commit and push as you go):\n" + out)
st = git("status", "--porcelain").stdout.strip()
if st:
    block("verify passes, but there are uncommitted changes. Commit them with a clear message and push:\n" + st[:1500])
git("fetch", "-q")
ahead = git("rev-list", "--count", "@{u}..HEAD")
if ahead.returncode != 0:
    block("verify passes, but this branch has no upstream. Push it: git push -u origin HEAD")
if ahead.stdout.strip() not in ("", "0"):
    block(f"verify passes, but {ahead.stdout.strip()} commit(s) are not pushed. Run git push.")
if os.path.exists(counter):
    os.remove(counter)
open(os.path.join(state, "DONE"), "w").write(time.strftime("%Y-%m-%d %H:%M:%S"))
sys.exit(0)
