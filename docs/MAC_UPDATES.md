# Local changes during a Mac update

The Dock launcher and **Update Kerf Studio** use `tools/mac/update_repo.sh`. It fetches the tracked branch and
fast-forwards when possible. Local commits that diverge from that branch stop the update; offline launches keep
the installed copy.

Tracked edits are checked before being set aside. Filenames containing spaces, quotes, Unicode, tabs or newlines
retain their exact identity. Both staged and unstaged edits are checked, including a staged change that was later
undone only in the working file. Independent edits to the same text file can merge; conflicting lines or overlapping
additions, deletions and file-type changes stop the update and identify the affected paths.

When an update can proceed, Git temporarily saves tracked edits and then restores their staged/unstaged split.
Untracked files stay in place. An untracked file that blocks an incoming file stops the fast-forward without being
overwritten. The updater's saved work is identified by a unique marker, so another worktree creating a newer stash
does not change which edits are restored.

## Recovery copies

Each update that sets tracked edits aside retains a Git stash labelled `kerf update …: local changes set aside`,
even after a successful restore. These are recovery copies, not unfinished updates. Existing and newer stashes are
kept too. No stash is automatically popped or dropped; stash positions are shared across worktrees and can change.

The update result prints the exact saved revision. If restoration fails, inspect `git status` and resolve the
reported working-tree issue before retrying the printed `git stash apply --index <saved-revision>` command.
Use that revision to inspect the saved work with `git stash show --stat <saved-revision>`; `--index` restores the
staged changes as well as the working files. The saved revision remains available if an apply needs recovery.

Successful-update backups can be reviewed and cleaned up manually later. No updater in this flow deletes them.
Tests use temporary local Git repositories, including intervening stashes and failed restores; they do not update
the user's checkout or launch the native app.
