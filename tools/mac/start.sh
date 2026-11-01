#!/bin/bash
# Started by the Kerf Studio Mac app (tools/mac/KerfStudio.swift). Updates the repo, re-runs setup when dependencies
# changed, then becomes the Kerf Studio server (exec), so quitting the app stops it.
# Lines starting with STATUS / ERROR are shown in the app window while it starts.
REPO="$1"
STATE="$HOME/Library/Application Support/KerfStudio"
mkdir -p "$STATE"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.claude/local:$HOME/.npm-global/bin:$HOME/.homebrew/bin:$PATH"
export LANG="${LANG:-en_US.UTF-8}" PYTHONUTF8=1 PYTHONUNBUFFERED=1
cd "$REPO" 2>/dev/null || { echo "ERROR Kerf Forge folder not found: $REPO"; exit 1; }
echo "--- $(date) Kerf Studio app start"
# updates: fast-forward only, never over local changes; skipped quietly when offline
if [ -z "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
  echo "STATUS Checking for updates…"
  git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=10 pull -q --ff-only 2>&1 || true
fi
SUM="$(shasum pyproject.toml setup.sh tools/render/package.json 2>/dev/null | shasum | cut -c1-16)"
if [ "$SUM" != "$(cat "$STATE/deps.sum" 2>/dev/null)" ] || [ ! -x .venv/bin/kerf ]; then
  echo "STATUS Installing updates (the first time can take a few minutes)…"
  # indent setup's output so none of its lines are mistaken for STATUS / ERROR lines
  if ./setup.sh 2>&1 | while IFS= read -r l; do echo "  $l"; done; [ "${PIPESTATUS[0]}" -eq 0 ]; then echo "$SUM" > "$STATE/deps.sum"
  else echo "ERROR Setup failed. Details are in ~/Library/Logs/KerfStudio.log"; exit 1; fi
fi
echo "STATUS Starting the engine…"
# --idle-exit is only a safety net if the app crashes; while the app runs it checks in every 5 s
exec .venv/bin/kerf studio --no-open --port 8765 --idle-exit 150
