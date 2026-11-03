import json
from types import SimpleNamespace

import pytest

from kerf import stages


def project(tmp_path, structural=False, moving=False, wiring=False):
    item = SimpleNamespace(spec={"structural": structural})
    data = {"requirements": [{"id": "sizing", "check": "cantilever_stress", "part": "arm"}] if structural else [],
            "assembly": {"joints": [{"name": "pivot", "child": "arm.axis", "range": [-30, 30]}] if moving else []},
            "wiring": [{"id": "lead", "route": [[0, 0, 0]], "length_mm": 100}] if wiring else []}
    (tmp_path / "project.yaml").write_text("contract")
    return SimpleNamespace(dir=tmp_path, data=data, printed={"arm": item}, items={"arm": item},
                           fingerprint=lambda: "geometry")


def evidence(p):
    fp = stages.fingerprint(p)
    report = {"stage_fingerprint": fp, "requirements": [{"id": "sizing", "ok": True, "value": 3}],
              "assembly": {"sweeps": [{"joint": "pivot", "clear": True, "samples": 9}]},
              "electrical": {"routes": [{"id": "lead", "hits": [], "max_routed_mm": 50, "cut_min_mm": 58}]}}
    (p.dir / "out").mkdir(exist_ok=True)
    (p.dir / "out" / "report.json").write_text(json.dumps(report))
    (p.dir / "rough_review.json").write_text(json.dumps({"stage": "rough", "stage_fingerprint": fp,
        "independent": True, "reviewer": "separate-reviewer", "findings": [], "summary": "Rough load paths, travel and routes examined."}))
    return report


def test_grandfather_and_simple_part(tmp_path):
    p = project(tmp_path, structural=True)
    assert stages.status(p)["detail_unlocked"]
    stages.initialize(tmp_path)
    assert not stages.status(p)["detail_unlocked"]
    p.data["requirements"] = []
    p.printed["arm"].spec = {}
    assert stages.status(p)["detail_unlocked"]


def test_risky_project_unlocks_only_with_current_evidence(tmp_path):
    p = project(tmp_path, structural=True, moving=True, wiring=True)
    stages.initialize(tmp_path)
    with pytest.raises(ValueError, match="strength-sizing"):
        stages.require_detail(p)
    evidence(p)
    stages.require_detail(p)
    (tmp_path / "layout.py").write_text("changed layout")
    assert not stages.status(p)["detail_unlocked"]


@pytest.mark.parametrize("change", ["paused", "skipped", "missing_strength", "collision", "missing_route", "self_review"])
def test_asserted_pass_does_not_replace_evidence(tmp_path, change):
    p = project(tmp_path, structural=True, moving=True, wiring=True)
    stages.initialize(tmp_path)
    report = evidence(p)
    if change in {"paused", "skipped"}:
        report["requirements"][0][change] = True
    elif change == "missing_strength":
        report["requirements"] = []
    elif change == "collision":
        report["assembly"]["sweeps"][0]["clear"] = False
    elif change == "missing_route":
        report["electrical"]["routes"] = []
    else:
        rough = json.loads((tmp_path / "rough_review.json").read_text())
        rough["reviewer"] = json.loads((tmp_path / stages.MARKER).read_text())["designer"]
        (tmp_path / "rough_review.json").write_text(json.dumps(rough))
    report["ok"] = True
    assert not stages.status(p, report)["detail_unlocked"]


def test_marker_is_not_overwritten(tmp_path):
    stages.initialize(tmp_path)
    with pytest.raises(FileExistsError):
        stages.initialize(tmp_path)


def test_pipeline_collects_rough_checks_but_blocks_export(tmp_path, monkeypatch):
    from kerf import pipeline, project as P
    from test_redesign_first import _proj
    path = _proj(tmp_path, monkeypatch, 500)
    p = P.load(path)
    stages.initialize(p.dir)
    # A declared load-bearing part requires sizing and rough review.
    yaml = p.dir / "project.yaml"
    yaml.write_text(yaml.read_text().replace("block: {file: parts/block.py}",
                                           "block: {file: parts/block.py, structural: true}"))
    monkeypatch.setattr(pipeline, "first_look", lambda *args: None)
    def forbidden(*args, **kwargs):
        pytest.fail("Detail files were exported while gates were locked")
    monkeypatch.setattr(pipeline.export, "step_assembly", forbidden)
    rough = pipeline.run(path, sweeps=False)
    assert rough["parts"] and not rough["stage_gates"]["detail_unlocked"]
    built = pipeline.run(path, sweeps=False, do_export=True)
    assert not built["ok"]
    assert any("stage gate strength-sizing" in x for x in built["problems"])
    assert not (p.dir / "out" / "assembly.step").exists()
