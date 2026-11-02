"""Geometry helpers on top of build123d: volumes, overlaps, meshes, mesh-based print analysis."""
from __future__ import annotations

import numpy as np
from build123d import ShapeList, Location, Vector

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


class _Memo:
    """Per-shape cache slot (geometry-derived data keyed by the shape's TopoDS). Copies and pickles come out empty, so a
    copied shape recomputes instead of carrying objects that cannot be copied (manifold3d meshes)."""
    __slots__ = ("key", "value")

    def __init__(self, key=None, value=None):
        self.key, self.value = key, value

    def get(self, shape):
        return self.value if self.key is not None and self.key.IsPartner(shape.wrapped) else None

    def __copy__(self):
        return _Memo()

    def __deepcopy__(self, memo):
        return _Memo()

    def __reduce__(self):
        return (_Memo, ())


def _memo_get(shape, attr):
    m = getattr(shape, attr, None)
    return m.get(shape) if isinstance(m, _Memo) else None


def _memo_set(shape, attr, value):
    try:
        setattr(shape, attr, _Memo(shape.wrapped, value))
    except Exception:  # noqa: BLE001 - shapes that refuse attributes just aren't cached
        pass


def _fast_box(shape):
    """World axis-aligned box that CONTAINS the shape (may be a little larger when rotated): the shape's own-frame box,
    computed once and cached on the shape, with its 8 corners moved by the current location. bbox() re-derives an
    optimal box from the exact geometry on every call (OCC BRepBndLib.AddOptimal), which was > 90 % of the time of an
    assembly interference pass (820 pairs x 2 boxes per pose on drone_foldable_wings)."""
    km = kmesh(shape)
    if km is not None:
        return bbox(shape)
    try:
        cached = _memo_get(shape, "_kerf_box")
        M = _loc_matrix(shape.location)
        if cached is None:
            lo, hi = bbox(shape)
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            local = (corners - M[:, 3]) @ M[:, :3]                       # world -> own frame
            cached = (local.min(axis=0), local.max(axis=0))
            _memo_set(shape, "_kerf_box", cached)
        llo, lhi = cached
        corners = np.array([[x, y, z] for x in (llo[0], lhi[0]) for y in (llo[1], lhi[1]) for z in (llo[2], lhi[2])])
        w = corners @ M[:, :3].T + M[:, 3]
        return w.min(axis=0), w.max(axis=0)
    except Exception:  # noqa: BLE001 - odd shape types: the exact box
        return bbox(shape)


def bbox_overlap(a, b, pad: float = 0.0) -> bool:
    """Could a and b touch? Conservative (never False for touching shapes): cached boxes moved with the shapes."""
    amin, amax = _fast_box(a)
    bmin, bmax = _fast_box(b)
    return bool(np.all(amin - pad <= bmax) and np.all(bmin - pad <= amax))


# Mesh prefilter for overlap(): most pairs whose boxes overlap do not actually touch (every motion-sweep step tests
# hundreds of them), and an exact B-rep boolean costs 0.1 - several s each. Each shape is tessellated ONCE to within
# PREFILTER_DEFLECTION of its true surface, kept in its own frame on the shape object, and placed with its current
# location; if the two meshes do not intersect, the true solids can only interpenetrate by less than ~2 x the
# deflection (0.04 mm, far below what an FDM printer resolves), so the pair is reported clear. Any mesh contact,
# and any shape whose tessellation is not a closed manifold, goes to the exact boolean, so every reported volume is
# still exact. KERF_EXACT_OVERLAP=1 turns the prefilter off.
PREFILTER_DEFLECTION = 0.02


def _loc_matrix(loc) -> np.ndarray:
    t = loc.wrapped.Transformation()
    return np.array([[t.Value(r + 1, c + 1) for c in range(4)] for r in range(3)])


def _local_manifold(shape):
    """Closed manifold of the shape in its own frame (cached on the shape), or None when it cannot be made."""
    m = _memo_get(shape, "_kerf_prefilter")
    if m is not None:
        return None if m is False else m                 # False = tried, no closed mesh
    m = None
    try:
        import trimesh
        from . import meshy
        v, f = mesh(shape, tol=PREFILTER_DEFLECTION, ang=0.2)
        M = _loc_matrix(shape.location)
        v = (v - M[:, 3]) @ M[:, :3]                     # world -> own frame (rotation is orthonormal)
        t = trimesh.Trimesh(v, f, process=True)          # weld the per-face vertex copies
        cand = meshy.to_manifold(t)
        if cand.status().name == "NoError" and not cand.is_empty():
            m = cand
    except Exception:  # noqa: BLE001 - no prefilter for this shape; the exact path still runs
        m = None
    _memo_set(shape, "_kerf_prefilter", m if m is not None else False)
    return m


def _meshes_touch(a, b) -> bool:
    """False only when both shapes have closed meshes and those meshes do not intersect (see PREFILTER_DEFLECTION)."""
    import os
    if os.environ.get("KERF_EXACT_OVERLAP"):
        return True
    ma, mb = _local_manifold(a), _local_manifold(b)
    if ma is None or mb is None:
        return True
    wa = ma.transform(_loc_matrix(a.location))
    wb = mb.transform(_loc_matrix(b.location))
    return (wa ^ wb).volume() > 0.0


GAP_SCREEN_MM = 0.2    # > 2 x PREFILTER_DEFLECTION: how far a mesh gap can sit from the exact one, with margin


def mesh_gap(a, b, search: float = 1e4):
    """Gap (mm) between the two shapes' cached closed meshes (tessellated to PREFILTER_DEFLECTION, so within
    2 x that of the exact B-rep distance; 0 when they touch or overlap), in a fraction of a second where OCC's exact
    distance takes tens of seconds on lofted parts. None when either shape has no closed mesh."""
    if kmesh(a) is not None or kmesh(b) is not None:
        return None
    ma, mb = _local_manifold(a), _local_manifold(b)
    if ma is None or mb is None:
        return None
    wa, wb = ma.transform(_loc_matrix(a.location)), mb.transform(_loc_matrix(b.location))
    if (wa ^ wb).volume() > 0.0:
        return 0.0
    return float(wa.min_gap(wb, search))


def overlap(a, b) -> float:
    """Volume (mm^3) shared by two located shapes. 0 when they only touch."""
    if not bbox_overlap(a, b, pad=0.01):
        return 0.0
    if kmesh(a) is not None or kmesh(b) is not None:     # a fused Meshy part: intersect in mesh space
        return float((_manifold(a) ^ _manifold(b)).volume())
    if not _meshes_touch(a, b):                          # fast reject; the exact boolean below decides every hit
        return 0.0
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
    try:
        verts, tris = shape.tessellate(tol, ang)
    except AttributeError:   # a face OCC cannot triangulate (KiCad's XT60 contact cone): mesh the rest, as the STL/GLB writers do
        verts, tris = [], []
        for fc in shape.faces():
            try:
                fv, ft = fc.tessellate(tol, ang)
            except AttributeError:
                continue
            tris += [[a + len(verts), b + len(verts), c + len(verts)] for a, b, c in ft]
            verts += list(fv)
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
    # 0.25 deg of slack: an exact 45 deg chamfer or teardrop roof tessellates to nz a hair past -sin(45) and is printable
    mask = ok & (nz < -np.sin(np.radians(angle_deg + 0.25))) & (cz > zmin + 0.05)
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
