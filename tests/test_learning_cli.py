"""Learning evidence inspection stays read-only and reachable through the CLI."""
import json
from kerf import cli


def test_scorecards_command_reads_configured_repo(monkeypatch, tmp_path, capsys):
    from kerf import scorecards
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(scorecards, "read", lambda repo: calls.append(repo) or {"lessons": []})
    assert cli.main(["learn", "scorecards"]) == 0
    assert json.loads(capsys.readouterr().out) == {"lessons": []}
    assert calls == [tmp_path]


def test_new_project_receives_stage_marker(monkeypatch, tmp_path):
    from kerf import stages
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["new", "learning_clip", "A clip"]) == 0
    assert (tmp_path / "projects/learning_clip/stage_gates.json").is_file()


def test_unknown_stage_project_explains_recovery(capsys):
    assert cli.main(["learn", "stages", "missing_learning_project"]) == 1
    assert "kerf status" in capsys.readouterr().out
