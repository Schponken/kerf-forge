"""Kerf Studio: param writing keeps the file intact, trials never touch the real project, API basics + safety."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
import yaml

from kerf import studio

YAML = """name: t   # title
params:
  arm_len: {value: 100, min: 60, max: 140, step: 1, label: Arm length}   # pivot to tip
  plain: 7.5   # a bare value
  other: {value: 3, min: 1, max: 5}
parts: {}
"""


def test_write_params_keeps_comments_and_checks_ranges(tmp_path):
    f = tmp_path / "project.yaml"
    f.write_text(YAML)
    assert sorted(studio.write_params(f, {"arm_len": 120, "plain": 8})) == ["arm_len", "plain"]
    txt = f.read_text()
    assert "# pivot to tip" in txt and "# a bare value" in txt and "# title" in txt
    d = yaml.safe_load(txt)
    assert d["params"]["arm_len"]["value"] == 120 and d["params"]["plain"] == 8 and d["params"]["other"]["value"] == 3
    with pytest.raises(ValueError, match="outside its allowed range"):
        studio.write_params(f, {"arm_len": 200})
    with pytest.raises(ValueError, match="unknown param"):
        studio.write_params(f, {"nope": 1})
    assert yaml.safe_load(f.read_text())["params"]["arm_len"]["value"] == 120   # failed writes change nothing


def test_trial_copy_leaves_the_real_project_alone(tmp_path, monkeypatch):
    proj = tmp_path / "projects" / "demo"
    (proj / "parts").mkdir(parents=True)
    (proj / "project.yaml").write_text(YAML)
    (proj / "review.json").write_text("{}")
    (proj / "out").mkdir()
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(studio, "TRIALS", tmp_path / "trials")
    dst = studio.trial_copy("demo", {"arm_len": 90})
    assert yaml.safe_load((dst / "project.yaml").read_text())["params"]["arm_len"]["value"] == 90
    assert yaml.safe_load((proj / "project.yaml").read_text())["params"]["arm_len"]["value"] == 100
    assert not (dst / "out").exists() and not (dst / "review.json").exists()


def test_claude_stream_lines():
    ev = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Researching"},
                                                       {"type": "tool_use", "name": "Bash", "input": {"command": "kerf check x\nmore"}}]}}
    lines = studio._claude_lines(json.dumps(ev))
    assert lines[:2] == ["Researching", "  > Bash: kerf check x"]
    assert json.loads(lines[2][2:]) == {"k": "tool", "name": "Bash", "what": "kerf check x", "phase": "check"}


@pytest.mark.parametrize("tool,inp,phase", [
    ("WebSearch", {"query": "servo arm"}, "research"),
    ("Agent", {"subagent_type": "design-researcher"}, "research"),
    ("Write", {"file_path": "/r/projects/x/DESIGN.md"}, "plan"),
    ("Edit", {"file_path": "/r/projects/x/project.yaml"}, "contract"),
    ("Write", {"file_path": "/r/projects/x/parts/arm.py"}, "parts"),
    ("Agent", {"subagent_type": "part-designer", "description": "arm"}, "parts"),
    ("Bash", {"command": ".venv/bin/kerf build x"}, "build"),
    ("Agent", {"subagent_type": "design-reviewer"}, "review"),
    ("Bash", {"command": "git pull --rebase && git push"}, "ship"),
    ("Read", {"file_path": "/r/CLAUDE.md"}, None)])
def test_design_phase_classifier(tool, inp, phase):
    assert studio._phase(tool, inp) == phase
    assert studio._claude_lines("plain text") == ["plain text"]


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.read()


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_api_pages_and_projects(server):
    code, html = _get(server + "/")
    assert code == 200 and b"Kerf Studio" in html
    code, body = _get(server + "/api/projects")
    names = [p["name"] for p in json.loads(body)["projects"]]
    assert "servo_link" in names
    code, body = _get(server + "/api/project/servo_link")
    d = json.loads(body)
    assert any(p["key"] == "arm_len" for p in d["params"]) and "DESIGN.md" in d["docs"]
    code, body = _get(server + "/files/servo_link/DESIGN.md")
    assert code == 200 and body.startswith(b"#")


def test_api_refuses_bad_input(server):
    for path in ("/files/servo_link/../../CLAUDE.md", "/files/servo_link/..%2F..%2FCLAUDE.md", "/api/project/nope"):
        with pytest.raises(urllib.error.HTTPError) as e:
            _get(server + path)
        assert e.value.code == 404
    assert _post(server + "/api/run", {"project": "nope", "action": "check"})[0] == 404
    assert _post(server + "/api/run", {"project": "servo_link", "action": "rm"})[0] == 400
    assert _post(server + "/api/save", {"project": "servo_link", "values": {"arm_len": 9999}})[0] == 400
    assert _post(server + "/api/new", {"name": "Bad Name!", "description": "x"})[0] == 400
    assert _post(server + "/api/new", {"name": "servo_link", "description": "x"})[0] == 400


def test_progress_events_are_off_by_default_and_ordered_when_on(capsys, monkeypatch):
    from kerf import pipeline, progress
    monkeypatch.delenv("KERF_PROGRESS", raising=False)
    progress.emit("x")
    assert capsys.readouterr().out == ""
    monkeypatch.setenv("KERF_PROGRESS", "1")
    pipeline.run("servo_link", sweeps=False)
    ev = [json.loads(l[2:]) for l in capsys.readouterr().out.splitlines() if l.startswith("@@")]
    stages = [e["stage"] for e in ev if e["k"] == "stage"]
    assert ev[0]["k"] == "start" and ev[-1]["k"] == "done" and stages == ["build", "print", "fit", "requirements"]
    assert {e["id"] for e in ev if e["k"] == "part"} == set(ev[0]["parts"])
    assert [e["id"] for e in ev if e["k"] == "req"] == ev[0]["reqs"]
