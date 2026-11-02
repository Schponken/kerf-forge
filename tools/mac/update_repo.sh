#!/bin/bash
# Update the Kerf Forge folder from GitHub without losing local changes (used by start.sh and the Update app).
# Fast-forward with local changes preserved, including their staged/unstaged split. Refuse overlapping edits
# before stashing; independent edits to the same text file can be merged by Git when the stash is restored.
# Prints one line starting with UPDATED / UP-TO-DATE / NOT-UPDATED / OFFLINE.
cd "${1:-.}" || exit 1
git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=10 fetch -q 2>/dev/null || { echo "OFFLINE could not reach GitHub"; exit 0; }
UP="$(git rev-parse -q --verify '@{u}' 2>/dev/null)" || { echo "NOT-UPDATED no upstream branch"; exit 0; }
[ "$(git rev-parse HEAD)" = "$UP" ] && { echo "UP-TO-DATE"; exit 0; }
git merge-base --is-ancestor HEAD "$UP" || { echo "NOT-UPDATED this folder has its own commits; push or rebase them first"; exit 0; }
LOCAL_FILES=()
while IFS= read -r -d '' f; do LOCAL_FILES+=("$f"); done < <(
  git diff --no-renames --name-only -z
  git diff --cached --no-renames --name-only -z
)
if [ "${#LOCAL_FILES[@]}" -eq 0 ]; then
  git merge -q --ff-only "$UP" && echo "UPDATED $(git log --oneline -1 | cut -c1-60)" \
    || echo "NOT-UPDATED fast-forward failed; local files were kept (see Git's message above)"
  exit 0
fi
INCOMING_FILES=()
while IFS= read -r -d '' f; do INCOMING_FILES+=("$f"); done < <(git diff --no-renames --name-only -z HEAD "$UP")
CHECK_DIR="$(mktemp -d)" || { echo "NOT-UPDATED could not prepare the conflict check"; exit 0; }
trap 'rm -rf "$CHECK_DIR"' EXIT
CLASH=""
for f in "${LOCAL_FILES[@]}"; do
  for incoming in "${INCOMING_FILES[@]}"; do
    [ "$f" = "$incoming" ] || continue
    # Check both views: an unstaged undo must not hide a conflicting staged change. Add/delete/type conflicts
    # are left untouched; only regular text files with all three versions get the line-level dry run.
    if [ -f "$f" ] && [ ! -L "$f" ] \
      && git --literal-pathspecs ls-tree HEAD -- "$f" | grep -Eq '^100(644|755) ' \
      && git --literal-pathspecs ls-tree "$UP" -- "$f" | grep -Eq '^100(644|755) ' \
      && git --literal-pathspecs ls-files --stage -- "$f" | grep -Eq '^100(644|755) ' \
      && git show "HEAD:$f" > "$CHECK_DIR/base" 2>/dev/null \
      && git show "$UP:$f" > "$CHECK_DIR/up" 2>/dev/null \
      && git show ":$f" > "$CHECK_DIR/index" 2>/dev/null \
      && cat < "$f" > "$CHECK_DIR/mine" \
      && git merge-file -q -p "$CHECK_DIR/index" "$CHECK_DIR/base" "$CHECK_DIR/up" > /dev/null 2>&1 \
      && git merge-file -q -p "$CHECK_DIR/mine" "$CHECK_DIR/base" "$CHECK_DIR/up" > /dev/null 2>&1; then
      break
    fi
    printf -v CLASH '%s %q' "$CLASH" "$f"
    break
  done
done
if [ -n "$CLASH" ]; then
  echo "NOT-UPDATED your local changes and the update conflict (same lines, additions, deletions or file types) in:$CLASH - commit or undo them, then update"
  exit 0
fi
STASH_LABEL="kerf update $$ ${CHECK_DIR##*/}: local changes set aside"
git stash push -q -m "$STASH_LABEL" \
  || { echo "NOT-UPDATED could not set local changes aside"; exit 0; }
SAVED_STASH=""
# refs/stash is shared across worktrees. Another update may push between our push and this lookup.
while read -r oid subject; do
  if [[ "$subject" == *": $STASH_LABEL" ]]; then SAVED_STASH="$oid"; break; fi
done < <(git reflog show --format='%H %gs' refs/stash)
if [ -z "$SAVED_STASH" ]; then
  echo "NOT-UPDATED could not identify this update's saved work; inspect git stash list before retrying"
  exit 0
fi
if git merge -q --ff-only "$UP"; then
  RESULT="UPDATED $(git log --oneline -1 | cut -c1-60)"
else
  RESULT="NOT-UPDATED fast-forward failed"
fi
# Restore our exact entry, including the index. Keep the recovery copy: checking then dropping a mutable stash
# position can remove another worktree's newer entry, even after a successful restore.
if git stash apply --index "$SAVED_STASH" >/dev/null 2>&1; then
  echo "$RESULT (your staged and unstaged changes kept); recovery stash kept: $SAVED_STASH"
else
  echo "$RESULT but local edits need recovery. Inspect git status; your saved work is in stash $SAVED_STASH (git stash apply --index $SAVED_STASH)"
fi
