"""Evidence-backed lesson applications. Historical failures are not applications or savings."""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTCOMES = ("caught", "missed", "blocked_good_work", "no_issue")


@contextmanager
def locked(repo: Path | str | None = None):
    directory = Path(repo or ROOT) / "learning"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".scorecards.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def write(data: dict, repo: Path | str | None = None):
    """Caller holds locked() across reading, updating and writing."""
    path = Path(repo or ROOT) / "learning" / "lessons.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    temporary.replace(path)


def summarize(events: list[dict]) -> dict:
    caught = [e for e in events if e["outcome"] == "caught"]
    blocked = sum(e["outcome"] == "blocked_good_work" for e in events)
    known = [e["saved_min"] for e in caught if e.get("saved_min") is not None]
    projects = {e.get("project") for e in caught if e.get("project")}
    flag = "blocking" if blocked else "dead" if len(events) >= 3 and not caught else "unmeasured" if not events else "observed"
    return {"times_applied": len(events), "times_caught": len(caught),
            "what_caught": [e["evidence"] for e in caught], "blocked_good_work": blocked,
            "saved_min": sum(known) if caught and len(known) == len(caught) else None,
            "known_saved_min": sum(known), "savings_unknown": len(caught) - len(known), "flag": flag,
            "promotion": "proposed gate" if len(projects) >= 2 and not blocked else None}


def read(repo: Path | str | None = None) -> dict:
    path = Path(repo or ROOT) / "learning" / "lessons.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"lessons": []}
    for row in data["lessons"]:
        row["scorecard"] = summarize(row.get("applications", []))
    return data


def preserve(data: dict, previous: dict) -> dict:
    """A diary rebuild replaces observations, never the application ledger."""
    old = {row["id"]: row for row in previous.get("lessons", [])}
    present = {row["id"] for row in data["lessons"]}
    for row in data["lessons"]:
        row["applications"] = old.get(row["id"], {}).get("applications", [])
    for lid, row in old.items():
        if lid not in present and row.get("applications"):
            data["lessons"].append({**row, "historical_only": True})
    for row in data["lessons"]:
        row["scorecard"] = summarize(row.get("applications", []))
    return data


def record(lesson_id: str, *, event_id: str, outcome: str, evidence: str,
           project: str | None = None, saved_min: float | None = None, savings_source: str | None = None, repo: Path | str | None = None) -> dict:
    if not isinstance(event_id, str) or not event_id.strip() or not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("event ID and evidence are required")
    if project is not None and (not isinstance(project, str) or not project.strip()):
        raise ValueError("project must be a nonempty name when supplied")
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {', '.join(OUTCOMES)}")
    if saved_min is not None and (isinstance(saved_min, bool) or not isinstance(saved_min, (int, float)) or not math.isfinite(saved_min) or saved_min < 0 or outcome != "caught"):
        raise ValueError("saved minutes must be a finite nonnegative measurement for a caught issue")
    if saved_min is not None and (not isinstance(savings_source, str) or not savings_source.strip()):
        raise ValueError("reported savings require a source describing how they were established")
    with locked(repo):
        data = read(repo)
        row = next((r for r in data["lessons"] if r["id"] == lesson_id), None)
        if row is None:
            raise ValueError("unknown lesson ID")
        event = {"id": event_id, "outcome": outcome, "evidence": evidence, "project": project, "saved_min": saved_min, "savings_source": savings_source}
        applications = row.setdefault("applications", [])
        existing = next((e for e in applications if e["id"] == event_id), None)
        if existing is not None:
            if existing != event:
                raise ValueError("event ID already records different evidence")
            return row
        applications.append(event)
        row["scorecard"] = summarize(applications)
        write(data, repo)
        return row
