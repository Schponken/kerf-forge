"""Repo-scoped, read-only Codex session discovery and honest source freshness."""
import json
import subprocess

import pytest

from kerf import codex_work, studio


@pytest.fixture(autouse=True)
def bundle_executable(tmp_path, monkeypatch):
    # Do not fall back to the host's real app bundle; tests isolate PATH separately.
    cli = tmp_path / "ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
    cli.parent.mkdir(parents=True)
    monkeypatch.setattr(codex_work, "_MACOS_BUNDLE_EXECUTABLE", cli)
    return cli


def test_executable_prefers_path_over_macos_bundle(tmp_path, monkeypatch, bundle_executable):
    cli = tmp_path / "bin/codex"
    cli.parent.mkdir()
    cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli.chmod(0o755)
    bundle_executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    bundle_executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(cli.parent))
    monkeypatch.setattr(codex_work.platform, "system", lambda: "Darwin")
    assert codex_work._executable() == str(cli)


@pytest.mark.parametrize("platform,found", [("Darwin", True), ("Linux", False), ("Windows", False)])
def test_executable_bundle_is_macos_only(tmp_path, monkeypatch, bundle_executable, platform, found):
    bundle_executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    bundle_executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(codex_work.platform, "system", lambda: platform)
    assert codex_work._executable() == (str(bundle_executable) if found else None)


