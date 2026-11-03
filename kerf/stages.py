"""Approved Learning Mode gates for newly created projects; old projects stay unchanged.

Checks supply measured evidence. An attributed independent rough review is supplied
separately, never synthesized here and never written to review.json.
Reviewer identity is attributed local evidence, not cryptographic independence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

MARKER = "stage_gates.json"


def initialize(directory: Path) -> None:
    """Call only when creating a project, before any generation work starts."""
    path = Path(directory) / MARKER
    with path.open("x", encoding="utf-8") as f:
        json.dump({"version": 1, "designer": os.environ.get("KERF_SESSION_ID") or
                   os.environ.get("CODEX_THREAD_ID") or "designer"}, f)
        f.write("\n")


def _read(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def fingerprint(proj) -> str:
    """Include layout/research inputs absent from the geometry-only fingerprint."""
    h = hashlib.sha256(proj.fingerprint().encode())
    h.update(json.dumps(getattr(proj, "params", {}), sort_keys=True, default=str).encode())
    for path in sorted(Path(__file__).parent.glob("*.py")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    for p in sorted(proj.dir.rglob("*")):
        if p.is_file() and p.suffix in {".py", ".yaml", ".md"} and "out" not in p.relative_to(proj.dir).parts:
            h.update(str(p.relative_to(proj.dir)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def status(proj, report=None) -> dict:
    marker = proj.dir / MARKER
    if not marker.exists():
        return {"enabled": False, "detail_unlocked": True, "gates": [], "problems": []}
    from . import requirements
    config = _read(marker)
    report = _read(proj.dir / "out" / "report.json") if report is None else report
    current = fingerprint(proj)
    fresh = report.get("stage_fingerprint") == current
    reqs = proj.data.get("requirements") or []
    structural = {i for i, it in proj.printed.items() if it.spec.get("structural") or it.spec.get("load_axis")}
    for req in reqs:
        if req.get("check") in requirements.STRENGTH_CHECKS:
            structural.update(i for i in proj.printed if any(v == i or isinstance(v, list) and i in v for v in req.values()))
    moving = {j.get("name", j["child"].split(".")[0]) for j in proj.data.get("assembly", {}).get("joints", [])
              if j.get("range", [0, 0])[1] > j.get("range", [0, 0])[0]}
    powered = any(any(k in str(it.spec.get("catalog", "")) for k in ("servos.", "motors", "steppers", "boards."))
                  for it in proj.items.values())
    wiring = proj.data.get("wiring") or []
    gates = []

    def add(name, applicable, passed):
        gates.append({"id": name, "applicable": bool(applicable), "passed": bool(passed) if applicable else None})

    rows = {r.get("id"): r for r in report.get("requirements", [])}
    strength = True
    for part in structural:
        candidates = [r for r in reqs if r.get("check") in requirements.STRENGTH_CHECKS and
                      any(v == part or isinstance(v, list) and part in v for v in r.values())]
        strength &= bool(candidates) and all(rows.get(r.get("id", r["check"]), {}).get("ok") is True and
                     rows.get(r.get("id", r["check"]), {}).get("value") is not None and
                     not any(rows.get(r.get("id", r["check"]), {}).get(k) for k in ("paused", "skipped", "advisory"))
                     for r in candidates)
    add("strength-sizing", structural, fresh and strength)
    sweeps = {s.get("joint"): s for s in report.get("assembly", {}).get("sweeps", [])}
    add("block-motion", moving, fresh and all(sweeps.get(j, {}).get("clear") is True and
        sweeps.get(j, {}).get("samples", 0) >= 2 for j in moving))
    routes = {r.get("id"): r for r in report.get("electrical", {}).get("routes", [])}
    add("layout-wire-paths", wiring or powered, fresh and bool(wiring) and all(w.get("route") and
        w.get("id") in routes and not routes[w["id"]].get("hits") and
        routes[w["id"]].get("max_routed_mm", 0) > 0 and
        float(w.get("length_mm", 0)) >= routes[w["id"]].get("cut_min_mm", float("inf")) for w in wiring))
    rough = _read(proj.dir / "rough_review.json")
    add("rough-review", structural or moving or wiring or powered,
        rough.get("stage_fingerprint") == current and rough.get("stage") == "rough" and
        rough.get("independent") is True and isinstance(rough.get("reviewer"), str) and bool(rough["reviewer"].strip()) and
        rough.get("reviewer") != config.get("designer") and rough.get("findings") == [] and
        isinstance(rough.get("summary"), str) and bool(rough["summary"].strip()))
    problems = [f"stage gate {g['id']}: current evidence required before detail/export" for g in gates
                if g["applicable"] and not g["passed"]]
    if config.get("version") != 1:
        problems.append("stage gates: invalid creation marker")
    return {"enabled": True, "detail_unlocked": not problems, "gates": gates, "problems": problems}


def require_detail(proj) -> None:
    result = status(proj)
    if not result["detail_unlocked"]:
        raise ValueError("; ".join(result["problems"]))
