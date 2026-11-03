"""Cache writes validate and publish one exact geometry serialization."""
import pickle

import pytest
from build123d import Box, persistence

from kerf import partcache


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(partcache, "DIR", tmp_path)
    monkeypatch.delenv("KERF_NO_CACHE", raising=False)
    return tmp_path


def test_store_serializes_once_and_validates_published_bytes(cache, monkeypatch):
    shape = Box(2, 3, 4).solid()
    shape.label = "exact block"
    shape.kerf_notes = ["retained note"]
    serialized, validated = [], []
    serialize, loads = persistence.serialize_shape, pickle.loads

    def record_shape(wrapped):
        data = serialize(wrapped)
        serialized.append(data)
        return data

    def record_loads(data):
        validated.append(data)
        return loads(data)

    monkeypatch.setattr(persistence, "serialize_shape", record_shape)
    monkeypatch.setattr(pickle, "loads", record_loads)
    deps = {"kerf:ctx.py"}
    partcache.store("block", shape, deps)
    blob = (cache / "block.pkl").read_bytes()
    assert len(serialized) == 1
    assert validated == [blob]
    rec = loads(blob)
    assert rec["deps"] == sorted(deps)
    assert rec["deps_hash"] == partcache.deps_hash(deps)
    restored = partcache.lookup("block")
    assert restored.label == shape.label
    assert restored.kerf_notes == shape.kerf_notes
    assert serialize(restored.wrapped) == serialized[0]


@pytest.mark.parametrize("failure", ["serialize", "read_back", "publish"])
def test_failed_store_preserves_existing_entry(cache, monkeypatch, failure):
    shape = Box(2, 3, 4).solid()
    partcache.store("block", shape, set())
    prior = (cache / "block.pkl").read_bytes()

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic cache failure")

    if failure == "serialize":
        monkeypatch.setattr(persistence, "serialize_shape", fail)
    elif failure == "read_back":
        monkeypatch.setattr(pickle, "loads", fail)
    else:
        monkeypatch.setattr(type(cache), "replace", fail)
    partcache.store("block", shape, set())
    assert (cache / "block.pkl").read_bytes() == prior
    if failure != "publish":
        assert list(cache.iterdir()) == [cache / "block.pkl"]


def test_disabled_store_does_not_serialize(cache, monkeypatch):
    monkeypatch.setenv("KERF_NO_CACHE", "1")

    def fail(*args, **kwargs):
        pytest.fail("disabled cache serialized a shape")

    monkeypatch.setattr(persistence, "serialize_shape", fail)
    partcache.store("block", Box(2, 3, 4).solid(), set())
    assert list(cache.iterdir()) == []
