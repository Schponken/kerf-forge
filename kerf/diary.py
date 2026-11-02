"""Learning Mode phase 2, the diary: what went wrong in a project, at which stage it was found, and what it cost to fix.

Everything is rebuilt from git history, so it works on projects that were made before this existed:
  - each projects/<p>/review.json version (findings with severity and part, verdict, date) is a review round;
  - commit subjects/bodies that say "check|build|verify ... PASS|FAIL" are check events;
  - the commits touching projects/<p> give times and which part modules were redrawn.
Stage of a problem (from the tree at the commit that recorded it): no part files yet = "before parts";
median part file < ROUGH_BYTES = "rough" (stub parts); a design-review finding on real parts = "final review";
a failed check on real parts = "detail". Cost: wall time from the finding to the commit that fixed it (raw gap and an
active-time estimate that caps each gap between commits), and the part modules changed on the way (redraws).
Historical costs are ESTIMATES (git cannot see idle time, parallel work or tokens); `log_session` adds measured
token usage from a Claude Code session log. Output: learning/diary/<p>.json and .md. No AI calls anywhere.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ROUGH_BYTES = 1500          # median part file below this = stub parts (drone_foldable_wings: stubs ~650, real parts 4000+)
GAP_CAP_MIN = 90            # a gap between two commits counts at most this long as active work
SIM_MIN = 0.25              # same part and this much word overlap = the same finding in the next review round
STAGES = ("before parts", "rough", "detail", "final review")
_EVENT = re.compile(r"\b(quick check|check|build|verify|acceptance)\b[^.;:\n]{0,24}?\b(PASS|FAIL)\b", re.I)


def _git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode and check:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout if not r.returncode else ""


def _t(s: str) -> datetime:
    return datetime.fromisoformat(s)


def commits(repo: Path, p: str) -> list[dict]:
    """Commits touching projects/<p>, oldest first: hash, time, subject, body, files (only the project's)."""
    out = _git(repo, "log", "--reverse", "--name-only", "--format=%x1e%H%x1f%aI%x1f%s%x1f%b%x1f", "--", f"projects/{p}")
    res = []
    for rec in out.split("\x1e")[1:]:
        h, when, subj, body, files = rec.split("\x1f", 4)
        res.append({"hash": h, "time": when, "subject": subj.strip(), "body": body.strip(),
                    "files": [f for f in files.split("\n") if f.strip()]})
    return res


def review_versions(repo: Path, p: str, cms: list[dict]) -> list[dict]:
    """Each distinct review.json that was committed, oldest first: {commit, time, review}."""
    vers, last = [], None
    for c in cms:
        if f"projects/{p}/review.json" not in c["files"]:
            continue
        raw = _git(repo, "show", f"{c['hash']}:projects/{p}/review.json", check=False)
        try:
            rv = json.loads(raw)
        except ValueError:
            continue                                  # the file was removed in this commit
        if rv != last:
            vers.append({"commit": c["hash"], "time": c["time"], "review": rv})
            last = rv
    return vers


def part_files(repo: Path, p: str) -> dict[str, list[str]]:
    """module stem -> printed part names, from the project.yaml `parts:` table (newest copy in git)."""
    raw = _git(repo, "show", f"HEAD:projects/{p}/project.yaml", check=False)
    try:
        parts = (yaml.safe_load(raw) or {}).get("parts") or {}
    except yaml.YAMLError:
        parts = {}
    mods: dict[str, list[str]] = {}
    for name, spec in parts.items():
        f = spec.get("file") if isinstance(spec, dict) else None
        if f:
            mods.setdefault(Path(f).stem, []).append(name)
    return mods


def _module_for(part: str, mods: dict[str, list[str]]) -> str | None:
    for m, names in mods.items():
        if part in names:
            return m
    for m in mods:                                     # fallback: hub_r -> hub, wing_l1 -> wing
        if part == m or part.startswith(m + "_") or re.sub(r"_?[lr]?\d*$", "", part) == m:
            return m
    return None


def stage_at(repo: Path, p: str, commit: str, kind: str = "review") -> tuple[str, str]:
    out = _git(repo, "ls-tree", "-l", "-r", commit, f"projects/{p}/parts", check=False)
    sizes = [int(l.split()[3]) for l in out.splitlines() if l.strip().endswith(".py") and len(l.split()) > 3]
    if not sizes:
        return "before parts", "no part files in the tree at that commit"
    med = statistics.median(sizes)
    if med < ROUGH_BYTES:
        return "rough", f"{len(sizes)} part files, median {int(med)} bytes (stubs)"
    return ("final review" if kind == "review" else "detail",
            f"{len(sizes)} real part files, median {int(med)} bytes")


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9_]{2,}", s.lower())[:60]}


