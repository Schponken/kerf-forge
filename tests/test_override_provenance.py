"""Python override variants keep native input identity; saved YAML and output locations stay unchanged."""
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from kerf import cli, gallery, partcache, pipeline, project, studio


BODY = """from build123d import Box, Align
def build(ctx):
    return ctx.finish(Box(ctx.p.w, 4, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)).solid())
"""


def make_project(tmp_path, monkeypatch, *, params=None, derived=None, source=BODY):
    root = tmp_path / "projects/fixture"
    (root / "parts").mkdir(parents=True)
    data = {"name": "Synthetic override", "params": {"w": 8} if params is None else params,
            "parts": {"body": {}}, "assembly": {"root": "body"}}
    if derived is not None:
        data["derived"] = derived
    (root / "project.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    (root / "parts/body.py").write_text(source, encoding="utf-8")
    monkeypatch.setattr(partcache, "DIR", tmp_path / "cache")
    monkeypatch.setattr(project, "PROJECTS", root.parent)
    monkeypatch.setattr(studio, "PROJECTS", root.parent)
    monkeypatch.setattr(gallery, "ROOT", tmp_path)
    monkeypatch.delenv("KERF_NO_CACHE", raising=False)
    monkeypatch.setenv("KERF_NO_ATTRIBUTION", "1")
    return root


def test_variant_report_cannot_match_saved_design_review(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch)
    yaml_before = (root / "project.yaml").read_bytes()
    baseline = pipeline.run(str(root), mode="sketch")
    assert baseline["ok"] and baseline["parts"]["body"]["size_mm"] == [8, 4, 4]
    fp = project.load(str(root)).fingerprint()
    assert baseline["fingerprint"] == fp
    # Synthetic reviewer response only; do not create or approve a project's review.json.
    review = {"verdict": "PASS", "fingerprint": fp, "scores": {"body": {key: 4 for key in cli.INTENT}}}
    old_exists, old_read = Path.exists, Path.read_text
    monkeypatch.setattr(Path, "exists", lambda p: p == root / "review.json" or old_exists(p))
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw: json.dumps(review) if p == root / "review.json" else old_read(p, *a, **kw))
    assert cli.review_status(str(root))["ok"] and not cli.review_status(str(root))["out_stale"]

    variant = pipeline.run(str(root), overrides={"w": 16}, mode="sketch")
    assert variant["ok"] and variant["parts"]["body"]["size_mm"] == [16, 4, 4]
    saved = json.loads((root / "out/report.json").read_text(encoding="utf-8"))
    assert saved["params"]["w"] == 16 and saved["fingerprint"] == variant["fingerprint"] != fp
    assert project.load(str(root)).fingerprint() == fp and (root / "project.yaml").read_bytes() == yaml_before
    assert (root / "out/viewer.html").is_file()
    status = cli.review_status(str(root))
    assert status["ok"] and status["out_stale"]  # Review still covers the saved design, not these variant outputs.
    assert not gallery.collect("fixture", {})["built"]
    assert studio.summary("fixture")["stale"]


def test_type_identity_preserves_signed_zero_and_native_containers(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch, params={"v": 0})
    values = [False, 0, 0.0, -0.0, "0", [0], [0.0], [False], None,
              {"x": 0}, {"x": 0.0}, {0: "v"}, {"0": "v"}, {None: "v"}, {"null": "v"}]
    fingerprints = [project.load(str(root), {"v": v}).fingerprint() for v in values]
    assert len(set(fingerprints)) == len(values)
    assert fingerprints == [project.load(str(root), {"v": v}).fingerprint() for v in values]
    base = project.load(str(root))
    assert fingerprints[2] == base.fingerprint()  # Saved numeric defaults are floats.


@pytest.mark.parametrize("default,value", [(8, 8.0), (True, 1.0), (None, None), ("enum", "enum"),
    ([1, True, "x"], [1, True, "x"]), ({"value": {"a": 1, "b": False}}, {"a": 1, "b": False})])
def test_exact_typed_noop_keeps_default_fingerprint_and_cache_key(tmp_path, monkeypatch, default, value):
    root = make_project(tmp_path, monkeypatch, params={"v": default})
    baseline = project.load(str(root))
    noop = project.load(str(root), {"v": value})
    assert noop.override_signature == b"" and noop.fingerprint() == baseline.fingerprint()
    args = ("body", baseline.items["body"].spec, baseline.params, "Bambu Lab A2L")
    assert partcache.key(baseline, *args) == partcache.key(noop, "body", noop.items["body"].spec, noop.params, args[-1])


