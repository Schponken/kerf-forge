"""Self-contained assembly viewer: `kerf build` writes projects/<p>/out/viewer.html.

One HTML file, no network: three.js subset (kerf/assets/viewer3d.js) + the page (kerf/assets/viewer.html) + the
project data (meshes, joints, report) inlined as JSON. Opens by double-click on any machine.

Kinematics come from the engine, not a re-implementation: every moving joint is nudged by a small amount with
assembly.solve(), and the rigid motion of its child item gives the joint's world axis (revolute) or direction
(linear) at the home pose. The page then composes, for each item, the motions of its ancestor joints
(root first, deepest last) about those home axes, which is exactly how a kinematic chain moves.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import numpy as np

from . import assembly as A
from . import attribution
from . import geom

ASSETS = Path(__file__).resolve().parent / "assets"
PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756", "#72B7B2", "#EECA3B", "#9D755D", "#FF9DA6", "#BAB0AC"]
PURCHASED = "#3A3F44"
KEEPOUT = "#FF6A1A"
DELTA = 1.0  # deg or mm used to probe each joint


def _mat(loc) -> np.ndarray:
    t = loc.wrapped.Transformation()
    m = np.eye(4)
    for r in range(3):
        for c in range(4):
            m[r, c] = t.Value(r + 1, c + 1)
    return m


def _b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def mesh(shape, tol=0.05, ang=0.25, face_starts=False):
    """World-space triangle mesh of a placed shape: (N x 3 float32 vertices, M x 3 uint32 triangles).
    face_starts=True also returns, for every face in shape.faces() order, the index of its first triangle."""
    km = geom.kmesh(shape)
    if km is not None:      # fused Meshy part: one mesh, treated as a single face for click-to-edit
        v, t = np.asarray(km[0], np.float32), np.asarray(km[1], np.uint32)
        return (v, t, np.zeros(1, np.uint32)) if face_starts else (v, t)
    vs, ts, starts = [], [], []
    off = ntri = 0
    for f in shape.faces():
        starts.append(ntri)
        v, t = f.tessellate(tol, ang)
        if not t:
            continue
        ntri += len(t)
        vs.append(np.array([[p.X, p.Y, p.Z] for p in v], dtype=np.float32))
        ts.append(np.array(t, dtype=np.uint32) + off)
        off += len(v)
    if not vs:
        v, t = np.zeros((0, 3), np.float32), np.zeros((0, 3), np.uint32)
    else:
        v, t = np.concatenate(vs), np.concatenate(ts)
    return (v, t, np.array(starts, dtype=np.uint32)) if face_starts else (v, t)


def joint_motion(asm, e) -> dict:
    """World axis of a moving joint at the home pose, measured from the engine's own solve()."""
    items = asm.proj.items
    A.solve(asm)
    m0 = _mat(items[e.child].shape.location)
    probe = e.home + DELTA if e.home + DELTA <= e.range[1] else e.home - DELTA
    d = probe - e.home
    A.solve(asm, {e.name: probe})
    m1 = _mat(items[e.child].shape.location)
    A.solve(asm)
    D = m1 @ np.linalg.inv(m0)
    R, t = D[:3, :3], D[:3, 3]
    out = {"name": e.name, "kind": e.kind, "range": [float(e.range[0]), float(e.range[1])], "home": float(e.home),
           "parent": f"{e.parent}.{e.pjoint}", "child": e.child, "moves": sorted(asm.subtree(e.child))}
    if e.kind == "revolute":
        th = np.radians(d)
        axis = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * np.sin(th))
        axis /= np.linalg.norm(axis)
        # a point on the axis: (I - R) p = t, least squares (the system is rank 2)
        p = np.linalg.lstsq(np.eye(3) - R, t, rcond=None)[0]
        p -= axis * np.dot(p - _mat(items[e.child].shape.location)[:3, 3], axis)  # nearest to the child origin
        out.update(axis=[round(float(x), 6) for x in axis], point=[round(float(x), 4) for x in p])
    else:
        dirn = t / d
        out.update(axis=[round(float(x), 6) for x in dirn / (np.linalg.norm(dirn) or 1)], point=[0.0, 0.0, 0.0],
                   scale=round(float(np.linalg.norm(dirn)), 6))
    return out