@pytest.mark.parametrize("kind", ["missing", "nonexecutable", "directory", "broken-symlink"])
def test_unusable_bundle_reports_unavailable_without_launching(tmp_path, monkeypatch, bundle_executable, kind):
    if kind == "nonexecutable":
        bundle_executable.write_text("not executable", encoding="utf-8")
        bundle_executable.chmod(0o644)
    elif kind == "directory":
        bundle_executable.mkdir()
    elif kind == "broken-symlink":
        bundle_executable.symlink_to(tmp_path / "missing")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(codex_work.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(codex_work, "_Reader", lambda *args: pytest.fail("unavailable executable must not launch"))
    result = codex_work._collect(tmp_path)
    assert result["sessions"] == []
    assert result["source"]["state"] == "unavailable"
    assert "PATH" in result["source"]["detail"] and "Shared Codex claims still appear" in result["source"]["detail"]


def test_repository_matching_uses_origin_or_checkout_not_title(tmp_path, monkeypatch):
    root = tmp_path / "kerf"
    root.mkdir()
    origin = "github.com/Schponken/kerf-forge"
    assert codex_work._origin("git@github.com:Schponken/kerf-forge.git") == origin
    assert codex_work._origin("https://github.com/Schponken/kerf-forge.git") == origin
    monkeypatch.setattr(codex_work, "_repo_origin", lambda cwd: "github.com/someone/else")
    assert codex_work._belongs({"cwd": str(root / "projects/demo")}, root, origin)
    assert codex_work._belongs({"gitInfo": {"originUrl": "git@github.com:Schponken/kerf-forge.git"}}, root, origin)
    assert not codex_work._belongs({"name": "kerf-forge", "cwd": str(tmp_path / "other")}, root, origin)
    assert not codex_work._belongs({"gitInfo": {"originUrl": "https://github.com/Schponken/kerf-forge-copy"}}, root, origin)


@pytest.mark.parametrize("status,state,label", [
    ({"type": "active", "activeFlags": []}, "working", "Working"),
    ({"type": "active", "activeFlags": ["waitingOnApproval"]}, "waiting", "Needs approval"),
    ({"type": "active", "activeFlags": ["waitingOnUserInput"]}, "waiting", "Needs your answer"),
    ({"type": "systemError"}, "blocked", "Session error"),
    ({"type": "notLoaded"}, "idle", "Not loaded"),
])
def test_saved_history_never_claims_live_status(status, state, label):
    thread = {"id": "demo", "name": "Make the gripper", "status": status}
    observed = codex_work._record(thread, {}, live=True)
    assert (observed["state"], observed["status_label"]) == (state, label)
    saved = codex_work._record(thread, {}, live=False)
    assert saved["state"] == "idle" and "unavailable" in saved["status_label"]


def test_summary_uses_public_activity_and_explicit_checkboxes():
    thread = {"id": "demo", "name": "Keep this exact title", "status": {"type": "idle"}}
    turn = {"status": "completed", "items": [
        {"type": "agentMessage", "text": "Checking the fit."},
        {"type": "reasoning", "text": "private reasoning"},
        {"type": "commandExecution", "command": "secret command", "aggregatedOutput": "secret output"},
        {"type": "plan", "text": "- [x] Inspect\n- [ ] Validate\nNot a counted step"},
    ]}
    result = codex_work._record(thread, turn, live=True)
    assert result["title"] == thread["name"]
    assert result["activity"] == "Last activity: ran a command"
    assert result["steps"] == [{"title": "Inspect", "status": "completed"}, {"title": "Validate", "status": "pending"}]
    assert "secret" not in json.dumps(result) and "private reasoning" not in json.dumps(result)
    thread["status"] = {"type": "active", "activeFlags": []}
    turn["items"] = [{"type": "commandExecution", "status": "inProgress"}]
    assert codex_work._record(thread, turn, live=True)["activity"] == "Running a command"
    assert codex_work._record(thread, turn, live=False)["activity"] == "Last activity: ran a command"


@pytest.mark.parametrize("discovery", ["path", "macos-bundle"])
def test_protocol_falls_back_to_saved_history_and_only_reads(tmp_path, monkeypatch, discovery):
    root = tmp_path / "repo"
    root.mkdir()
    calls = tmp_path / "calls.jsonl"
    cli = tmp_path / "codex"
    cli.write_text("""#!/usr/bin/env python3
import json, sys
from pathlib import Path
if 'proxy' in sys.argv:
    raise SystemExit(1)
for line in sys.stdin:
    request = json.loads(line)
    method = request['method']
    with Path(CALLS).open('a') as f:
        f.write(json.dumps(request)+'\\n')
    if method == 'initialized':
        continue
    if method == 'initialize':
        result = {}
    elif method == 'thread/list':
        result = {'data': [{'id':'ours','name':'Work on Kerf','cwd':ROOT,'status':{'type':'notLoaded'}},
                           {'id':'other','name':'Unrelated private chat','cwd':'/nonexistent/other'}], 'nextCursor':None}
    elif method == 'thread/turns/list':
        assert request['params']['threadId'] == 'ours'
        result = {'data':[{'status':'completed','items':[{'type':'agentMessage','text':'Tests passed.'}]}]}
    else:
        raise AssertionError('not a read-only method: '+method)
    print(json.dumps({'id':request['id'],'result':result}),flush=True)
""".replace("CALLS", repr(str(calls))).replace("ROOT", repr(str(root))), encoding="utf-8")
    cli.chmod(0o755)
    monkeypatch.setattr(codex_work.shutil, "which", lambda name: str(cli) if discovery == "path" else None)
    monkeypatch.setattr(codex_work.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(codex_work, "_MACOS_BUNDLE_EXECUTABLE", cli)
    result = codex_work._collect(root)
    assert [s["id"] for s in result["sessions"]] == ["ours"]
    assert result["sessions"][0]["activity"] == "Tests passed."
    assert result["sessions"][0]["state"] == "idle"
    assert result["source"]["state"] == "partial"
    assert "Saved" in result["source"]["detail"]
    assert {json.loads(line)["method"] for line in calls.read_text().splitlines()} == {
        "initialize", "initialized", "thread/list", "thread/turns/list"}


def test_failed_refresh_retains_stale_snapshot_and_throttles_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(codex_work, "_CACHE", {})
    clock = [100.0]
    monkeypatch.setattr(codex_work.time, "time", lambda: clock[0])
    calls = []

    def collect(root):
        calls.append(root)
        if len(calls) > 1:
            raise TimeoutError()
        return {"sessions": [{"id": "demo", "state": "working"}], "source": {"name": "Codex", "updated_at": 100}}

    monkeypatch.setattr(codex_work, "_collect", collect)
    assert codex_work.snapshot(tmp_path)["sessions"][0]["state"] == "working"
    clock[0] = 131
    result = codex_work.snapshot(tmp_path)
    assert result["sessions"][0]["state"] == "stale"
    assert result["source"]["updated_at"] == 100 and result["source"]["state"] == "unavailable"
    codex_work.snapshot(tmp_path)
    assert len(calls) == 2


def test_work_combines_main_claims_codex_and_local_jobs(monkeypatch):
    from kerf import live
    monkeypatch.setattr(studio, "LIVE", {"work": None, "work_key": None, "last_fetch": 100, "fetch_error": None})
    monkeypatch.setattr(studio, "_live_thread", lambda: None)
    monkeypatch.setattr(studio, "_git", lambda *args: "" if args[0] == "symbolic-ref" else "main-sha")
    monkeypatch.setattr(studio, "JOBS", {})
    seen = []
    monkeypatch.setattr(live, "work_data", lambda root, ref, **kw: seen.append(ref) or {"cards": [], "feed": []})
    def snapshot(root):
        studio.LIVE["work"] = None  # The fetch thread may invalidate the cache while Codex is being read.
        return {"sessions": [{"id": "codex-thread", "provider": "Codex", "title": "Work page", "state": "working"}],
                "source": {"name": "Codex", "state": "ok"}}
    monkeypatch.setattr(codex_work, "snapshot", snapshot)
    result = studio.work()
    assert seen == ["origin/main"]
    assert result["items"][0]["provider"] == "Codex" and result["counts"]["running"] == 1
    assert {s["name"] for s in result["sources"]} == {"Codex", "Shared claims", "Studio jobs"}


def test_claim_identity_and_activity_are_explicit(tmp_path, monkeypatch):
    from kerf.live import _claims_mod
    claims = _claims_mod()
    for key in ("CODEX_THREAD_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDECODE"):
        monkeypatch.delenv(key, raising=False)
    assert claims.session_source() == {}
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-1")
    assert claims.session_source() == {"provider": "Codex", "thread_id": "thread-1"}
    monkeypatch.setenv("CLAUDECODE", "1")  # A Claude child can inherit its launcher's Codex environment.
    assert claims.session_source() == {"provider": "Claude Code"}
    monkeypatch.delenv("CLAUDECODE")
    monkeypatch.setattr(claims, "DIR", tmp_path)
    monkeypatch.setattr(claims, "session_id", lambda: "owner")
    monkeypatch.setattr(claims, "git", lambda *args: subprocess.CompletedProcess(args, 0))
    path = tmp_path / "work.json"
    path.write_text(json.dumps({"session": "owner", "item": "Work page"}), encoding="utf-8")
    claims.cmd_beat("Checking   source freshness")
    saved = json.loads(path.read_text())
    assert saved["activity"] == "Checking source freshness" and saved["thread_id"] == "thread-1"
    claims.cmd_beat()
    assert json.loads(path.read_text())["activity"] == saved["activity"]
    monkeypatch.setenv("CLAUDECODE", "1")
    claims.cmd_beat()
    assert json.loads(path.read_text())["provider"] == "Claude Code"
    assert "thread_id" not in json.loads(path.read_text())
