#!/bin/bash
# Double-click: update Kerf Forge, restart the engine on the new code, and reinstall the Kerf Studio app (one window).
# It never restarts under a running job: a design / change / fix in progress would stop with the engine.
cd "$(dirname "$0")/../.." || exit 1
if curl -fs http://127.0.0.1:8765/api/jobs 2>/dev/null | grep -q '"state": "running"'; then
  echo "A Kerf Studio job is still running (a design, change or check). Let it finish (or stop it in Studio), then run this again."
  exit 1
fi
echo "Updating Kerf Studio..."
git pull -q --ff-only 2>/dev/null || echo "(not updated from GitHub: local changes in the folder; installing what is here)"
pkill -f "kerf studio --no-open --port 8765" 2>/dev/null || true
./tools/mac/install_app.sh && echo "Done: Kerf Studio is updated and open. You can close this window."
