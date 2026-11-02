"""tools/batch_verify.py: when a batched full test run is due (Spencer 2026-11-02: test many features in one run)."""
import importlib.util, time
from pathlib import Path

spec = importlib.util.spec_from_file_location("batch_verify", Path(__file__).resolve().parent.parent / "tools/batch_verify.py")
bv = importlib.util.module_from_spec(spec); spec.loader.exec_module(bv)
NOW = 1_800_000_000.0


def test_no_feature_commits_never_due():
    assert bv.due({"plan_done": 10}, [], 99, NOW)[0] is False


def test_first_batch_is_due():
    assert bv.due({}, [("a", int(NOW), "x")], 5, NOW)[0] is True


def test_batches_wait_for_enough_items():
    feats = [("a", int(NOW - 3600), "feature")]
    assert bv.due({"plan_done": 10}, feats, 10 + bv.BATCH_ITEMS - 1, NOW)[0] is False
    assert bv.due({"plan_done": 10}, feats, 10 + bv.BATCH_ITEMS, NOW)[0] is True


def test_old_untested_work_is_due():
    feats = [("a", int(NOW - (bv.MAX_AGE_H + 1) * 3600), "feature")]
    assert bv.due({"plan_done": 10}, feats, 10, NOW)[0] is True


def test_chore_commits_are_not_features():
    for s in ["claim: Firmware proven", "claim heartbeat: X", "release claims", "STATUS: notes", "batch verify: lock"]:
        assert bv.CHORE.match(s)
    assert not bv.CHORE.match("drone_foldable_wings: pivot system done")


def test_plan_done_counts_checked_boxes():
    assert bv.plan_done("- [x] a\n- [ ] b\n  - [x] c\n") == 2


def test_status_says_when_a_batch_is_running(tmp_path, monkeypatch, capsys):
    """A fresh lock from any session means a full run is going: status says so instead of DUE."""
    import json, time
    lock = tmp_path / "batch-verify.json"
    monkeypatch.setattr(bv, "LOCK", lock)
    monkeypatch.setattr(bv, "load", lambda: {})
    monkeypatch.setattr(bv, "feature_commits", lambda c: [])
    monkeypatch.setattr(bv, "plan_done", lambda: 0)
    lock.write_text(json.dumps({"session": "other", "heartbeat": time.time() - 600}))
    bv.cmd_status()
    assert "RUNNING NOW" in capsys.readouterr().out
    lock.write_text(json.dumps({"session": "other", "heartbeat": time.time() - 100 * 60}))   # stale
    bv.cmd_status()
    out = capsys.readouterr().out
    assert "RUNNING NOW" not in out and "due: no feature commits" in out