def test_input_snapshot_survives_derived_shadowing(tmp_path, monkeypatch):
    source = "from build123d import Box\ndef build(ctx):\n    return ctx.finish(Box(ctx.p.b, 2, 3).solid())\n"
    root = make_project(tmp_path, monkeypatch, params={"a": 1}, derived={"b": "a*2", "a": "1"}, source=source)
    base, variant = project.load(str(root)), project.load(str(root), {"a": 2})
    assert base.params["a"] == variant.params["a"] == 1
    assert base.params["b"] == 2 and variant.params["b"] == 4
    assert base.fingerprint() != variant.fingerprint()
    assert project.build(base).items["body"].shape.volume == pytest.approx(12)
    assert project.build(variant).items["body"].shape.volume == pytest.approx(24)


def test_snapshot_is_input_provenance_not_later_parameter_mutation(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch, params={"v": []})
    original = [1, True]
    loaded = project.load(str(root), {"v": original})
    signature = loaded.override_signature
    original.append("later mutation")
    assert loaded.override_signature == signature
    assert project.load(str(root), {"v": original}).override_signature != signature


def test_override_name_order_and_shared_noncyclic_values_are_deterministic(tmp_path, monkeypatch):
    root = make_project(tmp_path, monkeypatch, params={"a": [], "b": []})
    shared = [1, "x"]
    a = project.load(str(root), {"b": [shared, shared], "a": shared})
    b = project.load(str(root), {"a": [1, "x"], "b": [[1, "x"], [1, "x"]]})
    assert a.override_signature == b.override_signature and a.fingerprint() == b.fingerprint()


@pytest.mark.parametrize("values,widths", [
    ([{"a": 2, "b": 4}, {"b": 4, "a": 2}, {1: 3, "1": 5}, {"1": 5, 1: 3}, {True: 6, "True": 7}], [2, 4, 3, 5, 6]),
    ([True, 1, 1.0], [2, 3, 4]),
])
def test_ordered_and_typed_variants_have_independent_warm_geometry(tmp_path, monkeypatch, values, widths):
    source = """from build123d import Box
def build(ctx):
    v = ctx.p.v
    width = next(iter(v.values())) if isinstance(v, dict) else (2 if type(v) is bool else 3 if type(v) is int else 4)
    return ctx.finish(Box(width, 2, 3).solid())
"""
    root = make_project(tmp_path, monkeypatch, params={"v": 0}, source=source)
    keys = set()
    for value, width in zip(values, widths):
        cold = project.build(project.load(str(root), {"v": value})).items["body"]
        assert cold.error is None and not cold.cached
        assert cold.shape.volume == pytest.approx(width * 6)
        warm = project.build(project.load(str(root), {"v": value})).items["body"]
        assert warm.error is None and warm.cached and warm.shape.volume == pytest.approx(width * 6)
        assert warm.cache_key == cold.cache_key and warm.cache_key not in keys
        keys.add(warm.cache_key)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), [float("nan")], {float("inf"): 1},
    (1, 2), {1, 2}, b"bytes", Fraction(1, 2), np.float64(1), object(), {(1, 2): "tuple key"}])
def test_unsupported_or_nonfinite_input_refuses_before_derived(tmp_path, monkeypatch, value):
    root = make_project(tmp_path, monkeypatch, params={"v": 0}, derived={"canary": "1/0"})
    with pytest.raises(project.ProjectError, match="override 'v': .*finite|override 'v': unsupported"):
        project.load(str(root), {"v": value})
    assert not (root / "out").exists() and not partcache.DIR.exists()


@pytest.mark.parametrize("kind", ["list", "dict"])
def test_cyclic_inputs_fail_clearly(tmp_path, monkeypatch, kind):
    root = make_project(tmp_path, monkeypatch, params={"v": 0}, derived={"canary": "1/0"})
    value = [] if kind == "list" else {}
    if kind == "list":
        value.append(value)
    else:
        value["self"] = value
    with pytest.raises(project.ProjectError, match="override 'v': cyclic override container"):
        project.load(str(root), {"v": value})


def test_variant_reads_extend_existing_catalog_union(tmp_path, monkeypatch):
    source = BODY.replace('    return ctx.finish', '    from kerf import catalog\n    catalog.get("servos.SG90" if ctx.p.w > 8 else "servos.MG996R")\n    return ctx.finish')
    root = make_project(tmp_path, monkeypatch, source=source)
    assert pipeline.run(str(root), mode="sketch")["ok"]
    original = set(json.loads((root / project.DEPS).read_text(encoding="utf-8")))
    assert "servos.MG996R" in original and "servos.SG90" not in original
    report = pipeline.run(str(root), overrides={"w": 16}, mode="sketch")
    union = set(json.loads((root / project.DEPS).read_text(encoding="utf-8")))
    assert report["ok"] and original | {"servos.SG90"} <= union
    assert report["fingerprint"] == project.load(str(root), {"w": 16}).fingerprint()
    assert report["fingerprint"] != project.load(str(root)).fingerprint()
    assert pipeline.run(str(root), mode="sketch")["ok"]
    assert union <= set(json.loads((root / project.DEPS).read_text(encoding="utf-8")))
