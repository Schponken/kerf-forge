"""Read-only local context before a focused test run; does not decide batch eligibility."""
from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout.rstrip()


def pytest_selection(command: str) -> str | None:
    """Return only literal test paths/node IDs, never arbitrary options or their values."""
    try:
        args = shlex.split(command)
    except ValueError:
        return None
    # ps may leave spaces in executable paths unquoted; the caller has already checked comm.
    match = re.search(r"(?:^|[/\s])pytest(?:\s|$)", command)
    if not match:
        return None
    selections = [arg for arg in args if re.fullmatch(
        r"tests(?:/[\w.-]+)*(?:\.py)?(?:::[\w.-]+)*", arg, flags=re.ASCII)]
    return ", ".join(selections) if selections else "selection unavailable (options/expressions omitted)"


def active_tests() -> list[str]:
    rows = []
    for line in run("ps", "-axo", "pid=,comm=").splitlines():
        pid, executable = line.strip().split(None, 1)
        if not re.fullmatch(r"python(?:\d+(?:\.\d+)*)?|pytest", Path(executable).name, flags=re.IGNORECASE):
            continue
        try:
            selection = pytest_selection(run("ps", "-p", pid, "-o", "args="))
        except subprocess.CalledProcessError:  # process ended between snapshots
            continue
        if selection is not None:
            rows.append(f"PID {pid}: {selection}")
    return rows


def main() -> None:
    print(f"Checkout: {run('git', 'rev-parse', '--show-toplevel')}")
    print(f"HEAD: {run('git', 'rev-parse', 'HEAD')}")
    dirty = run("git", "--no-optional-locks", "status", "--short", "--untracked-files=normal")
    print(f"Dirty files:\n{dirty}" if dirty else "Dirty files: none")
    print("Active local pytest processes (snapshot; literal test paths/node IDs only):")
    print("\n".join(active_tests()) or "none observed")
    print("Run this checkout's matching tools/batch_verify.py status separately; it may fetch shared state.")


if __name__ == "__main__":
    main()
