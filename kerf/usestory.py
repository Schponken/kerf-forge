"""Use story (docs/VISION.md section 2): who uses the thing, where, how often and what goes wrong, written into
project.yaml and turned into requirements, so a design is checked against its life and not only its shape.

  use_story:
    who: "a hobby FPV pilot, flying alone"
    where: [outdoor]                       # indoor | outdoor | desk | car | field | workshop | water ... (free tags)
    how_often: "3 sessions a week, 6 packs each"
    goes_wrong:
      - {hazard: heat, max_c: 45, why: "summer sun at the field; stored indoors"}
      - {hazard: rain, why: "caught in a drizzle"}
      - {hazard: gloves, handles: [{item: battery, from: [0, 0, 1]}], why: "winter flying"}
      - {hazard: drop, height_m: 0.75, survive: false, consequence: "knocked off the desk: a link may crack; reprint it"}
      - {hazard: crash, speed_m_s: 15, survive: false, consequence: "an arm breaks first; swap it in 5 minutes"}
      - {hazard: other, what: "grabs a 150 g object", covered_by: [torque_shoulder, torque_elbow]}

Each hazard becomes requirement checks (`requirements()`), run with the project's own requirements:
- heat   -> `heat_limit`: every printed part's material heat deflection temperature (ISO 75, from the catalog's
            datasheet values) is above max_c: at 0.45 MPa for every part, at 1.8 MPa for parts with a strength case.
- rain   -> `rain_cover`: every rain-sensitive electronic item (boards, flight controllers, ESCs, receivers, video
            transmitters, power supplies...) is roofed from above by another part in the home pose.
- gloves -> `access_opening` per handled item: a gloved finger's opening (38 mm; bare 32 mm; FAA HF-STD-001
            Exhibit 4.4.3.2) clear from the item's touch face to outside the assembly.
- drop / crash -> `impact_case`: the impact speed and the average stopping force from the work-energy balance
            (F * s = m g (h + s) for a drop, F * s = 1/2 m v^2 for a crash; s = stop_mm, default 2 mm, a printed part
            on a hard floor), and proof that a strength case (`fea_static` with `case: drop` / `crash`) carries it.
            `survive: false` with a `consequence` records an accepted failure instead (what breaks, how it's fixed).
- other  -> `story_covered`: the listed requirements exist and pass.
The impact numbers are also available to requirement expressions as story_drop_n, story_drop_v, story_crash_n,
story_crash_v (e.g. `force_n: [0, 0, "-story_drop_n * 0.5"]`).

A project needs a use story unless it is listed in LEGACY (the projects made before use stories; they get one as
they are revisited).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

G = 9.80665
HAZARDS = ("drop", "crash", "heat", "rain", "gloves", "other")
STOP_MM = 2.0              # default stopping distance of an impact: a printed part on a hard floor (conservative)
FINGER_OPENING_MM = {"gloved": 38.0, "bare": 32.0}   # FAA HF-STD-001 Exhibit 4.4.3.2, one or two fingers, push button
# catalog paths of electronics that must stay dry (a catalog entry with `waterproof: true` is exempt)
RAIN_SENSITIVE = ("boards.", "drone.stacks.", "drone.escs.", "drone.fcs.", "drone.vtx.", "drone.gps.",
                  "electronics.receivers.", "electronics.becs.", "electronics.supplies.")
LEGACY = {"bionic_finger", "check_shelf_bracket", "fpv_wing", "pan_tilt", "robotic_gripper_claw",
          "robotic_gripper_desk", "servo_link", "tvc_drone"}


def story(proj) -> dict | None:
    return proj.data.get("use_story")


def problems(proj) -> list[str]:
    """Schema problems: missing story (for a new project), missing fields, unknown hazards, missing numbers."""
    s = story(proj)
    if s is None:
        from .project import PROJECTS
        in_repo = Path(proj.dir).resolve().parent == Path(PROJECTS).resolve()
        if proj.dir.name in LEGACY or proj.data.get("check_only") or not in_repo:   # scratch / test copies: not required
            return []
        return ["use_story: missing. Every new project states who uses it, where, how often and what goes wrong "
                "(docs/ARCHITECTURE.md 'use_story'); the hazards become requirements"]
    out = [f"use_story: '{k}' missing" for k in ("who", "where", "how_often", "goes_wrong") if k not in s]
    for i, h in enumerate(s.get("goes_wrong") or []):
        kind = h.get("hazard")
        tag = f"use_story.goes_wrong[{i}] ({kind})"
        if kind not in HAZARDS:
            out.append(f"{tag}: unknown hazard (use {', '.join(HAZARDS)})")
            continue
        if h.get("survive", True) is False:
            if not h.get("consequence"):
                out.append(f"{tag}: survive: false needs a `consequence` (what breaks and how it is fixed)")
            continue
        need = {"drop": ["height_m"], "crash": ["speed_m_s"], "heat": ["max_c"], "gloves": ["handles"],
                "other": ["what", "covered_by"]}.get(kind, [])
        out += [f"{tag}: needs `{k}`" for k in need if k not in h]
    return out


def _mass_kg(proj) -> float:
    from .checks import item_mass_g
    return sum(item_mass_g(it) for it in proj.items.values() if it.role != "keepout") / 1000.0


def impact(h: dict, m_kg: float) -> dict:
    """Impact speed (m/s), energy (J) and average stopping force (N) of a drop or crash hazard."""
    s = float(h.get("stop_mm", STOP_MM)) / 1000.0
    if h["hazard"] == "drop":
        hm = float(h["height_m"])
        v = math.sqrt(2 * G * hm)
        e = m_kg * G * (hm + s)
    else:
        v = float(h["speed_m_s"])
        e = 0.5 * m_kg * v * v
    return {"v_m_s": round(v, 2), "energy_j": round(e, 2), "force_n": round(e / s, 1), "stop_mm": s * 1000, "mass_kg": round(m_kg, 3)}


def numbers(proj) -> dict:
    """story_<hazard>_n / _v for requirement expressions (worst of each kind; survived hazards only)."""
    out = {}
    s = story(proj) or {}
    m = None
    for h in s.get("goes_wrong") or []:
        if h.get("hazard") in ("drop", "crash") and h.get("survive", True) is not False and not problems_of(h):
            m = _mass_kg(proj) if m is None else m
            r = impact(h, float(h.get("mass_kg", m)))
            k = h["hazard"]
            out[f"story_{k}_n"] = max(out.get(f"story_{k}_n", 0.0), r["force_n"])
            out[f"story_{k}_v"] = max(out.get(f"story_{k}_v", 0.0), r["v_m_s"])
    return out


def problems_of(h: dict) -> bool:
    need = {"drop": "height_m", "crash": "speed_m_s"}.get(h.get("hazard"))
    return bool(need and need not in h)


def requirements(proj) -> list[dict]:
    """The requirement entries the use story adds (ids story_*), in run_all's format."""
    s = story(proj) or {}
    out, seen = [], {}
    for i, h in enumerate(s.get("goes_wrong") or []):
        kind, why = h.get("hazard"), h.get("why", "")
        if kind not in HAZARDS or h.get("survive", True) is False:
            continue
        seen[kind] = seen.get(kind, 0) + 1
        rid = h.get("id", f"story_{kind}" + ("" if seen[kind] == 1 else f"_{seen[kind]}"))
        if kind == "heat" and "max_c" in h:
            out.append({"id": rid, "check": "heat_limit", "max_c": h["max_c"], "why": why or f"use story: up to {h['max_c']} °C"})
        elif kind == "rain":
            out.append({"id": rid, "check": "rain_cover", "why": why or "use story: rain"})
        elif kind == "gloves":
            for j, hd in enumerate(h.get("handles") or []):
                out.append({"id": f"{rid}_{hd['item']}", "check": "access_opening", "item": hd["item"],
                            "from_dir": hd.get("from", [0, 0, 1]), "gloved": True, "ignore": hd.get("ignore", []),
                            "why": why or f"use story: {hd['item']} handled with gloves"})
        elif kind in ("drop", "crash") and not problems_of(h):
            out.append({"id": rid, "check": "impact_case", "hazard": kind, "index": i, "why": why or f"use story: {kind}"})
        elif kind == "other" and "covered_by" in h:
            out.append({"id": rid, "check": "story_covered", "ids": list(h["covered_by"]), "what": h.get("what", ""),
                        "why": why or f"use story: {h.get('what', '')}"})
    gw = [h for h in s.get("goes_wrong") or [] if h.get("hazard") == "gloves" and h.get("survive", True) is not False]
    gloved = {hd["item"] for h in gw for hd in h.get("handles") or []}
    for hd in s.get("handles") or []:          # things touched in use: a bare finger (gloved when the story says so)
        if hd["item"] in gloved:
            continue
        out.append({"id": f"story_handle_{hd['item']}", "check": "access_opening", "item": hd["item"],
                    "from_dir": hd.get("from", [0, 0, 1]), "gloved": bool(gw), "ignore": hd.get("ignore", []),
                    "why": f"use story: {hd['item']} is handled {hd.get('how_often', 'in use')}"})
    if s.get("field_repair"):
        out.append({"id": "story_field_repair", "check": "repair_access", "parts": list(s["field_repair"]),
                    "why": "use story: these parts are replaced in the field, on the finished device"})
    return out


