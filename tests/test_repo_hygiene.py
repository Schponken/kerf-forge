"""Keep reproducible output/cache files out of Git, retaining documented source assets."""
from pathlib import Path
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def tracked():
    return subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')[:-1]


def test_no_tracked_build_outputs_or_scratch():
    bad = []
    for name in tracked():
        p = Path(name)
        output = len(p.parts) > 2 and p.parts[0] in ('projects', 'evals') and p.parts[2] == 'out'
        cache = any(s in p.parts for s in ('__pycache__', 'node_modules', '.venv', '.cache', '.pytest_cache'))
        scratch = p.suffix in ('.pyc', '.pyo', '.bak', '.orig', '.rej', '.log', '.swp') or p.name.endswith('~')
        if output or cache or scratch:
            bad.append(name)
    assert bad == [], f'Generated/scratch files must stay untracked: {bad}'


def test_usability_evidence_is_only_small_contact_sheets():
    images = [ROOT / f for f in tracked() if f.startswith('docs/usability/') and Path(f).suffix.lower() in
              ('.jpg', '.jpeg', '.png', '.webp')]
    assert all(p.name.endswith(('-contact.jpg', '-contact.webp')) for p in images), images
    total = sum(p.stat().st_size for p in images)
    assert total < 1_000_000, f'{total} bytes: compress contact sheets and put full captures in PR evidence'


def test_ignore_rules_cover_generated_files_but_preserve_sources(tmp_path):
    ignored = ['projects/demo/out/report.json', 'evals/demo/out/assembly.stl', '.cache/parts/a.pkl',
               'tests/__pycache__/a.pyc', 'tools/render/node_modules/a.js', 'notes.bak', 'scratch.log',
               'docs/usability/2099-01-01/before.png', 'docs/usability/2099-01-01/full.jpg',
               'docs/usability/2099-01-01/full.webp']
    kept = ['catalog/models/board.step', 'projects/demo/imports/user.step', 'projects/demo/catalog_deps.json',
            'docs/results/demo.png', 'tools/render/package-lock.json', 'verify/BATCH.json',
            'docs/usability/2099-01-01/studio-contact.jpg']
    # Check the repository policy without installed symlinks, user ignores or Git templates influencing it.
    subprocess.run(['git', 'init', '--quiet', '--template=', str(tmp_path)], check=True)
    (tmp_path / '.gitignore').write_bytes((ROOT / '.gitignore').read_bytes())
    r = subprocess.run(['git', '-c', f'core.excludesFile={os.devnull}', 'check-ignore', '--no-index', '--stdin'], cwd=tmp_path,
                       input='\n'.join(ignored + kept) + '\n', capture_output=True, text=True)
    assert r.returncode in (0, 1), r.stderr
    assert set(r.stdout.splitlines()) == set(ignored)


def test_readme_render_links_still_point_to_tracked_files():
    links = re.findall(r'\]\((docs/results/[^)]+)\)', (ROOT / 'README.md').read_text(encoding='utf-8'))
    names = set(tracked())
    assert links
    assert all(link in names and (ROOT / link).is_file() for link in links), links
