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
from pathlib import Path

import numpy as np

from . import assembly as A
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


def mesh(shape, tol=0.05, ang=0.25) -> tuple[np.ndarray, np.ndarray]:
    """World-space triangle mesh of a placed shape: (N x 3 float32 vertices, M x 3 uint32 triangles)."""
    vs, ts = [], []
    off = 0
    for f in shape.faces():
        v, t = f.tessellate(tol, ang)
        if not t:
            continue
        vs.append(np.array([[p.X, p.Y, p.Z] for p in v], dtype=np.float32))
        ts.append(np.array(t, dtype=np.uint32) + off)
        off += len(v)
    if not vs:
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.uint32)
    return np.concatenate(vs), np.concatenate(ts)


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


def data(proj, asm, rep: dict) -> dict:
    """Everything the page shows. Leaves the assembly at its home pose."""
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
    out_items = []
    for k, (iid, it) in enumerate(items.items()):
        if it.shape is None:
            continue
        v, t = mesh(it.shape)
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
        })
    keep = ("project", "dir", "fingerprint", "printer", "params", "parts", "purchased", "requirements", "problems",
            "warnings", "bom", "files", "seconds")
    rp = {k: rep.get(k) for k in keep}
    a = rep.get("assembly") or {}
    rp["assembly"] = {k: a.get(k) for k in ("interference", "fasteners", "sweeps")}
    rp["ok"] = not rep.get("problems")
    return {"items": out_items, "joints": joints, "report": rp,
            "bounds": [[round(float(x), 3) for x in lo], [round(float(x), 3) for x in hi]]}


def html(d: dict) -> str:
    page = (ASSETS / "viewer.html").read_text()
    lib = (ASSETS / "viewer3d.js").read_text()
    js = json.dumps(d, separators=(",", ":"), default=str).replace("</", "<\\/")
    title = (d["report"].get("project") or "Kerf assembly").replace("<", "&lt;")
    # str.replace takes the replacement literally; each placeholder occurs once in the template
    page = page.replace("{{TITLE}}", title)
    page = page.replace("/*DATA*/", js, 1)
    return page.replace("/*KV3*/", lib.replace("</script", "<\\/script"), 1)


def write(proj, asm, rep: dict, path) -> Path:
    path = Path(path)
    path.write_text(html(data(proj, asm, rep)))
    return path
