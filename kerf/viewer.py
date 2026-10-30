"""Self-contained interactive assembly viewer: projects/<p>/out/viewer.html (no network needed to open it).

Each item is meshed once in its own local frame. Joint motion is not re-implemented from build123d's joint maths;
it is *measured* from the real solver (assembly.solve) and stored as a rigid motion in the parent's frame:

    child_world(v) = parent_world @ motion(v - home) @ rel_home

revolute: rotation by (v - home) degrees about a fixed axis through a fixed point; linear: translation along a
fixed direction. `fk()` is the same maths in Python, so tests can prove the page poses parts exactly like the solver.
"""
from __future__ import annotations

import base64
import html
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from . import assembly as A, geom
from .export import PALETTE, PURCHASED_COLOR

ROOT = Path(__file__).resolve().parent.parent
RENDER_DIR = ROOT / "tools" / "render"
LIB = RENDER_DIR / ".cache" / "viewer-lib.js"
TEMPLATE = RENDER_DIR / "viewer_template.html"
FIT_TOL_MM = 1e-3          # measured joint motion must reproduce the solver to this accuracy


def matrix(loc) -> np.ndarray:
    """4x4 homogeneous matrix of a build123d Location."""
    t = loc.wrapped.Transformation()
    m = np.eye(4)
    for i in range(3):
        for j in range(4):
            m[i, j] = t.Value(i + 1, j + 1)
    return m


def _world(proj) -> dict:
    return {iid: matrix(it.shape.location) for iid, it in proj.items.items() if it.shape is not None}


def _motion(kind: str, axis, point, dv: float) -> np.ndarray:
    m = np.eye(4)
    if kind == "revolute":
        r = Rotation.from_rotvec(np.radians(dv) * np.asarray(axis)).as_matrix()
        p = np.asarray(point)
        m[:3, :3] = r
        m[:3, 3] = p - r @ p
    elif kind == "linear":
        m[:3, 3] = np.asarray(axis) * dv
    return m


def _measure(asm, e, scale: float) -> dict:
    """Measure one joint's motion from the solver; raise if it is not the rigid motion we model."""
    def rel(v):
        A.solve(asm, {e.name: v})
        w = _world(asm.proj)
        return np.linalg.inv(w[e.parent]) @ w[e.child]

    lo, hi = e.range
    home = e.home
    span = 60.0 if e.kind == "revolute" else (hi - lo) / 2
    d = min(hi - home, span) if hi - home >= home - lo else -min(home - lo, span)
    r0, r1 = rel(home), rel(home + d)
    step = r1 @ np.linalg.inv(r0)
    if e.kind == "revolute":
        rv = Rotation.from_matrix(step[:3, :3]).as_rotvec()
        axis = rv / np.radians(d)
        if abs(np.linalg.norm(axis) - 1) > 1e-6:
            raise ValueError(f"joint {e.name}: measured rotation {np.degrees(np.linalg.norm(rv)):.4f} deg for a {d} deg step")
        point = np.linalg.lstsq(np.eye(3) - step[:3, :3], step[:3, 3], rcond=None)[0]
    else:
        if not np.allclose(step[:3, :3], np.eye(3), atol=1e-9):
            raise ValueError(f"joint {e.name}: linear joint also rotates the child")
        axis = step[:3, 3] / d
        point = np.zeros(3)
    out = {"name": e.name, "kind": e.kind, "parent": e.parent, "child": e.child, "range": [float(lo), float(hi)],
           "home": float(home), "axis": axis.tolist(), "point": point.tolist(), "rel_home": r0.tolist()}
    for v in np.linspace(lo, hi, 7):                      # prove the model against the solver over the whole range
        pred = _motion(e.kind, axis, point, v - home) @ r0
        err = np.abs(pred - rel(v))
        err = max(err[:3, 3].max(), err[:3, :3].max() * scale)
        if err > FIT_TOL_MM:
            raise ValueError(f"joint {e.name}: viewer motion model is off by {err:.4g} mm at {v:.2f}")
    A.solve(asm)
    return out


def fk(data: dict, values: dict | None = None) -> dict:
    """World matrix of every item for joint values {name: v} (others at home) — same maths as the page."""
    values = values or {}
    world = {data["root"]: np.eye(4)}
    for j in data["joints"]:
        v = float(values.get(j["name"], j["home"]))
        world[j["child"]] = world[j["parent"]] @ _motion(j["kind"], j["axis"], j["point"], v - j["home"]) @ np.array(j["rel_home"])
    return world


