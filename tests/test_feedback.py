"""Learn from results (kerf/feedback.py): findings recorded with Kerf's prediction, repeated ones turned into
proposals with their evidence, rules appended to ENGINEERING.md."""
import json

import pytest

from kerf import feedback as FB


def _proj(root, name, use):
    d = root / name
    (d / "out").mkdir(parents=True)
    (d / "project.yaml").write_text("name: X\nparts:\n  arm: {file: parts/arm.py, material: PETG}\nassembly: {root: arm, joints: []}\n")
    (d / "out" / "report.json").write_text(json.dumps({"fingerprint": "abc", "failure_modes": [
        {"part": "arm", "fails_in": "arm_crash", "use": use, "how": "bends", "at": "[1, 2, 3]"}]}))
    return d


def test_record_learn_and_apply(tmp_path):
    a, b = _proj(tmp_path, "quad", 0.9), _proj(tmp_path, "rover", 0.3)
    photo = tmp_path / "snap.jpg"
    photo.write_bytes(b"jpg")
    r = FB.record(str(a), "arm", "broke", "snapped at the root", case="crash", files=[str(photo)])
    assert r["n"] == 1 and r["predicted"]["use"] == 0.9 and r["files"] == ["001_snap.jpg"]
    assert (a / "feedback" / "001_snap.jpg").exists()
    FB.record(str(a), "arm", "broke", "again, same place", case="crash")
    FB.record(str(b), "arm", "broke", "cracked on a kerb", case="crash")
    FB.record(str(b), None, "fit-tight", "bearing seat too tight")
    with pytest.raises(ValueError, match="no part"):
        FB.record(str(a), "wing", "broke", "x")
    with pytest.raises(ValueError, match="--what"):
        FB.record(str(a), "arm", "exploded", "x")
    props = FB.learn(FB.findings(tmp_path))
    kinds = {p["kind"]: p for p in props}
    assert kinds["design fix"]["title"] == "quad: arm broke 2 times" and len(kinds["design fix"]["evidence"]) == 2
    assert "PETG parts broke in 2 projects" in kinds["ENGINEERING.md rule"]["title"]
    assert "rover: arm broke at 30% predicted use" in kinds["model gap"]["title"]              # the cases missed it
    assert "kerf calibrate" in kinds["catalog correction"]["rule"]
    assert "Kerf predicted: arm_crash at 90%" in kinds["design fix"]["evidence"][0] and "001_snap.jpg" in kinds["design fix"]["evidence"][0]
    eng = tmp_path / "ENGINEERING.md"
    eng.write_text("# Engineering\n")
    assert FB.apply_rules(props, eng) == 2 and "## Learned from results" in eng.read_text()
    assert FB.apply_rules(props, eng) == 0                                                       # not twice
    md = FB.write(props, tmp_path / "LEARNED.md").read_text()
    assert md.count("Evidence:") == len(props)
