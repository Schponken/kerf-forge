"""Load a project (project.yaml + part modules) and build every part."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import catalog
from .ctx import Ctx

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"


class ProjectError(ValueError):
    pass


@dataclass
class Item:
    id: str
    role: str                 # printed | purchased | keepout
    spec: dict
    shape: object = None
    build_ms: int = 0
    error: str | None = None


@dataclass
class Project:
    name: str
    dir: Path
    data: dict
    params: dict
    items: dict = field(default_factory=dict)

    @property
    def printed(self):
        return {k: v for k, v in self.items.items() if v.role == "printed"}

    def out(self, *p) -> Path:
        d = self.dir / "out"
        d.mkdir(exist_ok=True)
        return d.joinpath(*p)

    def fingerprint(self) -> str:
        """Hash of everything that defines the geometry: yaml, part sources, catalog, kerf engine source."""
        h = hashlib.sha256()
        files = [self.dir / "project.yaml", *sorted((self.dir / "parts").glob("*.py")),
                 catalog.CATALOG, *sorted((ROOT / "kerf").glob("*.py"))]
        for f in files:
            if f.exists():
                h.update(f.name.encode())
                h.update(f.read_bytes())
        return h.hexdigest()[:16]


def resolve_dir(name_or_path: str) -> Path:
    p = Path(name_or_path)
    if (p / "project.yaml").exists():
        return p.resolve()
    if (PROJECTS / name_or_path / "project.yaml").exists():
        return (PROJECTS / name_or_path).resolve()
    raise ProjectError(f"no project.yaml at '{name_or_path}' or projects/{name_or_path}")


def param_values(data: dict, overrides: dict | None = None) -> dict:
    vals = {}
    for k, v in (data.get("params") or {}).items():
        val = v["value"] if isinstance(v, dict) else v
        vals[k] = float(val) if isinstance(val, (int, float)) else val
    for k, v in (overrides or {}).items():
        if k not in vals:
            raise ProjectError(f"unknown param override '{k}'")
        vals[k] = v
    # derived values: evaluated in order, may use earlier params (python expressions over params only)
    for k, expr in (data.get("derived") or {}).items():
        try:
            vals[k] = float(eval(str(expr), {"__builtins__": {}}, {**_MATH, **vals}))
        except Exception as e:  # noqa: BLE001
            raise ProjectError(f"derived '{k}' = {expr!r}: {e}") from e
    return vals


import math as _m
_MATH = {n: getattr(_m, n) for n in ("sqrt", "sin", "cos", "tan", "atan2", "radians", "degrees", "pi", "ceil", "floor")}
_MATH.update(min=min, max=max, abs=abs, round=round)


def load(name_or_path: str, overrides: dict | None = None) -> Project:
    d = resolve_dir(name_or_path)
    data = yaml.safe_load((d / "project.yaml").read_text()) or {}
    for key in ("name", "parts", "assembly"):
        if key not in data:
            raise ProjectError(f"{d.name}/project.yaml is missing '{key}'")
    proj = Project(name=data["name"], dir=d, data=data, params=param_values(data, overrides))
    for pid, spec in (data.get("parts") or {}).items():
        proj.items[pid] = Item(pid, "printed", spec or {})
    for pid, spec in (data.get("purchased") or {}).items():
        proj.items[pid] = Item(pid, "purchased", spec or {})
    for pid, spec in (data.get("keepouts") or {}).items():
        proj.items[pid] = Item(pid, "keepout", spec or {})
    return proj


def _load_module(path: Path):
    name = f"kerf_part_{path.parent.parent.name}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def shared_layout(proj: Project) -> dict:
    """Optional project-level layout module (project.yaml `layout: parts/layout.py`) with
    `def layout(p, cat) -> dict`. Its values are added to every part's ctx.p, so dimensions that two parts must
    agree on (hole positions, seat heights) are computed once, from params and the catalog."""
    f = proj.data.get("layout")
    if not f:
        return {}
    from types import SimpleNamespace
    mod = _load_module(proj.dir / f)
    out = mod.layout(SimpleNamespace(**proj.params), catalog)
    if not isinstance(out, dict):
        raise ProjectError(f"{f}: layout() must return a dict")
    clash = set(out) & set(proj.params)
    if clash:
        raise ProjectError(f"{f}: layout() redefines params {sorted(clash)}")
    return out


def build(proj: Project, only: list[str] | None = None) -> Project:
    from . import proxies

    try:
        proj.params = {**proj.params, **shared_layout(proj)}
    except Exception as e:  # noqa: BLE001
        for it in proj.items.values():
            it.error = f"layout failed: {type(e).__name__}: {e}"
        return proj
    for pid, it in proj.items.items():
        if only and pid not in only:
            continue
        t0 = time.time()
        try:
            params = {**proj.params, **{k: (v["value"] if isinstance(v, dict) else v) for k, v in (it.spec.get("params") or {}).items()}}
            ctx = Ctx(pid, params, {"project": proj.name, "spec": it.spec})
            if it.role == "printed":
                f = proj.dir / it.spec.get("file", f"parts/{pid}.py")
                if not f.exists():
                    raise ProjectError(f"part file {f.relative_to(proj.dir)} not found")
                mod = _load_module(f)
                if not hasattr(mod, "build"):
                    raise ProjectError(f"{f.name} has no build(ctx) function")
                it.shape = mod.build(ctx)
            else:
                it.shape = proxies.build(ctx, it.spec)
            if it.shape is None or not hasattr(it.shape, "kerf_sites"):
                raise ProjectError(f"{pid}: build must return ctx.finish(shape)")
        except Exception as e:  # noqa: BLE001 — report per part, keep building the rest
            import traceback
            it.error = f"{type(e).__name__}: {e}"
            it.trace = traceback.format_exc(limit=6)
        it.build_ms = int((time.time() - t0) * 1000)
    return proj
