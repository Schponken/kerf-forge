"""Per-part build cache: `kerf check` / `kerf build` / Studio "Try" rebuild only the printed parts whose inputs changed.

The memo idea from cadgen (docs/teardowns/text-to-cad.md) at Kerf's scale: one cache entry per printed part, keyed by
everything its `build(ctx)` can see:
  - the part's source file, plus every other file in the project's parts/ folder that is not itself a part module
    (shared helpers such as fingerlib.py or layout.py, which part modules import) or that its source names by file;
  - project.yaml source_files: explicitly declared shared data and helpers outside parts/;
  - the part's resolved params (project params + layout values + the item's own params) and its project.yaml spec;
  - a temporary variant's typed original override-input signature, before derived/layout can shadow those values;
  - the printer's measured-fit profile and the material (iface reads them);
  - the build123d version and this file;
  - the engine files the part used: every kerf/*.py whose code ran while the part was built (recorded per part with
    sys.monitoring, each function reported once per build, so it costs nothing measurable), plus the kerf modules
    those files and the part's own source import (constants are read, not run) and, transitively, the modules imported
    at their top level. Hashed on lookup like the catalog entries, so editing an engine file the part never touches
    keeps it a hit (before 2026-11-02 any kerf/*.py edit rebuilt every part of every project);
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
import sys
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


# ---- engine files a build used (see the module docstring) ----

KERF = ROOT / "kerf"
_PREFIX = str(KERF) + os.sep
_TOOL = 4                       # sys.monitoring tool id (0-2 and 5 are reserved for debuggers/coverage/profilers)
_ACTIVE: list = []              # code-file sets of the recordings in progress (nested and concurrent ones all collect)
_MON: bool | None = None
_ALL = "kerf:*"                 # dependency on the whole engine (monitoring unavailable): hashed as engine_version()


def _on_start(code, offset):
    fn = code.co_filename
    if fn.startswith(_PREFIX):
        for s in _ACTIVE:
            s.add(fn)
    return sys.monitoring.DISABLE                    # once per code object until the next recording restarts events


def _monitor() -> bool:
    global _MON
    if _MON is None:
        try:
            m = sys.monitoring
            m.use_tool_id(_TOOL, "kerf-partcache")
            m.register_callback(_TOOL, m.events.PY_START, _on_start)
            _MON = True
        except Exception:  # noqa: BLE001 - no monitoring (id taken, old Python): depend on the whole engine
            _MON = False
    return _MON


_GRAPH: dict | None = None


_IMPORTS: dict = {}


def _kerf_imports(src: str, pkg_relative: bool) -> tuple[set, set]:
    """(all, top-level) names of kerf modules a source imports. pkg_relative: `from . import x` means kerf.x."""
    k = (hashlib.sha256(src.encode()).hexdigest(), pkg_relative)
    if k not in _IMPORTS:
        _IMPORTS[k] = _parse_imports(src, pkg_relative)
    return _IMPORTS[k]


def _parse_imports(src: str, pkg_relative: bool) -> tuple[set, set]:
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set(), set()
    mods = {f.stem for f in KERF.glob("*.py")}
    top_nodes = set(map(id, tree.body))

    def names(node):
        out = set()
        if isinstance(node, ast.Import):
            for a in node.names:
                parts = a.name.split(".")
                if parts[0] == "kerf" and len(parts) > 1:
                    out.add(parts[1])
                elif parts[0] == "kerf":
                    out.add("__init__")
        elif isinstance(node, ast.ImportFrom):
            m = node.module or ""
            if (node.level == 1 and pkg_relative) or m == "kerf" or m.startswith("kerf."):
                base = m.split(".")[1] if m.startswith("kerf.") else (m.split(".")[0] if node.level else "")
                if base:
                    out.add(base)
                else:                                    # from . import a, b  /  from kerf import a, b
                    out |= {a.name for a in node.names}
                    out.add("__init__")
        return {n for n in out if n in mods}

    every, top = set(), set()
    for node in ast.walk(tree):
        n = names(node)
        every |= n
        if id(node) in top_nodes:
            top |= n
    return every, top


def _graph() -> dict:
    """kerf module -> (every kerf module it imports, the ones it imports at top level)."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = {f.stem: _kerf_imports(f.read_text(encoding="utf-8", errors="replace"), True)
                  for f in KERF.glob("*.py")}
    return _GRAPH


def engine_deps(used_modules, direct_imports=()) -> set:
    """Engine files whose change can change a build that ran `used_modules` (and whose own source imports
    `direct_imports`): those, everything they import, and the top-level import closure of all of it."""
    g = _graph()
    out = set(used_modules) | set(direct_imports)
    for m in list(out):
        out |= g.get(m, (set(), set()))[0]
    todo = list(out)
    while todo:
        for n in g.get(todo.pop(), (set(), set()))[1]:
            if n not in out:
                out.add(n)
                todo.append(n)
    return {f"kerf:{m}.py" for m in out}


_FHASH: dict = {}


