"""Learning Mode phase 3, look-back and the lesson ladder.

Reads the diaries (learning/diary/<p>.json, kerf/diary.py), turns every problem into a plain-language lesson by KEYWORD
RULES (no AI calls), says the earliest stage it could have been caught and what would have caught it, and groups the same
lesson across all projects. A lesson climbs a ladder, by how many projects it hit:
  note             seen once (one project)
  instruction      seen in 2+ projects
  proposed gate    seen in 2+ projects where it was found at final review or cost redrawn parts
A proposed gate is only a proposal for Spencer to approve: nothing here enforces anything or changes a check.
Files: learning/lessons.json (data) and learning/LESSONS.md (the short form sessions read).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import diary

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ("proposed gate", "instruction", "note")
KINDS = ("strength", "fit/collision", "wiring", "motion/assembly", "print", "access/fasteners", "process")
STAGE_RANK = {s: i for i, s in enumerate(diary.STAGES)}
# catcher types: "existing check, run earlier" | "new check" | "planning step"
EXISTING, NEW, PLAN = "existing check run earlier", "new check", "planning step"

# id, kind, lesson, earliest stage, catcher type, what would have caught it, keyword patterns (word hits in the finding)
# Patterns starting with "!!" are decisive (6), "!" strong (3: one hit is enough); plain ones are weak (need three hits). A hit in the finding's
# headline (first 140 characters) counts double. Below MIN_SCORE a problem is "unclassified".
RULES = [
    ("strength-size-from-loads", "strength", "Size load-carrying parts from their loads (section, material, safety factor) before detail drawing.",
     "rough", EXISTING, "the *_fea / fea_static / cantilever_stress requirements run on the rough parts (stress checks are paused in this repo, "
     "see PAUSED.json: until resumed, a hand check of the section in DESIGN.md)",
     [r"!_fea\b", r"!\bfea\b", r"!von mises", r"!\bmpa\b", r"!safety factor", r"!\bsnap", r"!fatigue", r"!times over", r"!load path", r"!\bstress",
      r"!too thin", r"!bending", r"!deflect", r"yield", r"strength", r"section"]),
    ("strength-infill-and-walls", "strength", "Set infill, walls and minimum wall thickness for each part from its load when the part is first drawn, not at review.",
     "rough", EXISTING, "the infill check (kerf/infill.py) and the wall-thickness check run on the rough parts",
     [r"!!infill", r"!!thin walls?", r"!walls? below", r"!wall thickness", r"!1-wall", r"!overbuilt", r"perimeters?", r"fragile", r"\bwalls?\b"]),
    ("wiring-routes-through-solid", "wiring", "Route every wire through holes and channels that exist; check the routes as soon as the parts they cross are real.",
     "detail", EXISTING, "the wiring route check in `kerf check` run after each part group is drawn, not after all of them",
     [r"!!routes? pass", r"!through solid", r"!wiring routes?", r"!routed path", r"lead channel", r"pass-?through", r"\bwires?\b"]),
    ("wiring-lead-lengths", "wiring", "Check every lead is long enough along its routed path (plus slack) when the route is first drawn.",
     "detail", EXISTING, "the wiring length check against the routed path, run when the routes are first declared",
     [r"!!leads? (are|is) too short", r"!lead length", r"!declared at \d+ ?mm", r"!too short", r"!extension", r"slack", r"\bgauge\b", r"\bawg\b", r"solder", r"connector"]),
    ("motion-stops-and-travel", "motion/assembly", "Prove each moving part's full travel, its stop and its over-travel on the rough assembly (servo throw, horn, linkage), not after detail.",
     "rough", EXISTING, "the hard_stop and clearance_min requirements swept past the stop on the rough parts, with the servo's real travel in project.yaml",
     [r"!over-?travel", r"!\btravel\b", r"!(spread|hard|end) stop", r"!stop post", r"!the stop\b", r"!past the (proxy|stop)", r"!pushrod", r"!linkage",
      r"!servo (arm|throw|travel|sweep)", r"!backlash", r"!full sweep", r"\bhorn\b", r"\bsweep", r"\bfold", r"\bplay\b", r"\bbinds?\b", r"hinge", r"pivot", r"\bstops?\b"]),
    ("assembly-cannot-be-fitted", "motion/assembly", "Walk the assembly order on the rough parts: every part must reach its place along a free path (insert paths, horn and servo order).",
     "rough", EXISTING, "insertion_paths / horn_paths (kerf/access.py) and the ASSEMBLY.md order run on the rough parts",
     [r"!cannot be (fitted|assembled|installed|inserted)", r"!can't (be )?(fit|assembl|install)", r"!can not be fitted", r"!no way (in|to)", r"!one way in",
      r"!insert path", r"!assembly order", r"!closed box", r"!horn.{0,40}(fitted|installed|reach)", r"!(fitted|installed) (first|last)", r"!would not fit", r"!did not fit"]),
    ("access-tools-and-fasteners", "access/fasteners", "Check a key or screwdriver can reach every screw, and every insert and nut is placed, when the fastener is first drawn.",
     "detail", EXISTING, "hex_key_reach, repair_access and connector_access run per part group; ball-end keys listed in ASSEMBLY.md",
     [r"!!ball-end", r"!hex key", r"!straight key", r"!screwdriver", r"!(cannot|can't) reach", r"!key.{0,30}(reach|screw)", r"!repair access", r"!heat-?set",
      r"!nut trap", r"\bkey\b", r"\binserts?\b", r"\baccess\b", r"\bscrews?\b", r"fastener", r"\bbolts?\b"]),
    ("fit-collision-clearance", "fit/collision", "Run the collision and clearance checks on the rough assembly and after every part group; fix the part that owns the overlap.",
     "rough", EXISTING, "`kerf check` (interference, clearance_min, prop_clearance) after each part group instead of once at the end",
     [r"!collid", r"!collision", r"!overlap", r"!clash", r"!interfer", r"!intersect", r"!running clearance", r"!zero clearance", r"!\brub\b", r"!foul",
      r"!no room", r"!crowded", r"!touch(es|ed)?\b", r"clearance", r"\bfit\b"]),
    ("print-orientation-and-supports", "print", "Choose print orientation, supports and plate layout when each part is drawn, from its load direction and overhangs.",
     "detail", EXISTING, "the print checks (overhang, bed fit, layer direction) in `kerf check`, read per part as it is drawn",
     [r"!print setup", r"!supports? (needed|removal)", r"!no supports", r"!overhang", r"!brim", r"!orientation", r"!boss-down", r"!floating", r"!tall on a", r"print", r"support", r"\bplate\b", r"\bbed\b", r"\blayer", r"warp", r"\btpu\b"]),
    ("process-docs-in-step", "process", "Update DESIGN.md, ASSEMBLY notes and the BOM in the same commit as the decision they record.",
     "detail", PLAN, "a planning step: DESIGN.md requirements table and part list re-read at each milestone",
     [r"!design\.md", r"!assembly\.md", r"!out of date", r"!\berc\b", r"!kicad", r"!pin table", r"documentation", r"export", r"\bbom\b"]),
]
MIN_SCORE = 3
REVIEW_EARLY = ("process-review-early", "process",
                "Review before the end: run the design reviewer (or at least its checks) on the contract and the rough parts, then again after detail, not only at the final review.",
                "rough", PLAN, "a planning step: a design-reviewer pass on the DESIGN.md contract + rough assembly, and `kerf check` at every part-group milestone")
OTHER_ID = "other-unclassified"
EARLY_MIN_FINDINGS = 5          # a first review round with at least this many problems = "found all at the end"


def _classify(text: str, head: str) -> str | None:
    """Rule with the highest score (strong hit 3, weak hit 1, doubled when in the headline); ties go to the earlier rule."""
    best, best_n = None, MIN_SCORE - 1
    for r in RULES:
        n = 0
        for pat in r[6]:
            w, pat = (6, pat[2:]) if pat.startswith("!!") else (3, pat[1:]) if pat.startswith("!") else (1, pat)
            n += w * (2 if re.search(pat, head, re.I) else 1 if re.search(pat, text, re.I) else 0)
        if n > best_n:
            best, best_n = r[0], n
    return best


def _rule(rid: str) -> tuple:
    return next(r for r in RULES if r[0] == rid)


def from_diary(d: dict) -> list[dict]:
    """The lesson occurrences in one project's diary."""
    p, occ = d["project"], []
    for x in d["problems"]:
        text = f"{x['issue']} {x.get('fix', '')}"
        rid = _classify(text, x["issue"][:140])
        if not rid:
            occ.append({"lesson": OTHER_ID, "project": p, "problem": x["id"], "severity": x.get("severity"), "part": x.get("part"),
                        "stage": x["stage"], "cost_min": x.get("active_minutes_est"), "redrawn": x.get("parts_redrawn") or [],
                        "issue": x["issue"][:140]})
            continue
        occ.append({"lesson": rid, "project": p, "problem": x["id"], "severity": x.get("severity"), "part": x.get("part"),
                    "stage": x["stage"], "cost_min": x.get("active_minutes_est"), "redrawn": x.get("parts_redrawn") or [],
                    "issue": x["issue"][:140]})
    # "review only at the end": the first review round already held a pile of problems and no earlier stage saw any
    rev = [x for x in d["problems"] if x["source"] == "review"]
    first = [x for x in rev if x.get("review_round") == 1]
    if len(first) >= EARLY_MIN_FINDINGS and all(x["stage"] == "final review" for x in first):
        sev = sum(1 for x in first if x.get("severity") in ("blocker", "major"))
        occ.append({"lesson": REVIEW_EARLY[0], "project": p, "problem": f"{p}-review-round-1", "severity": "blocker" if sev else "minor",
                    "part": None, "stage": "final review", "cost_min": sum(x.get("active_minutes_est") or 0 for x in first),
                    "redrawn": sorted({m for x in first for m in x.get("parts_redrawn") or []}),
                    "issue": f"{len(first)} problems ({sev} blocker/major) first seen in review round 1; no earlier review or check found any"})
    return occ


