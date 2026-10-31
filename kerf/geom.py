"""Geometry helpers on top of build123d: volumes, overlaps, meshes, mesh-based print analysis."""
from __future__ import annotations

import numpy as np
from build123d import Shape, ShapeList, Location, Vector

# Interference below this volume is treated as numerical noise from coplanar/touching faces.
OVERLAP_TOL_MM3 = 0.05


def solids(shape) -> list:
    if shape is None:
        return []
    if isinstance(shape, (list, tuple, ShapeList)):
        return [s for sh in shape for s in solids(sh)]
    return list(shape.solids())


def kmesh(shape):
    """World (V, F) of a `source: meshy` part's fused mesh (kerf/meshy.py), or None for an ordinary B-rep shape."""
    km = getattr(shape, "kerf_mesh", None)
    if km is None or isinstance(shape, (list, tuple, ShapeList)):
        return None
    t = shape.location.wrapped.Transformation()
    M = np.array([[t.Value(r + 1, c + 1) for c in range(4)] for r in range(3)])
    V, F = km
    return V @ M[:, :3].T + M[:, 3], F


def _manifold(shape):
    from . import meshy
    km = kmesh(shape)
    if km is None:
        return meshy.brep_manifold(shape, tol=0.02, ang=0.15)
    import trimesh
    return meshy.to_manifold(trimesh.Trimesh(km[0], km[1], process=False))


def volume(shape) -> float:
    km = kmesh(shape)
    if km is not None:
        return float(_manifold(shape).volume())
    return float(sum(s.volume for s in solids(shape)))


def bbox(shape):
    km = kmesh(shape)
    if km is not None:
        return km[0].min(axis=0), km[0].max(axis=0)
    b = shape.bounding_box()
    return np.array([b.min.X, b.min.Y, b.min.Z]), np.array([b.max.X, b.max.Y, b.max.Z])


def bbox_overlap(a, b, pad: float = 0.0) -> bool:
    amin, amax = bbox(a)
    bmin, bmax = bbox(b)
    return bool(np.all(amin - pad <= bmax) and np.all(bmin - pad <= amax))


def overlap(a, b) -> float:
    """Volume (mm^3) shared by two located shapes. 0 when they only touch."""
    if not bbox_overlap(a, b, pad=0.01):
        return 0.0
    if kmesh(a) is not None or kmesh(b) is not None:     # a fused Meshy part: intersect in mesh space
        return float((_manifold(a) ^ _manifold(b)).volume())
    try:
        r = a.intersect(b)
    except Exception:  # fall back to operator form on odd shape types
        r = a & b
    return volume(r)


def mesh(shape, tol: float = 0.02, ang: float = 0.15):
    """(vertices Nx3, faces Mx3) triangle mesh of a shape, in its current location."""
    km = kmesh(shape)
    if km is not None:
        return km
    verts, tris = shape.tessellate(tol, ang)
    v = np.array([[p.X, p.Y, p.Z] for p in verts], dtype=float)
    f = np.array(tris, dtype=np.int64).reshape(-1, 3)
    return v, f


def located(shape, loc: Location):
    return shape.moved(loc)


def overhang(v: np.ndarray, f: np.ndarray, angle_deg: float = 45.0, bed_z: float | None = None):
    """Area (mm^2) and fraction of the surface facing down steeper than angle_deg, ignoring faces on the bed."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    area2 = np.linalg.norm(n, axis=1)
    ok = area2 > 1e-12
    nz = np.zeros(len(f))
    nz[ok] = n[ok, 2] / area2[ok]
    area = area2 / 2
    zmin = v[:, 2].min() if bed_z is None else bed_z
    cz = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
    mask = ok & (nz < -np.sin(np.radians(angle_deg))) & (cz > zmin + 0.05)
    total = float(area.sum())
    oh = float(area[mask].sum())
    return oh, (oh / total if total else 0.0), mask


def thickness_samples(v: np.ndarray, f: np.ndarray, n: int = 1500, seed: int = 0):
    """Local wall thickness by casting a ray inward from sample points on the surface.

    Returns an array of thickness values (mm). Uses trimesh's pure-numpy ray tracer."""
    import trimesh

    m = trimesh.Trimesh(vertices=v, faces=f, process=True)
    if len(m.faces) == 0:
        return np.array([])
    pts, fi = trimesh.sample.sample_surface_even(m, n, seed=seed)
    if len(pts) == 0:
        return np.array([])
    normals = m.face_normals[fi]
    origins = pts - normals * 1e-3
    locs, idx_ray, _ = m.ray.intersects_location(origins, -normals, multiple_hits=False)
    out = np.full(len(pts), np.inf)
    d = np.linalg.norm(locs - origins[idx_ray], axis=1)
    out[idx_ray] = d
    return out[np.isfinite(out)]


def mesh_stats(v: np.ndarray, f: np.ndarray) -> dict:
    """Watertightness, body count and volume of a triangle mesh (vertices welded at 1e-4 mm)."""
    import trimesh

    m = trimesh.Trimesh(vertices=v, faces=f, process=True, validate=True)
    m.merge_vertices(digits_vertex=4)
    bodies = len(m.split(only_watertight=False)) if len(m.faces) else 0
    return {"watertight": bool(m.is_watertight), "winding_consistent": bool(m.is_winding_consistent),
            "bodies": int(bodies), "volume": float(abs(m.volume)) if m.is_watertight else None}


def world_point(loc: Location, p) -> np.ndarray:
    q = loc * Location(Vector(*p))
    return np.array([q.position.X, q.position.Y, q.position.Z])


def world_dir(loc: Location, d) -> np.ndarray:
    o = world_point(loc, (0, 0, 0))
    t = world_point(loc, d)
    v = t - o
    return v / (np.linalg.norm(v) or 1)


def write_glb(shapes, path, linear_deflection: float = 0.05, angular_deflection: float = 0.2, label: str = "assembly"):
    """GLB of located, coloured shapes. Plain B-rep -> build123d's exporter; if any shape is a fused Meshy part
    (kerf_mesh) every shape is written as a mesh with trimesh in the same convention (metres, Z-up -> Y-up)."""
    from build123d import Compound, export_gltf
    if not any(kmesh(s) is not None for s in shapes):
        export_gltf(Compound(children=list(shapes), label=label), str(path), binary=True,
                    linear_deflection=linear_deflection, angular_deflection=angular_deflection)
        return
    import trimesh
    sc = trimesh.Scene()
    for k, s in enumerate(shapes):
        v, f = mesh(s, tol=linear_deflection, ang=angular_deflection)
        m = trimesh.Trimesh(np.c_[v[:, 0], v[:, 2], -v[:, 1]] * 0.001, f, process=False)
        c = getattr(s, "color", None)
        rgba = [int(round(255 * x)) for x in (tuple(c) if c is not None else (0.6, 0.6, 0.6, 1.0))]
        m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(rgba, (len(f), 1)))
        sc.add_geometry(m, geom_name=f"{getattr(s, 'label', '') or 'part'}_{k}")
    sc.export(str(path), file_type="glb")
