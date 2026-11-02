"""Per-part build cache: `kerf check` / `kerf build` / Studio "Try" rebuild only the printed parts whose inputs changed.

The memo idea from cadgen (docs/teardowns/text-to-cad.md) at Kerf's scale: one cache entry per printed part, keyed by
everything its `build(ctx)` can see:
  - the part's source file, plus every other file in the project's parts/ folder that is not itself a part module
    (shared helpers such as fingerlib.py or layout.py, which part modules import) or that its source names by file;
  - the part's resolved params (project params + layout values + the item's own params) and its project.yaml spec;
  - the printer's measured-fit profile and the material (iface reads them);
  - the engine version: every kerf/*.py source and the build123d version;
  - the catalog entries the part read on its last real build (recorded per part; hashed on lookup, so editing one
    of them is a miss and an edit anywhere else in the catalog is not).
The value is the built shape (OpenCascade binary BREP, exact) plus everything `ctx.finish` attached to it (fastener and
pin sites, joints, notes, BOM rows, mesh cuts, label, colour), stored under .cache/parts/, and next to it the part's
print-check results (lookup_extra/store_extra), which depend on nothing but the part. Set KERF_NO_CACHE=1 to
bypass it; `kerf verify` does, so the definition of done always builds every part from scratch.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / ".cache" / "parts"
_ENGINE: str | None = None


def enabled() -> bool:
    return os.environ.get("KERF_NO_CACHE", "") in ("", "0")


def engine_version() -> str:
    """Hash of the engine source and the CAD kernel version: any engine change invalidates every cached part."""
    global _ENGINE
    if _ENGINE is None:
        import build123d
        h = hashlib.sha256(getattr(build123d, "__version__", "?").encode())
        for f in sorted((ROOT / "kerf").glob("*.py")):
            h.update(f.name.encode())
            h.update(f.read_bytes())
        _ENGINE = h.hexdigest()[:16]
    return _ENGINE


def key(proj, pid: str, spec: dict, params: dict, printer: str) -> str:
    """Cache key of everything except the catalog (catalog deps are only known after a build; see lookup)."""
    from . import calibrate
    parts_dir = proj.dir / "parts"
    own = proj.dir / spec.get("file", f"parts/{pid}.py")
    part_files = {(proj.dir / ((s or {}).get("file") or f"parts/{q}.py")).resolve()
                  for q, s in (proj.data.get("parts") or {}).items()}
    src = own.read_text(encoding="utf-8", errors="replace") if own.exists() else ""
    h = hashlib.sha256()
    h.update(engine_version().encode())
    # helpers in parts/ (anything not a part module), plus any other part module this one names ("yoke_l.py")
    for f in [own, *sorted(p for p in parts_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                           and p.resolve() != own.resolve()
                           and (p.resolve() not in part_files or p.name in src))]:
        h.update(str(f.relative_to(proj.dir)).encode())
        h.update(f.read_bytes() if f.exists() else b"<missing>")
    h.update(json.dumps(params, sort_keys=True, default=repr).encode())
    h.update(json.dumps(spec, sort_keys=True, default=repr).encode())
    h.update(printer.encode())
    prof = calibrate.profile_path(printer)
    h.update(prof.read_bytes() if prof.exists() else b"<no profile>")
    return f"{proj.dir.name}-{pid}-{h.hexdigest()[:20]}"


# ---- exact serialisation of what ctx.finish attaches (build123d's own pickling is lossy or unsupported) ----

def _shape(cls, data: bytes, label: str):
    from build123d.persistence import deserialize_shape
    s = cls(deserialize_shape(data))
    s.label = label
    return s


def _location(m):
    from build123d import Location
    from OCP.gp import gp_Trsf
    from OCP.TopLoc import TopLoc_Location
    t = gp_Trsf()
    t.SetValues(*m)
    return Location(TopLoc_Location(t))


def _axis(o, d):
    from build123d import Axis
    return Axis(o, d)


def _color(rgba):
    from build123d import Color
    return Color(*rgba)


class _Pickler(pickle.Pickler):
    def reducer_override(self, obj):
        from build123d import Axis, Color, Location, Shape
        from build123d.persistence import serialize_shape
        if isinstance(obj, Shape):
            return _shape, (type(obj), serialize_shape(obj.wrapped), obj.label)
        if isinstance(obj, Location):          # all 12 doubles: build123d pickles locations as float32
            t = obj.wrapped.Transformation()
            return _location, (tuple(t.Value(r, c) for r in (1, 2, 3) for c in (1, 2, 3, 4)),)
        if isinstance(obj, Axis):
            return _axis, (tuple(obj.position), tuple(obj.direction))
        if isinstance(obj, Color):
            return _color, (tuple(obj),)
        return NotImplemented


ATTRS = ("kerf_sites", "kerf_joints", "kerf_notes", "kerf_pins", "kerf_mesh_cuts", "kerf_bom", "kerf_features", "kerf_sharp_ok", "kerf_stub")


def _dump(shape, deps: list) -> bytes:
    meta = {a: getattr(shape, a) for a in ATTRS if hasattr(shape, a)}
    meta["color"] = shape.color
    bio = io.BytesIO()
    _Pickler(bio, protocol=pickle.HIGHEST_PROTOCOL).dump({"shape": shape, "meta": meta, "deps": deps})
    return bio.getvalue()


def _attach_joints(shape, joints):
    from build123d import LinearJoint, RevoluteJoint, RigidJoint
    for j in joints:
        if j.kind == "rigid":
            RigidJoint(j.label, to_part=shape, joint_location=j.loc)
        elif j.kind == "revolute":
            RevoluteJoint(j.label, to_part=shape, axis=j.axis, angular_range=j.range)
        elif j.kind == "linear":
            LinearJoint(j.label, to_part=shape, axis=j.axis, linear_range=j.range)


def lookup(k: str):
    """The cached shape for key k, or None. A hit also re-records the part's catalog reads (catalog_deps.json)."""
    from . import catalog
    f = DIR / f"{k}.pkl"
    if not enabled() or not f.exists():
        return None
    try:
        rec = pickle.loads(f.read_bytes())
        if catalog.deps_hash(rec["deps"]) != rec["deps_hash"]:
            return None
        shape = rec["shape"]
        meta = rec["meta"]
        if meta.get("color") is not None:
            shape.color = meta["color"]
        for a in ATTRS:
            if a in meta:
                setattr(shape, a, meta[a])
        _attach_joints(shape, meta.get("kerf_joints", []))
    except Exception:  # noqa: BLE001 — a corrupt or incompatible entry is just a miss
        return None
    for p in rec["deps"]:
        with contextlib.suppress(Exception):
            catalog.get(p)
    with contextlib.suppress(OSError):
        f.touch()                                      # recently used: kept by prune()
    return shape


