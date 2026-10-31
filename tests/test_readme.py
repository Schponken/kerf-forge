"""README.md carries a results block that tools/readme_results.py can regenerate: one row per eval project."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_results_block_has_a_row_per_eval():
    spec = importlib.util.spec_from_file_location("readme_results", ROOT / "tools/readme_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    s = (ROOT / "README.md").read_text()
    assert mod.START in s and mod.END in s
    table = mod.rows().splitlines()
    evals = [d.name for d in (ROOT / "evals").iterdir() if (d / "acceptance.py").exists()]
    assert len(table) == 2 + len(evals) and all(any(f"| {e} |" in r for r in table) for e in evals)
