"""Updater conflicts are checked before local edits move, with path and index fidelity."""
from pathlib import Path
import os
import shutil
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "tools/mac/update_repo.sh"


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.PIPE)


@pytest.fixture
def repos(tmp_path):
    origin, work, other = (tmp_path / name for name in ("origin.git", "work", "other"))
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    for path in (work, other):
        git(tmp_path, "clone", "-q", str(origin), str(path))
        git(path, "config", "user.name", "Updater test")
        git(path, "config", "user.email", "test@example.invalid")
    return work, other


def commit(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    git(repo, "push", "-qu", "origin", "main")


def seed(repos, filename="notes.txt"):
    work, other = repos
    text = "".join(f"line {i}\n" for i in range(30))
    for name in (filename, "remote.txt", "scratch.txt"):
        path = other / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    commit(other, "Baseline")
    git(work, "pull", "-q", "origin", "main")
    git(work, "branch", "-qu", "origin/main")
    return text


def run(repo, env=None):
    return subprocess.run(["bash", str(SCRIPT), str(repo)], capture_output=True, text=True, timeout=20, env=env)


@pytest.mark.parametrize("filename", ["tools/mac/Update Kerf Studio.command", 'notes/quoted "file".txt',
                                     "notes/café.txt", "notes/tab\tname.txt", "notes/line\nname.txt"])
def test_conflicting_paths_are_blocked_before_stashing(repos, filename):
    work, other = repos
    text = seed(repos, filename)
    (other / filename).write_text(text.replace("line 0\n", "upstream\n"), encoding="utf-8")
    commit(other, "Incoming change")
    local = text.replace("line 0\n", "local\n")
    (work / filename).write_text(local, encoding="utf-8")
    before = git(work, "rev-parse", "HEAD")
    result = run(work)
    assert result.returncode == 0 and result.stdout.startswith("NOT-UPDATED"), result
    assert git(work, "rev-parse", "HEAD") == before
    assert (work / filename).read_text(encoding="utf-8") == local
    assert not git(work, "stash", "list")
    assert len(result.stdout.splitlines()) == 1


@pytest.mark.parametrize("filename", ["notes.txt", "assembly notes.txt", "café.txt", 'quoted "note".txt', "-n"])
def test_update_keeps_both_index_and_worktree_edits(repos, filename):
    work, other = repos
    text = seed(repos, filename)
    remote = text.replace("line 28\n", "upstream\n")
    (other / filename).write_text(remote, encoding="utf-8")
    commit(other, "Remote end")
    (work / filename).write_text(text.replace("line 0\n", "staged\n"), encoding="utf-8")
    git(work, "add", "--", filename)
    (work / filename).write_text(text.replace("line 0\n", "staged\n").replace("line 14\n", "unstaged\n"), encoding="utf-8")
    result = run(work)
    assert result.stdout.startswith("UPDATED"), result
    assert git(work, "show", ":" + filename).decode() == remote.replace("line 0\n", "staged\n")
    assert (work / filename).read_text(encoding="utf-8") == remote.replace("line 0\n", "staged\n").replace("line 14\n", "unstaged\n")
    assert git(work, "diff", "--cached", "--name-only", "-z") == filename.encode() + b"\0"
    assert len(git(work, "stash", "list").splitlines()) == 1
    assert git(work, "show", "refs/stash^2:" + filename).decode() == text.replace("line 0\n", "staged\n")
    assert git(work, "rev-parse", "refs/stash").decode().strip() in result.stdout


def test_staged_rename_and_existing_stash_survive(repos):
    work, other = repos
    text = seed(repos)
    (work / "scratch.txt").write_text("saved earlier\n")
    git(work, "stash", "push", "-qm", "User's earlier work")
    earlier = git(work, "rev-parse", "refs/stash")
    git(work, "mv", "notes.txt", "renamed notes.txt")
    (work / "scratch.txt").write_text("unstaged work\n")
    (work / "untracked note.txt").write_text("keep this too\n")
    (other / "remote.txt").write_text("new remote\n")
    commit(other, "Remote only")
    result = run(work)
    assert result.stdout.startswith("UPDATED"), result
    assert git(work, "diff", "--cached", "--name-status", "-z") == b"R100\0notes.txt\0renamed notes.txt\0"
    assert (work / "renamed notes.txt").read_text() == text and not (work / "notes.txt").exists()
    assert (work / "scratch.txt").read_text() == "unstaged work\n"
    assert (work / "untracked note.txt").read_text() == "keep this too\n"
    assert len(git(work, "stash", "list").splitlines()) == 2
    assert git(work, "rev-parse", "stash@{1}") == earlier
    assert git(work, "show", "stash@{1}:scratch.txt") == b"saved earlier\n"


def test_index_conflict_is_not_hidden_by_an_undone_worktree_edit(repos):
    work, other = repos
    text = seed(repos)
    (work / "notes.txt").write_text(text.replace("line 0\n", "staged\n"))
    git(work, "add", "notes.txt")
    (work / "notes.txt").write_text(text)
    (other / "notes.txt").write_text(text.replace("line 0\n", "upstream\n"))
    commit(other, "Conflicting index line")
    before = git(work, "rev-parse", "HEAD")
    result = run(work)
    assert result.stdout.startswith("NOT-UPDATED"), result
    assert git(work, "rev-parse", "HEAD") == before and not git(work, "stash", "list")
    assert git(work, "show", ":notes.txt").decode() == text.replace("line 0\n", "staged\n")
    assert (work / "notes.txt").read_text() == text


@pytest.mark.parametrize("dirty", [False, True])
def test_untracked_obstruction_is_reported_without_overwriting_it(repos, dirty):
    work, other = repos
    seed(repos)
    (other / "local note.txt").write_text("incoming\n")
    commit(other, "New file")
    (work / "local note.txt").write_text("my note\n")
    if dirty:
        (work / "notes.txt").write_text("staged work\n")
        git(work, "add", "notes.txt")
    before = git(work, "rev-parse", "HEAD")
    result = run(work)
    assert "NOT-UPDATED" in result.stdout, result
    assert git(work, "rev-parse", "HEAD") == before
    assert (work / "local note.txt").read_text() == "my note\n"
    assert len(git(work, "stash", "list").splitlines()) == int(dirty)
    if dirty:
        assert git(work, "show", ":notes.txt") == b"staged work\n"
        assert (work / "notes.txt").read_text() == "staged work\n"


def test_failed_restore_keeps_a_recovery_stash(repos):
    work, other = repos
    seed(repos)
    (work / "notes.txt").write_text("my local work\n")
    git(work, "add", "notes.txt")
    (other / "remote.txt").write_text("remote update\n")
    commit(other, "Remote change")
    hook = work / ".git/hooks/post-merge"
    hook.write_text('#!/bin/bash\nprintf "changed during update\\n" > notes.txt\n')
    hook.chmod(0o755)
    result = run(work)
    assert "recovery" in result.stdout.lower(), result
    assert git(work, "stash", "list")
    assert git(work, "show", "refs/stash:notes.txt") == b"my local work\n"
    assert git(work, "show", "refs/stash^2:notes.txt") == b"my local work\n"
    assert (work / "notes.txt").read_text() == "changed during update\n"
    assert git(work, "rev-parse", "refs/stash").decode().strip() in result.stdout


def test_newer_stash_is_not_restored_or_dropped_by_the_updater(repos):
    work, other = repos
    seed(repos)
    (work / "notes.txt").write_text("my local work\n")
    git(work, "add", "notes.txt")
    (other / "remote.txt").write_text("remote update\n")
    commit(other, "Remote change")
    hook = work / ".git/hooks/post-merge"
    hook.write_text('#!/bin/bash\nprintf "other work\\n" > scratch.txt\ngit stash push -qm "Other new stash"\n')
    hook.chmod(0o755)
    result = run(work)
    assert result.stdout.startswith("UPDATED") and "recovery stash kept" in result.stdout, result
    assert (work / "notes.txt").read_text() == "my local work\n"
    assert git(work, "show", ":notes.txt") == b"my local work\n"
    assert len(git(work, "stash", "list").splitlines()) == 2
    assert git(work, "show", "stash@{0}:scratch.txt") == b"other work\n"
    assert git(work, "show", "stash@{1}:notes.txt") == b"my local work\n"


def test_file_type_change_is_not_treated_as_a_text_only_merge(repos):
    work, other = repos
    seed(repos)
    (other / "notes.txt").write_text("target")
    commit(other, "Short baseline")
    git(work, "pull", "-q", "--ff-only")
    (other / "notes.txt").unlink()
    (other / "notes.txt").symlink_to("target")  # Same blob bytes, different file type.
    commit(other, "Change to symlink")
    (work / "notes.txt").write_text("local work")
    before = git(work, "rev-parse", "HEAD")
    result = run(work)
    assert result.stdout.startswith("NOT-UPDATED"), result
    assert git(work, "rev-parse", "HEAD") == before and not git(work, "stash", "list")
    assert not (work / "notes.txt").is_symlink() and (work / "notes.txt").read_text() == "local work"


def test_intervening_stash_between_push_and_capture_is_not_applied(repos, tmp_path):
    work, other = repos
    seed(repos)
    (work / "notes.txt").write_text("my local work\n")
    git(work, "add", "notes.txt")
    (other / "remote.txt").write_text("remote update\n")
    commit(other, "Remote change")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "git"
    wrapper.write_text('''#!/bin/bash
if [ "$1" = stash ] && [ "$2" = push ]; then
  "$UPDATE_TEST_GIT_REAL" "$@" || exit
  printf 'intervening work\\n' > scratch.txt
  "$UPDATE_TEST_GIT_REAL" stash push -qm 'Intervening stash'
else
  exec "$UPDATE_TEST_GIT_REAL" "$@"
fi
''')
    wrapper.chmod(0o755)
    result = run(work, {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                        "UPDATE_TEST_GIT_REAL": shutil.which("git")})
    assert result.stdout.startswith("UPDATED"), result
    assert (work / "notes.txt").read_text() == "my local work\n"
    assert git(work, "show", ":notes.txt") == b"my local work\n"
    assert len(git(work, "stash", "list").splitlines()) == 2
    assert git(work, "show", "stash@{0}:scratch.txt") == b"intervening work\n"
    assert git(work, "show", "stash@{1}:notes.txt") == b"my local work\n"
