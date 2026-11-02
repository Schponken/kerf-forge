"""Test selection must stay explicit; caching must not share a previous test's state."""
import json
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_markers_select_expensive_tests_without_removing_them():
    files = ["tests/test_viewer.py", "tests/test_ship.py", "tests/test_fea.py"]
    def collect(*options):
        r = subprocess.run([sys.executable, "-m", "pytest", "-n", "0", "--collect-only", "-q", *files, *options],
                           cwd=ROOT, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stdout + r.stderr
        return {s for s in r.stdout.splitlines() if s.startswith("tests/") and "::" in s}
    all_tests = collect()
    quick = collect("-m", "not slow")
    expensive = collect("-m", "slow")
    browsers = collect("-m", "browser")
    projects = collect("-m", "all_projects")
    assert all_tests == quick | expensive and quick.isdisjoint(expensive)
    assert browsers and projects and browsers | projects <= expensive
    assert "tests/test_fea.py::test_cantilever_matches_beam_theory" in expensive
    assert "tests/test_viewer.py::test_page_kinematics_match_engine" in quick
    # No default marker exclusion: verify/batch still includes every test.
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "-m" not in config["tool"]["pytest"]["ini_options"]["addopts"].split()


@pytest.mark.browser
def test_shared_browser_disconnect_keeps_server_and_discards_contexts(tmp_path):
    script = tmp_path / "clients.mjs"
    script.write_text(f"""import {{browser}} from '{ROOT}/tests/browser.mjs';
const a = await browser(), p = await a.newPage();
await p.route('https://example.test/**', r => r.fulfill({{body:'example'}}));
await p.goto('https://example.test'); await p.evaluate(() => localStorage.setItem('secret','first test'));
await a.close();
const b = await browser(); const empty = b.contexts().length === 0;
const q = await b.newPage(); await q.route('https://example.test/**', r => r.fulfill({{body:'example'}}));
await q.goto('https://example.test'); const value = await q.evaluate(() => localStorage.getItem('secret'));
console.log(JSON.stringify({{empty, value}})); await b.close();
""", encoding="utf-8")
    r = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=45)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout.strip()) == {"empty": True, "value": None}
