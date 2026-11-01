"""Sharp inside corners: the straight re-entrant edges between two flat faces that have no fillet.

A sharp inside corner concentrates stress (cracks start there) and prints a weak layer seam. Every one should be
filleted unless it is intentional: the corners inside a fastener or mount feature (nut hexes, servo dog-bones, slots)
cut by kerf/iface.py are exempt by their interface sites. pipeline.py lists them per part, worst first: corners in a
highly stressed zone (kerf/stressmap.py hot zones) lead the warning.
"""
from __future__ import annotations

from collections import defaultdict

from build123d import GeomType

MIN_LEN = 2.0        # mm: shorter edges are fillet run-outs and chamfer seams, not corners
SITE_RADIUS = 6.0    # mm around an interface site: corners of the fastener feature itself


def sharp_inside(shape, sites=()) -> list[dict]:
    """[{at: [x,y,z], len: mm}] for every unfilleted concave straight edge between two planar faces."""
    owners = defaultdict(list)
    for f in shape.faces():
        if f.geom_type != GeomType.PLANE:
            continue
        for e in f.edges():
            owners[e].append(f)
    site_pts = [s.loc.position for s in sites] if sites else []
    out = []
    for e, fs in owners.items():
        if len(fs) != 2 or e.geom_type != GeomType.LINE or e.length < MIN_LEN:
            continue
        c = e.center()
        n1, n2 = fs[0].normal_at(c), fs[1].normal_at(c)
        if abs(n1.dot(n2)) > 0.97:                       # (nearly) coplanar: not a corner
            continue
        # just outside face 1 and just inside face 2 is solid only where the faces meet in a re-entrant (concave) corner
        if not shape.is_inside(c + n1 * 0.2 - n2 * 0.2):
            continue
        if any((c - p).length < SITE_RADIUS for p in site_pts):
            continue
        out.append({"at": [round(c.X, 1), round(c.Y, 1), round(c.Z, 1)], "len": round(e.length, 1)})
    return out


def advice(part: str, corners: list[dict], hot_zones=(), cell: float = 0.0) -> str | None:
    if not corners:
        return None
    def near_hot(c):
        return any(max(abs(a - b) for a, b in zip(c["at"], z["at"])) <= cell for z in hot_zones) if cell else False
    hot = [c for c in corners if near_hot(c)]
    shown = (hot or sorted(corners, key=lambda c: -c["len"]))[:4]
    where = ", ".join(str(c["at"]) for c in shown)
    total = sum(c["len"] for c in corners)
    return (f"{part}: {len(corners)} sharp inside corner(s) ({total:.0f} mm of edge)"
            + (f", {len(hot)} in a highly stressed zone" if hot else "")
            + f", e.g. at {where}: fillet them (stress concentration, weak layer seam) or say in DESIGN.md why one must "
              "stay sharp (a mating part sits in it)")
