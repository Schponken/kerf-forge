"""Regenerate the results table in README.md (between the RESULTS markers) from each eval project's
out/report.json (kerf build), its review.json / review status and its evals/<id>/acceptance.py.

    .venv/bin/python tools/readme_results.py          # rewrite the block
    .venv/bin/python tools/readme_results.py --check  # exit 1 if the block is out of date
Run it after `kerf build` of every eval project (kerf verify does those builds)."""
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"


def rows():
    from kerf import cli
    out = ["| Project | Build | Review | Eval | Printed parts | Purchased | Mass (g, parts) | Plates | Renders |",
           "|---|---|---|---|---|---|---|---|---|"]
    for d in sorted(p for p in (ROOT / "evals").iterdir() if (p / "acceptance.py").exists()):
        pid = d.name
        rep_f = ROOT / "projects" / pid / "out" / "report.json"
        if not rep_f.exists():
            out.append(f"| {pid} | not built | — | — | | | | | |")
            continue
        rep = json.loads(rep_f.read_text())
        rs = cli.review_status(pid) if hasattr(cli, "review_status") else {"ok": False}
        try:
            fails = importlib.import_module(f"evals.{pid}.acceptance").accept(rep, ROOT / "projects" / pid)
        except Exception as e:  # noqa: BLE001
            fails = [f"acceptance crashed: {e}"]
        mass = round(sum(p.get("mass_est_g", 0) * 1 for p in rep.get("parts", {}).values())
                     + sum(p.get("mass_g", 0) * (p.get("qty") or 1) for p in rep.get("purchased", {}).values()), 1)
        plates = len((rep.get("files") or {}).get("plates") or [])
        src = ROOT / "projects" / pid / "out" / "renders" / "assembly_sheet.png"
        sheet = f"docs/results/{pid}.png"          # committed copy (out/ is not in git)
        if src.exists():
            (ROOT / "docs" / "results").mkdir(parents=True, exist_ok=True)
            (ROOT / sheet).write_bytes(src.read_bytes())
        out.append(f"| {pid} | {'PASS' if rep.get('ok') else 'FAIL'} | {'PASS' if rs.get('ok') else 'stale/none'} | "
                   f"{'PASS' if not fails else 'FAIL'} | {len(rep.get('parts', {}))} | {len(rep.get('purchased', {}))} | "
                   f"{mass} | {plates} | [assembly]({sheet}) |")
    return "\n".join(out)


def main():
    readme = ROOT / "README.md"
    s = readme.read_text(encoding="utf-8")
    i, j = s.index(START) + len(START), s.index(END)
    new = s[:i] + "\n" + rows() + "\n" + s[j:]
    if "--check" in sys.argv:
        sys.exit(0 if new == s else 1)
    readme.write_text(new, encoding="utf-8")
    print(rows())


if __name__ == "__main__":
    main()
