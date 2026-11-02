"""kerf verify builds each project in its own child process (memory freed between projects; one process for all
projects was OOM-killed at 6 GB)."""
import os

from kerf.cli import _run_isolated


def test_project_runs_in_child_process_and_reports():
    r = _run_isolated("check_shelf_bracket", check_only=True)
    assert set(r) == {"ok", "problems", "seconds"} and isinstance(r["ok"], bool)
    assert isinstance(r["seconds"], (int, float)) and r["seconds"] > 0          # VERIFY.json keeps each project's time


def test_a_crashing_build_is_a_failure_not_an_exception():
    r = _run_isolated("no_such_project_xyz", check_only=True)
    assert r["ok"] is False and "exited" in r["problems"][0]


def test_verify_keeps_the_slowest_tests():
    """kerf verify runs pytest --durations=30 and keeps the slowest lines in VERIFY.json (next speed-up's input)."""
    from kerf import cli
    out = "== slowest 30 durations ==\n12.50s call     tests/test_a.py::test_x\n3.01s setup    tests/test_b.py::test_y\n" \
          "(25 durations < 0.005s hidden.)\n2 passed in 16s"
    assert cli._slowest_tests(out) == ["12.50s call     tests/test_a.py::test_x", "3.01s setup    tests/test_b.py::test_y"]
