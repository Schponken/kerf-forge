#!/usr/bin/env bash
# Kerf Studio as a Mac app: builds ~/Applications/Kerf Studio.app, puts it on the Dock and opens it.
# Run from the repo:  ./tools/mac/install_app.sh   (safe to re-run; it replaces the old app)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$HOME/Applications/Kerf Studio.app"
[ "$(uname)" = "Darwin" ] || { echo "This builds a macOS app; on other systems run: $REPO/.venv/bin/kerf studio"; exit 1; }
[ -x "$REPO/.venv/bin/kerf" ] || "$REPO/setup.sh"

rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Kerf Studio</string>
  <key>CFBundleDisplayName</key><string>Kerf Studio</string>
  <key>CFBundleIdentifier</key><string>dev.kerfforge.studio</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>KerfStudio</string>
  <key>CFBundleIconFile</key><string>KerfStudio</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict></plist>
PLIST

# launcher: start the local server if it isn't running, wait for it, open an app window
cat > "$APP/Contents/MacOS/KerfStudio" <<LAUNCH
#!/bin/bash
REPO="$REPO"
URL="http://127.0.0.1:8765/"
LOG="\$HOME/Library/Logs/KerfStudio.log"
export PATH="/opt/homebrew/bin:/usr/local/bin:\$HOME/.local/bin:\$HOME/.claude/local:\$HOME/.npm-global/bin:\$HOME/.homebrew/bin:\$PATH"
if ! curl -fs "\${URL}api/projects" >/dev/null 2>&1; then
  cd "\$REPO" && nohup .venv/bin/kerf studio --no-open --port 8765 >>"\$LOG" 2>&1 &
  for i in \$(seq 1 60); do curl -fs "\${URL}api/projects" >/dev/null 2>&1 && break; sleep 0.25; done
fi
for b in "Google Chrome" "Microsoft Edge" "Brave Browser" "Chromium"; do
  if [ -d "/Applications/\$b.app" ] || [ -d "\$HOME/Applications/\$b.app" ]; then
    open -na "\$b" --args --app="\$URL" --window-size=1440,920 --user-data-dir="\$HOME/Library/Application Support/KerfStudio/browser"
    exit 0
  fi
done
open "\$URL"
LAUNCH
chmod +x "$APP/Contents/MacOS/KerfStudio"

# icon: 1024 px PNG -> .icns
ICONSET="$(mktemp -d)/KerfStudio.iconset"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$REPO/tools/mac/icon.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$REPO/tools/mac/icon.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/KerfStudio.icns"
touch "$APP"

# Dock: add once (re-runs don't duplicate it)
if ! defaults read com.apple.dock persistent-apps 2>/dev/null | grep -q "Kerf Studio.app"; then
  defaults write com.apple.dock persistent-apps -array-add "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>file://${APP// /%20}/</string><key>_CFURLStringType</key><integer>15</integer></dict></dict></dict>"
  killall Dock
fi
echo "Installed: $APP (on your Dock). Opening it now..."
open "$APP"
