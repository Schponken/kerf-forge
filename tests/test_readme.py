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
    assert not any("acceptance crashed" in r for r in table)


def test_acceptance_gets_a_path(tmp_path, monkeypatch):
    """Graders use proj_dir / "project.yaml"; the README tool must hand them a Path like run_evals does."""
    import json, sys, types
    spec = importlib.util.spec_from_file_location("readme_results", ROOT / "tools/readme_results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seen = []
    from kerf import cli
    monkeypatch.setattr(cli, "review_status", lambda pid: {"ok": False})
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    (tmp_path / "evals" / "x").mkdir(parents=True)
    (tmp_path / "evals" / "x" / "acceptance.py").write_text("")
    (tmp_path / "projects" / "x" / "out").mkdir(parents=True)
    (tmp_path / "projects" / "x" / "out" / "report.json").write_text(json.dumps({"ok": True}))
    fake = types.ModuleType("evals.x.acceptance")
    fake.accept = lambda rep, proj_dir: seen.append(proj_dir) or []
    monkeypatch.setitem(sys.modules, "evals.x.acceptance", fake)
    assert "| x | PASS |" in mod.rows()
    assert seen and all(isinstance(p, Path) for p in seen)
