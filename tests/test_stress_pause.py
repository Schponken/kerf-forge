"""Stress simulations can be paused (Spencer, 2026-11-02): paused checks report NOT RUN (never a pass value), the
report says strength is unproven, and paused PLAN items are not handed out by `claims.py next`."""
import importlib.util, json
from pathlib import Path

from kerf import requirements as R


def test_paused_stress_check_is_not_run(tmp_path, monkeypatch):
    f = tmp_path / "PAUSED.json"; f.write_text(json.dumps({"stress_sims": "later"}))
    monkeypatch.setattr(R, "PAUSE_FILE", f)
    monkeypatch.delenv("KERF_STRESS", raising=False)
    called = []
    monkeypatch.setitem(R.REGISTRY, "fea_static", lambda *a, **k: called.append(1) or {"ok": True, "value": 1})
    r = R._run_one(None, None, {"check": "fea_static", "id": "arm"}, quick=False)
    assert not called and r["paused"] and r["value"] is None and "NOT RUN" in r["detail"]
    monkeypatch.setenv("KERF_STRESS", "1")               # one run with them on
    assert R.stress_paused() == ""


def test_no_pause_file_runs_everything(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "PAUSE_FILE", tmp_path / "none.json")
    assert R.stress_paused() == ""
    assert {"fea_static", "impact_fea", "natural_freq", "weak_link"} <= R.STRESS_SIMS


def test_paused_plan_items_are_not_handed_out(monkeypatch):
    spec = importlib.util.spec_from_file_location("claims", Path(__file__).resolve().parent.parent / "tools/claims.py")
    c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
    monkeypatch.setattr(c, "open_items", lambda: ["PAUSED: stress - arm FEA", "Build the gripper"])
    assert c.workable_items() == ["Build the gripper"]
