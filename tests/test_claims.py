"""Two simulated sessions share a remote: claims never overlap, refusals are honoured, release frees items."""
import os
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "claims.py"
PLAN = "# P\n- [x] done\n- [ ] Item one\n- [ ] Parent\n  - [ ] Sub A\n  - [ ] Sub B\n"


def sh(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


def run_tool(cwd, tool, *a, env=None):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(cwd), "KERF_SESSION_ID": cwd.name,
           "PYTHONDONTWRITEBYTECODE": "1", **(env or {})}
    return subprocess.run([sys.executable, str(cwd / "tools" / tool), *a], cwd=cwd, capture_output=True,
                          text=True, env=env)


def claims(cwd, *a, **kw):
    return run_tool(cwd, "claims.py", *a, **kw)


@pytest.fixture
def repos(tmp_path):
    sh(tmp_path, "git", "init", "-q", "-b", "main", "--bare", "r.git")
    a = tmp_path / "a"
    sh(tmp_path, "git", "clone", "-q", "r.git", "a")
    (a / "tools").mkdir()
    shutil.copy(TOOL, a / "tools/claims.py"); shutil.copy(TOOL.with_name("budget.py"), a / "tools/budget.py")  # claims.py checks the budget switch
    shutil.copy(TOOL.with_name("batch_verify.py"), a / "tools/batch_verify.py")
    (a / "PLAN.md").write_text(PLAN)
    (a / ".gitignore").write_text(".claude/state/\n")
    for c in (["add", "-A"], ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "init"], ["push", "-q", "-u", "origin", "main"]):
        assert sh(a, "git", *c).returncode == 0
    sh(tmp_path, "git", "clone", "-q", "r.git", "b")
    b = tmp_path / "b"
    for d in (a, b):
        sh(d, "git", "config", "user.email", "a@b"); sh(d, "git", "config", "user.name", "t")
    return a, b, tmp_path / "r.git"


def test_two_sessions(repos):
    a, b, remote = repos

    assert claims(a, "next").stdout.strip() == "Item one"
    assert claims(b, "next").stdout.strip() == "Sub A"            # parent items count through their sub-items
    assert claims(b, "take", "Item one").returncode == 1          # held by a
    assert claims(a, "next").stdout.strip() == "Sub B"
    assert claims(b, "next").returncode == 1                      # nothing free
    assert claims(b, "others-cover").returncode == 1              # b still holds Sub A itself
    assert claims(a, "release").returncode == 0
    assert "Item one" in [l[7:] for l in claims(b, "list").stdout.splitlines() if l.startswith("[FREE]")]
    assert claims(b, "take", "Item one").returncode == 0


def test_refuses_mid_rebase(repos):
    """A claim during a conflicted rebase must not stack claim commits for every open item."""
    a, _, _ = repos
    head = sh(a, "git", "rev-parse", "HEAD").stdout
    (Path(sh(a, "git", "rev-parse", "--absolute-git-dir").stdout.strip()) / "rebase-merge").mkdir()
    r = claims(a, "next")
    assert r.returncode != 0 and "mid-rebase-merge" in r.stderr
    assert sh(a, "git", "rev-parse", "HEAD").stdout == head and not (a / "claims").exists()


def shared(remote, name):
    r = sh(remote, "git", "show", f"main:claims/{name}.json")
    return json.loads(r.stdout) if r.returncode == 0 else None


def snapshot(repo):
    """Include byte-for-byte staged state and dirty/untracked content, not just branch ancestry."""
    status = sh(repo, "git", "status", "--porcelain").stdout
    index = Path(sh(repo, "git", "rev-parse", "--path-format=absolute", "--git-path", "index").stdout.strip())
    return (sh(repo, "git", "rev-parse", "HEAD").stdout, sh(repo, "git", "symbolic-ref", "-q", "HEAD").stdout,
            status, index.read_bytes(), {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*")
                                       if p.is_file() and not {".git", ".claude"}.intersection(p.relative_to(repo).parts)})


def dirty_feature(a):
    assert sh(a, "git", "checkout", "-qb", "codex/feature").returncode == 0
    (a / "feature.py").write_text("feature code\n")
    sh(a, "git", "add", "feature.py"); sh(a, "git", "commit", "-qm", "feature only")
    assert sh(a, "git", "push", "-qu", "origin", "codex/feature").returncode == 0
    (a / "feature.py").write_text("staged code\n")
    sh(a, "git", "add", "feature.py")
    (a / "feature.py").write_text("unstaged code\n")
    (a / "scratch.txt").write_text("untracked content\n")
    (a / "claims").mkdir()
    (a / "claims/unrelated.json").write_text('{"session": "unpublished"}\n')
    sh(a, "git", "add", "claims/unrelated.json")