def _sim(a: dict, b: dict) -> float:
    """Word overlap of two findings if they can be the same one in two review rounds (same part, or very similar), else 0."""
    wa, wb = _words(a.get("issue", "")), _words(b.get("issue", ""))
    sim = len(wa & wb) / max(1, len(wa | wb))
    return sim if sim >= (SIM_MIN if a.get("part") == b.get("part") else 0.6) else 0.0


def _modules_changed(cms: list[dict], lo: int, hi: int, p: str) -> list[str]:
    """part modules (and shared helpers) edited in commits lo..hi inclusive."""
    pre, mods = f"projects/{p}/parts/", set()
    for c in cms[lo:hi + 1]:
        mods |= {Path(f).stem for f in c["files"] if f.startswith(pre) and f.endswith(".py")}
    return sorted(mods)


def _cost(cms: list[dict], i: int, j: int | None, target: str | None, p: str, mods: dict) -> dict:
    """Cost of a problem recorded at commit index i, fixed at commit index j (None = still open)."""
    if j is None:
        return {"wall_minutes": None, "active_minutes_est": None, "parts_redrawn": [], "target_redrawn": False}
    wall = (_t(cms[j]["time"]) - _t(cms[i]["time"])).total_seconds() / 60
    active = sum(min(GAP_CAP_MIN, (_t(cms[k]["time"]) - _t(cms[k - 1]["time"])).total_seconds() / 60) for k in range(i + 1, j + 1))
    red = _modules_changed(cms, i + 1, j, p)
    return {"wall_minutes": round(wall), "active_minutes_est": round(active), "parts_redrawn": red,
            "target_redrawn": bool(target and target in red)}


def _fix_index(cms: list[dict], i: int, upto: int, target: str | None, p: str) -> tuple[int, str]:
    """Commit that fixed it: first after i touching the finding's own module, else first touching any part, else `upto`."""
    pre = f"projects/{p}/parts/"
    for k in range(i + 1, upto + 1):
        if target and f"{pre}{target}.py" in cms[k]["files"]:
            return k, "first commit after the finding that redrew its part"
    for k in range(i + 1, upto + 1):
        if any(f.startswith(pre) and f.endswith(".py") for f in cms[k]["files"]):
            return k, "first commit after the finding that redrew any part (its own part was not touched)"
    return upto, "no part was redrawn; closed by the next review/check result"


