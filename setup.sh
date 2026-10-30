#!/usr/bin/env bash
# One-command environment setup. Safe to re-run. Ends with `kerf doctor`, which must print ALL OK.
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
[ -x .venv/bin/python ] || uv venv -q -p 3.12 .venv
uv pip install -q --python .venv/bin/python -e .
# gmsh (FEA meshing) needs a few X/GL shared libraries even when headless
if ! .venv/bin/python -c "import gmsh" >/dev/null 2>&1; then
  (apt-get update -q && apt-get install -y -q libglu1-mesa libxcursor1 libxinerama1 libxft2 libxrender1) >/dev/null 2>&1 \
    || sudo -n sh -c 'apt-get update -q && apt-get install -y -q libglu1-mesa libxcursor1 libxinerama1 libxft2 libxrender1' >/dev/null 2>&1 || true
fi
(cd tools/render && npm ci --silent --no-audit --no-fund)
# Chromium for headless rendering: use the preinstalled Playwright browser if present, else install it.
if ! ls "${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}"/chromium-* >/dev/null 2>&1 && ! ls ~/.cache/ms-playwright/chromium-* >/dev/null 2>&1; then
  (cd tools/render && npx playwright install chromium)
fi
.venv/bin/kerf doctor
