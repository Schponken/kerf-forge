"""kerf/agent.py: Studio jobs run on Claude Code or ChatGPT Codex (Spencer, 2026-11-02: Codex takes over when Claude's
usage runs out). No real agent is started: binaries are faked on PATH."""
import json
import os
import stat

import pytest

from kerf import agent


@pytest.fixture
def bins(tmp_path, monkeypatch):
    def make(*names):
        for n in names:
            f = tmp_path / n
            f.write_text("#!/bin/sh\nexit 0\n")
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("KERF_AGENT", raising=False)
    monkeypatch.delenv("KERF_CODEX_ARGS", raising=False)
    monkeypatch.setattr(agent, "MODE_FILE", tmp_path / "agent_mode")
    return make


def test_auto_prefers_claude_and_falls_back_to_codex(bins):
    bins("claude", "codex")
    assert agent.pick() == "claude"
    assert agent.pick(claude_blocked="usage out until 7 PM") == "codex"
    assert agent.can_take_over()


def test_auto_without_codex_keeps_claude_and_cannot_take_over(bins):
    bins("claude")
    assert agent.pick(claude_blocked="usage out") == "claude"   # Studio then waits for the reset, as before
    assert not agent.can_take_over()


def test_forced_modes(bins, monkeypatch):
    bins("claude", "codex")
    agent.set_mode("codex")
    assert agent.mode() == "codex" and agent.pick() == "codex" and not agent.can_take_over()
    monkeypatch.setenv("KERF_AGENT", "claude")
    assert agent.pick(claude_blocked="x") == "claude"
    with pytest.raises(ValueError):
        agent.set_mode("gpt")


def test_nothing_installed(bins):
    bins()
    assert agent.pick() is None


def test_codex_command_rewrites_the_skill_and_keeps_prompt_last(bins):
    bins("codex")
    cmd = agent.command("codex", "/kerf a desk lamp\n\nProject folder name: projects/lamp.")
    assert cmd[1:3] == ["exec", "--json"] and agent.who_runs(cmd) == "codex"
    assert cmd[3:-1] == ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.network_access=true", "--skip-git-repo-check"]
    assert "--full-auto" not in cmd and "--dangerously-bypass-approvals-and-sandbox" not in cmd
    assert ".claude/skills/kerf/SKILL.md" in cmd[-1] and "a desk lamp" in cmd[-1] and "AGENTS.md" in cmd[-1]
    assert not cmd[-1].startswith("/kerf")
    r = agent.command("codex", "continue", resume="thread-123")
    assert r[r.index("resume") + 1] == "thread-123" and r[-1].startswith("continue")
    assert r[3:r.index("resume")] == cmd[3:-1]


@pytest.mark.parametrize("resume", [None, "thread-123"])
def test_explicit_codex_args_still_replace_defaults(bins, monkeypatch, resume):
    bins("codex")
    monkeypatch.setenv("KERF_CODEX_ARGS", "--sandbox 'read-only'")
    cmd = agent.command("codex", "inspect only", resume=resume)
    assert cmd[3:-1] == ["--sandbox", "read-only", *(["resume", resume] if resume else [])]
    assert cmd[-1].startswith("inspect only")


def test_claude_command_unchanged(bins):
    bins("claude")
    cmd = agent.command("claude", "/kerf x", resume="s1")
    assert cmd[1:3] == ["-p", "/kerf x"] and "--resume" in cmd and "stream-json" in cmd
    assert agent.who_runs(cmd) == "claude"


def _ev(line):
    return [json.loads(x[2:]) for x in agent.codex_lines(line) if x.startswith("@@")]


def test_codex_events_become_studio_lines():
    assert _ev(json.dumps({"type": "thread.started", "thread_id": "abc"})) == [{"k": "session", "id": "abc"}]
    msg = agent.codex_lines(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Sizing the servo"}}))
    assert msg[0] == "Sizing the servo" and json.loads(msg[1][2:])["k"] == "note"
    cmd = _ev(json.dumps({"type": "item.started", "item": {"type": "command_execution", "command": ".venv/bin/kerf check lamp"}}))
    assert cmd[0]["k"] == "tool" and cmd[0]["cmd"] == ".venv/bin/kerf check lamp"
    edits = _ev(json.dumps({"type": "item.completed", "item": {"type": "file_change", "changes": [{"path": "projects/lamp/parts/base.py"}]}}))
    assert edits[0]["path"] == "projects/lamp/parts/base.py"
    assert agent.codex_lines(json.dumps({"type": "turn.completed", "usage": {}})) == ["== finished =="]
    assert "stopped with an error" in agent.codex_lines(json.dumps({"type": "turn.failed", "error": {"message": "boom"}}))[0]
    assert agent.codex_lines("plain warning") == ["plain warning"] and agent.codex_lines("  ") == []


def _fake_codex(path):
    f = path / "codex"
    f.write_text("#!/bin/sh\n"
                 "echo '{\"type\":\"thread.started\",\"thread_id\":\"t-1\"}'\n"
                 "echo '{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"took over\"}}'\n"
                 "echo '{\"type\":\"turn.completed\",\"usage\":{}}'\n")
    f.chmod(0o755)


def _wait(job):
    import time
    for _ in range(200):
        if job.state != "running":
            break
        time.sleep(0.05)
    job.proc.wait()
    for _ in range(100):
        if job.ended:
            break
        time.sleep(0.05)


def test_studio_runs_codex_when_claude_usage_is_out(bins, tmp_path, monkeypatch):
    from kerf import studio
    bins("claude")
    _fake_codex(tmp_path)
    monkeypatch.setitem(studio.USAGE, "until", 9e12)          # Claude's usage is used up
    monkeypatch.setattr(studio, "on_finished", lambda j: None)
    j = studio.agent_job("quote", "agent_test_q", "/kerf QUOTE ONLY. a lamp", "Options for: a lamp")
    _wait(j)
    assert j.agent == "codex" and j.cmd[1] == "exec" and studio.CUTOFF_NOTE in j.cmd[-1]
    assert j.state == "done" and j.session == "t-1" and "took over" in j.lines
    assert studio.claude_ready()["agent"] == "codex"


def test_paused_claude_job_is_taken_over_by_codex(bins, tmp_path, monkeypatch):
    from kerf import studio
    bins("claude")
    _fake_codex(tmp_path)
    monkeypatch.setattr(studio, "on_finished", lambda j: None)
    monkeypatch.setattr(studio, "budget_stop", lambda: "")
    monkeypatch.setattr(studio, "settings", lambda: {"autoresume": True})

    class Old:                                               # a Claude design job the usage limit paused
        id, kind, project, label, env, session, resumed_by = "old1", "design", "agent_test_d", "New design: lamp", None, "s9", None
        agent, request, lines = "claude", "a desk lamp", []
    old = Old()
    studio.schedule_resume(old)
    assert old.resumed_by
    new = studio.JOBS[old.resumed_by]
    _wait(new)
    assert new.agent == "codex" and "Codex took over" in new.label and "a desk lamp" in new.cmd[-1]
    assert "(Codex took over: Claude's usage ran out)" in old.lines
