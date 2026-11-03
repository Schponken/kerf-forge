"""Work overview: combine observed jobs and sessions with clearly labelled git claims."""
from __future__ import annotations

import math
import re
import time

from .progress import STAGES

STATES = {"running", "claimed", "waiting", "paused", "continued", "failed", "done", "stopped", "stale", "idle"}
LABELS = {"running": "Working", "claimed": "Claimed", "waiting": "Needs your input", "failed": "Failed",
          "paused": "Paused", "continued": "Continued in another job",
          "done": "Finished", "stopped": "Stopped", "stale": "No recent update", "idle": "Not running"}
PHASES = {"research": "Researching options", "plan": "Planning the design", "contract": "Defining requirements",
          "parts": "Designing parts", "check": "Checking the design", "build": "Building the kit",
          "review": "Reviewing the result", "ship": "Saving the work"}


def number(value, default=None):
    try:
        n = float(value)
        return n if math.isfinite(n) and n >= 0 else default
    except (TypeError, ValueError):
        return default


def plain(value, limit=500):
    return " ".join(str(value or "").replace("`", "").split())[:limit]


def plan_steps(plan: str, item: str) -> list[dict]:
    """Only explicit descendant checkboxes count as steps; prose does not imply a checklist."""
    rows = [(len(m[1]), m[2].lower() == "x", m[3].strip()) for line in plan.splitlines()
            if (m := re.match(r"^(\s*)- \[([ xX])\] (.+)$", line))]
    key = plain(item).casefold()
    for i, (indent, checked, title) in enumerate(rows):
        candidate = plain(title).casefold()
        if key != candidate and not (len(candidate) >= 12 and key.startswith(candidate + " ")):
            continue
        descendants = []
        for row in rows[i + 1:]:
            if row[0] <= indent:
                break
            descendants.append(row)
        return [{"title": plain(t), "status": "done" if done else "pending"}
                for j, (depth, done, t) in enumerate(descendants)
                if j + 1 == len(descendants) or descendants[j + 1][0] <= depth]
    return []


def _progress(steps, label="task steps"):
    steps = [s for s in (steps or []) if isinstance(s, dict) and plain(s.get("title"))]
    if not steps:
        return None, []
    done = sum(s.get("status") in ("done", "completed") for s in steps)
    return {"done": done, "total": len(steps), "label": label}, [plain(s["title"]) for s in steps
                                                                if s.get("status") not in ("done", "completed")]


def _projects(source):
    values = source.get("projects") or ([source["project"]] if source.get("project") else [])
    if isinstance(values, (str, dict)):
        values = [values]
    out = []
    for value in values:
        name = value.get("name") if isinstance(value, dict) else value
        if name and name != "*" and not any(p["name"] == name for p in out):
            out.append({"name": str(name), "title": plain(value.get("title") if isinstance(value, dict) else None)
                        or str(name).replace("_", " ")})
    return out


def _item(source, origin, now):
    state = {"working": "running", "blocked": "failed"}.get(source.get("state"), source.get("state"))
    if origin == "claim":
        state = "stale" if source.get("stale") else "claimed"
    elif state not in STATES:
        state = "idle"
    provider = {"codex": "Codex", "claude": "Claude", "claude code": "Claude Code", "studio": "Studio"}.get(
        str(source.get("provider", "")).casefold(), "Session")
    full = plain(source.get("description") or source.get("full") or source.get("title") or source.get("item"), 3000)
    title = plain(source.get("title") or source.get("item") or "Untitled work", 240)
    if origin == "claim" and not source.get("title"):
        title = re.sub(r"\s*\([^)]*(?:Spencer|Studio request|2026-)[^)]*\)", "", full).split(":", 1)[0][:160]
    progress, remaining = _progress(source.get("steps"))
    updated = number(source.get("updated_at"))
    if updated is None and source.get("since_commit_min") is not None:
        updated = max(0, now - (number(source.get("since_commit_min"), 0) * 60))
    activity = plain(source.get("activity"), 400)
    if not activity:
        activity = "Claim recorded; live activity is not available." if origin == "claim" else "No activity detail reported."
    attention = plain(source.get("attention"), 400) or None
    if not attention:
        attention = {"stale": ("No recent ownership update. Check with this claim's owner before taking over."
                                if origin == "claim" else "No recent update. This session may have stopped; check before taking over."),
                     "waiting": "This session is waiting for your input.",
                     "failed": "The last run failed. Open its activity to see what needs fixing."}.get(state)
    return {"id": f"{origin}:{source.get('id') or source.get('claim_id') or source.get('session') or title}",
            "provider": provider, "session": str(source.get("session") or source.get("id") or ""),
            "chat_id": source.get("thread_id") if origin == "session" and provider == "Codex" and isinstance(source.get("thread_id"), str) else None,
            "title": title, "description": full, "projects": _projects(source), "state": state,
            "status_label": LABELS[state] if origin == "claim" else plain(source.get("status_label"), 120) or LABELS[state],
            "activity": activity, "action": plain(source.get("action"), 120) if origin == "session" and state != "stale" else "",
            "updated_at": updated,
            "started_at": number(source.get("started_at")), "source": origin,
            "source_label": plain(source.get("source_label") or source.get("source"), 160)
                            or {"claim": "Git claim", "session": "Local session", "job": "Studio job"}[origin],
            "source_detail": plain(source.get("source_detail") or source.get("detail"), 700),
            "live": source.get("live") if isinstance(source.get("live"), bool) else None,
            "branch": plain(source.get("branch"), 200) or None,
            "progress": progress, "remaining": remaining, "eta": None, "attention": attention,
            "url": source.get("url"), "job_id": None, "picture": source.get("picture")}


