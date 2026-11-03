"""Local test context stays read-only; shared environments import the active checkout."""
import importlib.util
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("test_context_tool", ROOT / "tools/test_context.py")
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


def test_context_sanitizes_processes_and_uses_only_local_reads(monkeypatch, capsys):
    calls = []

    def run(*args):
        calls.append(args)
        if args == ("git", "rev-parse", "--show-toplevel"):
            return "/checkout"
        if args == ("git", "rev-parse", "HEAD"):
            return "abc123"
        if args == ("git", "--no-optional-locks", "status", "--short", "--untracked-files=normal"):
            return " M kerf/example.py"
        if args == ("ps", "-axo", "pid=,comm="):
            return "12 /Library/Frameworks/Python.app/Contents/MacOS/Python\n13 /bin/zsh\n14 /usr/bin/python3\n15 /bin/pytest"
        if args == ("ps", "-p", "12", "-o", "args="):
            return '/shared env/bin/python3.12 -m pytest tests/test_a.py::test_a -k "secret expression" --token=secret'
        if args == ("ps", "-p", "14", "-o", "args="):
            return "python3 tools/other.py --token=secret"
        if args == ("ps", "-p", "15", "-o", "args="):
            raise subprocess.CalledProcessError(1, args)
        raise AssertionError(args)

    monkeypatch.setattr(context, "run", run)
    context.main()
    out = capsys.readouterr().out
    assert "Checkout: /checkout\nHEAD: abc123\nDirty files:\n M kerf/example.py" in out
    assert "PID 12: tests/test_a.py::test_a" in out
    assert "PID 13" not in out and "PID 14" not in out and "PID 15" not in out
    assert "secret" not in out and "--token" not in out
    assert "status separately" in out
    assert all(call[0] in ("git", "ps") for call in calls)
    assert context.pytest_selection("pytest -k secret") == "selection unavailable (options/expressions omitted)"
    assert context.pytest_selection("pytest 'unterminated") is None


def test_shared_environment_imports_each_checkout_with_console_and_module(tmp_path):
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert config["pythonpath"] == ["."]
    # The wrong tree on PYTHONPATH stands in for a shared editable environment's installed source.
    trees = [tmp_path / "checkout_a", tmp_path / "checkout_b"]
    for tree in trees:
        (tree / "kerf").mkdir(parents=True)
        (tree / "kerf/__init__.py").write_text(f"TREE = {tree.name!r}\n")
        (tree / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath = ["."]\n')
        (tree / "test_tree.py").write_text(
            f"import kerf\ndef test_tree():\n    assert kerf.TREE == {tree.name!r}\n")
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": ""}
    for tree, other in (trees, trees[::-1]):
        env["PYTHONPATH"] = str(other)
        for command in ([str(ROOT / ".venv/bin/pytest")], [sys.executable, "-m", "pytest"]):
            result = subprocess.run([*command, "-q", "test_tree.py"], cwd=tree, env=env,
                                    capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            assert "1 passed" in result.stdout