def _b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def model(proj, asm, rep: dict) -> dict:
    """Everything the page needs, as JSON. Leaves the assembly at home."""
    A.solve(asm)
    shapes = {iid: it.shape for iid, it in proj.items.items() if it.shape is not None}
    lo = np.min([geom.bbox(s)[0] for i, s in shapes.items() if proj.items[i].role != "keepout"], axis=0)
    hi = np.max([geom.bbox(s)[1] for i, s in shapes.items() if proj.items[i].role != "keepout"], axis=0)
    diag = float(np.linalg.norm(hi - lo))
    tol = max(0.02, diag / 3000)
    world = _world(proj)
    items = []
    for k, (iid, it) in enumerate(proj.items.items()):
        if it.shape is None:
            continue
        v, f = geom.mesh(it.shape, tol, 0.2)
        inv = np.linalg.inv(world[iid])
        local = (np.c_[v, np.ones(len(v))] @ inv.T)[:, :3]
        color = PALETTE[k % len(PALETTE)] if it.role == "printed" else PURCHASED_COLOR
        if it.role == "keepout":
            color = "#ff6619"
        info = {"id": iid, "role": it.role, "color": color, "qty": it.spec.get("qty", 1),
                "pos": _b64(local.astype("<f4")), "idx": _b64(f.astype("<u4")), "nv": len(v), "nt": len(f)}
        if it.role == "printed":
            r = rep.get("parts", {}).get(iid, {})
            info["print"] = {k2: r.get(k2) for k2 in ("ok", "material", "print_rot", "size_mm", "mass_est_g", "infill",
                                                      "overhang_pct", "wall_p02_mm", "watertight", "problems", "warnings")}
            info["files"] = rep.get("files", {}).get("parts", {}).get(iid, [])
        elif it.role == "purchased":
            info["catalog"] = it.spec.get("catalog")
            info["mass_g"] = rep.get("purchased", {}).get(iid, {}).get("mass_g")
        items.append(info)
    joints = []
    for e in asm.edges:                                    # topological order: parents before children
        if e in asm.movable:
            joints.append(_measure(asm, e, diag))
        else:
            r = np.linalg.inv(world[e.parent]) @ world[e.child]
            joints.append({"name": e.name, "kind": "rigid", "parent": e.parent, "child": e.child, "range": [0, 0],
                           "home": 0.0, "axis": [0, 0, 1], "point": [0, 0, 0], "rel_home": r.tolist()})
    A.solve(asm)
    return {"name": proj.data.get("name", proj.name), "project": proj.name, "description": proj.data.get("description", ""),
            "ok": rep.get("ok", not rep.get("problems")), "fingerprint": rep.get("fingerprint"), "printer": rep.get("printer"),
            "root": asm.root, "bbox": [lo.tolist(), hi.tolist()], "items": items, "joints": joints,
            "bom": rep.get("bom", []), "plates": rep.get("files", {}).get("plates", []),
            "requirements": [{k: r.get(k) for k in ("id", "check", "ok", "value", "limit", "detail")} for r in rep.get("requirements", [])],
            "problems": rep.get("problems", []), "warnings": rep.get("warnings", [])}


def lib() -> str:
    """Minified three.js + OrbitControls (global KV), bundled once from tools/render/node_modules."""
    src = RENDER_DIR / "viewer_lib.mjs"
    if not LIB.exists() or LIB.stat().st_mtime < src.stat().st_mtime:
        LIB.parent.mkdir(exist_ok=True)
        if not (RENDER_DIR / "node_modules" / ".bin" / "esbuild").exists():   # older checkout: deps predate the viewer
            subprocess.run(["npm", "ci", "--silent", "--no-audit", "--no-fund"], cwd=RENDER_DIR, capture_output=True, timeout=600)
        r = subprocess.run(["npx", "--no-install", "esbuild", str(src), "--bundle", "--minify", "--format=iife",
                            "--global-name=KV", "--log-level=warning", f"--outfile={LIB}"],
                           cwd=RENDER_DIR, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError(f"viewer bundle failed (run ./setup.sh): {r.stderr.strip()[-600:]}")
    return LIB.read_text()


def page(data: dict) -> str:
    t = TEMPLATE.read_text()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return (t.replace("/*__LIB__*/", lib().replace("</script", "<\\/script"))
             .replace("__TITLE__", html.escape(data["name"]))
             .replace('"__DATA__"', payload))


def write(proj, asm, rep: dict, path: Path) -> dict:
    data = model(proj, asm, rep)
    path.write_text(page(data))
    return {"file": path.name, "kb": round(path.stat().st_size / 1024), "joints": [j["name"] for j in data["joints"] if j["kind"] != "rigid"]}