def data(proj, asm, rep: dict, fea: dict | None = None, assembly_md: str | None = None, preview: bool = False) -> dict:
    """Everything the page shows. Leaves the assembly at its home pose.
    fea: the build's FEA surface fields by requirement id (pipeline `fea_viz`), for the stress colours.
    assembly_md: out/ASSEMBLY.md text, for the build-it-step-by-step mode."""
    A.solve(asm)
    items = proj.items
    solid = [it.shape for it in items.values() if it.shape is not None and it.role != "keepout"]
    lo = np.min([geom.bbox(s)[0] for s in solid], axis=0)
    hi = np.max([geom.bbox(s)[1] for s in solid], axis=0)
    center = (lo + hi) / 2
    joints = [joint_motion(asm, e) for e in asm.movable]
    chain = {}
    for iid in items:
        js, n = [], iid
        while n in asm.by_child:
            e = asm.by_child[n]
            if e in asm.movable:
                js.append(e.name)
            n = e.parent
        chain[iid] = list(reversed(js))  # root-most joint first
    if preview:   # the first look: the model now, click-to-edit and build steps when the checks finish
        attr, attr_error = {}, "click-to-edit is added when the checks finish"
    else:
      try:  # click-to-edit: which line and params made each face (kerf/attribution.py)
        attr, attr_error = attribution.compute(proj), None
      except Exception as e:  # noqa: BLE001 - the viewer still works without it; the page says why
        attr, attr_error = {}, f"{type(e).__name__}: {e}"
    A.solve(asm)
    stress = _stress_cases(proj, fea or {})
    out_items = []
    for k, (iid, it) in enumerate(items.items()):
        if it.shape is None:
            continue
        v, t, fs = mesh(it.shape, face_starts=True)
        b0, b1 = geom.bbox(it.shape)
        c = (np.asarray(b0) + np.asarray(b1)) / 2
        dvec = c - center
        n = float(np.linalg.norm(dvec)) or 1.0
        role = it.role
        out_items.append({
            "id": iid, "role": role,
            "color": PALETTE[k % len(PALETTE)] if role == "printed" else (KEEPOUT if role == "keepout" else PURCHASED),
            "catalog": it.spec.get("catalog"), "material": it.spec.get("material"),
            "explode": [round(float(x), 4) for x in dvec / n * (1 + n / 100)],  # same rule as export.glb(explode=)
            "joints": chain[iid], "verts": _b64(v), "tris": _b64(t), "nv": int(len(v)), "nt": int(len(t)),
            "faceStart": _b64(fs), "src": it.spec.get("file"), "attr": _attr_compact(attr.get(iid), len(fs)),
            "catalog_source": _cat_source(it.spec.get("catalog")),
            "label": _label(it), "off_board": bool(it.spec.get("off_board")),
        })
        if iid in stress:
            out_items[-1]["stress"] = _stress_on(v, stress[iid])
    keep = ("project", "dir", "fingerprint", "printer", "params", "parts", "purchased", "requirements", "problems",
            "warnings", "bom", "files", "seconds")
    rp = {k: rep.get(k) for k in keep}
    a = rep.get("assembly") or {}
    rp["assembly"] = {k: a.get(k) for k in ("interference", "fasteners", "sweeps")}
    rp["ok"] = not rep.get("problems")
    rp["preview"] = preview                    # checks still running: the page says so instead of PASS / FAIL
    params = {}
    for name, spec in (proj.data.get("params") or {}).items():
        sp = spec if isinstance(spec, dict) else {"value": spec}
        params[name] = {k: sp.get(k) for k in ("value", "min", "max", "step", "label", "unit")}
    if preview:
        steps, steps_error = None, "the build-it steps are added when the checks finish"
    else:
      try:   # build it step by step: parts, screws, inserts and the ASSEMBLY.md text per step
        steps, steps_error = assembly_steps(proj, asm, rep, assembly_md), None
      except Exception as e:  # noqa: BLE001 - the rest of the viewer works without it; the page says why
        steps, steps_error = None, f"{type(e).__name__}: {e}"
    A.solve(asm)
    return {"items": out_items, "joints": joints, "report": rp, "params": params, "attr_error": attr_error,
            "steps": steps, "steps_error": steps_error, "project_dir": f"projects/{proj.dir.name}",
            "bounds": [[round(float(x), 3) for x in lo], [round(float(x), 3) for x in hi]]}


def _cat_source(path):
    if not path:
        return None
    try:
        from . import catalog
        e = catalog.get(path)
        return {"source": e.get("source"), "confidence": e.get("confidence"), "note": e.get("note")}
    except Exception:  # noqa: BLE001
        return None


def _attr_compact(a, nfaces):
    """Per-face [line, moves, resizes] for the page; None when the part has no attribution or faces don't line up."""
    if not a or len(a["faces"]) != nfaces:
        return None
    return {"file": a["file"], "lines": a["lines"], "whole": a["whole"],
            "faces": [[f["line"], f["moves"], f["resizes"]] for f in a["faces"]]}


