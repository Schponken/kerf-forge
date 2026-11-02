"""Optimise, then explain (docs/VISION.md section 2): `kerf optimise <p>` searches the params project.yaml declares
under `optimise:` for a lighter / cheaper / stronger design that still passes every check, and writes the trade-off.

  optimise:
    vary: [arm_t, arm_w]            # params (their min / max / step bound the search), or {name: [min, max, step]}
    goal: {minimise: mass}          # mass (device g) | cost (filament + bought parts, USD) | {maximise: <requirement id>}
    max_runs: 12                    # evaluations (each is a check run on a scratch copy; the project is never touched)
    mode: check                     # the kerf/modes.py depth each evaluation runs (check = every check incl. FEA)

Search: a pattern search from the current values. Each round tries one step up and one step down on every param and
moves to the best candidate; an infeasible design is ranked by how far its failing requirements miss (so the search
first walks into the passing region), a passing one by the goal. It stops at the budget or when no step helps, then
halves the steps once. The table lists every evaluation; the explanation names what stops it going further: the
binding requirement (least margin) at the best point and the check each rejected neighbour failed.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / ".cache" / "optimise"


def use(row: dict) -> float | None:
    """How much of its limit a requirement row uses (1 = at the limit; > 1 fails), for max / min bounds."""
    v, lim, b = row.get("value"), row.get("limit"), row.get("bound", "max")
    if not isinstance(v, (int, float)) or not isinstance(lim, (int, float)) or lim == 0:
        return None
    if b == "min":
        return lim / v if v > 0 else float("inf")
    if b == "max":
        return v / lim
    return None


def miss(rep: dict) -> float:
    """How far a design is from passing: sum over failed requirements of (use - 1), 1 per other failure."""
    tot = 0.0
    for r in rep.get("requirements") or []:
        if not r.get("ok") and not r.get("advisory"):
            u = use(r)
            tot += (u - 1.0) if u is not None and u > 1.0 else 1.0
    other = [p for p in rep.get("problems") or [] if not p.startswith("requirement '")]
    return tot + len(other)


def objective(rep: dict, goal: dict, cost_fn=None) -> float:
    """Smaller is better."""
    if "minimise" in goal:
        what = goal["minimise"]
        if what == "mass":
            m = rep.get("mass") or {}
            return float(m.get("device_g") or m.get("printed_g") or 0.0)
        if what == "cost":
            return float(cost_fn(rep) if cost_fn else 0.0)
        raise ValueError(f"optimise goal minimise: mass | cost, not '{what}'")
    if "maximise" in goal:
        rid = goal["maximise"]
        row = next((r for r in rep.get("requirements") or [] if r.get("id") == rid), None)
        if row is None or use(row) is None:
            raise ValueError(f"optimise goal maximise: requirement '{rid}' has no numeric value / limit")
        return use(row)                      # less of the limit used = more margin
    raise ValueError("optimise goal: {minimise: mass | cost} or {maximise: <requirement id>}")


def _rank(rep, goal, cost_fn):
    return (0, objective(rep, goal, cost_fn)) if rep.get("ok") else (1, miss(rep))


def _space(proj_data: dict, vary) -> dict:
    params = proj_data.get("params") or {}
    out = {}
    items = vary.items() if isinstance(vary, dict) else [(k, None) for k in vary]
    for k, rng in items:
        p = params.get(k)
        if p is None:
            raise ValueError(f"optimise: '{k}' is not a param")
        if rng:
            lo, hi, step = (float(x) for x in rng)
        else:
            if not isinstance(p, dict) or "min" not in p or "max" not in p:
                raise ValueError(f"optimise: param '{k}' needs min / max (or give [min, max, step])")
            lo, hi = float(p["min"]), float(p["max"])
            step = float(p.get("step") or (hi - lo) / 8)
        start = float(p["value"] if isinstance(p, dict) else p)
        out[k] = {"lo": lo, "hi": hi, "step": step, "start": start}
    return out


def search(space: dict, evaluate, goal: dict, max_runs: int = 12, cost_fn=None) -> dict:
    """Pattern search. evaluate(values) -> report dict. Returns {best, history}."""
    cache, hist = {}, []

    def ev(vals):
        key = tuple(round(vals[k], 6) for k in space)
        if key not in cache:
            if len(cache) >= max_runs:
                return None
            rep = evaluate(dict(vals))
            cache[key] = rep
            hist.append({"values": dict(vals), "ok": bool(rep.get("ok")), "objective": objective(rep, goal, cost_fn) if rep.get("ok") else None,
                         "miss": round(miss(rep), 3), "failed": [r["id"] for r in rep.get("requirements") or [] if not r.get("ok")]
                         + [p for p in rep.get("problems") or [] if not p.startswith("requirement '")][:3]})
        return cache[key]

    cur = {k: s["start"] for k, s in space.items()}
    step = {k: s["step"] for k, s in space.items()}
    rep = ev(cur)
    best = (_rank(rep, goal, cost_fn), cur)
    halved = False
    while True:
        moved = False
        cands = []
        for k, s in space.items():
            for sgn in (1, -1):
                v = round(cur[k] + sgn * step[k], 6)
                if s["lo"] - 1e-9 <= v <= s["hi"] + 1e-9:
                    c = dict(cur, **{k: v})
                    r = ev(c)
                    if r is not None:
                        cands.append((_rank(r, goal, cost_fn), c))
        if cands:
            rk, c = min(cands, key=lambda x: x[0])
            if rk < best[0]:
                best, cur, moved = (rk, c), c, True
        if not moved:
            if halved or len(cache) >= max_runs:
                break
            step = {k: v / 2 for k, v in step.items()}
            halved = True
        if len(cache) >= max_runs:
            break
    key = tuple(round(best[1][k], 6) for k in space)
    return {"best": best[1], "best_report": cache[key], "history": hist}


def explain(res: dict, space: dict, goal: dict) -> list[str]:
    """Why the search stopped where it did: the binding requirement and what each rejected neighbour failed."""
    rep = res["best_report"]
    L = []
    if not rep.get("ok"):
        L.append("No passing design was found in the searched range; the closest one still fails: "
                 + ", ".join(r["id"] for r in rep.get("requirements") or [] if not r.get("ok")) + ".")
    rows = [(use(r), r) for r in rep.get("requirements") or [] if use(r) is not None and r.get("ok")]
    rows.sort(key=lambda x: -x[0])
    if rows:
        u, r = rows[0]
        L.append(f"Binding: `{r['id']}` uses {u:.0%} of its limit at the best point ({r.get('value')} vs {r.get('limit')}).")
        if len(rows) > 1:
            L.append("Next closest: " + ", ".join(f"`{x['id']}` {uu:.0%}" for uu, x in rows[1:4]) + ".")
    best = res["best"]
    for h in res["history"]:
        d = {k: h["values"][k] - best[k] for k in space if abs(h["values"][k] - best[k]) > 1e-9}
        if len(d) == 1 and not h["ok"]:
            (k, dv), = d.items()
            L.append(f"{k} {'+' if dv > 0 else ''}{dv:g} fails {', '.join(map(str, h['failed'][:3]))}.")
    return L


def write_md(name: str, res: dict, space: dict, goal: dict, out: Path) -> Path:
    keys = list(space)
    gname = goal.get("minimise") or f"use of {goal.get('maximise')}"
    L = [f"# Optimise — {name}", "", f"Goal: {'minimise ' + gname if 'minimise' in goal else 'maximise the margin of ' + goal['maximise']}; "
         f"every check must pass. Searched: " + ", ".join(f"{k} {s['lo']:g}..{s['hi']:g} (step {s['step']:g}, was {s['start']:g})"
                                                       for k, s in space.items()) + ".", "",
         "## Result", ""]
    b = res["best"]
    L.append("Best: " + ", ".join(f"**{k} = {b[k]:g}**" for k in keys) + (" (passes every check)" if res["best_report"].get("ok") else " (still failing)"))
    L += [""] + [f"- {x}" for x in explain(res, space, goal)] + ["", "## Every evaluation", "",
          "| " + " | ".join(keys) + f" | passes | {gname} | failing |", "|" + "---|" * (len(keys) + 3)]
    for h in res["history"]:
        o = "-" if h["objective"] is None else f"{h['objective']:.3g}"
        L.append("| " + " | ".join(f"{h['values'][k]:g}" for k in keys) + f" | {'yes' if h['ok'] else 'no'} | {o} | "
                 + (", ".join(map(str, h["failed"][:4])) or "-") + " |")
    L += ["", "Apply it by setting these values in project.yaml `params` (Studio: the sliders), then `kerf build`."]
    out.mkdir(parents=True, exist_ok=True)
    f = out / "OPTIMISE.md"
    f.write_text("\n".join(L) + "\n", encoding="utf-8")
    js = json.dumps({"goal": goal, "space": space, "best": b, "history": res["history"]}, indent=1, default=str)
    (out / "optimise.json").write_text(js, encoding="utf-8")
    return f


def run(name: str, evaluate=None) -> dict:
    from . import pipeline, project as P
    src = P.resolve_dir(name)
    data = yaml.safe_load((src / "project.yaml").read_text(encoding="utf-8")) or {}
    spec = data.get("optimise")
    if not spec:
        raise ValueError(f"{src.name}/project.yaml has no `optimise:` block (vary, goal, max_runs)")
    space = _space(data, spec["vary"])
    goal = spec.get("goal") or {"minimise": "mass"}
    mode = spec.get("mode", "check")
    if evaluate is None:
        dst = SCRATCH / src.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "review.json"))

        def evaluate(vals):                      # the scratch copy's report; the project's own out/ is never written
            return pipeline.run(str(dst), overrides=vals, mode=mode)
    res = search(space, evaluate, goal, int(spec.get("max_runs", 12)))
    f = write_md(data.get("name", src.name), res, space, goal, src / "out")
    return {**res, "file": str(f)}
