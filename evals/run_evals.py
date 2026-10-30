"""Run every eval: the project must exist, have a fresh out/report.json from `kerf build`, and pass acceptance."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_one(eval_dir: Path) -> dict:
    eid = eval_dir.name
    pdir = ROOT / "projects" / eid
    res = {"id": eid, "ok": False, "failures": []}
    if not (pdir / "project.yaml").exists():
        res["failures"].append(f"projects/{eid} does not exist yet")
        return res
    rp = pdir / "out" / "report.json"
    if not rp.exists():
        res["failures"].append(f"projects/{eid}/out/report.json missing; run kerf build {eid}")
        return res
    rep = json.loads(rp.read_text())
    from kerf import project as P
    fp = P.load(eid).fingerprint()
    if rep.get("fingerprint") != fp:
        res["failures"].append(f"report.json is stale (report {rep.get('fingerprint')}, geometry {fp}); run kerf build {eid}")
        return res
    if not rep.get("files"):
        res["failures"].append("report.json has no exported files; run kerf build (not check)")
    spec = importlib.util.spec_from_file_location(f"accept_{eid}", eval_dir / "acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        res["failures"] += mod.accept(rep, pdir)
    except Exception as e:  # noqa: BLE001
        res["failures"].append(f"acceptance crashed: {type(e).__name__}: {e}")
    res["ok"] = not res["failures"]
    return res


def run_all() -> list:
    return [run_one(d) for d in sorted((ROOT / "evals").iterdir()) if (d / "acceptance.py").exists()]


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    for r in run_all():
        print(("PASS " if r["ok"] else "FAIL ") + r["id"], *[f"\n   - {f}" for f in r["failures"]])
