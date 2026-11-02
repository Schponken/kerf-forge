#!/usr/bin/env bash
# Kerf Studio as a real Mac app: builds ~/Applications/Kerf Studio.app (native, one window, one instance),
# puts it on the Dock and opens it.
# Run from the repo:  ./tools/mac/install_app.sh   (safe to re-run; it replaces the old app)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$HOME/Applications/Kerf Studio.app"
[ "$(uname)" = "Darwin" ] || { echo "This builds a macOS app; on other systems run: $REPO/.venv/bin/kerf studio"; exit 1; }
STATE="$HOME/Library/Application Support/KerfStudio"
LOG="$HOME/Library/Logs/KerfStudio.log"
mkdir -p "$STATE" "$(dirname "$LOG")"
appsum() { (cd "$REPO" && shasum tools/mac/KerfStudio.swift tools/mac/install_app.sh | shasum | cut -c1-16); }
# --if-outdated (run by setup.sh / start.sh): rebuild only when the app's source changed, in the background, so the
# script that called us (possibly the running app's own start-up) is never blocked or killed by the rebuild.
if [ "${1:-}" = "--if-outdated" ]; then
  [ "$(appsum)" = "$(cat "$STATE/app.sum" 2>/dev/null)" ] && exit 0
  # the single-window browser launcher (no Apple command line tools yet): keep it until swiftc appears
  [ "$(appsum)-fallback" = "$(cat "$STATE/app.sum" 2>/dev/null)" ] && ! xcrun -f swiftc >/dev/null 2>&1 && exit 0
  echo "Kerf Studio app is out of date: rebuilding it in the background (log: $LOG)"
  nohup "$0" --update >>"$LOG" 2>&1 </dev/null &
  exit 0
fi
if [ "${1:-}" = "--update" ]; then
  echo "--- $(date) rebuilding Kerf Studio.app"
  # the old browser-window launcher is a bash script; let it finish starting before replacing the app under it
  for _ in $(seq 1 90); do pgrep -f "bash.*Kerf Studio.app/Contents/MacOS/KerfStudio" >/dev/null || break; sleep 1; done
  sleep 2
fi
[ -x "$REPO/.venv/bin/kerf" ] || "$REPO/setup.sh"
# the app is a small native program (tools/mac/KerfStudio.swift); compiling it needs Apple's command line tools
# Without them (no swiftc) the app is a small launcher instead that still keeps ONE window: a click while it is open
# brings that window forward (it never opens a second one); `xcode-select --install` once upgrades it to the native app.
NATIVE=1
xcrun -f swiftc >/dev/null 2>&1 || NATIVE=0
# remember which dependency set is installed, so the app only re-runs setup when it changes
(cd "$REPO" && shasum pyproject.toml setup.sh tools/render/package.json | shasum | cut -c1-16) > "$STATE/deps.sum"

# close what the old launcher left open: Kerf Studio copies (old browser-window version) and a running app
osascript -e 'if application id "dev.kerfforge.studio" is running then tell application id "dev.kerfforge.studio" to quit' >/dev/null 2>&1 || true
pkill -f "KerfStudio/browser" 2>/dev/null || true
sleep 1

BUILD="$(mktemp -d)"
if [ "$NATIVE" = 1 ] && ! xcrun swiftc -O -target "$(uname -m)-apple-macos11.0" -o "$BUILD/KerfStudio" "$REPO/tools/mac/KerfStudio.swift" \
    -framework Cocoa -framework WebKit -framework UserNotifications; then
  echo "The native app did not compile (error above): installing the single-window launcher instead."
  NATIVE=0
fi
if [ "$NATIVE" = 0 ]; then
  echo "Apple's command line tools are not installed: installing the single-window launcher (run 'xcode-select --install' for the native app)."
  cat > "$BUILD/KerfStudio" <<LAUNCH
