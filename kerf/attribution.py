"""Which code line and which project params produced each face of each printed part (for viewer click-to-edit).

Line: each part's build() runs under a line tracer limited to the part file. After every executed line, the faces of
every solid in scope are fingerprinted by the SURFACE they lie on (plane: normal + offset; cylinder: axis + radius;
...), which later trimming does not change. A finished face belongs to the first line after which its surface
existed. Calls into helpers (iface, features) are credited to the part-file line that called them, which is the
line Spencer would edit.

Params: every project param (project.yaml `params:`) is nudged by one step and the parts rebuilt; a face whose
surface no longer exists "moves" with that param, and one whose surface stays but whose area changes "resizes"
with it. A param that moves nearly every face of a part just repositions the part and is reported per part.

Everything is computed in the part's own frame (unplaced), so assembly placement does not matter.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from build123d import Compound, Location, Solid
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Sphere, GeomAbs_Torus

from . import project as P

ND = 3  # rounding (mm / unit vectors) for surface identity


def _canon(v):
    """Direction with a deterministic sign, so a surface and its flipped normal compare equal."""
    v = [round(x, ND) + 0.0 for x in v]
    for x in v:
        if abs(x) > 10 ** -ND:
            return v if x > 0 else [-y + 0.0 for y in v]
    return v


def surface_key(face) -> tuple:
    s = BRepAdaptor_Surface(face.wrapped)
    t = s.GetType()
    if t == GeomAbs_Plane:
        ax = s.Plane().Axis()
        n = _canon([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        p = ax.Location()
        return ("plane", *n, round(n[0] * p.X() + n[1] * p.Y() + n[2] * p.Z(), ND) + 0.0)
    if t in (GeomAbs_Cylinder, GeomAbs_Cone):
        g = s.Cylinder() if t == GeomAbs_Cylinder else s.Cone()
        ax = g.Axis()
        d = _canon([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        p = ax.Location()
        dot = p.X() * d[0] + p.Y() * d[1] + p.Z() * d[2]
        foot = [round(c - dot * dd, ND) + 0.0 for c, dd in zip((p.X(), p.Y(), p.Z()), d)]  # axis point nearest origin
        extra = (round(g.Radius(), ND),) if t == GeomAbs_Cylinder else (round(g.SemiAngle(), ND), round(g.Apex().X(), ND), round(g.Apex().Y(), ND), round(g.Apex().Z(), ND))
        return ("cyl" if t == GeomAbs_Cylinder else "cone", *d, *foot, *extra)
    if t == GeomAbs_Sphere:
        g = s.Sphere()
        c = g.Location()
        return ("sphere", round(c.X(), ND), round(c.Y(), ND), round(c.Z(), ND), round(g.Radius(), ND))
    if t == GeomAbs_Torus:
        g = s.Torus()
        ax = g.Axis()
        d = _canon([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        c = ax.Location()
        return ("torus", *d, round(c.X(), ND), round(c.Y(), ND), round(c.Z(), ND), round(g.MajorRadius(), ND), round(g.MinorRadius(), ND))
    c = face.center()  # free-form surface: no stable identity; centre + area is the best available
    return ("free", round(c.X, 2), round(c.Y, 2), round(c.Z, 2), round(face.area, 2))


def _unplaced(shape):
    return shape.located(Location())


def _solids_in(value):
    if isinstance(value, (Solid, Compound)):
        try:
            return [value] if value.solids() else []
        except Exception:  # noqa: BLE001
            return []
    return []


def trace_lines(proj, pid: str) -> dict:
    """{surface_key: first part-file line after which that surface existed} for one printed part."""
    it = proj.items[pid]
    fname = str((proj.dir / it.spec["file"]).resolve())
    first: dict = {}
    last_line: dict = {}

    def note(frame, line):
        for v in list(frame.f_locals.values()):
            for s in _solids_in(v):
                try:
                    faces = _unplaced(s).faces()
                except Exception:  # noqa: BLE001
                    continue
                for f in faces:
                    try:
                        first.setdefault(surface_key(f), line)
                    except Exception:  # noqa: BLE001
                        pass

    def local(frame, event, arg):
        if event in ("line", "return"):
            prev = last_line.get(id(frame))
            if prev is not None:
                note(frame, prev)
            last_line[id(frame)] = frame.f_lineno
        return local

    def glob(frame, event, arg):
        if event == "call" and str(Path(frame.f_code.co_filename).resolve()) == fname:
            return local
        return None

    old = sys.gettrace()
    sys.settrace(glob)
    try:
        P.build(proj, only=[pid])
    finally:
        sys.settrace(old)
    return first


def _face_table(shape):
    """[(surface_key, area)] for every face, in the same order as shape.faces() (used for the viewer mesh)."""
    out = []
    for f in _unplaced(shape).faces():
        out.append((surface_key(f), round(f.area, 2)))
    return out


def compute(proj, only: list[str] | None = None) -> dict:
    """{part_id: {"file", "faces": [{"line", "moves": [param...], "resizes": [param...]}], "whole": [param...],
    "lines": {line: code}}} for the printed parts of an already-built project. Rebuilds the parts (traced, then once
    per param), so call it after checks; it does not change proj's shapes."""
    pids = [p for p in proj.printed if (only is None or p in only) and proj.items[p].shape is not None]
    base = {p: _face_table(proj.items[p].shape) for p in pids}
    out = {}
    for pid in pids:
        p2 = P.load(str(proj.dir))
        first = trace_lines(p2, pid)
        src = (proj.dir / proj.items[pid].spec["file"]).read_text(encoding="utf-8").splitlines()
        faces = [{"line": first.get(k), "moves": [], "resizes": []} for k, _ in base[pid]]
        out[pid] = {"file": str(Path(proj.items[pid].spec["file"])), "faces": faces, "whole": [],
                    "lines": {ln: src[ln - 1].strip() for ln in sorted({f["line"] for f in faces if f["line"]}) if 0 < ln <= len(src)}}
    params = proj.data.get("params") or {}
    for name, spec in params.items():
        v = spec["value"] if isinstance(spec, dict) else spec
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        step = float(spec.get("step", 0) or 0) if isinstance(spec, dict) else 0.0
        step = step or max(abs(v) * 0.02, 0.5)
        hi = spec.get("max") if isinstance(spec, dict) else None
        nv = v + step if hi is None or v + step <= hi else v - step
        try:
            p2 = P.build(P.load(str(proj.dir), {name: nv}), only=pids)
        except Exception:  # noqa: BLE001 - a param that breaks the build at +1 step simply gets no attribution
            continue
        for pid in pids:
            sh = p2.items[pid].shape
            if sh is None:
                continue
            now = _face_table(sh)
            keys = {k for k, _ in now}
            area = defaultdict(float)
            for k, a in now:
                area[k] += a
            barea = defaultdict(float)
            for k, a in base[pid]:
                barea[k] += a
            moved = [i for i, (k, _) in enumerate(base[pid]) if k not in keys]
            if len(moved) >= 0.8 * len(base[pid]):
                out[pid]["whole"].append(name)
                continue
            for i, (k, _) in enumerate(base[pid]):
                if k not in keys:
                    out[pid]["faces"][i]["moves"].append(name)
                elif abs(area[k] - barea[k]) > max(0.01, 1e-4 * barea[k]):
                    out[pid]["faces"][i]["resizes"].append(name)
    return out
