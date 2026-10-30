"""Vendor CAD proxies: a purchased part shown with the manufacturer's own STEP model.

project.yaml:
    pico: {catalog: boards.rpi_pico, proxy: step, base: board, model: rpi_pico.step,
           model_rot: [90, -90, 0], model_pos: [-25.5, 10.5, 0.5], groups: {holes: pico}}

- The catalog-driven `base` proxy (default from the catalog category, e.g. board, servo) is built first; its joints and
  fastener sites are kept unchanged, so a vendor model never moves a screw hole or a joint.
- The STEP from `catalog/models/` (source + licence in catalog/models/SOURCES.md) is rotated by `model_rot` (deg,
  build123d Rot) then moved by `model_pos` into the base proxy's frame.
- It must then agree with the catalog: every face of its bounding box within STEP_BBOX_TOL of the base proxy's, and a
  real hole at every fastener site (a probe of 0.7 x the screw diameter along the site axis touches nothing). Either
  failure raises, naming the axis or the site, so a wrong model, unit or transform can never pass silently.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from build123d import Align, Compound, Cylinder, Pos, Rot, import_step

from . import catalog, geom
from .ctx import Ctx
from .proxies import DEFAULT_BY_CATEGORY, REG, proxy

MODELS = Path(__file__).resolve().parent.parent / "catalog" / "models"
STEP_BBOX_TOL = 0.5   # mm, per bounding-box face (PLAN: vendor model vs catalog entry)


@lru_cache(maxsize=32)
def _load(path: str, mtime: float):
    return import_step(path)


def load_model(name: str, models_dir: Path | None = None):
    p = (models_dir or MODELS) / name
    if not p.exists():
        raise FileNotFoundError(f"vendor model {p} not found (put it in catalog/models/ with a SOURCES.md entry)")
    return _load(str(p), p.stat().st_mtime)


def _bbox(s):
    lo, hi = geom.bbox(s)
    return list(lo), list(hi)


def compare_bbox(model, ref, tol: float = STEP_BBOX_TOL) -> list[str]:
    """Faces of model's bounding box more than tol from ref's (both already in the same frame)."""
    (ml, mh), (rl, rh) = _bbox(model), _bbox(ref)
    out = []
    for k, ax in enumerate("XYZ"):
        for side, a, b in (("min", ml[k], rl[k]), ("max", mh[k], rh[k])):
            if abs(a - b) > tol:
                out.append(f"{ax} {side}: model {a:.2f} vs catalog {b:.2f} mm (off by {a - b:+.2f})")
    return out


def missing_holes(model, sites) -> list[str]:
    out = []
    for s in sites:
        d = float(s.screw.lstrip("M"))
        depth = max(s.grip, s.engage, 0.5)
        probe = s.loc * (Pos(0, 0, -depth + 0.05) * Cylinder(0.35 * d, depth - 0.1, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        v = geom.overlap(model, probe)
        if v > 1e-3:
            p = geom.world_point(s.loc, (0, 0, 0))
            out.append(f"no {s.screw} hole in the model at site {s.group} ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}): {v:.2f} mm3 of material")
    return out


@proxy("step")
def step(ctx, spec):
    """Vendor STEP model on top of the catalog proxy `base`; see the module docstring. Joints and sites are the base's."""
    base = spec.get("base") or DEFAULT_BY_CATEGORY.get(str(spec.get("catalog", "")).split(".")[0])
    if base not in REG or base == "step":
        raise ValueError(f"{ctx.id}: proxy: step needs base: <catalog proxy kind> (have {sorted(k for k in REG if k != 'step')})")
    ref_ctx = Ctx(ctx.id, ctx.params, ctx.meta)
    ref = REG[base](ref_ctx, spec)
    model = load_model(spec["model"], Path(spec["models_dir"]) if spec.get("models_dir") else None)
    rx, ry, rz = (float(v) for v in spec.get("model_rot", (0, 0, 0)))
    x, y, z = (float(v) for v in spec.get("model_pos", (0, 0, 0)))
    # bake the transform into the geometry: the item's own location must stay identity (joints/sites are in its frame)
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    trsf = (Pos(x, y, z) * Rot(rx, ry, rz)).wrapped.Transformation()
    placed = Compound(BRepBuilderAPI_Transform(model.wrapped, trsf, True, True).Shape())   # geometry copied + moved
    problems = compare_bbox(placed, ref)
    problems += missing_holes(placed, ref_ctx.sites)
    if problems:
        raise ValueError(f"{ctx.id}: vendor model {spec['model']} does not match {spec.get('catalog')}: " + "; ".join(problems))
    ctx.joints.extend(ref_ctx.joints)
    ctx.sites.extend(ref_ctx.sites)
    ctx.notes.extend(ref_ctx.notes)
    return ctx.finish(placed, color=getattr(ref, "color", None))