def level_of(evidence: list[dict]) -> str:
    projects = {e["project"] for e in evidence}
    costly = {e["project"] for e in evidence if e["stage"] == "final review" or e["redrawn"]}
    if len(projects) >= 2 and len(costly) >= 2:
        return "proposed gate"
    return "instruction" if len(projects) >= 2 else "note"


def group(diaries: list[dict]) -> dict:
    evid: dict[str, list[dict]] = {}
    by_problem: dict[str, str] = {}
    for d in diaries:
        for o in from_diary(d):
            evid.setdefault(o["lesson"], []).append(o)
            by_problem[o["problem"]] = o["lesson"]
    meta = {r[0]: r for r in RULES} | {REVIEW_EARLY[0]: REVIEW_EARLY + ([],)}
    lessons = []
    for lid, ev in evid.items():
        if lid == OTHER_ID:
            row = {"id": lid, "kind": "other", "lesson": "No rule matched these problems; read them in the diaries.", "earliest_stage": None,
                   "catcher_type": None, "catcher": None}
        else:
            m = meta[lid]
            row = {"id": lid, "kind": m[1], "lesson": m[2], "earliest_stage": m[3], "catcher_type": m[4], "catcher": m[5]}
        row.update(level="note" if lid == OTHER_ID else level_of(ev), count=len(ev), projects=sorted({e["project"] for e in ev}),
                   late_by_stages=max((STAGE_RANK[e["stage"]] - STAGE_RANK[row["earliest_stage"]] for e in ev), default=0) if row["earliest_stage"] else 0,
                   cost_min=sum(e["cost_min"] or 0 for e in ev), evidence=ev)
        lessons.append(row)
    lessons.sort(key=lambda r: (LEVELS.index(r["level"]), -len(r["projects"]), -r["count"], r["id"]))
    return {"rule": "1 project = note; 2+ projects = instruction; 2+ projects found at final review or costing redraws = proposed gate (never auto-enforced)",
            "projects": sorted(d["project"] for d in diaries), "lessons": lessons, "by_problem": by_problem}


