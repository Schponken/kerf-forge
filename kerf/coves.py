"""Cove fillets by boolean: fill a straight concave edge between two flat faces with a fillet-shaped prism.

OCC's fillet operator can fail, or crash the process outright (seen on the robotic_gripper_desk body: a segfault, not
an exception, so safe_fillet cannot catch it), on bodies built from many unioned slabs. A concave fillet adds material,
so the same result can be had with a union: the prism between the corner, the two tangent points and the fillet arc.
This module builds that prism for each edge and unions it, which only ever needs a boolean.

An edge is filled only where both faces really carry on at least r past the edge (the tangent points sit on material
at both ends of the edge); otherwise the cove would stick out into the air past a short face, so it is skipped and
reported, like safe_fillet's failures.
"""
from __future__ import annotations

from build123d import GeomType, Location, Plane, Polygon, Vector, Circle, extrude


def _faces_of(shape, e):
    """The two planar faces of `shape` that share edge `e` (by geometry: edge identity is not stable)."""
    c = e.center()
    fs = [f for f in shape.faces() if f.geom_type == GeomType.PLANE and any(
        (x.center() - c).length < 1e-3 and abs(x.length - e.length) < 1e-3 for x in f.edges())]
    return fs if len(fs) == 2 else None


def cove(shape, e, r: float):
    """The cove prism for concave edge `e` of `shape` (None if the edge is not a straight concave edge between two
    planar faces, or a face ends within r of the edge)."""
    if e.geom_type != GeomType.LINE:
        return None
    fs = _faces_of(shape, e)
    if fs is None:
        return None
    c = e.center()
    n1, n2 = fs[0].normal_at(c), fs[1].normal_at(c)          # outward normals
    k = n1.dot(n2)
    if abs(k) > 0.97 or not shape.is_inside(c + n1 * 0.2 - n2 * 0.2) or not shape.is_inside(c + n2 * 0.2 - n1 * 0.2):
        return None                                           # coplanar or convex
    a = r / (1 + k)
    p0, p1 = e.position_at(0), e.position_at(1)
    d = (p1 - p0).normalized()
    # tangent points: on face 1 at distance r from face 2 and vice versa, relative to the edge's line
    centre_off = n1 * a + n2 * a                              # circle centre from the edge, in the air wedge
    t1_off, t2_off = centre_off - n1 * r, centre_off - n2 * r
    for p in (p0 + d * 0.3, c, p1 - d * 0.3):                # both faces carry on past the tangent points
        if not (shape.is_inside(p + t1_off - n1 * 0.2) and shape.is_inside(p + t2_off - n2 * 0.2)):
            return None
    x = (t1_off - (t1_off.dot(d)) * d).normalized()
    pl = Plane(origin=p0, x_dir=x, z_dir=d)
    to2 = lambda v: (v.dot(pl.x_dir), v.dot(pl.y_dir))        # noqa: E731
    # the corner vertex sinks 0.02 into the material (a clean fuse, no coplanar sides); the tangent points stay exact,
    # since moving them off the faces leaves a sliver outside the arc
    tri = Polygon(to2(-(n1 + n2) * 0.02), to2(t1_off), to2(t2_off), align=None)
    disc = Location(to2(centre_off) + (0,)) * Circle(r)
    prof = tri - disc
    return extrude(pl * prof, e.length, dir=(d.X, d.Y, d.Z))


def cove_fillets(shape, edges, r: float):
    """Union a cove of radius r into every given concave edge. Returns (shape, skipped: list[str])."""
    coves, skipped = [], []
    for e in edges:
        cv = cove(shape, e, r)
        if cv is None or cv.volume <= 0:
            c = e.center()
            skipped.append(f"cove r{r} at ({c.X:.1f}, {c.Y:.1f}, {c.Z:.1f}): not a concave edge with {r} mm of face on both sides")
        else:
            coves.append(cv)
    for cv in coves:
        shape = shape + cv
    return shape, skipped
