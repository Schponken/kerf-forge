"""kerf gallery: one page from the projects' builds (status chips, numbers, renders, viewer, BOM)."""
import json

from kerf import gallery


def test_page_from_collected_projects(tmp_path):
    p = {"name": "demo", "title": "Demo rig", "description": "A <test> rig.", "built": True, "ok": True, "review": True,
         "review_why": "", "eval": False, "eval_fail": ["need >= 3 legs"], "fingerprint": "x", "parts": ["a", "b"],
         "purchased": 3, "mass_g": 188, "plates": 1, "bom_total": 77.83,
         "requirements": [{"id": "power", "check": "power_budget", "ok": True, "value": 0.417, "limit": 1.0, "skipped": False},
                          {"id": "reach", "check": "distance", "ok": False, "value": 222.0, "limit": [230, 300], "skipped": False}],
         "bom": [{"type": "printed", "item": "a", "qty": 1, "spec": "PETG", "buy": "https://x.example/petg", "total_usd": 1.39}],
         "img_assembly": True, "viewer": True}
    nb = {**p, "name": "nb", "title": "Not built", "built": False, "ok": False, "review": False, "review_why": "no review.json",
          "eval": None, "requirements": [], "bom": [], "bom_total": None, "img_assembly": False, "viewer": False}
    h = gallery.page([p, nb], "2026-10-31 03:00 UTC")
    assert h.startswith("<title>Kerf Forge Gallery</title>") and "<!doctype" not in h.lower()
    assert "A &lt;test&gt; rig." in h                                   # text is escaped
    assert '<a class="btn" href="demo/viewer.html"' in h and 'src="demo/assembly.jpg"' in h
    assert "$77.83" in h and "need &gt;= 3 legs" in h and "230–300" in h
    assert '<li class="bad"><span class="mono">reach</span>' in h
    assert "not built" in h and "no review.json" in h


def test_build_real_project_tree(tmp_path):
    """Builds the gallery files for the seed project (a stale or missing build is shown as not built, never fails)."""
    r = gallery.build(["servo_link"], out=tmp_path / "g", when="t")
    idx = (tmp_path / "g" / "index.html").read_text()
    assert "Servo test rig" in idx
    files = json.loads((tmp_path / "g" / "files.json").read_text())
    assert files == r["files"] and all((tmp_path / "g" / k).exists() for k in files)
