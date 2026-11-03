"""Which AI agent runs Studio's jobs (new design, quote, edit, fix, resume, Learning Mode): Claude Code or ChatGPT Codex.

Spencer, 2026-11-02: when Claude's usage runs out, Codex must be able to take over building and developing projects.
Mode comes from KERF_AGENT (or .cache/studio/agent): "claude", "codex", or "auto" (default). Auto uses Claude Code when it
is installed and its usage isn't used up, otherwise Codex; a Claude job cut off by the usage limit is continued by Codex.

Both agents get the same task text. Claude's starts with "/kerf" (its skill); Codex has no slash skills, so that is
rewritten to "follow .claude/skills/kerf/SKILL.md" and Codex reads AGENTS.md (its own rules) on its own.
Codex runs with the workspace-write sandbox (`--sandbox workspace-write`) and network on so it can research and push.
Spencer can change those flags with KERF_CODEX_ARGS; no approval-policy override is added here.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODE_FILE = ROOT / ".cache" / "studio" / "agent"
MODES = ("auto", "claude", "codex")
CODEX_FLAGS = ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.network_access=true", "--skip-git-repo-check"]


def mode() -> str:
    m = os.environ.get("KERF_AGENT", "").strip().lower()
    if not m:
        try:
            m = MODE_FILE.read_text(encoding="utf-8").strip().lower()
        except OSError:
            m = ""
    return m if m in MODES else "auto"


def set_mode(m: str) -> str:
    m = (m or "").strip().lower()
    if m not in MODES:
        raise ValueError(f"agent must be one of {', '.join(MODES)}")
    MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(m, encoding="utf-8")
    return m


def claude_bin() -> str | None:
    return shutil.which("claude")


def codex_bin() -> str | None:
    try:
        from .codex_work import _executable as find   # same discovery Studio's Work page uses
        return find()
    except Exception:  # noqa: BLE001
        return shutil.which("codex")


def pick(claude_blocked: str = "", has_claude: bool | None = None) -> str | None:
    """'claude' or 'codex' for the next job, or None when neither can run. claude_blocked: why Claude can't start now;
    has_claude: whether Claude Code is installed (default: on PATH)."""
    m = mode()
    claude = bool(claude_bin()) if has_claude is None else has_claude
    if m == "claude":
        return "claude" if claude else None
    if m == "codex":
        return "codex" if codex_bin() else None
    if claude and not claude_blocked:
        return "claude"
    if codex_bin():
        return "codex"
    return "claude" if claude else None


def can_take_over() -> bool:
    """A Claude job cut off by the usage limit is continued by Codex (auto mode with Codex installed)."""
    return mode() == "auto" and bool(codex_bin())


def to_codex(prompt: str) -> str:
    p = prompt.lstrip()
    if p.startswith("/kerf"):
        p = ("Follow the kerf skill: read .claude/skills/kerf/SKILL.md and do what it says for this request "
             "(AGENTS.md says how its Claude-only steps translate for you).\nRequest:" + p[len("/kerf"):])
    return p + ("\n\nYou are ChatGPT Codex, started by Kerf Studio on Spencer's Mac. Read AGENTS.md first. Work "
                "autonomously to the end; never write review.json (leave the design-reviewer step for Claude as AGENTS.md "
                "says); commit and push as you go.")


def command(who: str, prompt: str, resume: str | None = None, claude_exe: str | None = None) -> list[str]:
    """The command line for one job. The prompt is always the last argument."""
    if who == "codex":
        exe = codex_bin() or "codex"
        flags = shlex.split(os.environ["KERF_CODEX_ARGS"]) if os.environ.get("KERF_CODEX_ARGS") else list(CODEX_FLAGS)
        tail = ["resume", resume] if resume else []
        return [exe, "exec", "--json", *flags, *tail, to_codex(prompt)]
    exe = claude_exe or claude_bin() or "claude"
    return [exe, "-p", prompt, *(["--resume", resume] if resume else []), "--output-format", "stream-json", "--verbose"]


def who_runs(cmd: list[str]) -> str:
    return "codex" if len(cmd) > 1 and cmd[1] == "exec" else "claude"


# ---------------------------------------------------------------- Codex `exec --json` events -> Studio's job lines
CODEX_USAGE_RX = re.compile(r"usage limit|rate limit|quota|hit your limit|insufficient_quota", re.I)


def codex_lines(raw: str) -> list[str]:
    """One line of `codex exec --json` (JSONL: thread.started, item.started/completed, turn.completed/failed, error)
    as the same lines and '@@' events _claude_lines gives, so Activity, the thought web and resume work unchanged."""
    raw = raw.strip()
    if not raw:
        return []
    try:
        ev = json.loads(raw)
    except Exception:  # noqa: BLE001 - plain text (warnings) shows as is
        return [raw]
    if not isinstance(ev, dict):
        return [raw]
    t = ev.get("type", "")
    out: list[str] = []
    if t == "thread.started" and ev.get("thread_id"):
        out.append("@@" + json.dumps({"k": "session", "id": str(ev["thread_id"])}))
    elif t in ("item.started", "item.completed"):
        it = ev.get("item") or {}
        kind = it.get("type") or it.get("item_type")
        if kind in ("agent_message", "assistant_message") and t == "item.completed" and (it.get("text") or "").strip():
            txt = it["text"].strip()
            out += [txt, "@@" + json.dumps({"k": "note", "text": txt[:400]})]
        elif kind == "command_execution" and t == "item.started":
            c = str(it.get("command") or "").splitlines()[0][:200] if it.get("command") else ""
            out += [f"  > Bash: {c[:140]}",
                    "@@" + json.dumps({"k": "tool", "name": "Bash", "what": c[:140], "phase": "build", "cmd": c})]
        elif kind == "file_change" and t == "item.completed":
            for ch in it.get("changes") or []:
                pth = str(ch.get("path") or "")
                out += [f"  > Edit: {pth[:140]}",
                        "@@" + json.dumps({"k": "tool", "name": "Edit", "what": pth[:140], "phase": "design", "path": pth[:300]})]
        elif kind == "web_search" and t == "item.started":
            q = str(it.get("query") or "")[:160]
            out += [f"  > WebSearch: {q}", "@@" + json.dumps({"k": "tool", "name": "WebSearch", "what": q, "phase": "research", "query": q})]
        elif kind == "error" and it.get("message"):
            out.append(f"error: {it['message']}")
    elif t == "turn.completed":
        out.append("== finished ==")
    elif t in ("turn.failed", "error"):
        err = ev.get("error")
        msg = err.get("message") if isinstance(err, dict) else ev.get("message")
        out.append(f"== stopped with an error: {msg or raw[:200]} ==")
    return out