def summary(proj) -> dict | None:
    """For the report, ASSEMBLY.md and Studio: the story, with accepted failures listed plainly."""
    s = story(proj)
    if s is None:
        return None
    acc = [{"hazard": h.get("hazard"), "consequence": h.get("consequence", "")} for h in s.get("goes_wrong") or []
           if h.get("survive", True) is False]
    return {"who": s.get("who"), "where": s.get("where"), "how_often": s.get("how_often"),
            "hazards": [h.get("hazard") for h in s.get("goes_wrong") or []], "accepted_failures": acc}


# ---- the checks the story adds (registered with kerf/requirements.py) ----

from .requirements import check  # noqa: E402


def _hdt(material: str) -> tuple:
    from . import catalog
    m = catalog.get(f"materials.{material}")
    return m.get("hdt_045_c"), m.get("hdt_18_c")


@check("heat_limit")
def heat_limit(proj, asm, max_c, parts=None):
    """Every printed part keeps its shape at max_c: the material's ISO 75 heat deflection temperature (datasheet,
    catalog) above max_c, at 0.45 MPa for every part and at 1.8 MPa for parts that carry a strength case."""
    stressed = {r.get("part") for r in proj.data.get("requirements") or [] if r.get("check") in ("fea_static", "cantilever_stress")}
    bad, worst = [], math.inf
    for pid, it in proj.printed.items():
        if parts and pid not in parts:
            continue
        mat = it.spec.get("material", "PETG")
        h045, h18 = _hdt(mat)
        hdt, at = (h18, "1.8 MPa") if pid in stressed else (h045, "0.45 MPa")
        if hdt is None:
            bad.append(f"{pid}: {mat} has no heat deflection value in its datasheet; pick a rated material")
            continue
        worst = min(worst, hdt - max_c)
        if hdt <= max_c:
            bad.append(f"{pid}: {mat} softens at {hdt} °C ({at}) <= {max_c} °C")
    v = None if worst is math.inf else round(worst, 1)
    return {"ok": not bad, "value": v, "limit": 0,
            "detail": ("; ".join(bad) if bad else f"smallest margin {v} °C between a part's heat deflection temperature and {max_c} °C")}


