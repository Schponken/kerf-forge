"""Parameter saves touch only selected YAML scalar tokens; ambiguous or invalid edits never write."""
import math
import os

import pytest
import yaml

from kerf import studio


def source(tmp_path, text):
    p = tmp_path / "project.yaml"
    p.write_bytes(text.encode("utf-8"))
    os.utime(p, ns=(1_600_000_000_000_000_000, 1_600_000_000_000_000_000))
    return p


def unchanged(p, original, stamp):
    assert p.read_bytes() == original and p.stat().st_mtime_ns == stamp


def test_same_name_outside_params_is_never_edited_even_on_noop(tmp_path):
    text = "metadata:\n  length: 3\nparams:\n  length: 10   # target\nother:\n  length: 4\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    assert studio.write_params(p, {"length": 10}) == []
    unchanged(p, text.encode(), stamp)
    assert studio.write_params(p, {"length": 12}) == ["length"]
    assert p.read_text(encoding="utf-8") == text.replace("length: 10", "length: 12")


@pytest.mark.parametrize("body,old,new", [
    ("  length:\n    min: 1\n    value: 10 # pivot\n    max: 20\n", "value: 10", "value: 12"),
    ("  length: {min: 1, max: 20, value: 10} # pivot\n", "value: 10", "value: 12"),
    ("  'length': {value: 10, min: 1, max: 20}\n", "value: 10", "value: 12"),
    ('  "length": 10\n', '": 10', '": 12'),
    ("  length: &single !!float '10' # unshared tag/anchor\n", "'10'", "'12'"),
])
def test_block_flow_quoted_keys_and_scalar_prefixes(tmp_path, body, old, new):
    text = "# keep me\nparams:\n" + body + "metadata: {value: 10}\n"
    p = source(tmp_path, text)
    assert studio.write_params(p, {"length": 12}) == ["length"]
    assert p.read_text(encoding="utf-8") == text.replace(old, new, 1)


def test_inline_root_params_and_multiple_edits_use_original_spans(tmp_path):
    text = '{metadata: {a: 3}, "params": {"a": 10, b: {min: 1, value: 20, max: 100}}, after: 7}\n'
    p = source(tmp_path, text)
    assert studio.write_params(p, {"a": 12345, "b": 2.5}) == ["a", "b"]
    assert p.read_text(encoding="utf-8") == text.replace('"a": 10', '"a": 12345').replace('value: 20', 'value: 2.5')


def test_unicode_and_crlf_bytes_survive_changed_values(tmp_path):
    text = '\ufeffname: "Démo 🛠" # keep Ω\r\nparams:\r\n  "length-mm": 10 # µm\r\nmetadata: {length: 3}\r\n'
    p = source(tmp_path, text)
    assert studio.write_params(p, {"length-mm": 12}) == ["length-mm"]
    assert p.read_bytes() == text.replace('": 10', '": 12').encode("utf-8")


@pytest.mark.parametrize("number", ["10.000", "1.0e+1", "0xA", "!!float '10'"])
def test_noop_preserves_number_spelling_and_mtime(tmp_path, number):
    text = f"params: {{length: {number}}}\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    assert studio.write_params(p, {"length": 10}) == []
    unchanged(p, text.encode(), stamp)


def test_empty_edit_does_not_write_or_require_params(tmp_path):
    p = source(tmp_path, "name: demo\n")
    stamp = p.stat().st_mtime_ns
    assert studio.write_params(p, {}) == []
    unchanged(p, b"name: demo\n", stamp)


@pytest.mark.parametrize("second,message", [(101, "outside its allowed range"), (0, "outside its allowed range"),
                                          (math.nan, "finite number"), (math.inf, "finite number"),
                                          (-math.inf, "finite number"), ("nope", "convert")])
def test_all_requested_values_validate_before_any_write(tmp_path, second, message):
    text = "params:\n  a: 10\n  b:\n    value: 20\n    min: 1\n    max: 100\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    with pytest.raises(ValueError, match=message):
        studio.write_params(p, {"a": 123, "b": second})
    unchanged(p, text.encode(), stamp)


@pytest.mark.parametrize("text,message", [
    ("params: {length: 10}\nparams: {length: 20}\n", "duplicate key"),
    ("params: {length: 10, 'length': 20}\n", "duplicate key"),
    ("params: {length: {value: 10, value: 20}}\n", "duplicate key"),
    ("params: {length: {value: 10, min: 1, min: 3}}\n", "duplicate key"),
    ("defaults: &d {length: 10}\nparams: {<<: *d}\n", "merged"),
    ("defaults: &d {params: {length: 10}}\n<<: *d\n", "merged"),
    ("defaults: &d {value: 10}\nparams: {length: {<<: *d}}\n", "merged"),
    ("defaults: &d {length: 10}\nparams: *d\n", "aliased/shared"),
    ("params: &p {length: 10}\nmetadata: *p\n", "aliased/shared"),
    ("params: {length: &n 10}\nmetadata: *n\n", "aliased/shared"),
    ("metadata: &n 10\nparams: {length: *n}\n", "aliased/shared"),
    ("params: {length: &p {value: 10}, other: *p}\n", "aliased/shared"),
    ("&root\nparams: {length: 10}\nself: *root\n", "aliased/shared"),
    ("params: {length: {min: 1}}\n", "numeric scalar"),
    ("params: {length: [10]}\n", "numeric scalar"),
    ("params: {length: true}\n", "numeric scalar"),
    ("params: {length: 'ten'}\n", "numeric scalar"),
    ("params: {other: 10}\n", "unknown param"),
])
def test_ambiguous_or_non_numeric_targets_leave_all_bytes_untouched(tmp_path, text, message):
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    with pytest.raises(ValueError, match=message):
        studio.write_params(p, {"length": 12})
    unchanged(p, text.encode(), stamp)


def test_unrelated_recursive_alias_is_bounded_and_unchanged(tmp_path):
    text = "metadata: &m {self: *m}\nparams: {length: 10}\n"
    p = source(tmp_path, text)
    assert studio.write_params(p, {"length": 12}) == ["length"]
    assert p.read_text(encoding="utf-8") == text.replace("length: 10", "length: 12")


def test_failed_precision_verification_cannot_write_a_partial_edit(tmp_path):
    text = "params: {a: 10, length: 1.234567}\n"
    p = source(tmp_path, text)
    stamp = p.stat().st_mtime_ns
    with pytest.raises(ValueError, match="param write check failed"):
        studio.write_params(p, {"a": 11, "length": 1.2345671})
    unchanged(p, text.encode(), stamp)


def test_changed_list_omits_an_unchanged_formatted_value(tmp_path):
    p = source(tmp_path, "params: {a: 10, length: 1.234567}\n")
    assert studio.write_params(p, {"a": 11, "length": 1.2345670001}) == ["a"]
    assert yaml.safe_load(p.read_text(encoding="utf-8"))["params"] == {"a": 11, "length": 1.234567}


def test_large_yaml_integer_can_be_replaced_without_float_overflow(tmp_path):
    p = source(tmp_path, f"params: {{length: {10 ** 400}}}\n")
    assert studio.write_params(p, {"length": 12}) == ["length"]
    assert p.read_bytes() == b"params: {length: 12}\n"