def store(k: str, shape, deps: set) -> None:
    from . import catalog
    if not enabled():
        return
    try:
        blob = _dump(shape, sorted(deps))
        rec = pickle.loads(blob)                       # round-trip now: never store what can't be read back
        rec["deps_hash"] = catalog.deps_hash(rec["deps"])
        out = io.BytesIO()
        _Pickler(out, protocol=pickle.HIGHEST_PROTOCOL).dump(rec)
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = DIR / f"{k}.tmp{os.getpid()}"
        tmp.write_bytes(out.getvalue())
        tmp.replace(DIR / f"{k}.pkl")
        prune()
    except Exception:  # noqa: BLE001 — caching is an optimisation; a part that can't be stored is rebuilt next time
        return


KEEP = 1500     # newest cache files kept; older ones (old param values, old engine versions) are deleted


def prune(keep: int = KEEP) -> None:
    files = list(DIR.glob("*.pkl"))
    if len(files) <= keep * 1.2:
        return
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        with contextlib.suppress(OSError):
            f.unlink()


def lookup_extra(k: str | None, name: str):
    """A result computed from part k alone (its print checks), stored next to it; None when absent or stale."""
    f = DIR / f"{k}.{name}.pkl"
    if not k or not enabled() or not f.exists() or not (DIR / f"{k}.pkl").exists():
        return None
    from . import catalog
    try:
        rec = pickle.loads(f.read_bytes())
        if catalog.deps_hash(rec["deps"]) != rec["deps_hash"]:
            return None
    except Exception:  # noqa: BLE001
        return None
    for p in rec["deps"]:
        with contextlib.suppress(Exception):
            catalog.get(p)
    return rec["value"]


def store_extra(k: str | None, name: str, value, deps: set) -> None:
    from . import catalog
    if not k or not enabled():
        return
    try:
        out = io.BytesIO()
        _Pickler(out, protocol=pickle.HIGHEST_PROTOCOL).dump(
            {"value": value, "deps": sorted(deps), "deps_hash": catalog.deps_hash(sorted(deps))})
        pickle.loads(out.getvalue())
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = DIR / f"{k}.{name}.tmp{os.getpid()}"
        tmp.write_bytes(out.getvalue())
        tmp.replace(DIR / f"{k}.{name}.pkl")
    except Exception:  # noqa: BLE001
        return


@contextlib.contextmanager
def recording():
    """Collect the catalog paths read inside the block (one part's build)."""
    from . import catalog
    with catalog.recording() as s:
        yield s