def html(d: dict) -> str:
    page = (ASSETS / "viewer.html").read_text(encoding="utf-8")
    lib = (ASSETS / "viewer3d.js").read_text(encoding="utf-8")
    js = json.dumps(d, separators=(",", ":"), default=str).replace("</", "<\\/")
    title = (d["report"].get("project") or "Kerf assembly").replace("<", "&lt;")
    # str.replace takes the replacement literally; each placeholder occurs once in the template
    page = page.replace("{{TITLE}}", title)
    page = page.replace("/*DATA*/", js, 1)
    return page.replace("/*KV3*/", lib.replace("</script", "<\\/script"), 1)


def write(proj, asm, rep: dict, path, fea: dict | None = None, preview: bool = False) -> Path:
    """preview: the quick first viewer, written as soon as the parts are placed (no click-to-edit, no build steps,
    status "checks running"); the full one replaces it at the end of the run."""
    path = Path(path)
    md = path.parent / "ASSEMBLY.md"
    page = html(data(proj, asm, rep, fea=fea, assembly_md=md.read_text(encoding="utf-8") if md.exists() and not preview else None,
                     preview=preview))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(page, encoding="utf-8")
    tmp.replace(path)                       # whole file at once: Studio may be loading it while a run goes on
    return path


def embedded(path) -> dict | None:
    """The data a written viewer.html carries (meshes, report, steps), or None when it has none."""
    t = Path(path).read_text(encoding="utf-8")
    a = t.find('id="kerf-data">')
    if a < 0:
        return None
    a = t.index(">", a) + 1
    return json.loads(t[a:t.index("</script>", a)])


# ---------------------------------------------------------------- stress colours
STRESS_SCALE = 200.0   # stored per vertex as round(utilisation * 200) in one byte: 0..1.275 of the allowed stress


def _stress_cases(proj, fea: dict) -> dict:
    """Per printed part: every FEA case's surface triangles (centroids moved to the world home pose) and their
    utilisation (von Mises / allowed stress)."""
    out = {}
    for rid, viz in fea.items():
        part = viz.get("part")
        it = proj.items.get(part)
        if it is None or it.shape is None or viz.get("tris") is None or not viz.get("allow"):
            continue
        tris = np.asarray(viz["tris"], float)
        cen = tris.mean(axis=1)
        m = _mat(it.shape.location)
        world = cen @ m[:3, :3].T + m[:3, 3]
        util = np.asarray(viz["vm"], float) / float(viz["allow"])
        out.setdefault(part, []).append({"id": rid, "c": world, "u": util, "p999": viz.get("p999"), "allow": viz["allow"],
                                         "peak": viz.get("peak")})
    return out


def _stress_on(verts: np.ndarray, cases: list[dict]) -> dict:
    """Utilisation at every viewer vertex: worst case over the part's load cases, each from its 4 nearest FEA surface
    triangles (inverse-distance weighted)."""
    from scipy.spatial import cKDTree
    v = np.asarray(verts, float)
    best = np.zeros(len(v))
    for c in cases:
        k = min(4, len(c["c"]))
        d, i = cKDTree(c["c"]).query(v, k=k)
        if k == 1:
            d, i = d[:, None], i[:, None]
        w = 1.0 / np.maximum(d, 1e-3)
        best = np.maximum(best, (c["u"][i] * w).sum(axis=1) / w.sum(axis=1))
    q = np.clip(np.round(best * STRESS_SCALE), 0, 255).astype(np.uint8)
    return {"u": _b64(q), "scale": STRESS_SCALE,
            "cases": [{"id": c["id"], "use": round(float(c["p999"]) / float(c["allow"]), 4) if c.get("p999") is not None else None,
                       "allow_mpa": round(float(c["allow"]), 2), "p999_mpa": c.get("p999"), "peak_mpa": c.get("peak")} for c in cases]}


def _label(it) -> str:
    if it.role == "printed":
        return f"printed, {it.spec.get('material', 'PETG')}"
    if it.role == "keepout":
        return "clearance volume"
    from .ship import human_item
    try:
        return human_item(it)
    except Exception:  # noqa: BLE001
        return it.spec.get("catalog") or it.role


# ---------------------------------------------------------------- build it step by step
STEP_RE = re.compile(r"^Step ([1-9]\d*) — ")   # step 0 / 0b (test fit, centre servos) stay in the intro


