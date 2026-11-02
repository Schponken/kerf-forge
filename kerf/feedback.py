"""Learn from results (docs/VISION.md section 2): what happened to a built design goes back into Kerf.

  kerf feedback <project> --part arm_1 --what broke --note "snapped at the root in a crash into a post"
                [--case crash] [--at "root"] [--file photo.jpg --file blackbox.bbl]

records one finding in projects/<p>/feedback/findings.jsonl (files copied next to it, so the evidence stays with the
project) together with what Kerf predicted for that part at the time (its failure-table row: the case it should fail
in and how much of its limit that case used, from out/report.json). `kerf feedback --learn` then reads every
project's findings and writes LEARNED.md: repeated findings become proposed rules, each with its evidence lines:
- the same part and kind of problem two or more times -> a design fix for that project;
- the same kind of problem on the same material in two or more projects -> a proposed ENGINEERING.md rule;
- a part that broke although Kerf predicted a low use (< 50 %) -> the load case missed something (a model gap);
- fits reported tight / loose -> the calibration route (`kerf calibrate` + `kerf feedback <material>`), the catalog
  correction for printed fits.
`--learn --apply` appends the proposed rules to ENGINEERING.md under "Learned from results" (each with its evidence),
for a person to keep, edit or delete in review.
"""
from __future__ import annotations

import datetime as _dt
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHAT = ("broke", "cracked", "bent", "loose", "wore", "overheated", "fit-tight", "fit-loose", "print-failed", "other")
REPEAT = 2            # findings before a pattern is proposed
LOW_USE = 0.5         # a part that broke while its worst case used less than this is a model gap


def _dir(proj_dir: Path) -> Path:
    return proj_dir / "feedback"


