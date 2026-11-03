"""Read Codex session summaries for this repository without starting or resuming work.

Protocol: https://learn.chatgpt.com/docs/app-server (thread/list and thread/turns/list).
Prefer the running daemon; a separate stdio reader can see saved history, not live runtime state.
"""
from __future__ import annotations

import json
import os
import platform
import re
import selectors
import shutil
import subprocess
import threading
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlparse

REFRESH_SECONDS = 30
MAX_SESSIONS = 20
_MACOS_BUNDLE_EXECUTABLE = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex")
_CACHE: dict[str, dict] = {}
_LOCK = threading.Lock()


class _Reader:
    """One bounded, read-only JSON-lines connection; notifications are ignored."""
    def __init__(self, command: list[str], deadline: float):
        self.deadline, self.buffer, self.seq = deadline, b"", 0
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)

    def call(self, method: str, params: dict) -> dict:
        if method not in ("initialize", "thread/list", "thread/turns/list"):
            raise ValueError("Work viewer only reads session metadata")
        self.seq += 1
        self.proc.stdin.write((json.dumps({"id": self.seq, "method": method, "params": params}) + "\n").encode())
        while time.monotonic() < self.deadline:
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                message = json.loads(line)
                if message.get("id") != self.seq:
                    continue
                if "error" in message:
                    raise RuntimeError("Codex could not read session metadata")
                return message.get("result") or {}
            if self.selector.select(max(0, self.deadline - time.monotonic())):
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("Codex session reader is unavailable")
                self.buffer += chunk
                if len(self.buffer) > 4 * 1024 * 1024:
                    raise RuntimeError("Codex session response exceeds the viewer limit")
        raise TimeoutError("Codex session reader timed out")

    def initialize(self):
        self.call("initialize", {"clientInfo": {"name": "kerf_work_viewer", "title": "Kerf Studio Work", "version": "0.1.0"}})
        self.proc.stdin.write(b'{"method":"initialized"}\n')

    def close(self):
        self.selector.close()
        self.proc.terminate()
        try:
            self.proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=1)
        self.proc.stdin.close()
        self.proc.stdout.close()


def _origin(value: str) -> str:
    value = value.strip()
    if re.match(r"^[^/@]+@[^/:]+:", value):
        value = "ssh://" + value.replace(":", "/", 1)
    parsed = urlparse(value)
    if parsed.hostname:
        return parsed.hostname.lower() + parsed.path.removesuffix(".git").rstrip("/")
    return str(Path(value).resolve()) if value else ""


@lru_cache(maxsize=256)
def _repo_origin(cwd: str) -> str:
    if not cwd or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        return ""
    try:
        result = subprocess.run(["git", "-C", cwd, "remote", "get-url", "origin"],
                                capture_output=True, text=True, timeout=1)
        return _origin(result.stdout) if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _belongs(thread: dict, root: Path, origin: str) -> bool:
    cwd = thread.get("cwd") or ""
    if cwd and Path(cwd).resolve().is_relative_to(root):
        return True
    recorded = _origin((thread.get("gitInfo") or {}).get("originUrl") or "")
    return bool(origin and (recorded == origin or (not recorded and _repo_origin(cwd) == origin)))


def _text(value, limit=450) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _chat_url(thread_id) -> str | None:
    # https://learn.chatgpt.com/docs/app/commands#deep-links — existing local chats only.
    if (not isinstance(thread_id, str) or not thread_id or thread_id.strip() != thread_id
            or thread_id.lower() in {"new", ".", ".."} or re.search(r"[\x00-\x1f\x7f/\\]", thread_id)):
        return None
    return "codex://threads/" + quote(thread_id, safe="")


def _record(thread: dict, turn: dict, live: bool) -> dict:
    status = thread.get("status") or {}
    kind, flags = status.get("type"), status.get("activeFlags") or []
    state, label = "idle", "Saved chat · live status unavailable"
    if live:
        state, label = {"active": ("working", "Working"), "idle": ("idle", "Idle"),
                        "systemError": ("blocked", "Session error")}.get(kind, ("idle", "Not loaded"))
        if kind == "active" and flags:
            state, label = "waiting", "Needs approval" if "waitingOnApproval" in flags else "Needs your answer"
    activity, action, steps = "", "", []
    labels = {"commandExecution": "Running a command", "fileChange": "Editing project files",
              "webSearch": "Researching", "mcpToolCall": "Using a connected tool"}
    past = {"commandExecution": "Last activity: ran a command", "fileChange": "Last activity: edited project files",
            "webSearch": "Last activity: researched information", "mcpToolCall": "Last activity: used a connected tool"}
    for item in turn.get("items") or []:
        item_type = item.get("type")
        if item_type == "agentMessage":
            summary = _text(item.get("text"))
            if summary:
                activity, action = summary, ""
        elif item_type in labels:
            active = live and kind == "active" and not flags and item.get("status") == "inProgress"
            action = labels[item_type] if active else past[item_type]
        elif item_type == "plan":
            steps = [{"title": _text(text, 220), "status": "completed" if mark.lower() == "x" else "pending"}
                     for mark, text in re.findall(r"^\s*[-*] \[([ xX])\] (.+)$", item.get("text", ""), re.M)]
    turn_status = turn.get("status")
    if not activity:
        activity = action or {"completed": "Last turn completed", "interrupted": "Last turn was interrupted",
                    "failed": "Last turn failed", "inProgress": "Last saved turn is in progress"}.get(turn_status, "No activity summary yet")
    if live and kind == "idle" and turn_status == "failed":
        state, label = "blocked", "Last turn failed"
    return {"id": thread["id"], "thread_id": thread["id"], "url": _chat_url(thread["id"]), "provider": "Codex",
            "title": thread.get("name") or _text(thread.get("preview"), 120) or "Codex session",
            "description": _text(thread.get("preview")), "state": state, "status_label": label,
            "activity": activity, "action": action, "started_at": turn.get("startedAt") or thread.get("createdAt"),
            "updated_at": thread.get("updatedAt"), "branch": (thread.get("gitInfo") or {}).get("branch"),
            "steps": steps, "live": live, "source": "Codex live session" if live else "Codex saved history"}


