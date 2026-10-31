"""Every text read/write in the engine names its encoding: under a C/POSIX locale (hooks, cron, nohup) the default is
ASCII and the UTF-8 assets (viewer.html, prices.json) failed with UnicodeDecodeError, failing every build."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_no_text_io_without_encoding():
    bad = []
    for f in sorted((ROOT / "kerf").glob("*.py")) + [ROOT / "tools" / "readme_results.py"]:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.read_text\(\)|\.write_text\(", line) and "encoding" not in line:
                bad.append(f"{f.name}:{i}")
            m = re.search(r"(?<![\w.])open\(([^)]*)\)", line)
            if m and "encoding" not in line and not re.search(r"['\"][rwa]b['\"]", m.group(1)):
                bad.append(f"{f.name}:{i}")
    assert not bad, bad


def test_prices_load_under_c_locale():
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0"}
    r = subprocess.run([sys.executable, "-c", "from kerf import ship; assert ship.load_prices()"], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
