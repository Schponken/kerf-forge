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
    browser_files = ["tests/test_work_page.py", "tests/test_viewer_build_it.py"]
    files = ["tests/test_viewer.py", "tests/test_ship.py", "tests/test_fea.py", "tests/test_thoughtweb.py",
             "tests/test_notify_targets.py", *browser_files]
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
    for path in browser_files:
        nodes = {node for node in all_tests if node.startswith(path + "::")}
        assert nodes and nodes <= browsers
    assert "tests/test_notify_targets.py::test_page_targets_and_click_through" in browsers
    assert {"tests/test_notify_targets.py::test_server_leaves_notifications_to_the_mac_app_while_it_is_open",
            "tests/test_notify_targets.py::test_swift_app_posts_clickable_notifications"} <= quick
    assert "tests/test_thoughtweb.py::test_studio_draws_it_live_and_for_a_project" in browsers
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
