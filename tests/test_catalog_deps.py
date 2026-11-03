"""A project's fingerprint covers only the catalog entries its build read (catalog_deps.json), so an edit to an
unrelated catalog entry by another session does not invalidate its review, while an edit to an entry it uses does."""
import json

from kerf import catalog, pipeline, project as P
from test_electrical import _write_project, SERVO_YAML


def _cat_copy(tmp_path, monkeypatch, edit=None):
    data = json.loads(catalog.CATALOG.read_text())
    if edit:
        edit(data)
    f = tmp_path / f"cat_{len(list(tmp_path.glob('cat_*')))}.json"
    f.write_text(json.dumps(data))
    monkeypatch.setattr(catalog, "CATALOG", f)
    catalog.load.cache_clear()


def test_fingerprint_follows_used_entries_only(tmp_path, monkeypatch):
    y = SERVO_YAML.format(servos="  s0: {catalog: servos.MG996R, proxy: box, size: [40, 20, 37]}", joints="j0: [0, 0, 40]",
                          tree="    - {parent: psu.j0, child: s0.bottom}",
                          wires="  - {id: w0, from: psu, to: s0, v: 5.0, gauge: 20, length_mm: 400, color: red/black}")
    d = _write_project(tmp_path / "fp", y, {})
    try:
        _cat_copy(tmp_path, monkeypatch)
        before = P.load(str(d)).fingerprint()                 # no deps file yet: whole catalog
        rep = pipeline.run(str(d), sweeps=False)
        deps = json.loads((d / "catalog_deps.json").read_text())
        assert "servos.MG996R" in deps and "electronics.supplies.meanwell_gst60a05" in deps and "wire.awg" in deps
        fp = rep["fingerprint"]
        assert fp == P.load(str(d)).fingerprint() and fp != before
        # an unrelated entry changes: same fingerprint
        _cat_copy(tmp_path, monkeypatch, lambda c: c["servos"]["SG90"].update(weight_g=99))
        assert P.load(str(d)).fingerprint() == fp
        # an entry the project uses changes: new fingerprint
        _cat_copy(tmp_path, monkeypatch, lambda c: c["servos"]["MG996R"].update(stall_current_a=2.6))
        assert P.load(str(d)).fingerprint() != fp
    finally:
        catalog.load.cache_clear()


def _small_project(tmp_path, monkeypatch):
    from kerf import calibrate
    d = _write_project(tmp_path / 'small', 'name: Small\nparts: {}\nassembly: {root: none}\n', {})
    f = tmp_path / 'hardware.json'
    f.write_text(json.dumps({'servos': {'used': {'weight_g': 10}, 'unused': {'weight_g': 20}}}), encoding='utf-8')
    monkeypatch.setattr(catalog, 'CATALOG', f)
    monkeypatch.setattr(calibrate, 'PRINTERS', tmp_path / 'printers')
    (d / P.DEPS).write_text('["servos.used"]', encoding='utf-8')
    return P.load(str(d)), f


def test_live_catalog_edits_need_no_manual_cache_reset(tmp_path, monkeypatch):
    import os
    proj, f = _small_project(tmp_path, monkeypatch)
    first = catalog.load()
    assert catalog.load() is first             # unchanged reads still reuse the parsed data
    fp = proj.fingerprint()
    data = json.loads(f.read_text(encoding='utf-8'))
    stat = f.stat()
    data['servos']['unused']['weight_g'] = 21
    f.write_text(json.dumps(data), encoding='utf-8')
    os.utime(f, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # same size and mtime; ctime still notices the edit
    assert proj.fingerprint() == fp
    data['servos']['used']['weight_g'] = 11
    f.write_text(json.dumps(data), encoding='utf-8')
    assert proj.fingerprint() != fp
    assert catalog.get('servos.used')['weight_g'] == 11
    # Reordering/reformatting JSON is not a design change.
    changed = proj.fingerprint()
    f.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
    assert proj.fingerprint() == changed
    del data['servos']['used']
    f.write_text(json.dumps(data), encoding='utf-8')
    assert proj.fingerprint() != changed       # deletion of a used entry also invalidates


def test_atomic_catalog_replacement_refreshes_cache(tmp_path, monkeypatch):
    import os
    proj, f = _small_project(tmp_path, monkeypatch)
    fp = proj.fingerprint()
    stat = f.stat()
    replacement = f.with_suffix('.new')
    replacement.write_text(f.read_text(encoding='utf-8').replace('10', '11'), encoding='utf-8')
    os.utime(replacement, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    replacement.replace(f)
    assert proj.fingerprint() != fp


def test_corrupt_manifest_is_conservative_and_repairable(tmp_path, monkeypatch):
    proj, f = _small_project(tmp_path, monkeypatch)
    for broken in ['{', '{}', '[null]', '[""]', 'null', '"servos.used"']:
        (proj.dir / P.DEPS).write_text(broken, encoding='utf-8')
        before = proj.fingerprint()
        data = json.loads(f.read_text(encoding='utf-8'))
        data['servos']['unused']['weight_g'] += 1
        f.write_text(json.dumps(data), encoding='utf-8')
        assert proj.fingerprint() != before   # unknown dependency scope covers the entire catalog
        catalog.track()
        catalog.get('servos.used')
        P.record_deps(proj)
        assert json.loads((proj.dir / P.DEPS).read_text(encoding='utf-8')) == ['servos.used']


def test_quick_recording_preserves_full_build_dependencies(tmp_path, monkeypatch):
    proj, f = _small_project(tmp_path, monkeypatch)
    (proj.dir / P.DEPS).write_text('["servos.used", "servos.unused"]', encoding='utf-8')
    catalog.track()
    catalog.get('servos.used')
    P.record_deps(proj)
    assert set(json.loads((proj.dir / P.DEPS).read_text(encoding='utf-8'))) == {'servos.unused', 'servos.used'}


def test_cached_part_hits_record_catalog_dependencies(tmp_path, monkeypatch):
    from kerf import partcache
    from test_partcache import YAML, BLOCK, PLATE
    monkeypatch.setattr(partcache, 'DIR', tmp_path / 'cache')
    monkeypatch.delenv('KERF_NO_CACHE', raising=False)
    d = _write_project(tmp_path / 'bolt', YAML, {'block': BLOCK, 'plate': PLATE})
    (d / 'parts' / 'helper.py').write_text('R = 3.0\n', encoding='utf-8')
    catalog.track()
    cold = P.build(P.load(str(d)))
    assert not {i.id: i.error for i in cold.items.values() if i.error}
    fresh = catalog.used()
    assert 'screws.M3' in fresh and fresh
    catalog.track()
    warm = P.build(P.load(str(d)))
    assert all(it.cached for it in warm.printed.values())
    assert fresh <= catalog.used()


def test_local_design_inputs_still_invalidate(tmp_path, monkeypatch):
    from kerf import calibrate
    proj, f = _small_project(tmp_path, monkeypatch)
    paths = [proj.dir / 'project.yaml', proj.dir / 'parts' / 'base.py',
             proj.dir / 'meshes' / 'shell.stl', proj.dir / 'imports' / 'mount.step',
             calibrate.profile_path(calibrate.DEFAULT_PRINTER)]
    for path in paths:
        before = proj.fingerprint()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((path.read_bytes() if path.exists() else b'') + b'\n# changed')
        assert proj.fingerprint() != before, path
