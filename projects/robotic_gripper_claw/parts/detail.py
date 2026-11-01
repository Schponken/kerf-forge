"""Detail pass shared by the claw's parts: round every sharp inside corner the build check would report.

Uses the engine's own detector (kerf.edges.sharp_inside: straight concave edges between two flat faces, the corners
of interface features exempt), maps each reported corner back to its edge and fillets it with kerf's safe_fillet
(docs/ENGINEERING.md s5: inside corners on a load path r >= 1 mm). `keep(at)` names corners a mating part sits in
(they stay sharp on purpose; DESIGN.md lists them). Corners OCC cannot fillet are returned so the part can report them.
"""
from build123d import Vector
from kerf import edges as E
from kerf.features import safe_fillet


def _edges(body, ctx, keep):
    out = []
    for c in E.sharp_inside(body, ctx.sites):   # the same rule as the build report: screw-feature corners exempt
        if keep(c["at"]):
            continue
        at = Vector(*c["at"])
        e = min(body.edges(), key=lambda x: (x.center() - at).length + abs(x.length - c["len"]))
        if (e.center() - at).length < 0.1:
            out.append(e)
    return out


def fillet_inside(ctx, body, r: float = 1.0, keep=lambda at: False, fallback: bool = True):
    """Returns (body, smaller, failed): `smaller` = corners that only took r / 2 (they run into a hole, a chamfer or a
    thin strip), `failed` = corners left sharp. fallback=False skips the r / 2 retry (its slivers can break FEA meshing)."""
    body, _ = safe_fillet(body, [(_edges(body, ctx, keep), r)])
    rest = _edges(body, ctx, keep)
    if not fallback:
        return body, [], [f"({e.center().X:.1f}, {e.center().Y:.1f}, {e.center().Z:.1f})" for e in rest]
    smaller = [f"({e.center().X:.1f}, {e.center().Y:.1f}, {e.center().Z:.1f})" for e in rest]
    body, failed = safe_fillet(body, [(rest, r / 2)])
    return body, [s for s in smaller if not any(s.split(")")[0] in f for f in failed)], failed


def convex(body, edges):
    """The edges of `edges` that are outside corners (not concave, not a tangent fillet seam)."""
    out = []
    for e in edges:
        fs = [f for f in body.faces() if any(e.is_same(x) for x in f.edges())]
        if len(fs) != 2:
            continue
        c = e.center()
        n1, n2 = fs[0].normal_at(c), fs[1].normal_at(c)
        if abs(n1.dot(n2)) > 0.97:
            continue
        if not body.is_inside(c + n1 * 0.2 - n2 * 0.2):
            out.append(e)
    return out