def _job(source, now):
    events = [e for e in source.get("events", []) if isinstance(e, dict)]
    kind = source.get("kind")
    is_agent = kind in ("design", "edit", "fix", "quote")
    state = source.get("state", "idle")
    provider = source.get("agent") if source.get("agent") in ("codex", "claude") else "claude"
    item = _item({**source, "title": source.get("label"), "started_at": source.get("started"),
                  "provider": provider if is_agent else "studio"}, "job", now)
    item["job_id"] = source.get("id")
    item["updated_at"] = max([number(source.get("started"), 0), number(source.get("ended"), 0)] +
                             [number(e.get("t"), 0) for e in events]) or None
    latest = next((e for e in reversed(events) if e.get("k") in ("note", "stage", "tool", "hint", "done")
                   and (e.get("k") != "note" or plain(e.get("text")))), {})
    note = next((e for e in reversed(events) if e.get("k") in ("hint", "done")
                 or (e.get("k") == "note" and plain(e.get("text")))), {}) if is_agent else {}
    if latest.get("k") in ("stage", "tool") and note.get("k") in ("hint", "done"):
        latest = note  # Cleanup tool events must not hide a setup failure or completed result.
    if latest.get("k") == "note":
        item["activity"] = plain(latest.get("text"), 400)
    elif latest.get("k") == "stage":
        item["activity"] = dict(STAGES).get(latest.get("stage"), "Running checks")
    elif latest.get("k") == "tool":
        item["activity"] = PHASES.get(latest.get("phase"), "Working on the task")
    elif latest.get("k") == "hint":
        item["activity"] = ("Waiting for the process to stop." if state == "running" else
                            "The process stopped after a setup problem.")
        item["attention"] = {"auth": f"{item['provider']} needs you to sign in again.",
                             "trust": f"{item['provider']} needs this project folder to be trusted."}.get(
                                 latest.get("code"), "The session reported a setup problem.")
    elif latest.get("k") == "done":
        item["activity"] = "Checks completed." if latest.get("ok") else "Checks found problems to fix."
    elif state == "running":
        item["activity"] = "Starting the job; waiting for its first update."
    if is_agent and state == "running" and latest.get("k") in ("stage", "tool"):
        if note.get("k") == "note":
            text = plain(note["text"], 400)
            item["action"] = item["activity"] if item["activity"] != text else ""
            item["activity"] = text
    if state == "paused":
        usage = source.get("usage") if isinstance(source.get("usage"), dict) else {}
        item["status_label"] = "Paused · usage limit" if usage else "Paused"
        item["activity"] = "Usage limit reached; this run is paused." if usage else "This run is paused."
        item["action"] = None
        if source.get("retry_blocked") is True:
            retry = "The budget switch currently blocks automatic retries."
        elif source.get("auto_resume") is False:
            retry = "Automatic retry is off. Open the job to review resume options."
        elif source.get("auto_resume") is True:
            retry = ("Automatic retry is enabled; retry timing is unavailable."
                     if source.get("resumable") else
                     "Automatic retry is enabled, but no resumable session is reported.")
        else:
            retry = "Automatic retry status is not reported. Open the job for details."
        item["attention"] = retry
        item["pause"] = {"reset_at": number(usage.get("until")) or None}
        resumed_by = source.get("resumed_by")
        if isinstance(resumed_by, str) and resumed_by and resumed_by != item["job_id"]:
            item.update(continued_by=resumed_by, state="continued", status_label=LABELS["continued"],
                        attention=None, pause=None)
    start = next((e for e in reversed(events) if e.get("k") == "start"), {})
    stages = list(dict.fromkeys(str(s) for s in start.get("stages", [])))
    reached = [e.get("stage") for e in events if e.get("k") == "stage" and e.get("stage") in stages]
    if stages and not is_agent:
        index = stages.index(reached[-1]) if reached else 0
        finished = len(stages) if state == "done" else index
        item["progress"] = {"done": finished, "total": len(stages), "label": "build stages"}
        item["remaining"] = [dict(STAGES).get(s, s) for s in stages[finished:]]
    expected = number(source.get("estimate_seconds"))
    elapsed = max(0, now - number(source.get("started"), now))
    if state == "running" and expected and not is_agent:
        if elapsed < expected:
            item["eta"] = {"seconds": round(expected - elapsed), "basis": "Based on previous runs of this project"}
        else:
            item["activity"] += " Taking longer than previous runs; finish time is uncertain."
    return item


