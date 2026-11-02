"""Stop gate: the session may only end when the definition of done is met.

Done (batched testing, Spencer 2026-11-02) = working tree clean, every commit pushed, no claim held, the last
batched full test run (tools/batch_verify.py) not failed and none due, and every open PLAN item claimed by another
active session. Escape: .claude/state/BLOCKED (external blocker), reported, never silent. A runaway guard allows a stop after 60 consecutive blocks.
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
# Batched testing (Spencer, 2026-11-02): no full `kerf verify` per session. Each change runs the tests and checks it
# touches; the full suite runs in batches via tools/batch_verify.py (CLAUDE.md "Batched testing").
st = git("status", "--porcelain").stdout.strip()
if st:
    block("There are uncommitted changes. Run the tests/checks your change touches, then commit and push:\n" + st[:1500])
git("fetch", "-q")
ahead = git("rev-list", "--count", "@{u}..HEAD")
if ahead.returncode != 0:
    block("This branch has no upstream. Push it: git push -u origin HEAD")
if ahead.stdout.strip() not in ("", "0"):
    block(f"{ahead.stdout.strip()} commit(s) are not pushed. Run git pull --rebase, then git push.")
py = os.path.join(root, ".venv/bin/python")
py = py if os.path.exists(py) else sys.executable
def tool(*a):
    return subprocess.run([py, *a], cwd=root, capture_output=True, text=True)
mine = tool(os.path.join(root, "tools/claims.py"), "mine").stdout.strip()
if mine:
    block("You still hold a claim. Finish it (targeted tests pass, PLAN box checked, STATUS.md entry), then "
          "`tools/claims.py release` and push:\n" + mine[:800])
bs = tool(os.path.join(root, "tools/batch_verify.py"), "status").stdout
if "last batch: FAIL" in bs:
    block("The last batched test run FAILED. Fixing it comes before new work: fix each failure at its cause "
          "(never by loosening a check), push, then `tools/batch_verify.py run --force`:\n" + bs[:3000])
if "DUE:" in bs:
    block("A batched full test run is due. Run `.venv/bin/python tools/batch_verify.py run` (it skips itself if "
          "another session is already running it), fix anything it reports, then continue:\n" + bs[:1500])
blocked = os.path.exists(os.path.join(state, "BLOCKED"))
cover = tool(os.path.join(root, "tools/claims.py"), "others-cover")
if cover.returncode != 0 and not blocked:
    block("Open PLAN items are free. Take the next one: `.venv/bin/python tools/claims.py next`.")
if blocked:
    print(json.dumps({"systemMessage": "Stop allowed on a recorded external blocker: "
                                       + open(os.path.join(state, "BLOCKED")).read()[:800]}))
if os.path.exists(counter):
    os.remove(counter)
open(os.path.join(state, "DONE"), "w").write(time.strftime("%Y-%m-%d %H:%M:%S"))
sys.exit(0)
