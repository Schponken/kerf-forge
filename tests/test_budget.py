"""Usage-limit awareness (Spencer, 2026-11-02): a shared budget switch stops new work; the full batch run waits for
other sessions and for the budget; verify resumes a cut-off run instead of redoing it."""
import importlib.util, json, sys, time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_budget_switch_shared_local_and_expiry(tmp_path, monkeypatch):
    b = _load("budget")
    monkeypatch.setattr(b, "SHARED", tmp_path / "claims/budget.json")
    monkeypatch.setattr(b, "LOCAL", tmp_path / "BUDGET_STOP")
    assert b.stopped() == ""
    b.SHARED.parent.mkdir()
    b.SHARED.write_text(json.dumps({"reason": "cap near", "until": None}))
    assert "cap near" in b.stopped()
    b.SHARED.write_text(json.dumps({"reason": "cap near", "until": time.time() - 1}))
    assert b.stopped() == ""                      # expired at the reset time
    b.LOCAL.write_text("weekly cap")
    assert "weekly cap" in b.stopped()


def test_claims_refuse_new_work_under_budget_stop(monkeypatch, capsys):
    sys.path.insert(0, str(TOOLS))
    c = _load("claims")
    import budget
    monkeypatch.setattr(budget, "stopped", lambda now=None: "cap near")
    assert c.main(["next"]) == 3 and c.main(["take", "x"]) == 3
    assert "budget stop" in capsys.readouterr().out


def test_batch_held_while_others_work_or_budget_stop(monkeypatch):
    bv = _load("batch_verify")
    import budget
    monkeypatch.setattr(budget, "stopped", lambda now=None: "")
    monkeypatch.setattr(bv, "others_working", lambda sid=None: ["abc"])
    assert "other session" in bv.hold_reason()
    monkeypatch.setattr(bv, "others_working", lambda sid=None: [])
    assert bv.hold_reason() == ""
    monkeypatch.setattr(budget, "stopped", lambda now=None: "cap near")
    assert bv.hold_reason().startswith("budget stop")


def test_verify_checkpoint_resumes_same_commit_only(tmp_path, monkeypatch):
    from kerf import cli
    monkeypatch.setattr(cli._Checkpoint, "PATH", tmp_path / "ck.json")
    ck = cli._Checkpoint(False, True)
    if ck.key is None:            # dirty tree: no checkpointing by design
        assert ck.done == {}
        return
    ck.save("tests", {"line": "5 passed", "ok": True})
    assert cli._Checkpoint(False, True).done["tests"]["ok"] is True
    assert cli._Checkpoint(True, True).done == {}          # a different kind of run starts fresh
    ck.clear()
    assert cli._Checkpoint(False, True).done == {}