def _ray_up_hits(origins: np.ndarray, V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Which origins (N, 3) have a triangle of mesh (V, F) straight above them (+Z ray, Möller-Trumbore)."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    e1, e2 = b - a, c - a
    d = np.array([0.0, 0.0, 1.0])
    p = np.cross(d, e2)                          # (T, 3)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    hits = np.zeros(len(origins), bool)
    for k, o in enumerate(origins):
        t0 = o - a
        u = np.einsum("ij,ij->i", t0, p) * inv
        q = np.cross(t0, e1)
        w = (q @ d) * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        hits[k] = bool(np.any(ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0)))
    return hits


def rain_sensitive(proj) -> list[str]:
    from . import catalog
    out = []
    for iid, it in proj.items.items():
        key = it.spec.get("catalog") or ""
        if it.role != "purchased" or not key.startswith(RAIN_SENSITIVE):
            continue
        try:
            if catalog.get(key).get("waterproof"):
                continue
        except Exception:  # noqa: BLE001
            pass
        out.append(iid)
    return out


@check("rain_cover")
def rain_cover(proj, asm, items=None, grid=5, min_cover=1.0):
    """Rain falls straight down: each rain-sensitive item's top is roofed by another part in the home pose (a grid of
    points on its top face, each with a part above it). Reports the least-covered item's covered fraction."""
    from . import assembly as A, geom
    A.solve(asm)
    sens = items or rain_sensitive(proj)
    if not sens:
        return {"ok": True, "value": 1.0, "limit": min_cover, "detail": "no rain-sensitive electronics in this project"}
    roofs = [(i, geom.mesh(it.shape, tol=0.2, ang=0.4)) for i, it in proj.items.items()
             if it.role != "keepout" and it.shape is not None and i not in sens]
    worst, rows = 1.0, []
    for iid in sens:
        lo, hi = geom.bbox(proj.items[iid].shape)
        xs, ys = np.linspace(lo[0], hi[0], grid + 2)[1:-1], np.linspace(lo[1], hi[1], grid + 2)[1:-1]
        P = np.array([[x, y, hi[2] + 0.05] for x in xs for y in ys])
        covered = np.zeros(len(P), bool)
        for _, (V, F) in roofs:
            vlo, vhi = V.min(0), V.max(0)
            if vhi[2] <= hi[2]:
                continue
            todo = ~covered & (P[:, 0] >= vlo[0]) & (P[:, 0] <= vhi[0]) & (P[:, 1] >= vlo[1]) & (P[:, 1] <= vhi[1])
            if todo.any():
                covered[todo] = _ray_up_hits(P[todo], V, F)
        f = float(covered.mean())
        rows.append(f"{iid} {f:.0%}")
        worst = min(worst, f)
    return {"ok": worst >= min_cover, "value": round(worst, 2), "limit": min_cover,
            "detail": "share of each sensitive item's top roofed from above: " + ", ".join(rows)}