def _sections(md: str) -> list[dict]:
    """ASSEMBLY.md split at its `## ` headings: [{title, lines}] (pictures dropped: the viewer shows the real model)."""
    out, cur = [], None
    for ln in md.splitlines():
        if ln.startswith("## "):
            cur = {"title": ln[3:].strip(), "lines": []}
            out.append(cur)
        elif cur is not None and not ln.startswith("!["):
            cur["lines"].append(ln)
    for c in out:
        while c["lines"] and not c["lines"][0].strip():
            c["lines"].pop(0)
        while c["lines"] and not c["lines"][-1].strip():
            c["lines"].pop()
    return out


def _pt(a) -> list:
    return [round(float(x), 3) for x in a]


def assembly_steps(proj, asm, rep: dict, md: str | None) -> dict | None:
    """The ASSEMBLY.md build order as data for the viewer's step-by-step mode: per step the parts already on, the
    part(s) going on with the direction they come from (same rule as the step pictures: kerf/ship.py), the heat-set
    inserts pressed first, the screws (seat point + axis, from the fastener check) and the joints that must then move
    freely, plus the step's own ASSEMBLY.md text. Intro / outro sections (tools, test fit, wiring) come along as text."""
    from . import ship
    from .iface import screw_spec
    a = rep.get("assembly") or {}
    A.solve(asm)
    st = ship.plan(asm, a.get("fasteners") or [], a.get("pins") or [])
    if not st:
        return None
    secs = _sections(md) if md else []
    by_step = {int(m.group(1)): c for c in secs if (m := STEP_RE.match(c["title"]))}
    first = next((k for k, c in enumerate(secs) if STEP_RE.match(c["title"])), len(secs))
    last = max((k for k, c in enumerate(secs) if STEP_RE.match(c["title"])), default=len(secs) - 1)
    intro = [c for c in secs[:first]]
    outro = [c for c in secs[last + 1:]]
    movable = {e.name for e in asm.movable}
    out = []
    for s in st:
        k = s["step"]
        joined = [i for x in s["attach"] for i in x["items"]]
        if s["bench_for"]:
            present = list(s["items"])
        else:
            present = [i for x in st[:k] if not x["bench_for"] or x["bench_for"] <= k for i in x["items"]]
            present += [i for i in joined if i not in present]
        groups = [{"items": [i], "off": _pt(ship._explode_offset(proj, asm, i, present)), "phase": 1} for i in s["items"]]
        groups += [{"items": list(x["items"]), "off": _pt(ship._explode_offset(proj, asm, x["via"], present)), "phase": 2,
                    "via": x["via"], "from_step": x["step"]} for x in s["attach"]]
        late = set(joined)
        screws = [{"at": _pt(j["at"]), "dir": _pt(j["dir"]), "screw": j["screw"], "len": float(j.get("length_mm") or 6),
                   "head": j.get("head"), "group": j["group"], "male": j["male"], "female": j["female"],
                   "phase": 2 if (j["male"] in late or j["female"] in late) else 1}
                  for j in s["fastener_joints"] if j.get("at") is not None and j.get("dir") is not None]
        inserts = []
        for x in s["inserts"]:
            it = proj.items[x["item"]]
            for site in getattr(it.shape, "kerf_sites", []) or []:
                if site.role != "female" or site.kind != "heatset":
                    continue
                w = it.shape.location * site.loc
                try:
                    sp = screw_spec(site.screw)
                except Exception:  # noqa: BLE001 - a size the catalog doesn't know gets a proportional glyph
                    sp = {"d": float(site.screw.lstrip("M") or 3)}
                d = float(sp.get("d") or 3)
                inserts.append({"item": x["item"], "at": _pt(geom.world_point(w, (0, 0, 0))),
                                "dir": _pt(-np.asarray(geom.world_dir(w, (0, 0, 1)))), "screw": site.screw,
                                "od": round(float(sp.get("insert_hole") or 1.4 * d), 2),
                                "len": round(float(sp.get("insert_len") or 1.5 * d), 2)})
        demos = []
        for f in s["fits"]:
            o = f.get("onto")
            if o and o.get("range") and o["joint"] in movable:
                demos.append(o["joint"])
        demos += [x["joint"] for x in s["attach"] if x.get("range") and x["joint"] in movable]
        sec = by_step.get(k)
        out.append({"n": k, "title": sec["title"].split(" — ", 1)[1] if sec and " — " in sec["title"] else ", ".join(s["items"]),
                    "items": list(s["items"]), "present": present, "groups": groups, "screws": screws, "inserts": inserts,
                    "demos": list(dict.fromkeys(demos)), "bench_for": s["bench_for"],
                    "lines": sec["lines"] if sec else []})
    return {"steps": out, "intro": intro, "outro": outro}