def overview(data: dict, sessions=(), jobs=(), sources=(), now=None) -> dict:
    """A fresh, read-only view; callers may cache git data independently of live session/job observations."""
    now = time.time() if now is None else now
    observed = [s for s in sessions if isinstance(s, dict)]
    items = [_item(s, "session", now) for s in observed]
    by_id = {i["id"].removeprefix("session:"): i for i in items}
    linked_claims = {}
    for claim in data.get("cards", []):
        if not isinstance(claim, dict):
            continue
        thread_id = str(claim.get("thread_id"))
        if thread_id in by_id:
            linked_claims.setdefault(thread_id, []).append(claim)
        else:
            items.append(_item(claim, "claim", now))
    for thread_id, claims in linked_claims.items():
        item = by_id[thread_id]
        scopes = [_item(c, "claim", now) for c in claims]
        stale = all(c["state"] == "stale" for c in scopes)
        if item["state"] == "idle":
            item["state"] = "stale" if stale else "claimed"
            item["status_label"] = "No recent claim update" if stale else "Claimed · live status unavailable"
        item["chat_title"] = item["title"]
        item["source_label"] += " + Git claim"
        item["title"] = " + ".join(c["title"] for c in scopes)
        item["description"] = "\n\n".join(c["description"] for c in scopes if c["description"]) or item["description"]
        item["claimed_tasks"] = scopes
        attention_count = sum(bool(c["attention"]) for c in scopes)
        if attention_count and not item["attention"]:
            item["attention"] = (f"{attention_count} claimed task{'s need' if attention_count != 1 else ' needs'} attention. "
                                 "Open scope to review each owner's update.")
        newest = max(claims, key=lambda c: number(c.get("updated_at"), 0))
        fresh_activity = max((c for c in claims if not c.get("stale") and c.get("activity")),
                             key=lambda c: number(c.get("updated_at"), 0), default=None)
        if item["live"] is False and fresh_activity:
            item["activity"] = plain(fresh_activity["activity"], 400)
            item["action"] = ""
            item["updated_at"] = number(fresh_activity.get("updated_at"))
        elif item["live"] is not True and number(newest.get("updated_at"), 0) > (item["updated_at"] or 0):
            item["updated_at"] = number(newest.get("updated_at"))
            if newest.get("activity"):
                item["activity"] = plain(newest["activity"], 400)
                item["action"] = ""
        item["projects"] = _projects({"projects": item["projects"] + [p for c in scopes for p in c["projects"]]})
        if len(scopes) == 1:
            if not item["progress"]:
                item["progress"], item["remaining"] = scopes[0]["progress"], scopes[0]["remaining"]
        else:
            # A session plan may cover only one claim; never imply it measures every owned task.
            item["progress"], item["remaining"] = None, []
            if all(c["progress"] for c in scopes):
                item["progress"] = {"done": sum(c["progress"]["done"] for c in scopes),
                                    "total": sum(c["progress"]["total"] for c in scopes), "label": "claimed task steps"}
                item["remaining"] = [f"{c['title']}: {step}" for c in scopes for step in c["remaining"]]
    job_items = [_job(j, now) for j in jobs if isinstance(j, dict)]
    by_job = {i["job_id"]: i for i in job_items}
    for item in job_items:
        if target_id := item.get("continued_by"):
            target = by_job.get(target_id)
            item["activity"] = (f"{target['provider']} continued this task in another job."
                                if target else "This task continued in another job; its current state is not reported.")
            item["continuation"] = {"job_id": target_id, "observed": bool(target),
                                    "provider": target["provider"] if target else None,
                                    "status_label": target["status_label"] if target else None}
    items += job_items
    order = {"waiting": 0, "paused": 1, "failed": 2, "running": 3, "claimed": 4, "stale": 5,
             "idle": 6, "continued": 7, "done": 8, "stopped": 9}
    items.sort(key=lambda i: (order[i["state"]], -(i["updated_at"] or 0), i["title"]))
    return {**data, "items": items, "updated_at": now, "sources": list(sources),
            "counts": {"running": sum(i["state"] == "running" for i in items),
                       "claimed": sum(i["state"] == "claimed" for i in items),
                       "waiting": sum(i["state"] == "waiting" for i in items),
                       "paused": sum(i["state"] == "paused" for i in items),
                       "attention": sum(bool(i["attention"]) for i in items),
                       "done": sum(i["state"] == "done" for i in items), "total": len(items)}}