#!/bin/bash
# Kerf Studio launcher (no native build yet): one window only. Open -> focus it; not open -> start the engine, open it.
REPO="$REPO"; URL="http://127.0.0.1:8765/"
STATE="\$HOME/Library/Application Support/KerfStudio"; BR="\$STATE/browser"; LOG="\$HOME/Library/Logs/KerfStudio.log"
mkdir -p "\$STATE" "\$(dirname "\$LOG")"
export PATH="/opt/homebrew/bin:/usr/local/bin:\$HOME/.local/bin:\$PATH"
up() { curl -fs "\${URL}api/projects" >/dev/null 2>&1; }
PID="\$(pgrep -o -f -- "--user-data-dir=\$BR")"
if [ -n "\$PID" ] && up; then
  WINS="\$(osascript -e "tell application \\"System Events\\" to count windows of (first process whose unix id is \$PID)" 2>/dev/null || echo 0)"
  osascript -e "tell application \\"System Events\\" to set frontmost of (first process whose unix id is \$PID) to true" >/dev/null 2>&1
  [ "\${WINS:-0}" -gt 0 ] && exit 0          # the window is there: it is in front now, nothing new opens
fi
if ! up; then
  nohup "\$REPO/tools/mac/start.sh" "\$REPO" >>"\$LOG" 2>&1 &
  for i in \$(seq 1 240); do up && break; sleep 0.25; done
fi
for b in "Google Chrome" "Microsoft Edge" "Brave Browser" "Chromium"; do
  if [ -d "/Applications/\$b.app" ] || [ -d "\$HOME/Applications/\$b.app" ]; then
    open -na "\$b" --args --app="\$URL" --window-size=1440,920 --user-data-dir="\$BR"; exit 0
  fi
done
open "\$URL"
LAUNCH
  chmod +x "$BUILD/KerfStudio"
fi

rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
mv "$BUILD/KerfStudio" "$APP/Contents/MacOS/KerfStudio"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Kerf Studio</string>
  <key>CFBundleDisplayName</key><string>Kerf Studio</string>
  <key>CFBundleIdentifier</key><string>dev.kerfforge.studio</string>
  <key>CFBundleVersion</key><string>2.0</string>
  <key>CFBundleShortVersionString</key><string>2.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>KerfStudio</string>
  <key>CFBundleIconFile</key><string>KerfStudio</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSMultipleInstancesProhibited</key><true/>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsArbitraryLoads</key><true/><key>NSAllowsLocalNetworking</key><true/></dict>
  <key>KerfRepo</key><string>$REPO</string>
</dict></plist>
PLIST
chmod +x "$REPO/tools/mac/start.sh"

# icon: 1024 px PNG -> .icns
ICONSET="$(mktemp -d)/KerfStudio.iconset"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$REPO/tools/mac/icon.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$REPO/tools/mac/icon.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/KerfStudio.icns"
codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true   # ad-hoc signature so macOS runs it
touch "$APP"

# Dock: exactly one Kerf Studio tile. Older installs / launchers left copies: remove every Kerf Studio tile that isn't
# this app (tools/mac/dock_dedupe.py; other Dock items untouched), then add this one if it isn't there.
PYD="$REPO/.venv/bin/python"; [ -x "$PYD" ] || PYD="$(command -v python3 || true)"
if [ -n "$PYD" ] && defaults export com.apple.dock - > "$STATE/dock.before.plist" 2>/dev/null; then
  if "$PYD" "$REPO/tools/mac/dock_dedupe.py" "$APP" < "$STATE/dock.before.plist" > "$STATE/dock.after.plist" 2> "$STATE/dock.log" \
     && ! grep -q "removed 0 " "$STATE/dock.log"; then
    defaults import com.apple.dock "$STATE/dock.after.plist" && cat "$STATE/dock.log" && killall Dock
  fi
fi
if ! defaults read com.apple.dock persistent-apps 2>/dev/null | grep -q "Kerf Studio.app"; then
  defaults write com.apple.dock persistent-apps -array-add "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>file://${APP// /%20}/</string><key>_CFURLStringType</key><integer>15</integer></dict></dict></dict>"
  killall Dock
fi
if [ "$NATIVE" = 1 ]; then appsum > "$STATE/app.sum"; else echo "$(appsum)-fallback" > "$STATE/app.sum"; fi
echo "Installed: $APP (on your Dock). Opening it now..."
open "$APP"