def _file_hash(name: str) -> str:
    f = KERF / name
    try:
        st = f.stat()
    except OSError:
        return "<missing>"
    k = (name, st.st_mtime_ns, st.st_size)
    if k not in _FHASH:
        _FHASH[k] = hashlib.sha256(f.read_bytes()).hexdigest()
    return _FHASH[k]


def deps_hash(deps) -> str:
    """Hash of the catalog entries and engine files ("kerf:<file>") a build read."""
    from . import catalog
    deps = sorted(deps)
    h = hashlib.sha256(catalog.deps_hash([d for d in deps if not d.startswith("kerf:")]).encode())
    for d in deps:
        if d.startswith("kerf:"):
            h.update(d.encode())
            h.update((engine_version() if d == _ALL else _file_hash(d[5:])).encode())
    return h.hexdigest()


def _catalog_deps(deps):
    return [d for d in deps if not d.startswith("kerf:")]


def key(proj, pid: str, spec: dict, params: dict, printer: str) -> str:
    """Cache key of everything except the catalog (catalog deps are only known after a build; see lookup)."""
    from . import calibrate, sources
    parts_dir = proj.dir / "parts"
    own = proj.dir / spec.get("file", f"parts/{pid}.py")
    part_files = {(proj.dir / ((s or {}).get("file") or f"parts/{q}.py")).resolve()
                  for q, s in (proj.data.get("parts") or {}).items()}
    src = own.read_text(encoding="utf-8", errors="replace") if own.exists() else ""
    import build123d
    h = hashlib.sha256(getattr(build123d, "__version__", "?").encode())
    h.update(Path(__file__).read_bytes())               # this file: the cache format
    # helpers in parts/ (anything not a part module), plus any other part module this one names ("yoke_l.py")
    files = [own, *sorted(p for p in parts_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                          and p.resolve() != own.resolve()
                          and (p.resolve() not in part_files or p.name in src))]
    files.extend(f for f in sources.extra_files(proj.dir, proj.data).values() if f not in files)
    for f in files:
        h.update(str(f.relative_to(proj.dir)).encode())
        b = f.read_bytes() if f.exists() else b"<missing>"
        h.update(b)
        if f.suffix == ".py":                            # engine modules the part's own code imports
            for d in sorted(engine_deps((), _kerf_imports(b.decode("utf-8", "replace"), False)[0])):
                h.update(d.encode())
                h.update(_file_hash(d[5:]).encode())
    # Variant identity preserves native key types/order; unsorted JSON also accepts mixed mapping keys.
    h.update(json.dumps(params, sort_keys=not bool(proj.override_signature), default=repr).encode())
    if proj.override_signature:
        h.update(b"\0overrides\0" + proj.override_signature)
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
        if deps_hash(rec["deps"]) != rec["deps_hash"]:
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
    for p in _catalog_deps(rec["deps"]):
        with contextlib.suppress(Exception):
            catalog.get(p)
    with contextlib.suppress(OSError):
        f.touch()                                      # recently used: kept by prune()
    return shape


def store(k: str, shape, deps: set) -> None:
    if not enabled():
        return
    try:
        blob = _dump(shape, sorted(deps))
        rec = pickle.loads(blob)                       # round-trip now: never store what can't be read back
        rec["deps_hash"] = deps_hash(rec["deps"])
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
        if deps_hash(rec["deps"]) != rec["deps_hash"]:
            return None
    except Exception:  # noqa: BLE001
        return None
    for p in _catalog_deps(rec["deps"]):
        with contextlib.suppress(Exception):
            catalog.get(p)
    return rec["value"]


def store_extra(k: str | None, name: str, value, deps: set) -> None:
    if not k or not enabled():
        return
    try:
        out = io.BytesIO()
        _Pickler(out, protocol=pickle.HIGHEST_PROTOCOL).dump(
            {"value": value, "deps": sorted(deps), "deps_hash": deps_hash(deps)})
        pickle.loads(out.getvalue())
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = DIR / f"{k}.{name}.tmp{os.getpid()}"
        tmp.write_bytes(out.getvalue())
        tmp.replace(DIR / f"{k}.{name}.pkl")
    except Exception:  # noqa: BLE001
        return


@contextlib.contextmanager
def recording():
    """Collect what the block (one part's build, or a result computed from one part) depends on: the catalog paths it
    read and, as "kerf:<file>", the engine files it ran (with their imports, see engine_deps)."""
    from . import catalog
    code: set = set()
    mon = _monitor()
    if mon:
        _ACTIVE.append(code)
        sys.monitoring.set_events(_TOOL, sys.monitoring.events.PY_START)
        sys.monitoring.restart_events()              # report every function again for this build
    try:
        with catalog.recording() as s:
            yield s
    finally:
        if mon:
            del _ACTIVE[next(i for i, r in enumerate(_ACTIVE) if r is code)]
            if not _ACTIVE:
                sys.monitoring.set_events(_TOOL, 0)
            s |= engine_deps({Path(f).stem for f in code})
        else:
            s.add(_ALL)
