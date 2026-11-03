"""Finite scalar parameter contract, without geometry or changing enum/list/bounds semantics."""
from fractions import Fraction

import numpy as np
import pytest
import yaml

from kerf import pipeline, project as P


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), np.float32("nan"), np.float32("inf")])
@pytest.mark.parametrize("boxed", [False, True])
def test_base_nonfinite_real_scalar_names_the_parameter(value, boxed):
    spec = {"value": value, "min": 0, "max": 20} if boxed else value
    with pytest.raises(P.ProjectError, match="param 'span'.*finite"):
        P.param_values({"params": {"span": spec}})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), np.float32("nan"), np.float64("inf")])
def test_nonfinite_override_is_rejected_before_derived_math(value):
    with pytest.raises(P.ProjectError, match="override 'span'.*finite"):
        P.param_values({"params": {"span": 2}, "derived": {"later": "1/0"}}, {"span": value})


@pytest.mark.parametrize("expr", ["1e309", "-1e309", "1e309 - 1e309", "1e308 * 1e308", "'nan'", "'inf'"])
def test_nonfinite_derived_result_names_expression(expr):
    with pytest.raises(P.ProjectError, match="derived 'reach'.*finite") as exc:
        P.param_values({"params": {}, "derived": {"reach": expr, "later": "1/0"}})
    assert repr(expr) in str(exc.value)


def test_base_and_derived_integer_float_overflow_have_context():
    with pytest.raises(P.ProjectError, match="param 'span'.*finite float"):
        P.param_values({"params": {"span": 10**400}})
    with pytest.raises(P.ProjectError, match="derived 'reach'.*10\\*\\*400"):
        P.param_values({"derived": {"reach": "10**400"}})


def test_valid_mixed_values_and_boolean_semantics_are_unchanged():
    vector = [1, 2, 3]
    data = {"params": {"count": 3, "fraction": 0.25, "enabled": True, "disabled": False,
                       "material": "PETG", "literal": "nan", "numeric_text": "1e309", "vector": vector,
                       "choice": {"value": "left", "label": "Side"}},
            "derived": {"double": "count * 2", "later": "double + 1", "flag": "True"}}
    result = P.param_values(data)
    assert result == {"count": 3.0, "fraction": .25, "enabled": 1.0, "disabled": 0.0, "material": "PETG",
                      "literal": "nan", "numeric_text": "1e309", "vector": [1, 2, 3], "choice": "left",
                      "double": 6.0, "later": 7.0, "flag": 1.0}
    assert type(result["enabled"]) is float and type(result["count"]) is float
    assert result["vector"] is vector and data["params"]["enabled"] is True
    assert P.param_values({}) == {}


@pytest.mark.parametrize("value", [0, 10**400, Fraction(1, 3), Fraction(10**400, 3), np.float32(2),
                                 True, False, "nan", "inf", "1e309", "left", [1, 2, 3]])
def test_valid_overrides_retain_their_type_and_value(value):
    result = P.param_values({"params": {"x": 1}}, {"x": value})
    assert result["x"] is value


def test_bounds_remain_ui_metadata_and_finite_values_are_not_clamped():
    data = {"params": {"span": {"value": 30, "min": 1, "max": 20, "step": 1}}}
    assert P.param_values(data)["span"] == 30
    assert P.param_values(data, {"span": -100})["span"] == -100
    with pytest.raises(P.ProjectError, match="unknown param override 'missing'"):
        P.param_values(data, {"missing": 1})


@pytest.mark.parametrize("params,derived,overrides,where", [
    ({"span": float("nan")}, {}, None, "param 'span'"),
    ({"span": {"value": float("inf")}}, {}, None, "param 'span'"),
    ({"span": 2}, {}, {"span": -float("inf")}, "override 'span'"),
    ({"span": 2}, {"reach": "1e309"}, None, "derived 'reach'"),
    ({"span": 2}, {"reach": "10**400"}, None, "derived 'reach'"),
])
def test_yaml_load_rejects_before_geometry(tmp_path, monkeypatch, params, derived, overrides, where):
    data = {"name": "finite parameter fixture", "parts": {"box": {"file": "must_not_build.py"}},
            "assembly": {"root": "box", "joints": []}, "params": params, "derived": derived}
    (tmp_path / "project.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    def must_not_build(*args, **kwargs):
        raise AssertionError("geometry must not start for invalid scalar parameters")
    monkeypatch.setattr(P, "build", must_not_build)
    with pytest.raises(P.ProjectError, match=where):
        pipeline.run(str(tmp_path), sweeps=False, overrides=overrides)


def test_finite_override_feeds_derived_in_order():
    data = {"params": {"span": 2}, "derived": {"double": "span * 2", "reach": "double + 5"}}
    assert P.param_values(data, {"span": 3}) == {"span": 3, "double": 6.0, "reach": 11.0}
    with pytest.raises(P.ProjectError, match="derived 'double'.*finite"):
        P.param_values(data, {"span": 1e308})
