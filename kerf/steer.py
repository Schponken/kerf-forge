"""Steering a running Studio design job from "How Kerf decided" without slowing it down or spending extra model turns.

Studio appends what Spencer asks ("focus on this question", "skip this one", or a short note) to
.cache/studio/steer/<project>.json. A PostToolUse hook (.claude/hooks/steer.py) hands any new entries to the job as
extra context on its next tool result: no message, no pause, no restart, and nothing happens at all when there is no
steering. Each entry records when the job received it, so Studio can show "Kerf has it". Stdlib only: the hook imports it.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / ".cache" / "studio" / "steer"
ACTIONS = {"focus": "Focus on", "skip": "Skip", "note": "Note"}
MAX_ENTRIES = 30


def path(project: str) -> Path:
    return DIR / f"{project}.json"


def read(project: str) -> list[dict]:
    try:
        return json.loads(path(project).read_text(encoding="utf-8")).get("entries", [])
    except Exception:  # noqa: BLE001 - missing or half-written file: no steering
        return []


def _write(project: str, entries: list[dict]):
    p = path(project)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"entries": entries}, indent=1), encoding="utf-8")
    os.replace(tmp, p)                       # atomic: the hook never reads half a file


def reset(project: str):
    """A new job starts with no steering left over from an earlier one."""
    path(project).unlink(missing_ok=True)


def add(project: str, action: str, label: str = "", text: str = "", node: str = "") -> dict:
    action = str(action)
    if action not in ACTIONS:
        raise ValueError("steer: action must be focus, skip or note")
    label, text = " ".join(str(label).split())[:200], " ".join(str(text).split())[:500]
    if action == "note" and not text:
        raise ValueError("steer: write what Kerf should know")
    if action != "note" and not label:
        raise ValueError("steer: say which question or option")
    entries = read(project)
    if len(entries) >= MAX_ENTRIES:
        raise ValueError(f"steer: at most {MAX_ENTRIES} steering notes per job")
    # the latest word on a question wins: "focus" then "skip" on the same one replaces, never contradicts
    entries = [e for e in entries if not (node and e.get("node") == node and e.get("action") != "note")]
    e = {"action": action, "label": label, "text": text, "node": str(node)[:40], "at": time.time(), "delivered": None}
    entries.append(e)
    _write(project, entries)
    return e


def message(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        if e["action"] == "focus":
            lines.append(f"- Focus on: {e['label']}" + (f" ({e['text']})" if e.get("text") else ""))
        elif e["action"] == "skip":
            lines.append(f"- Skip: {e['label']} (stop spending research on it; don't pick it unless nothing else works)")
        else:
            lines.append(f"- Note: {e['text']}")
    return ("Spencer is steering this design from Kerf Studio while it runs. Take this into account from now on, "
            "including in DESIGN.md's options and the helpers you brief; don't stop, restart or reply about it:\n" + "\n".join(lines))


def deliver(project: str) -> str:
    """New steering for the job (marked delivered), or "" when there is none."""
    entries = read(project)
    new = [e for e in entries if not e.get("delivered")]
    if not new:
        return ""
    now = time.time()
    for e in new:
        e["delivered"] = now
    _write(project, entries)
    return message(new)
