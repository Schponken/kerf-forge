"""Keep exactly one Kerf Studio tile on the Dock, pointing at the installed app (older installs and launchers left
copies). Reads `defaults export com.apple.dock -` on stdin, writes the cleaned plist to stdout, and says on stderr how
many tiles it removed. Only Kerf Studio tiles are touched; every other Dock item is kept as it was."""
import plistlib
import sys
from urllib.parse import unquote


def is_kerf(tile: dict) -> bool:
    td = tile.get("tile-data") or {}
    url = unquote(((td.get("file-data") or {}).get("_CFURLString")) or "")
    return url.rstrip("/").endswith("/Kerf Studio.app") or td.get("file-label") == "Kerf Studio" \
        or td.get("bundle-identifier") == "dev.kerfforge.studio"


def dedupe(dock: dict, app_path: str) -> tuple[dict, int]:
    apps = dock.get("persistent-apps") or []
    want = app_path.rstrip("/")
    kerf = [t for t in apps if is_kerf(t)]
    keep = next((t for t in kerf if unquote(t["tile-data"]["file-data"]["_CFURLString"]).rstrip("/").endswith(want)), None)
    out, removed = [], 0
    for t in apps:
        if is_kerf(t) and t is not keep:
            removed += 1
            continue
        out.append(t)
    dock["persistent-apps"] = out
    return dock, removed


if __name__ == "__main__":
    dock = plistlib.loads(sys.stdin.buffer.read())
    dock, n = dedupe(dock, sys.argv[1])
    sys.stdout.buffer.write(plistlib.dumps(dock))
    print(f"removed {n} extra Kerf Studio Dock tile(s)", file=sys.stderr)