def _names(ps: list[str]) -> str:
    return ', '.join(ps) if len(ps) <= 3 else f"{len(ps)} projects, e.g. {', '.join(ps[:3])}"


def render_md(data: dict) -> str:
    L = ["# Lessons learned (Learning Mode)", "",
         "Rebuilt by `kerf lookback` from the diaries in learning/diary/. A proposed gate is a PROPOSAL for Spencer to approve; nothing here is enforced.",
         f"Projects read: {', '.join(data['projects'])}.", ""]
    heads = {"proposed gate": "Proposed gates (need Spencer's approval)", "instruction": "Instructions (seen in 2+ projects)", "note": "Notes (seen once)"}
    for lv in LEVELS:
        rows = [r for r in data["lessons"] if r["level"] == lv and r["id"] != OTHER_ID]
        if not rows:
            continue
        L += [f"## {heads[lv]}", ""]
        for r in rows:
            stage = f"; catchable at {r['earliest_stage']}" if r["earliest_stage"] else ""
            L.append(f"- [{r['kind']}] {r['lesson']} ({r['count']}x in {_names(r['projects'])}{stage}). Would catch it: {r['catcher']}.")
        L.append("")
    other = next((r for r in data["lessons"] if r["id"] == OTHER_ID), None)
    if other:
        L.append(f"{other['count']} problem(s) matched no rule (listed in lessons.json under {OTHER_ID}).")
    return "\n".join(L).rstrip() + "\n"


def run(project: str | None = None, repo: Path | str | None = None) -> dict:
    repo = Path(repo or ROOT)
    if project:
        diary.write(repo, project)
    ds = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((repo / "learning" / "diary").glob("*.json")) if not f.name.endswith(".sessions.json")]
    data = group(ds)
    (repo / "learning" / "lessons.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    (repo / "learning" / "LESSONS.md").write_text(render_md(data), encoding="utf-8")
    lines = []
    for r in data["lessons"]:
        mine = [e for e in r["evidence"] if not project or e["project"] == project]
        if mine:
            late = f"found at {mine[0]['stage']}, catchable at {r['earliest_stage']}" if r["earliest_stage"] else "unclassified"
            lines.append(f"[{r['level']}] {r['id']}: {len(mine)} problem(s) here, {late}")
    return {"summary": "\n".join(lines) or "no problems in the diary", "data": data}
