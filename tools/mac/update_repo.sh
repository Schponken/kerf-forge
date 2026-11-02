#!/bin/bash
# Update the Kerf Forge folder from GitHub without losing local changes (used by start.sh and the Update app).
# Clean folder: fast-forward. Local changes that don't touch the files the update changes: set aside (git stash),
# fast-forward, put back. Overlapping files: no update, and say which files block it (never overwrite, never merge).
# Prints one line starting with UPDATED / UP-TO-DATE / NOT-UPDATED / OFFLINE.
cd "${1:-.}" || exit 1
git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=10 fetch -q 2>/dev/null || { echo "OFFLINE could not reach GitHub"; exit 0; }
UP="$(git rev-parse -q --verify '@{u}' 2>/dev/null)" || { echo "NOT-UPDATED no upstream branch"; exit 0; }
[ "$(git rev-parse HEAD)" = "$UP" ] && { echo "UP-TO-DATE"; exit 0; }
git merge-base --is-ancestor HEAD "$UP" || { echo "NOT-UPDATED this folder has its own commits; push or rebase them first"; exit 0; }
LOCAL="$(git status --porcelain --untracked-files=no | cut -c4-)"
if [ -z "$LOCAL" ]; then
  git merge -q --ff-only "$UP" && echo "UPDATED $(git log --oneline -1 | cut -c1-60)"; exit 0
fi
INCOMING="$(git diff --name-only HEAD "$UP")"
BOTH="$(comm -12 <(echo "$LOCAL" | sort -u) <(echo "$INCOMING" | sort -u))"
CLASH=""
for f in $BOTH; do                               # same file changed on both sides: fine unless the same lines are
  t="$(mktemp -d)"
  git show "HEAD:$f" > "$t/base" 2>/dev/null; git show "$UP:$f" > "$t/up" 2>/dev/null; cp "$f" "$t/mine"
  git merge-file -q -p "$t/mine" "$t/base" "$t/up" > /dev/null || CLASH="$CLASH $f"
  rm -rf "$t"
done
if [ -n "$CLASH" ]; then
  echo "NOT-UPDATED your local changes and the update change the same lines in:$CLASH - commit or undo them, then update"
  exit 0
fi
git stash push -q -m "kerf update $(date +%F_%H%M): local changes set aside" || { echo "NOT-UPDATED could not set local changes aside"; exit 0; }
if git merge -q --ff-only "$UP"; then
  git stash pop -q >/dev/null 2>&1 && echo "UPDATED $(git log --oneline -1 | cut -c1-60) (your local changes kept)" \
    || echo "UPDATED but local changes are still set aside: git stash pop"
else
  git stash pop -q >/dev/null 2>&1; echo "NOT-UPDATED fast-forward failed"
fi