def _executable() -> str | None:
    exe = shutil.which("codex")
    if exe:
        return exe
    # shortcut: only this verified app layout; custom installations must be on PATH.
    if platform.system() == "Darwin" and _MACOS_BUNDLE_EXECUTABLE.is_file() and os.access(_MACOS_BUNDLE_EXECUTABLE, os.X_OK):
        return str(_MACOS_BUNDLE_EXECUTABLE)
    return None


def _collect(root: Path) -> dict:
    exe = _executable()
    if not exe:
        return {"sessions": [], "source": {"name": "Codex", "state": "unavailable",
                "detail": "No runnable Codex executable was found. Custom installations must be on PATH. Shared Codex claims still appear."}}
    deadline, reader, is_live = time.monotonic() + 8, None, True
    try:
        try:
            reader = _Reader([exe, "app-server", "proxy"], min(deadline, time.monotonic() + 2))
            reader.initialize()
            reader.deadline = deadline
        except (OSError, RuntimeError, TimeoutError, ValueError):
            if reader:
                reader.close()
            is_live = False
            reader = _Reader([exe, "app-server", "--listen", "stdio://"], deadline)
            reader.initialize()
        origin, matches, cursor = _repo_origin(str(root)), [], None
        partial = False
        for _ in range(3):
            params = {"limit": 100, "sortKey": "updated_at", "useStateDbOnly": True,
                      "sourceKinds": ["cli", "vscode", "appServer", "exec", "subAgent", "unknown"]}
            if cursor:
                params["cursor"] = cursor
            page = reader.call("thread/list", params)
            for thread in page.get("data") or []:
                if time.monotonic() >= deadline:
                    partial = True
                    break
                if _belongs(thread, root, origin):
                    matches.append(thread)
            cursor = page.get("nextCursor")
            if not cursor or len(matches) >= MAX_SESSIONS or partial:
                break
        partial = partial or bool(cursor)
        records = []
        for thread in matches[:MAX_SESSIONS]:
            turn = {}
            try:
                turns = reader.call("thread/turns/list", {"threadId": thread["id"], "limit": 1,
                                    "itemsView": "summary", "sortDirection": "desc"}).get("data") or []
                turn = turns[0] if turns else {}
            except (OSError, RuntimeError, TimeoutError, ValueError):
                partial = True
            records.append(_record(thread, turn, is_live))
        detail = "Live Codex sessions for this repository." if is_live else "Saved Codex sessions; a live connection is unavailable. Running state is not inferred from saved chats."
        if partial:
            detail += " Showing a bounded recent snapshot; some older activity may be omitted."
        return {"sessions": records, "source": {"name": "Codex", "state": "ok" if is_live and not partial else "partial",
                                                "detail": detail, "updated_at": time.time()}}
    finally:
        if reader:
            reader.close()


def snapshot(root: Path, max_age: float = REFRESH_SECONDS) -> dict:
    """Cached, repo-scoped summaries. A failed refresh retains explicitly stale observations."""
    root = root.resolve()
    key, now = str(root), time.time()
    cached = _CACHE.get(key)
    if cached and now - cached["at"] < max_age:
        return cached["value"]
    if not _LOCK.acquire(blocking=False):
        return cached["value"] if cached else {"sessions": [], "source": {"name": "Codex", "state": "loading", "detail": "Reading session summaries…"}}
    try:
        try:
            value = _collect(root)
        except (OSError, RuntimeError, TimeoutError, ValueError, subprocess.SubprocessError):
            previous = (cached or {}).get("value", {})
            stale = []
            for session in previous.get("sessions", []):
                item = {**session, "state": "stale", "status_label": "Last known state", "action": "",
                        "live": None, "source": "Codex last known session"}
                if session.get("action") and session.get("activity") == session["action"]:
                    item["activity"] = "No fresh activity summary is available."
                stale.append(item)
            value = {"sessions": stale,
                     "source": {"name": "Codex", "state": "unavailable", "detail": "Could not refresh Codex sessions. Showing the last known snapshot, if available.",
                                "updated_at": previous.get("source", {}).get("updated_at")}}
        _CACHE[key] = {"at": now, "value": value}
        return value
    finally:
        _LOCK.release()
