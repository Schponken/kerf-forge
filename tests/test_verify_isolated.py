"""kerf verify builds each project in its own child process (memory freed between projects; one process for all
projects was OOM-killed at 6 GB)."""
import os

from kerf.cli import _run_isolated


def test_project_runs_in_child_process_and_reports():
    r = _run_isolated("check_shelf_bracket", check_only=True)
    assert set(r) == {"ok", "problems"} and isinstance(r["ok"], bool)


def test_a_crashing_build_is_a_failure_not_an_exception():
    r = _run_isolated("no_such_project_xyz", check_only=True)
    assert r["ok"] is False and "exited" in r["problems"][0]
