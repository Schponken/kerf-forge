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