def test_feature_lifecycle_preserves_everything_and_publishes_only_owned_claims(repos):
    a, b, remote = repos
    dirty_feature(a)
    before = snapshot(a)
    assert claims(a, "take", "Item one").returncode == 0
    initial = shared(remote, "item-one")
    assert initial["session"] == "a" and snapshot(a) == before
    assert claims(b, "take", "Sub A").returncode == 0
    other = shared(remote, "sub-a")
    assert claims(a, "beat", "Checking source freshness", env={"CODEX_THREAD_ID": "thread-a", "CLAUDECODE": "0",
                                                              "CLAUDE_CODE_SESSION_ID": ""}).returncode == 0
    beat = shared(remote, "item-one")
    assert beat["heartbeat"] >= initial["heartbeat"] and beat["activity"] == "Checking source freshness"
    assert beat["provider"] == "Codex" and beat["thread_id"] == "thread-a"
    assert claims(b, "take", "Item one").returncode == 1
    assert "taken by a" in claims(b, "list").stdout
    assert snapshot(a) == before and shared(remote, "sub-a") == other
    assert sh(remote, "git", "show", "main:feature.py").returncode != 0
    assert shared(remote, "unrelated") is None
    assert claims(a, "release").returncode == 0
    assert shared(remote, "item-one") is None and shared(remote, "sub-a") == other and snapshot(a) == before
    assert sh(a, "git", "for-each-ref", "--format=%(refname)", "refs/kerf/claims").stdout == ""


def test_detached_linked_worktree_uses_caller_identity(repos):
    a, b, remote = repos
    worker = a.parent / "worker"
    assert sh(a, "git", "worktree", "add", "--detach", str(worker), "HEAD").returncode == 0
    state = worker / ".claude/state"
    state.mkdir(parents=True)
    (state / "session_id").write_text("old-session")
    before = snapshot(worker)
    assert claims(worker, "next").returncode == 0
    assert shared(remote, "item-one")["session"] == "worker"
    assert claims(a, "mine").stdout.strip() == ""
    assert claims(worker, "beat", "Detached work").returncode == 0
    assert claims(worker, "release").returncode == 0
    assert snapshot(worker) == before and (state / "session_id").read_text() == "old-session"


def push_claim(repo, name, value):
    assert sh(repo, "git", "pull", "-q", "--ff-only").returncode == 0
    (repo / "claims").mkdir(exist_ok=True)
    (repo / f"claims/{name}.json").write_text(json.dumps(value))
    sh(repo, "git", "add", f"claims/{name}.json")
    assert sh(repo, "git", "commit", "-qm", "concurrent update").returncode == 0
    assert sh(repo, "git", "push", "-q").returncode == 0


def race_once(a, b, name, value):
    """A real push wins after A's snapshot, so A must retry its decision against the new remote tree."""
    hook = Path(sh(a, "git", "rev-parse", "--absolute-git-dir").stdout.strip()) / "hooks/pre-push"
    script = f'''#!{Path(sys.executable).resolve()}
import json, os, pathlib, subprocess
os.environ.pop("GIT_DIR", None)
os.environ.pop("GIT_WORK_TREE", None)
os.environ.pop("GIT_INDEX_FILE", None)
pathlib.Path(__file__).unlink()
repo = pathlib.Path({str(b)!r})
def git(*a): subprocess.run(["git", *a], cwd=repo, check=True, stdout=subprocess.DEVNULL)
git("pull", "-q", "--ff-only")
(repo / "claims").mkdir(exist_ok=True)
(repo / {f"claims/{name}.json"!r}).write_text({json.dumps(value)!r})
git("add", {f"claims/{name}.json"!r})
git("commit", "-qm", "concurrent push")
git("push", "-q")
'''
    hook.write_text(script)
    hook.chmod(0o755)


def test_concurrent_unrelated_push_retries_without_losing_either_claim(repos):
    a, b, remote = repos
    other = {"item": "Sub A", "session": "b", "heartbeat": time.time()}
    race_once(a, b, "sub-a", other)
    assert claims(a, "take", "Item one").returncode == 0
    assert shared(remote, "sub-a") == other and shared(remote, "item-one")["session"] == "a"


def test_concurrent_fresh_owner_wins_and_cannot_be_overwritten(repos):
    a, b, remote = repos
    other = {"item": "Item one", "session": "b", "heartbeat": time.time()}
    race_once(a, b, "item-one", other)
    assert claims(a, "take", "Item one").returncode == 1
    assert shared(remote, "item-one") == other


