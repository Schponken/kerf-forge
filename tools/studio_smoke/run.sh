#!/usr/bin/env bash
# Kerf Studio end-to-end smoke test: ./tools/studio_smoke/run.sh [out_prefix]
# Starts Studio on port 8790 with a stand-in `claude` (signed in, trusts the repo, streams a short fake edit), runs
# smoke.mjs in headless Chromium, then stops Studio and removes the duplicate it made. servo_link must be built.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/../.." && pwd)"; cd "$root"
tmp="$(mktemp -d)"; mkdir -p "$tmp/bin"; cp "$here/fake_claude" "$tmp/bin/claude"; chmod +x "$tmp/bin/claude"
printf '{"projects": {"%s": {"hasTrustDialogAccepted": true}}}' "$root" > "$tmp/.claude.json"
rm -rf projects/zz_studio_test_copy
PATH="$tmp/bin:$PATH" CLAUDE_CONFIG_DIR="$tmp" .venv/bin/python -m kerf.cli studio --no-open --port 8790 > "$tmp/studio.log" 2>&1 &
pid=$!; trap 'kill $pid 2>/dev/null; rm -rf projects/zz_studio_test_copy "$tmp"' EXIT
sleep 3
node "$here/smoke.mjs" http://127.0.0.1:8790/ "${1:-$tmp/shot}"