def record(project: str, part: str | None, what: str, note: str, case: str | None = None, at: str | None = None,
           files: list | None = None, when: str | None = None) -> dict:
    from . import project as P
    d = P.resolve_dir(project)
    if what not in WHAT:
        raise ValueError(f"--what {what}: use {', '.join(WHAT)}")
    data = __import__("yaml").safe_load((d / "project.yaml").read_text(encoding="utf-8")) or {}
    known = set(data.get("parts") or {}) | set(data.get("purchased") or {})
    if part and part not in known:
        raise ValueError(f"{d.name} has no part '{part}' (parts: {', '.join(sorted(known))})")
    fd = _dir(d)
    fd.mkdir(parents=True, exist_ok=True)
    when = when or _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    n = sum(1 for _ in (fd / "findings.jsonl").open(encoding="utf-8")) + 1 if (fd / "findings.jsonl").exists() else 1
    kept = []
    for f in files or []:
        src = Path(f)
        if not src.exists():
            raise ValueError(f"evidence file {f} not found")
        dst = fd / f"{n:03d}_{src.name}"
        shutil.copy2(src, dst)
        kept.append(dst.name)
    predicted = None
    rep_f = d / "out" / "report.json"
    material = (data.get("parts") or {}).get(part, {}).get("material", "PETG") if part in (data.get("parts") or {}) else None
    if rep_f.exists() and part:
        rep = json.loads(rep_f.read_text(encoding="utf-8"))
        row = next((r for r in rep.get("failure_modes") or [] if r.get("part") == part), None)
        if row:
            predicted = {k: row.get(k) for k in ("fails_in", "use", "how", "at")}
        predicted = predicted or {}
        predicted["fingerprint"] = rep.get("fingerprint")
    rec = {"n": n, "when": when, "project": d.name, "part": part, "material": material, "what": what, "case": case,
           "at": at, "note": note, "files": kept, "predicted": predicted}
    with (fd / "findings.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def findings(projects_dir: Path | None = None) -> list[dict]:
    out = []
    for f in sorted((projects_dir or ROOT / "projects").glob("*/feedback/findings.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def _ev(r: dict) -> str:
    pred = r.get("predicted") or {}
    p = f" (Kerf predicted: {pred.get('fails_in')} at {pred['use']:.0%})" if pred.get("use") is not None else ""
    ev = f"; evidence {', '.join(r['files'])}" if r.get("files") else ""
    return f"{r['project']} #{r['n']} {r['when']}: {r.get('part') or '-'} {r['what']}" + (f" in a {r['case']}" if r.get("case") else "") \
        + (f" at {r['at']}" if r.get("at") else "") + f": {r['note']}{p}{ev}"


def learn(rows: list[dict]) -> list[dict]:
    """Proposals from repeated findings: {kind, title, rule, evidence: [lines]}."""
    props = []
    by_part = defaultdict(list)
    by_mat = defaultdict(list)
    for r in rows:
        by_part[(r["project"], r.get("part"), r["what"])].append(r)
        if r.get("material") and r["what"] not in ("fit-tight", "fit-loose", "print-failed"):
            by_mat[(r["material"], r["what"])].append(r)
    for (proj, part, what), rs in sorted(by_part.items(), key=lambda kv: str(kv[0])):
        if part and len(rs) >= REPEAT and what not in ("fit-tight", "fit-loose"):
            props.append({"kind": "design fix", "title": f"{proj}: {part} {what} {len(rs)} times",
                          "rule": f"Redesign {part} in {proj} for the case it {what} in (strengthen the section there, or make "
                                  f"it a designed weak link with a `weak_link` requirement if it is meant to give way).",
                          "evidence": [_ev(r) for r in rs]})
    for (mat, what), rs in sorted(by_mat.items()):
        projs = sorted({r["project"] for r in rs})
        if len(projs) >= REPEAT:
            props.append({"kind": "ENGINEERING.md rule", "title": f"{mat} parts {what} in {len(projs)} projects",
                          "rule": f"{mat} parts {what} in service across projects ({', '.join(projs)}): raise the safety factor "
                                  f"for {mat} in this kind of load case, or prefer a tougher material; check the cases named below.",
                          "evidence": [_ev(r) for r in rs]})
    for r in rows:
        pred = r.get("predicted") or {}
        if r["what"] in ("broke", "cracked") and pred.get("use") is not None and pred["use"] < LOW_USE:
            props.append({"kind": "model gap", "title": f"{r['project']}: {r['part']} {r['what']} at {pred['use']:.0%} predicted use",
                          "rule": f"The load cases did not see this: {r['part']} {r['what']}" + (f" in a {r['case']}" if r.get("case") else "")
                                  + f" while its worst case ({pred.get('fails_in')}) used only {pred['use']:.0%}. Add a "
                                    f"requirement for this event (impact_fea / fea_static with its real load).",
                          "evidence": [_ev(r)]})
    fits = [r for r in rows if r["what"] in ("fit-tight", "fit-loose")]
    if fits:
        props.append({"kind": "catalog correction", "title": f"{len(fits)} fit report(s)",
                      "rule": "Print the fit coupon (`kerf calibrate <material>`), measure, and record it with "
                              "`kerf feedback <material> <report>`: that corrects the printed-fit allowances every project uses.",
                      "evidence": [_ev(r) for r in fits]})
    return props


def write(props: list[dict], out: Path) -> Path:
    L = ["# Learned from results", "", f"{len(props)} proposal(s) from the recorded findings (`kerf feedback`). "
         "Each one quotes its evidence; keep, edit or drop it.", ""]
    for p in props:
        L += [f"## {p['kind']}: {p['title']}", "", p["rule"], "", "Evidence:"] + [f"- {e}" for e in p["evidence"]] + [""]
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def apply_rules(props: list[dict], eng: Path) -> int:
    """Append ENGINEERING.md rules (with evidence) under 'Learned from results'; skips ones already there."""
    rules = [p for p in props if p["kind"] in ("ENGINEERING.md rule", "model gap")]
    text = eng.read_text(encoding="utf-8")
    add = []
    for p in rules:
        if p["title"] in text:
            continue
        add += [f"- **{p['title']}** — {p['rule']}"] + [f"  - evidence: {e}" for e in p["evidence"]]
    if not add:
        return 0
    if "## Learned from results" not in text:
        text = text.rstrip("\n") + "\n\n## Learned from results\n\nRules added by `kerf feedback --learn --apply` from recorded findings.\n"
    eng.write_text(text.rstrip("\n") + "\n" + "\n".join(add) + "\n", encoding="utf-8")
    return sum(1 for x in add if x.startswith("- **"))
