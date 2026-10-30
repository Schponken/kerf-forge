"""Two simulated sessions share a remote: claims never overlap, refusals are honoured, release frees items."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "claims.py"
PLAN = "# P\n- [x] done\n- [ ] Item one\n- [ ] Parent\n  - [ ] Sub A\n  - [ ] Sub B\n"


def sh(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


def claims(cwd, *a):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)}
    return subprocess.run([sys.executable, str(cwd / "tools/claims.py"), *a], cwd=cwd, capture_output=True,
                          text=True, env=env)


def test_two_sessions(tmp_path):
    sh(tmp_path, "git", "init", "-q", "-b", "main", "--bare", "r.git")
    a = tmp_path / "a"
    sh(tmp_path, "git", "clone", "-q", "r.git", "a")
    (a / "tools").mkdir()
    shutil.copy(TOOL, a / "tools/claims.py")
    (a / "PLAN.md").write_text(PLAN)
    (a / ".gitignore").write_text(".claude/state/\n")
    for c in (["add", "-A"], ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "init"], ["push", "-q", "-u", "origin", "main"]):
        assert sh(a, "git", *c).returncode == 0
    sh(tmp_path, "git", "clone", "-q", "r.git", "b")
    b = tmp_path / "b"
    for d in (a, b):
        sh(d, "git", "config", "user.email", "a@b"); sh(d, "git", "config", "user.name", "t")

    assert claims(a, "next").stdout.strip() == "Item one"
    assert claims(b, "next").stdout.strip() == "Sub A"            # parent items count through their sub-items
    assert claims(b, "take", "Item one").returncode == 1          # held by a
    assert claims(a, "next").stdout.strip() == "Sub B"
    assert claims(b, "next").returncode == 1                      # nothing free
    assert claims(b, "others-cover").returncode == 1              # b still holds Sub A itself
    assert claims(a, "release").returncode == 0
    assert "Item one" in [l[7:] for l in claims(b, "list").stdout.splitlines() if l.startswith("[FREE]")]
    assert claims(b, "take", "Item one").returncode == 0


def test_refuses_mid_rebase(tmp_path):
    """A claim during a conflicted rebase must not stack claim commits for every open item."""
    sh(tmp_path, "git", "init", "-q", "-b", "main", "--bare", "r.git")
    a = tmp_path / "a"
    sh(tmp_path, "git", "clone", "-q", "r.git", "a")
    (a / "tools").mkdir()
    shutil.copy(TOOL, a / "tools/claims.py")
    (a / "PLAN.md").write_text(PLAN)
    (a / ".gitignore").write_text(".claude/state/\n")
    sh(a, "git", "config", "user.email", "a@b"); sh(a, "git", "config", "user.name", "t")
    for c in (["add", "-A"], ["commit", "-qm", "init"], ["push", "-q", "-u", "origin", "main"]):
        assert sh(a, "git", *c).returncode == 0
    head = sh(a, "git", "rev-parse", "HEAD").stdout
    (Path(sh(a, "git", "rev-parse", "--absolute-git-dir").stdout.strip()) / "rebase-merge").mkdir()
    r = claims(a, "next")
    assert r.returncode != 0 and "mid-rebase-merge" in r.stderr
    assert sh(a, "git", "rev-parse", "HEAD").stdout == head and not (a / "claims").exists()
