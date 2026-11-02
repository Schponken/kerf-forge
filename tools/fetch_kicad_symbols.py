"""Fetch the KiCad symbol libraries catalog/pins.json uses (kicad-symbols, the tag apt ships on Ubuntu 24.04) into
~/.cache/kerf/ when no system copy exists (macOS / no apt). Run by setup.sh. Only the few libraries named in pins.json are
fetched (gitlab raw-file URLs), not the whole repository."""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kerf import circuit  # noqa: E402

URL = "https://gitlab.com/kicad/libraries/kicad-symbols/-/raw/{tag}/{lib}.kicad_sym"


def main() -> int:
    if circuit.symbol_dir() is not None:
        print(f"KiCad symbols: {circuit.symbol_dir()}")
        return 0
    libs = sorted({e["symbol"].split(":")[0] for e in circuit.load_pins().values() if e.get("symbol")})
    dst = circuit.CACHE_SYMBOLS
    dst.mkdir(parents=True, exist_ok=True)
    for lib in libs:
        f = dst / f"{lib}.kicad_sym"
        if not f.exists():
            url = URL.format(tag=circuit.KICAD_SYMBOLS_TAG, lib=lib)
            data = urllib.request.urlopen(url, timeout=120).read()
            if not data.lstrip().startswith(b"(kicad_symbol_lib"):
                raise SystemExit(f"{url}: not a KiCad symbol library")
            f.write_bytes(data)
    print(f"KiCad symbols {circuit.KICAD_SYMBOLS_TAG} ({', '.join(libs)}) in {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