@pytest.mark.parametrize("command", ["beat", "release"])
def test_ownership_rechecked_after_reclaim_race(repos, command):
    a, b, remote = repos
    assert claims(a, "take", "Item one").returncode == 0
    other = {"item": "Item one", "session": "b", "heartbeat": time.time(), "activity": "new owner"}
    race_once(a, b, "item-one", other)
    assert claims(a, command).returncode == 0
    assert shared(remote, "item-one") == other


def test_stale_claim_can_be_taken_but_local_claim_edits_cannot_release_another_owner(repos):
    a, b, remote = repos
    push_claim(b, "item-one", {"item": "Item one", "session": "b", "heartbeat": time.time() - 91 * 60})
    assert claims(a, "take", "Item one").returncode == 0
    (a / "claims").mkdir()
    (a / "claims/sub-a.json").write_text('{"session": "a"}')
    assert claims(b, "take", "Sub A").returncode == 0
    other = shared(remote, "sub-a")
    assert claims(a, "release").returncode == 0
    assert shared(remote, "sub-a") == other


def test_budget_reads_and_updates_shared_main_without_dirtying_feature(repos):
    a, b, remote = repos
    dirty_feature(a)
    before = snapshot(a)
    assert run_tool(a, "budget.py", "stop", "weekly cap").returncode == 0
    assert snapshot(a) == before and shared(remote, "budget")["reason"] == "weekly cap"
    assert run_tool(b, "budget.py", "status").returncode == 1
    assert claims(b, "next").returncode == 3 and claims(b, "take", "Item one").returncode == 3
    assert run_tool(a, "budget.py", "resume").returncode == 0
    assert snapshot(a) == before and shared(remote, "budget") is None
    assert claims(b, "next").returncode == 0
    assert run_tool(a, "budget.py", "stop", "already reset", "--until", "2000-01-01 00:00").returncode == 0
    assert claims(a, "next").returncode == 0
    state = a / ".claude/state"
    state.mkdir(parents=True)
    (state / "BUDGET_STOP").write_text("local cap")
    assert claims(a, "take", "Sub B").returncode == 3
    # Budget stops block new work, never prevent finishing and releasing existing work.
    assert claims(a, "beat").returncode == 0 and claims(a, "release").returncode == 0


def test_budget_stop_during_push_retry_blocks_claim(repos):
    a, b, remote = repos
    race_once(a, b, "budget", {"reason": "cap during push", "until": None})
    r = claims(a, "take", "Item one")
    assert r.returncode == 3 and "cap during push" in r.stdout
    assert shared(remote, "item-one") is None


@pytest.mark.parametrize("item", ["budget", "batch verify"])
def test_plan_titles_cannot_replace_shared_controls(repos, item):
    a, b, remote = repos
    (a / "PLAN.md").write_text(f"- [ ] {item}\n")
    control = {"session": "runner", "heartbeat": time.time(), "until": 1}
    key = item.replace(" ", "-")
    push_claim(b, key, control)
    r = claims(a, "take", item)
    assert r.returncode != 0 and "reserved" in r.stderr
    assert shared(remote, key) == control


def test_batch_status_reads_shared_lock_from_stale_feature_checkout(repos):
    a, b, remote = repos
    dirty_feature(a)
    push_claim(b, "batch-verify", {"session": "runner", "heartbeat": time.time()})
    before = snapshot(a)
    result = run_tool(a, "batch_verify.py", "status")
    assert result.returncode == 0 and "RUNNING NOW" in result.stdout and "runner" in result.stdout
    assert snapshot(a) == before


@pytest.mark.parametrize("failure", ["no_remote", "unreachable", "corrupt_claim", "corrupt_budget", "reject_push"])
def test_unavailable_or_unsafe_shared_state_never_claims_success(repos, failure):
    a, b, remote = repos
    if failure == "no_remote":
        sh(a, "git", "remote", "remove", "origin")
    elif failure == "unreachable":
        sh(a, "git", "remote", "set-url", "origin", str(remote.parent / "missing.git"))
    elif failure.startswith("corrupt"):
        push_claim(b, "budget" if failure == "corrupt_budget" else "item-one", ["not an object"])
    else:
        hook = remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n"); hook.chmod(0o755)
    before = snapshot(a)
    assert claims(a, "next").returncode != 0
    assert snapshot(a) == before
    if failure == "reject_push":
        assert shared(remote, "item-one") is None
    else:
        assert claims(a, "mine").returncode != 0
