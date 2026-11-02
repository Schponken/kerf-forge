"""Common command mistakes give a next step without a Python traceback."""
import pytest
from kerf import cli


@pytest.mark.parametrize('command', ['check','build','review-pack','review-status','simulate','firmware-check','optimise'])
def test_unknown_project_has_recovery(command, capsys):
    assert cli.main([command, 'definitely_missing_project']) == 1
    out = capsys.readouterr()
    assert 'Traceback' not in out.err + out.out
    assert 'project' in out.out.lower() and 'kerf status' in out.out


def test_review_pack_needs_build(monkeypatch, tmp_path, capsys):
    from kerf import project
    p = tmp_path / 'demo'
    p.mkdir()
    (p / 'project.yaml').write_text('name: Demo\nparts: {}\nassembly: {root: base}\n')
    assert cli.main(['review-pack', str(p)]) == 1
    assert 'kerf build' in capsys.readouterr().out


@pytest.mark.parametrize('value', ['-1','0','65536'])
def test_studio_port_validation(value, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(['studio','--port',value])
    assert e.value.code == 2
    assert '1 to 65535' in capsys.readouterr().err


@pytest.mark.parametrize('name', ['../outside', '/tmp/outside', 'bad name', 'a', 'x'*42])
def test_new_rejects_bad_names_without_creating_files(monkeypatch, tmp_path, capsys, name):
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    assert cli.main(['new', name, 'A title']) == 1
    assert not (tmp_path / 'projects').exists()
    assert 'desk_arm' in capsys.readouterr().out


def test_new_keeps_punctuation_and_newlines_in_the_title(monkeypatch, tmp_path, capsys):
    import yaml
    monkeypatch.setattr(cli, 'ROOT', tmp_path)
    title = 'Spencer’s mount: "camera"\nparts: broken'
    assert cli.main(['new', 'desk_mount', title]) == 0
    data = yaml.safe_load((tmp_path / 'projects/desk_mount/project.yaml').read_text(encoding='utf-8'))
    assert data['name'] == title and data['parts'] == {}
    assert 'starter' in capsys.readouterr().out