def build(repo: Path | str | None, p: str) -> dict:
    repo = Path(repo or ROOT)
    cms = commits(repo, p)
    if not cms:
        raise ValueError(f"no git history for projects/{p}")
    idx = {c["hash"]: n for n, c in enumerate(cms)}
    vers = review_versions(repo, p, cms)
    mods = part_files(repo, p)
    problems: list[dict] = []

    # --- design-review findings: followed from round to round
    open_: list[dict] = []                    # [{problem, finding}] still present in the latest round
    for n, v in enumerate(vers):
        rv, ci = v["review"], idx[v["commit"]]
        finds = rv.get("findings") or []
        nxt: list[dict] = []
        pairs = sorted(((_sim(o["finding"], f), a, b) for a, o in enumerate(open_) for b, f in enumerate(finds)), reverse=True)
        used_o, used_f = set(), set()
        for sim, a, b in pairs:                   # best matches first, each finding used once
            if sim and a not in used_o and b not in used_f:
                used_o.add(a), used_f.add(b)
                open_[a]["problem"]["rounds_seen"].append(v["commit"][:8])
                nxt.append({"problem": open_[a]["problem"], "finding": finds[b]})
        open_ = [o for a, o in enumerate(open_) if a not in used_o]
        for b, f in enumerate(finds):
            if b in used_f:
                continue
            stage, why = stage_at(repo, p, v["commit"])
            target = _module_for(f.get("part", ""), mods)
            pr = {"id": f"{p}-{len(problems) + 1}", "source": "review", "severity": f.get("severity"), "part": f.get("part"),
                  "issue": (f.get("issue") or "")[:600], "fix": (f.get("fix") or "")[:400],
                  "found_commit": v["commit"][:8], "found_time": v["time"], "review_round": n + 1,
                  "review_verdict": rv.get("verdict"), "stage": stage, "stage_why": why, "rounds_seen": [v["commit"][:8]],
                  "_ci": ci, "_target": target}
            problems.append(pr)
            nxt.append({"problem": pr, "finding": f})
        for o in open_:                       # gone from this round: fixed between its first round and this one
            pr = o["problem"]
            j, how = _fix_index(cms, pr["_ci"], ci, pr["_target"], p)
            pr.update(status="resolved", resolved_commit=cms[j]["hash"][:8], resolved_time=cms[j]["time"], resolved_how=how,
                      **_cost(cms, pr["_ci"], j, pr["_target"], p, mods))
        open_ = nxt
    last = vers[-1]["review"].get("verdict") if vers else None
    for o in open_:
        pr = o["problem"]
        pr.update(status="accepted at PASS" if last == "PASS" and pr["severity"] == "minor" else "open",
                  resolved_commit=None, resolved_time=None, resolved_how=None, **_cost(cms, pr["_ci"], None, None, p, mods))

    # --- failed checks recorded in commit messages: a FAIL is a problem until the next PASS of the same kind
    pending: dict[str, dict] = {}
    for k, c in enumerate(cms):
        if f"projects/{p}/review.json" in c["files"]:
            continue                                         # review rounds are already covered above
        for m in _EVENT.finditer(c["subject"] + "\n" + c["body"]):
            kind, res = m.group(1).lower().replace("quick check", "check"), m.group(2).upper()
            if res == "FAIL" and kind not in pending:
                stage, why = stage_at(repo, p, c["hash"], "check")
                pr = {"id": f"{p}-{len(problems) + 1}", "source": "check", "severity": None, "part": None,
                      "issue": f"{kind} FAIL: {c['subject'][:300]}", "fix": "", "found_commit": c["hash"][:8],
                      "found_time": c["time"], "stage": stage, "stage_why": why, "rounds_seen": [c["hash"][:8]],
                      "_ci": k, "_target": None}
                problems.append(pr)
                pending[kind] = pr
            elif res == "PASS" and kind in pending:
                pr = pending.pop(kind)
                pr.update(status="resolved", resolved_commit=c["hash"][:8], resolved_time=c["time"],
                          resolved_how=f"next {kind} PASS", **_cost(cms, pr["_ci"], k, None, p, mods))
    for pr in pending.values():
        pr.update(status="open", resolved_commit=None, resolved_time=None, resolved_how=None, **_cost(cms, pr["_ci"], None, None, p, mods))

    for pr in problems:
        pr.pop("_ci"), pr.pop("_target")
    d = {"project": p, "built_from": "git history", "cost_is_estimate": True,
         "note": "Costs are estimates from commit times and edited part files; token usage is measured and listed under sessions.",
         "commits": [{"hash": c["hash"][:8], "time": c["time"], "subject": c["subject"][:160],
                      "parts": _modules_changed([c], 0, 0, p)} for c in cms],
         "reviews": [{"commit": v["commit"][:8], "time": v["time"], "date": v["review"].get("date"), "verdict": v["review"].get("verdict"),
                      "findings": len(v["review"].get("findings") or [])} for v in vers],
         "problems": problems, "sessions": load_sessions(repo, p)}
    d["totals"] = totals(d)
    return d


def totals(d: dict) -> dict:
    ps = d["problems"]
    by_stage = {s: sum(1 for x in ps if x["stage"] == s) for s in STAGES}
    redraws = sorted({m for x in ps for m in x.get("parts_redrawn") or []})
    tok = {k: sum(s.get(k, 0) for s in d["sessions"]) for k in ("input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens")}
    return {"problems": len(ps), "by_stage": by_stage, "open": sum(1 for x in ps if x["status"] == "open"),
            "active_minutes_est": sum(x.get("active_minutes_est") or 0 for x in ps), "parts_redrawn": redraws, "tokens": tok}


# --- token usage from a Claude Code session log -------------------------------------------------------------------

