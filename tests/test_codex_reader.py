"""Chunk boundaries and limits of the read-only Codex JSON-lines connection."""
import io
import json
import time
from types import SimpleNamespace

import pytest

from kerf import codex_work


def reader_for(monkeypatch, payload, chunk_size=65536):
    stream = io.BytesIO(payload)
    proc = SimpleNamespace(stdin=io.BytesIO(), stdout=SimpleNamespace(fileno=lambda: 42))
    selector = SimpleNamespace(register=lambda *args: None, select=lambda timeout: [True])
    monkeypatch.setattr(codex_work.subprocess, "Popen", lambda *args, **kwargs: proc)
    monkeypatch.setattr(codex_work.selectors, "DefaultSelector", lambda: selector)
    monkeypatch.setattr(codex_work.os, "read", lambda fd, limit: stream.read(min(chunk_size, limit)))
    return codex_work._Reader(["fake-reader"], time.monotonic() + 10)


@pytest.mark.parametrize("chunk_size", [1, 7, 65536])
def test_chunked_utf8_notifications_and_buffered_next_response(monkeypatch, chunk_size):
    messages = [
        {"method": "notification", "params": {"text": "ignored"}},
        {"id": 99, "result": {"wrong": "request"}},
        {"id": 1, "result": {"data": [{"id": "chat", "name": "Hinge — café"}]}},
        {"method": "notification", "params": {}},
        {"id": 2, "result": {"data": [{"items": [{"type": "agentMessage", "text": "Checked ✓"}]}]}},
    ]
    payload = b"".join((json.dumps(message, ensure_ascii=False) + "\n").encode() for message in messages)
    reader = reader_for(monkeypatch, payload, chunk_size)
    assert reader.call("thread/list", {"limit": 1}) == messages[2]["result"]
    assert reader.call("thread/turns/list", {"threadId": "chat"}) == messages[4]["result"]
    requests = [json.loads(line) for line in reader.proc.stdin.getvalue().splitlines()]
    assert requests == [{"id": 1, "method": "thread/list", "params": {"limit": 1}},
                        {"id": 2, "method": "thread/turns/list", "params": {"threadId": "chat"}}]
    assert not reader.buffer


@pytest.mark.parametrize("extra", [0, 1])
def test_response_size_limit_is_unchanged(monkeypatch, extra):
    envelope = b'{"id":1,"result":{"text":"' + b'"}}\n'
    text = "x" * (4 * 1024 * 1024 - len(envelope) + extra)
    payload = b'{"id":1,"result":{"text":"' + text.encode() + b'"}}\n'
    reader = reader_for(monkeypatch, payload)
    if extra:
        with pytest.raises(RuntimeError, match="exceeds the viewer limit"):
            reader.call("thread/list", {})
    else:
        assert reader.call("thread/list", {}) == {"text": text}


@pytest.mark.parametrize("payload,error,match", [
    (b'{"id":1,"error":{"message":"private detail"}}\n', RuntimeError, "could not read session metadata"),
    (b'{"id":1,broken}\n', ValueError, None),
    (b'{"id":1', RuntimeError, "reader is unavailable"),
])
def test_protocol_failures_remain_failures(monkeypatch, payload, error, match):
    reader = reader_for(monkeypatch, payload, chunk_size=3)
    with pytest.raises(error, match=match):
        reader.call("thread/list", {})


def test_timeout_and_read_only_method_fence(monkeypatch):
    reader = reader_for(monkeypatch, b'')
    with pytest.raises(ValueError, match="only reads session metadata"):
        reader.call("turn/start", {})
    assert reader.proc.stdin.getvalue() == b'' and reader.seq == 0
    reader.deadline = 0
    with pytest.raises(TimeoutError, match="reader timed out"):
        reader.call("thread/list", {})
