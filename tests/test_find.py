"""Search-first (`kerf find`): sources mocked (no network in tests); REFERENCES.md block, licenses, STL measuring,
Thingiverse token handling, decisions kept across re-runs, and the check warning while a decision is TODO."""
import json
from pathlib import Path

import pytest
from build123d import Box, export_stl

from kerf import find as F


def _fake_printables(items):
    def post(url, payload, headers=None, timeout=30):
        assert url == F.PRINTABLES_API
        if payload["query"].startswith("mutation"):
            return {"data": {"getDownloadLink": {"ok": True, "output": {"link": f"https://files/{payload['variables']['id']}.stl"}}}}
        q = payload["variables"]["q"]
        return {"data": {"searchPrints2": {"items": items.get(q, [])}}}
    return post


ITEM = {"id": "10211", "name": "Pan tilt for MG90S", "slug": "pan-tilt-mg90s", "summary": "metal servo", "likesCount": 47,
        "downloadCount": 602, "license": {"name": "Creative Commons — Attribution", "abbreviation": "CC-BY"},
        "user": {"publicUsername": "maker"},
        "stls": [{"id": "1", "name": "base.stl", "fileSize": 1000}, {"id": "2", "name": "base.3mf", "fileSize": 1000}]}


@pytest.fixture
def stl(tmp_path):
    f = tmp_path / "box.stl"
    export_stl(Box(40, 30, 12), str(f))
    return f


@pytest.fixture
def offline(monkeypatch, stl):
    monkeypatch.delenv("THINGIVERSE_TOKEN", raising=False)
    monkeypatch.setattr(F, "_post_json", _fake_printables({"MG90S pan tilt": [ITEM]}))

    def dl(url, dest, timeout=60):
        dest.write_bytes(stl.read_bytes())
        return dest
    monkeypatch.setattr(F, "_download", dl)


def test_license_use():
    assert F.license_use("CC-BY") == "adapt OK, credit"
    assert F.license_use("CC-BY-NC-SA") == "adapt OK, credit, non-commercial, share-alike"
    assert F.license_use("Creative Commons - Attribution - Share Alike") == "adapt OK, credit, share-alike"
    assert F.license_use("CC-BY-ND") == "print as-is only (no remix)"
    assert F.license_use("SDFL") == "print as-is only (no remix)"
    assert F.license_use("CC0") == "adapt OK, credit"
    assert F.license_use("") == "reference only (no license stated)"


def test_measure_stl(stl, tmp_path):
    assert F.measure_stl(stl) == {"bbox_mm": [40.0, 30.0, 12.0], "watertight": True}
    png = tmp_path / "fake.stl"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
    with pytest.raises(ValueError, match="not a mesh"):
        F.measure_stl(png)


def test_find_writes_block_with_dims_and_decision(offline, tmp_path):
    refs = tmp_path / "REFERENCES.md"
    refs.write_text("# References\n\n## Decisions these support\n- keep me\n")
    r = F.find("MG90S pan tilt", tmp_path, date="2026-10-31")
    s = refs.read_text()
    assert "- keep me" in s and F.SECTION in s
    assert '### `kerf find "MG90S pan tilt"` (2026-10-31)' in s
    row = next(l for l in s.splitlines() if "Pan tilt for MG90S" in l)
    assert "https://www.printables.com/model/10211-pan-tilt-mg90s" in row and "CC-BY" in row and "adapt OK" in row
    assert "base.stl: 40 x 30 x 12 mm" in row and "base.3mf" not in row       # only STLs are measured
    assert "THINGIVERSE_TOKEN" in s and "site:makerworld.com MG90S pan tilt" in s and "mcmaster.com" in s
    assert r["skipped"].keys() == {"Thingiverse"}
    assert F.pending_decisions(tmp_path) == ["MG90S pan tilt"]


def test_rerun_replaces_block_and_keeps_decision(offline, tmp_path):
    F.find("MG90S pan tilt", tmp_path, date="2026-10-30")
    refs = tmp_path / "REFERENCES.md"
    s = refs.read_text().replace(F.TODO + " —", "Decision: adapt the base (CC-BY, credit maker) —")
    refs.write_text(s)
    F.find("MG90S pan tilt", tmp_path, date="2026-10-31")
    s = refs.read_text()
    assert s.count('kerf find "MG90S pan tilt"') == 1 and "(2026-10-31)" in s
    assert "Decision: adapt the base (CC-BY, credit maker)" in s and F.TODO not in s
    assert F.pending_decisions(tmp_path) == []


def test_add_hand_found_candidate(offline, tmp_path):
    F.find("MG90S pan tilt", tmp_path)
    F.add(tmp_path / "REFERENCES.md", "MG90S pan tilt", {"source": "MakerWorld", "title": "Tilt head",
                                                         "url": "https://makerworld.com/en/models/1", "license": "CC-BY-NC",
                                                         "dims": "52 x 30 x 20 mm (page)"})
    s = (tmp_path / "REFERENCES.md").read_text()
    row = next(l for l in s.splitlines() if "Tilt head" in l)
    assert "MakerWorld" in row and "non-commercial" in row and "52 x 30 x 20" in row
    with pytest.raises(ValueError, match="run kerf find first"):
        F.add(tmp_path / "REFERENCES.md", "other", {"title": "x", "url": "y"})


def test_long_query_falls_back_to_word_windows(monkeypatch):
    calls = []

    def post(url, payload, headers=None, timeout=30):
        calls.append(payload["variables"]["q"])
        return {"data": {"searchPrints2": {"items": [ITEM] if payload["variables"]["q"] == "pan tilt bracket" else []}}}
    monkeypatch.setattr(F, "_post_json", post)
    got = F.printables("MG90S servo pan tilt bracket", 5)
    assert calls[0] == "MG90S servo pan tilt bracket" and "pan tilt bracket" in calls and len(calls) <= 4
    assert len(got) == 1


def test_thingiverse_with_token(monkeypatch):
    seen = []

    def get(url, headers=None, timeout=30):
        seen.append((url, headers))
        if "/search/" in url:
            return {"hits": [{"id": 7, "name": "Servo bracket", "public_url": "https://www.thingiverse.com/thing:7",
                              "creator": {"name": "bob"}, "like_count": 3}]}
        return {"license": "Creative Commons - Attribution"}
    monkeypatch.setattr(F, "_get_json", get)
    out = F.thingiverse("servo bracket", 3, token="tok")
    assert out[0]["url"] == "https://www.thingiverse.com/thing:7" and out[0]["use"] == "adapt OK, credit"
    assert seen[0][1]["Authorization"] == "Bearer tok" and "servo%20bracket" in seen[0][0]
    with pytest.raises(PermissionError, match="THINGIVERSE_TOKEN"):
        monkeypatch.delenv("THINGIVERSE_TOKEN", raising=False)
        F.thingiverse("x")


def test_check_warns_while_decision_todo(offline, tmp_path):
    import textwrap
    from kerf import pipeline
    d = tmp_path / "p"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent("""
        name: t
        parts: {plate: {file: parts/plate.py, material: PETG}}
        assembly: {root: plate}
    """))
    (d / "parts" / "plate.py").write_text("from build123d import *\ndef build(ctx):\n    return ctx.finish(Box(20, 20, 3))\n")
    F.find("MG90S pan tilt", d)
    rep = pipeline.run(str(d), sweeps=False)
    assert any("no reuse decision" in w for w in rep["warnings"])
