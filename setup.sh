#!/usr/bin/env bash
# One-command environment setup. Safe to re-run. Ends with `kerf doctor`, which must print ALL OK.
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo "Setup needs Node.js and npm. Install the current LTS from https://nodejs.org, open a new terminal, then run ./setup.sh again."
  exit 1
fi
# Mac: first (so a later failing step can't skip it), keep the Kerf Studio app in step with its source; rebuilds it in the background when tools/mac changed
# (without Apple's command line tools it installs the single-window launcher; with them, the native one-window app)
if [ "$(uname)" = "Darwin" ] && [ -d "$HOME/Applications/Kerf Studio.app" ]; then
  ./tools/mac/install_app.sh --if-outdated || true
fi
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
# Fresh machines (cloud sandboxes, CI): uv's Python asks for clang/clang++ when a dependency builds from source
# (pybullet); use GCC when clang is missing. Package caches go under .cache/ when the default ones are not writable.
if [ -z "${CC:-}" ] && ! command -v clang >/dev/null && command -v gcc >/dev/null; then export CC=gcc; fi
if [ -z "${CXX:-}" ] && ! command -v clang++ >/dev/null && command -v g++ >/dev/null; then export CXX=g++; fi
writable() { mkdir -p "$1" 2>/dev/null && [ -w "$1" ]; }
if [ -z "${UV_CACHE_DIR:-}" ] && ! writable "$(uv cache dir 2>/dev/null || echo "$HOME/.cache/uv")"; then export UV_CACHE_DIR="$PWD/.cache/uv"; fi
if [ -z "${npm_config_cache:-}" ] && ! writable "$HOME/.npm"; then export npm_config_cache="$PWD/.cache/npm"; fi
[ -x .venv/bin/python ] || uv venv -q -p 3.12 .venv
# pybullet has no macOS arm64 wheel and its bundled zlib `#define fdopen NULL` breaks against recent Xcode SDKs
# (stdio.h declares fdopen): pre-defining the macro skips that line. Harmless on Linux.
CFLAGS="${CFLAGS:-} -Dfdopen=fdopen" uv pip install -q --python .venv/bin/python -e .
# gmsh (FEA meshing) needs a few X/GL shared libraries even when headless
if ! .venv/bin/python -c "import gmsh" >/dev/null 2>&1; then
  (apt-get update -q && apt-get install -y -q libglu1-mesa libxcursor1 libxinerama1 libxft2 libxrender1) >/dev/null 2>&1 \
    || sudo -n sh -c 'apt-get update -q && apt-get install -y -q libglu1-mesa libxcursor1 libxinerama1 libxft2 libxrender1' >/dev/null 2>&1 || true
fi
# KiCad symbol libraries for the circuit check (kerf/circuit.py): apt kicad-symbols, else the same tag from gitlab
if [ ! -d /usr/share/kicad/symbols ]; then
  (apt-get install -y -q kicad-symbols || sudo -n apt-get install -y -q kicad-symbols) >/dev/null 2>&1 || true
fi
.venv/bin/python tools/fetch_kicad_symbols.py
(cd tools/render && npm ci --silent --no-audit --no-fund)
# The locked Playwright version checks its own browser revision and headless shell.
# This is a no-op when cached, and repairs interrupted installs or an older browser cache.
(cd tools/render && npx --no-install playwright install chromium)
# Firmware check (kerf/fwcheck.py, `kerf firmware-check`): arduino-cli, the arduino:avr core and the sketch libraries at
# pinned versions under .cache/arduino (all from downloads.arduino.cc), and simavr to run the compiled Nano program.
# Anything that cannot be installed is reported here and by `kerf doctor`; the check then says NOT RUN, never PASS.
fw_tools() {
  local AR="$PWD/.cache/arduino" VER=1.3.1 PKG SHA
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)  PKG=Linux_64bit SHA=376428d7d45be640c00812a71612e1742edc2f5f9ee3742a2d6da7870e079588 ;;
    Linux-aarch64) PKG=Linux_ARM64 SHA=cf4f668b1add7a20310d79e83a1f3eb148031f95e5673d9171c65f5e9a126a94 ;;
    Darwin-arm64)  PKG=macOS_ARM64 SHA=723f8ddaf4875e87a20380c88c15ff9d55916c3c80cb432f1f980ea32cec2341 ;;
    Darwin-x86_64) PKG=macOS_64bit SHA=a0ca73f7e599d33a532fb2b1f8af9260541d990a684988bf8208abb42be83ced ;;
    *) echo "firmware check: no arduino-cli $VER build for $(uname -sm)"; return 1 ;;
  esac
  export ARDUINO_DIRECTORIES_DATA="$AR/data" ARDUINO_DIRECTORIES_DOWNLOADS="$AR/staging" ARDUINO_DIRECTORIES_USER="$AR/user"
  if ! "$AR/bin/arduino-cli" version 2>/dev/null | grep -q "Version: $VER "; then
    local t; t=$(mktemp -d)
    curl -fsSL -o "$t/cli.tgz" "https://downloads.arduino.cc/arduino-cli/arduino-cli_${VER}_${PKG}.tar.gz" || { rm -rf "$t"; return 1; }
    if [ "$( (sha256sum "$t/cli.tgz" 2>/dev/null || shasum -a 256 "$t/cli.tgz") | cut -d' ' -f1)" != "$SHA" ]; then
      echo "firmware check: arduino-cli download sha256 mismatch"; rm -rf "$t"; return 1
    fi
    mkdir -p "$AR/bin" && tar -xzf "$t/cli.tgz" -C "$AR/bin" arduino-cli; rm -rf "$t"
  fi
  local CLI="$AR/bin/arduino-cli" LIBS=("Servo@1.2.2" "Adafruit PWM Servo Driver Library@3.0.2" "Adafruit BusIO@1.16.2")
  [ -d "$AR/data/packages/arduino/hardware/avr/1.8.6" ] \
    || { "$CLI" core update-index && "$CLI" core install arduino:avr@1.8.6; } >/dev/null || return 1
  if [ "$(cat "$AR/user/.kerf-libs" 2>/dev/null)" != "${LIBS[*]}" ]; then   # keep in step with kerf/fwcheck.py LIBS
    { "$CLI" lib update-index && "$CLI" lib install --no-deps "${LIBS[@]}"; } >/dev/null || return 1
    echo "${LIBS[*]}" > "$AR/user/.kerf-libs"
  fi
  if [ "$(uname)" = "Darwin" ]; then
    command -v brew >/dev/null && { ls "$(brew --prefix)/include/simavr/sim_avr.h" >/dev/null 2>&1 \
      || { brew tap osx-cross/avr && brew install osx-cross/avr/simavr; } >/dev/null 2>&1 || echo "firmware check: brew could not install simavr (osx-cross/avr)"; }
  elif [ ! -f /usr/include/simavr/sim_avr.h ]; then
    (apt-get install -y -q simavr libsimavr-dev || (apt-get update -q && apt-get install -y -q simavr libsimavr-dev)) >/dev/null 2>&1 \
      || sudo -n sh -c 'apt-get update -q && apt-get install -y -q simavr libsimavr-dev' >/dev/null 2>&1 \
      || echo "firmware check: could not apt-install simavr libsimavr-dev"
  fi
}
fw_tools || echo "firmware check tools incomplete: \`kerf firmware-check\` will report NOT RUN (see kerf doctor)"
.venv/bin/kerf doctor