def session_usage(jsonl: Path | str) -> dict:
    """Sum the `usage` fields of a Claude Code session log (~/.claude/projects/<cwd>/<session>.jsonl).
    The log repeats one API message's usage on every content block it wrote, so usage is counted once per message id."""
    per: dict[str, dict] = {}
    first = last = sid = None
    models: set[str] = set()
    for line in Path(jsonl).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        sid = sid or d.get("sessionId")
        ts = d.get("timestamp")
        if ts:
            first, last = first or ts, ts
        m = d.get("message")
        if not isinstance(m, dict) or not isinstance(m.get("usage"), dict):
            continue
        u = m["usage"]
        key = m.get("id") or d.get("uuid") or str(len(per))
        cur = per.get(key, {})
        per[key] = {k: max(cur.get(k, 0), u.get(k) or 0) for k in
                    ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
        if m.get("model"):
            models.add(m["model"])
    s = lambda k: sum(x[k] for x in per.values())
    return {"session_id": sid, "messages": len(per), "first": first, "last": last, "models": sorted(models),
            "input_tokens": s("input_tokens"), "output_tokens": s("output_tokens"),
            "cache_creation_tokens": s("cache_creation_input_tokens"), "cache_read_tokens": s("cache_read_input_tokens")}


def _sessions_file(repo: Path, p: str) -> Path:
    return repo / "learning" / "diary" / f"{p}.sessions.json"


def load_sessions(repo: Path, p: str) -> list[dict]:
    try:
        return json.loads(_sessions_file(repo, p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def log_session(repo: Path | str | None, p: str, jsonl: Path | str, label: str = "") -> dict:
    """Append (or refresh, same session id) one session's measured token usage to the project's diary."""
    repo = Path(repo or ROOT)
    u = session_usage(jsonl)
    u["label"] = label
    rows = [r for r in load_sessions(repo, p) if not (u["session_id"] and r.get("session_id") == u["session_id"])] + [u]
    f = _sessions_file(repo, p)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return u


def newest_session_log() -> Path | None:
    logs = sorted((Path.home() / ".claude" / "projects").glob("*/*.jsonl"), key=lambda f: f.stat().st_mtime)
    return logs[-1] if logs else None


# --- output -------------------------------------------------------------------------------------------------------

def _short(mods: list[str]) -> str:
    return f"{len(mods)}: {', '.join(mods[:3])}{'...' if len(mods) > 3 else ''}" if mods else ""


def render_md(d: dict) -> str:
    t = d["totals"]
    L = [f"# Diary: {d['project']}", "",
         f"{t['problems']} problems recorded ({t['open']} open). Found at: " + ", ".join(f"{s} {n}" for s, n in t["by_stage"].items()) + ".",
         f"Estimated active fix time {t['active_minutes_est']} min; parts redrawn: {', '.join(t['parts_redrawn']) or 'none'}. "
         "Costs are estimates from git (commit times, edited part files).", ""]
    if d["reviews"]:
        L += ["## Review rounds", "", "| Commit | Date | Verdict | Findings |", "|---|---|---|---|"]
        L += [f"| {r['commit']} | {r['date']} | {r['verdict']} | {r['findings']} |" for r in d["reviews"]]
        L.append("")
    L += ["## Problems", "", "| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |", "|---|---|---|---|---|---|---|---|"]
    for x in d["problems"]:
        what = x["issue"].replace("|", "/").replace("\n", " ")[:90]
        L.append(f"| {x['id'].split('-')[-1]} | {x['severity'] or x['source']} | {x['part'] or ''} | {x['stage']} | {x['status']} | "
                 f"{x.get('active_minutes_est') if x.get('active_minutes_est') is not None else ''} | {_short(x.get('parts_redrawn') or [])} | {what} |")
    if d["sessions"]:
        k = t["tokens"]
        L += ["", "## Token use (measured, from session logs)", "",
              f"input {k['input_tokens']:,}, output {k['output_tokens']:,}, cache write {k['cache_creation_tokens']:,}, cache read {k['cache_read_tokens']:,} "
              f"across {len(d['sessions'])} session(s)."]
    return "\n".join(L) + "\n"


def write(repo: Path | str | None, p: str) -> Path:
    repo = Path(repo or ROOT)
    d = build(repo, p)
    out = repo / "learning" / "diary"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{p}.json").write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    (out / f"{p}.md").write_text(render_md(d), encoding="utf-8")
    return out / f"{p}.json"


def all_projects(repo: Path | str | None = None) -> list[str]:
    repo = Path(repo or ROOT)
    return sorted(q.name for q in (repo / "projects").iterdir()
                  if q.is_dir() and _git(repo, "log", "-1", "--format=%H", "--", f"projects/{q.name}", check=False).strip())
