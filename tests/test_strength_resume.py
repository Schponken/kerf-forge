"""Resuming the solver does not turn old, unrun strength checks into current evidence."""
import json
from types import SimpleNamespace

import pytest

from kerf import cli, requirements as R


def test_removing_strength_pause_preserves_other_holds(tmp_path, monkeypatch):
    pause = tmp_path / "PAUSED.json"
    state = {"stress_sims": "later", "batch_verify": "still held"}
    pause.write_text(json.dumps(state))
    monkeypatch.setattr(R, "PAUSE_FILE", pause)
    monkeypatch.delenv("KERF_STRESS", raising=False)
    assert R.stress_paused() == "later"
    del state["stress_sims"]
    pause.write_text(json.dumps(state))
    for check in R.STRESS_SIMS:
        monkeypatch.setitem(R.REGISTRY, check, lambda *a, **kw: {"ok": True, "value": 3})
        result = R._run_one(None, None, {"id": check, "check": check}, quick=False)
        assert result["value"] == 3 and not result.get("skipped") and not result.get("paused")
    assert json.loads(pause.read_text()) == {"batch_verify": "still held"}


@pytest.mark.parametrize("check", sorted(R.STRESS_SIMS))
@pytest.mark.parametrize("flag", ["paused", "skipped"])
def test_saved_unrun_strength_is_stale_after_resume(tmp_path, monkeypatch, check, flag):
    monkeypatch.setattr(R, "stress_paused", lambda: "")
    out = tmp_path / "out"
    out.mkdir()
    report = out / "report.json"
    original = json.dumps({"fingerprint": "same", "ok": True,
                           "requirements": [{"id": "strength", "check": check, flag: True, "value": None}]})
    report.write_text(original)
    msg = cli._out_stale(SimpleNamespace(dir=tmp_path), "same")
    assert "strength checks not run: strength" in msg and "strength is unproven" in msg and "run kerf build" in msg
    assert report.read_text() == original
    monkeypatch.setattr(R, "stress_paused", lambda: "later")
    assert cli._out_stale(SimpleNamespace(dir=tmp_path), "same") == ""


def test_saved_completed_strength_and_non_strength_skips_stay_current(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "stress_paused", lambda: "")
    (tmp_path / "out").mkdir()
    (tmp_path / "out/report.json").write_text(json.dumps({"fingerprint": "same", "requirements": [
        {"id": "strength", "check": "fea_static", "ok": True, "value": 3},
        {"id": "motion", "check": "motion", "skipped": True}]}))
    assert cli._out_stale(SimpleNamespace(dir=tmp_path), "same") == ""