@check("access_opening")
def access_opening(proj, asm, item, from_dir=(0, 0, 1), gloved=False, ignore=(), diameter_mm=None):
    """A finger reaches `item` from `from_dir`: a cylinder of the access-opening diameter (FAA HF-STD-001 Exhibit
    4.4.3.2: 38 mm gloved, 32 mm bare) from the centre of the item's face on that side to outside the assembly is
    free of every other part (except `ignore`). Value: the largest overlap volume (mm³) with another part."""
    from build123d import Cylinder, Location, Plane
    from . import assembly as A, geom
    A.solve(asm)
    D = float(diameter_mm or FINGER_OPENING_MM["gloved" if gloved else "bare"])
    d = np.array(from_dir, float)
    d /= np.linalg.norm(d)
    lo, hi = geom.bbox(proj.items[item].shape)
    c = (lo + hi) / 2
    half = (hi - lo) / 2
    start = c + d * (np.abs(d) @ half + 0.2)          # the item's face on the approach side (bbox), just outside it
    others = {i: it for i, it in proj.items.items() if it.role != "keepout" and it.shape is not None
              and i != item and i not in (ignore or ())}
    alo = np.min([geom.bbox(it.shape)[0] for it in others.values()] + [lo], axis=0)
    ahi = np.max([geom.bbox(it.shape)[1] for it in others.values()] + [hi], axis=0)
    L = float(max(np.abs(d) @ (ahi - alo), 1.0)) + 5.0
    x = np.cross(d, [1, 0, 0] if abs(d[0]) < 0.9 else [0, 1, 0])
    pl = Plane(origin=tuple(start), x_dir=tuple(x), z_dir=tuple(d))
    from build123d import Align
    cyl = pl * Cylinder(D / 2, L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    worst, who = 0.0, None
    for i, it in others.items():
        if not geom.bbox_overlap(cyl, it.shape):
            continue
        v = geom.overlap(cyl, it.shape)
        if v > worst:
            worst, who = v, i
    ok = worst < 1.0
    return {"ok": ok, "value": round(worst, 1), "limit": 1.0,
            "detail": f"{D:g} mm {'gloved' if gloved else 'bare'}-finger opening from {item} along {[round(float(v), 2) for v in d]}: "
                      + ("clear" if ok else f"blocked by {who} ({worst:.0f} mm³)")}


def _load_total_n(req, params) -> float:
    from .requirements import _ev
    tot = np.zeros(3)
    for ld in req.get("loads") or []:
        if "force_n" in ld:
            tot += np.array([_ev(v, params) for v in ld["force_n"]])
        elif "bearing_n" in ld:
            tot += np.array([_ev(v, params) for v in ld["bearing_n"]])
    return float(np.linalg.norm(tot))


@check("impact_case")
def impact_case(proj, asm, hazard, index):
    """The use story's drop / crash is carried by a strength case: some `fea_static` with `case: <hazard>` (or a
    load case named after it) applies at least the stopping force (its `share` of it, default all of it; a case
    that takes the hit at one of several identical parts states share: 1/n). Its own result proves the part holds."""
    h = story(proj)["goes_wrong"][index]
    m = float(h.get("mass_kg", _mass_kg(proj)))
    r = impact(h, m)
    p = {**(proj.params or {}), **numbers(proj)}
    dyn = [q.get("id", "impact_fea") for q in proj.data.get("requirements") or [] if q.get("check") == "impact_fea"
           and (q.get("hazard") == hazard or {"drop": "height_m", "crash": "speed_m_s"}[hazard] in q)]
    if dyn:                                        # the stiffness-based impact (kerf/req_dynamic.py) answers it
        return {"ok": True, "value": r["force_n"], "limit": r["force_n"],
                "detail": f"{hazard}: {r['v_m_s']} m/s, {r['energy_j']} J; simulated by {', '.join(dyn)} (impact force from "
                          f"the part's own stiffness; its row shows whether the part holds)"}
    cases = [q for q in proj.data.get("requirements") or []
             if q.get("check") == "fea_static" and hazard in (str(q.get("case", "")), str(q.get("load_case", "")))]
    if not cases:
        return {"ok": False, "value": 0.0, "limit": r["force_n"],
                "detail": f"{hazard}: {r['v_m_s']} m/s, {r['energy_j']} J, average stopping force {r['force_n']} N over "
                          f"{r['stop_mm']:g} mm ({r['mass_kg']} kg). No fea_static with case: {hazard} carries it: add one "
                          f"(loads may use story_{hazard}_n) or set survive: false with the consequence"}
    got = max(_load_total_n(q, p) / float(q.get("share", 1.0)) for q in cases)
    ids = ", ".join(q.get("id", "fea_static") for q in cases)
    return {"ok": got >= r["force_n"] * 0.999, "value": round(got, 1), "limit": r["force_n"],
            "detail": f"{hazard}: {r['v_m_s']} m/s, {r['energy_j']} J -> {r['force_n']} N average stopping force over "
                      f"{r['stop_mm']:g} mm; carried by {ids} (its own result shows the part holds)"}


@check("story_covered")
def story_covered(proj, asm, ids, what=""):
    """An `other` hazard names the requirements that answer it; they must exist (their pass / fail is reported on
    their own rows, so this row fails only when one is missing)."""
    have = {q.get("id", q.get("check")) for q in proj.data.get("requirements") or []}
    missing = [i for i in ids if i not in have]
    return {"ok": not missing, "value": len(ids) - len(missing), "limit": len(ids),
            "detail": (f"'{what}' answered by " + ", ".join(ids)) if not missing else f"'{what}': no requirement {missing}"}


from .requirements import UNITS  # noqa: E402

UNITS.update({"heat_limit": ("°C margin", "min"), "rain_cover": ("share roofed", "min"),
              "access_opening": ("mm³ blocked", "max"), "impact_case": ("N", "min"), "story_covered": ("requirements", "min")})
