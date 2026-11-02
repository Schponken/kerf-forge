"""Bounded workers, explicit expensive tests, and one isolated browser server per worker."""
from pathlib import Path
import selectors
import subprocess

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("browser") or item.get_closest_marker("all_projects"):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session")
def browser_endpoint(tmp_path_factory):
    log = tmp_path_factory.mktemp("browser") / "stderr.log"
    with log.open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(["node", str(Path(__file__).with_name("browser.mjs")), "--serve"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                assert selector.select(45), "Chromium startup timed out: " + log.read_text(encoding="utf-8")
            endpoint = proc.stdout.readline().strip()
            assert endpoint.startswith("ws://"), "Chromium failed: " + log.read_text(encoding="utf-8")
            yield endpoint
        finally:
            proc.stdin.close()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=15)
            proc.stdout.close()


@pytest.fixture(autouse=True)
def _shared_browser(request, monkeypatch):
    if request.node.get_closest_marker("browser"):
        monkeypatch.setenv("KERF_TEST_BROWSER_WS", request.getfixturevalue("browser_endpoint"))
