"""Setup retries use the locked browser; lockfile-only changes refresh the Mac app."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _exe(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/bash\n' + text + '\n', encoding='utf-8')
    path.chmod(0o755)


@pytest.mark.parametrize('cache_name', ['chromium-1', 'chromium-1243'])
def test_setup_repairs_stale_or_interrupted_browser_cache(tmp_path, cache_name):
    shutil.copyfile(ROOT / 'setup.sh', tmp_path / 'setup.sh')
    b = tmp_path / 'bin'
    b.mkdir()
    events = tmp_path / 'events'
    _exe(b / 'uv', 'echo uv >> "$SETUP_TEST_EVENTS"')
    _exe(b / 'node', 'exit 0')
    _exe(b / 'npm', 'echo npm >> "$SETUP_TEST_EVENTS"')
    _exe(b / 'npx', 'echo "npx $*" >> "$SETUP_TEST_EVENTS"')
    _exe(b / 'curl', 'exit 1')
    _exe(b / 'apt-get', 'exit 1')
    _exe(b / 'sudo', 'exit 1')
    _exe(b / 'uname', 'case "$1" in -m) echo x86_64;; *) echo Linux;; esac')
    _exe(tmp_path / '.venv/bin/python', 'exit 0')
    _exe(tmp_path / '.venv/bin/kerf', 'echo ALL OK')
    (tmp_path / 'tools/render').mkdir(parents=True)
    cache = tmp_path / 'browsers'
    (cache / cache_name).mkdir(parents=True)
    env = {**os.environ, 'PATH':str(b) + os.pathsep + os.defpath,
           'PLAYWRIGHT_BROWSERS_PATH':str(cache), 'SETUP_TEST_EVENTS':str(events)}
    for _ in range(2):
        r = subprocess.run(['bash', str(tmp_path / 'setup.sh')], env=env, capture_output=True, text=True, timeout=30)
        assert r.returncode == 0 and 'ALL OK' in r.stdout, r.stdout + r.stderr
    calls = events.read_text(encoding='utf-8').splitlines()
    assert calls.count('npx --no-install playwright install chromium') == 2


@pytest.mark.parametrize('missing',['node','npm'])
def test_missing_node_fails_before_installing_python_dependencies(tmp_path, missing):
    script = tmp_path / 'setup.sh'
    shutil.copyfile(ROOT / 'setup.sh', script)
    b = tmp_path / 'bin'
    b.mkdir()
    _exe(b / ('npm' if missing == 'node' else 'node'),'exit 0')
    for name in ['bash','dirname']:
        (b / name).symlink_to(shutil.which(name))
    r = subprocess.run([str(b / 'bash'), str(script)], env={**os.environ,'PATH':str(b)},
                       capture_output=True, text=True, timeout=10)
    assert r.returncode == 1
    assert 'Node.js and npm' in r.stdout and 'nodejs.org' in r.stdout
    assert not (tmp_path / '.venv').exists()


def _startup(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    for name in ['pyproject.toml','setup.sh','tools/render/package.json','tools/render/package-lock.json']:
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{}', encoding='utf-8')
    _exe(repo / 'setup.sh', 'echo setup >> "$START_TEST_EVENTS"')
    _exe(repo / '.venv/bin/kerf', 'echo "kerf $*" >> "$START_TEST_EVENTS"')
    _exe(repo / 'tools/mac/install_app.sh', 'exit 0')
    script = tmp_path / 'start.sh'
    text = (ROOT / 'tools/mac/start.sh').read_text(encoding='utf-8')
    text = '\n'.join(line for line in text.splitlines() if not line.startswith('export PATH='))
    text = text.replace('STATE="$HOME/Library/Application Support/KerfStudio"', 'STATE="$START_TEST_STATE"')
    script.write_text(text, encoding='utf-8')
    b = tmp_path / 'bin'
    b.mkdir()
    _exe(b / 'git', '''if [ "$1" = status ]; then
 [ "${START_TEST_DIRTY:-0}" = 1 ] && echo ' M project.yaml'
 exit 0
fi
echo pull >> "$START_TEST_EVENTS"
[ "${START_TEST_OFFLINE:-0}" != 1 ]''')
    events = tmp_path / 'events'
    env = {**os.environ,'PATH':str(b)+os.pathsep+os.defpath,'START_TEST_EVENTS':str(events),
           'START_TEST_STATE':str(tmp_path/'state')}
    return repo, script, events, env


def test_lockfile_only_change_reinstalls_and_cached_launch_does_not(tmp_path):
    repo, script, events, env = _startup(tmp_path)
    def run():
        subprocess.run(['bash',str(script),str(repo)],env=env,check=True,capture_output=True,text=True,timeout=15)
    run()
    run()
    assert events.read_text(encoding='utf-8').splitlines().count('setup') == 1
    (repo / 'tools/render/package-lock.json').write_text('{"changed":true}',encoding='utf-8')
    run()
    assert events.read_text(encoding='utf-8').splitlines().count('setup') == 2


@pytest.mark.parametrize('state,expected,pulls', [({'START_TEST_DIRTY':'1'},'Keeping your local changes',0),
                                                 ({'START_TEST_OFFLINE':'1'},'Could not update',1)])
def test_dirty_or_offline_launch_preserves_files_and_still_starts(tmp_path, state, expected, pulls):
    repo, script, events, env = _startup(tmp_path)
    original = 'my local work\n'
    (repo/'project.yaml').write_text(original,encoding='utf-8')
    r = subprocess.run(['bash',str(script),str(repo)],env={**env,**state},capture_output=True,text=True,timeout=15)
    assert r.returncode == 0 and expected in r.stdout
    assert (repo/'project.yaml').read_text(encoding='utf-8') == original
    calls = events.read_text(encoding='utf-8').splitlines()
    assert calls.count('pull') == pulls and any(x.startswith('kerf studio') for x in calls)


def test_installer_and_startup_use_the_same_lockfile_sensitive_stamp(tmp_path):
    for name in ['pyproject.toml','setup.sh','tools/render/package.json','tools/render/package-lock.json']:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}',encoding='utf-8')
    commands=[]
    for name in ['start.sh','install_app.sh']:
        src=(ROOT/'tools/mac'/name).read_text(encoding='utf-8')
        commands.append(re.search(r'shasum pyproject\.toml[^\n]*?\| shasum \| cut -c1-16',src).group())
    def stamps():
        return [subprocess.check_output(['bash','-c',c],cwd=tmp_path,text=True).strip() for c in commands]
    before=stamps();assert before[0] == before[1]
    (tmp_path/'tools/render/package-lock.json').write_text('{"changed":true}',encoding='utf-8')
    after=stamps();assert after[0] == after[1] and after[0] != before[0]
