"""Structural section generators: beams, pivot links and ribs whose shape follows the load (docs/ENGINEERING.md).

A beam's material belongs far from its neutral axis (second moment I grows with depth cubed), a closed section resists
twist ~100x better than an open one of the same material, and a part that must print without support cannot have a
downward face steeper than 45 deg. These helpers build such sections by construction:

    from kerf import features as F           # re-exported there
    body = F.beam([(0, 0, 0), (120, 0, 0)], section="box", depth=lambda s: 24 - 8 * s, width=14, wall=2.4)
    link = F.fork_link(110, ends=[{"bore": 3.4, "boss_d": 12, "length": 14}] * 2, section="box", depth=22, taper=0.7)
    body += F.rib_along(top_face, [(0, 0, 6), (40, 0, 6)], h=8)

Section frame: `depth` is measured along the bending direction (`up`), `width` across it. Every section comes in a
print-ready form for the side that lies on the bed (`bed`): overhanging flanges get 45 deg chamfers underneath, hollow
ceilings a 45 deg peaked roof, a lying tube a 45 deg flat foot and a teardrop bore. `printable=False` gives the textbook
shape (for comparing with hand formulas). Sections that cannot print support-free in the chosen orientation are
refused with the alternative (an I lying on its side bridges its whole web: use "C", which then opens upward, or "box").
"""
from __future__ import annotations

import math

from build123d import (Align, Circle, Cylinder, Face, Location, Plane, Polyline, Pos, Rectangle, Spline, Vector, Wire,
                       extrude, loft, make_face, sweep)

MIN_WALL = 1.2           # mm (docs/ENGINEERING.md section 5); same as features.MIN_WALL
SECTIONS = ("rect", "I", "T", "C", "box", "tube")
S45 = math.sqrt(0.5)


def _poly(pts) -> Face:
    out = []
    for x, y in pts:                                  # a zero-size chamfer repeats a corner
        if not out or math.hypot(x - out[-1][0], y - out[-1][1]) > 1e-9:
            out.append((x, y))
    if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-9:
        out.pop()
    return make_face(Polyline(*out, close=True)).face()


def _one(shape) -> Face:
    fs = shape.faces()
    if len(fs) != 1:
        raise ValueError(f"section came out as {len(fs)} pieces")
    return fs[0]


def _canonical(section: str, W: float, H: float, t: float, depth_vertical: bool, printable: bool) -> Face:
    """2D section in print coordinates: x horizontal, y up from the bed, centred on its bounding box.
    W, H = horizontal and vertical extents."""
    if section == "rect":
        return Rectangle(W, H).face()
    if t < MIN_WALL:
        raise ValueError(f"section wall {t} mm is below the {MIN_WALL} mm minimum")
    if section == "tube":
        R, r = W / 2, W / 2 - t
        if r <= 0:
            raise ValueError(f"tube wall {t} mm leaves no bore in a {W} mm tube")
        outer, inner = Circle(R).face(), Circle(r).face()
        if printable:   # a lying tube prints as a teardrop: 45 deg roof on the bore and on the outside, 45 deg foot
            outer = _one((outer + _poly([(-R * S45, R * S45), (R * S45, R * S45), (0, R / S45)])
                          + _poly([(-R * S45, -R * S45), (R * S45, -R * S45), (R * (2 * S45 - 1), -R),
                                   (-R * (2 * S45 - 1), -R)])).clean())
            inner = _one((inner + _poly([(-r * S45, r * S45), (r * S45, r * S45), (0, r / S45)])).clean())
        return _one(outer - inner)
    if H <= 2 * t or W <= 2 * t:
        raise ValueError(f"{section} section {W} x {H} mm is too small for {t} mm walls")
    if section == "box":
        xl, xr, yb, yt = -W / 2 + t, W / 2 - t, -H / 2 + t, H / 2 - t
        c = min((xr - xl) / 2, yt - yb) if printable else 0.0     # 45 deg ceiling; a peak when the cavity is tall enough
        inner = _poly([(xl, yb), (xr, yb), (xr, yt - c), (xr - c, yt), (xl + c, yt), (xl, yt - c)])
        return _one(Rectangle(W, H).face() - inner)
    if not depth_vertical and section in ("I", "T"):
        raise ValueError(f"an {section} section lying on its side prints its web as an unsupported overhang; "
                         "use section='C' (it then opens upward, flanges standing) or 'box', or turn the part so the "
                         "depth is vertical")
    if section == "T":            # flange on the bed, web up
        return _poly([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, -H / 2 + t), (t / 2, -H / 2 + t), (t / 2, H / 2),
                      (-t / 2, H / 2), (-t / 2, -H / 2 + t), (-W / 2, -H / 2 + t)])
    if section == "C" and not depth_vertical:   # U channel open upward: the standing walls are the flanges
        return _poly([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (W / 2 - t, H / 2), (W / 2 - t, -H / 2 + t),
                      (-W / 2 + t, -H / 2 + t), (-W / 2 + t, H / 2), (-W / 2, H / 2)])
    if section == "I":
        o = (W - t) / 2 if printable else 0.0
        if o > H - 2 * t:
            raise ValueError(f"I section {W} wide x {H} deep: the top flange's 45 deg chamfer ({o:.1f} mm) does not fit "
                             f"in the {H - 2 * t:.1f} mm web; make it deeper or narrower, or use 'box'")
        return _poly([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, -H / 2 + t), (t / 2, -H / 2 + t),
                      (t / 2, H / 2 - t - o), (W / 2, H / 2 - t), (W / 2, H / 2), (-W / 2, H / 2), (-W / 2, H / 2 - t),
                      (-t / 2, H / 2 - t - o), (-t / 2, -H / 2 + t), (-W / 2, -H / 2 + t)])
    if section == "C":            # web on the left, flanges top and bottom; 45 deg under the top flange
        o = (W - t) if printable else 0.0
        if o > H - 2 * t:
            raise ValueError(f"C section {W} wide x {H} deep: the top flange's 45 deg chamfer ({o:.1f} mm) does not fit; "
                             "make it deeper or narrower, or lay it so it opens upward")
        x0 = -W / 2 + t
        return _poly([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, -H / 2 + t), (x0, -H / 2 + t), (x0, H / 2 - t - o),
                      (W / 2, H / 2 - t), (W / 2, H / 2), (-W / 2, H / 2)])
    raise ValueError(f"unknown section '{section}' (one of {SECTIONS})")


def section_profile(section: str, depth: float, width: float, wall: float = 2.0, depth_vertical: bool = True,
                    printable: bool = True) -> Face:
    """The 2D section (XY plane, centred on its bounding box). depth_vertical: the bending depth is vertical on the
    printer (y); otherwise it is horizontal (x) and the width stands up. A tube's diameter is `depth`."""
    if section == "tube":
        W = H = depth
    else:
        W, H = (width, depth) if depth_vertical else (depth, width)
    return _canonical(section, W, H, wall, depth_vertical, printable)


def cavity_profile(section: str, depth: float, width: float, wall: float = 2.0, depth_vertical: bool = True,
                   printable: bool = True) -> Face | None:
    """The hollow of a section (box / tube bore, C channel slot) as a face, in section_profile's frame; None for a
    solid section. Cut as a beam it hollows a solid body only where wanted (closed ends at bosses)."""
    prof = section_profile(section, depth, width, wall, depth_vertical, printable)
    if prof.inner_wires():
        return make_face(prof.inner_wires()[0])
    if section == "C" and not depth_vertical:            # the U's slot, run 1 mm past the open top
        bb = prof.bounding_box()
        W, H = bb.size.X, bb.size.Y
        return _poly([(-W / 2 + wall, -H / 2 + wall), (W / 2 - wall, -H / 2 + wall), (W / 2 - wall, H / 2 + 1),
                      (-W / 2 + wall, H / 2 + 1)])
    return None


def _path(path):
    if not isinstance(path, (list, tuple)):          # already an edge or wire
        return path
    pts = [Vector(*p) for p in path]
    if len(pts) < 2:
        raise ValueError("beam path needs at least two points")
    return Spline(*pts) if len(pts) > 2 else Polyline(*pts)


def _frame(path, s: float, up: Vector, bed: Vector | None):
    """Plane at path parameter s: z = tangent, y = print-up (-bed) or `up`, x = y x z. Returns (plane, depth_vertical)."""
    t = path.tangent_at(s).normalized()
    p = path.position_at(s)
    u = (up - t * up.dot(t))
    if u.length < 1e-6:
        raise ValueError("beam `up` is parallel to the path")
    u = u.normalized()
    y, dv = u, True
    if bed is not None:
        b = -(bed - t * bed.dot(t))
        if b.length < 1e-6:
            raise ValueError("beam `bed` is parallel to the path")
        b = b.normalized()
        if abs(b.dot(u)) > 0.99:
            y = b                                     # depth vertical on the printer
        elif abs(b.dot(u)) < 0.01:
            y, dv = b, False                           # depth horizontal, width stands up
        else:
            raise ValueError("beam `bed` must be along or across `up` (a section is printed square to the bed)")
    return Plane(origin=p, x_dir=y.cross(t), z_dir=t), dv


def _sweep_or_loft(path, prof, depth, up, bed, stations: int = 7):
    """Solid through `prof(depth_at_s)` profiles framed along path (prof(d) -> Face in section coordinates)."""
    pth = _path(path)
    upv, bedv = Vector(*up), Vector(*bed) if bed is not None else None
    if not callable(depth):
        pl, _ = _frame(pth, 0.0, upv, bedv)
        return sweep(pl * prof(float(depth)), path=Wire(pth.edges()) if not isinstance(pth, Wire) else pth)
    profs = []
    for i in range(stations):
        si = i / (stations - 1)
        pl, _ = _frame(pth, si, upv, bedv)
        profs.append(pl * prof(float(depth(si))))
    return loft(profs, ruled=False)


def beam(path, section: str = "box", depth=10.0, width=8.0, wall: float = 2.0, up=(0, 0, 1), bed=None,
         stations: int = 7, printable: bool = True):
    """Solid beam along `path` (points or a build123d edge/wire). depth / width: numbers or functions of s in [0, 1]
    along the path (taper with the bending moment). up: the bending direction (depth axis). bed: the world direction
    of the printer bed for this part's print orientation (default: -up); it must lie along or across `up`."""
    pth = _path(path)
    upv = Vector(*up)
    bedv = Vector(*bed) if bed is not None else None
    f = lambda v, s: float(v(s)) if callable(v) else float(v)       # noqa: E731
    if not callable(depth) and not callable(width):
        pl, dv = _frame(pth, 0.0, upv, bedv)
        prof = pl * section_profile(section, f(depth, 0), f(width, 0), wall, dv, printable)
        return sweep(prof, path=Wire(pth.edges()) if not isinstance(pth, Wire) else pth, is_frenet=False)
    profs = []
    for i in range(stations):
        s = i / (stations - 1)
        pl, dv = _frame(pth, s, upv, bedv)
        profs.append(pl * section_profile(section, f(depth, s), f(width, s), wall, dv, printable))
    return loft(profs, ruled=False)


def bending_I(shape, origin, normal, depth_dir) -> tuple[float, float]:
    """(area mm^2, second moment mm^4 for bending along depth_dir) of the section of `shape` cut at (origin, normal)."""
    import numpy as np
    from .requirements import section_props
    sp = section_props(shape, origin, normal)
    d = np.asarray(depth_dir, float)
    d = d - sp["n"] * d.dot(sp["n"])
    d /= np.linalg.norm(d)
    de = np.array([d.dot(sp["e1"]), d.dot(sp["e2"])])
    return sp["area"], float(de @ sp["S"] @ de)


def fork_link(L: float, ends, section: str = "box", depth: float = 20.0, width: float | None = None,
              wall: float = 2.4, taper: float = 1.0, fillet_r: float = 3.0, channel_d: float | None = None):
    """A link between two pivots L mm apart, printed flat as built: pivot axes along Z (bores print round), link along
    +X from pivot 0 at the origin, bending in the XY plane (depth along Y, tapering from `depth` at pivot 0 to
    depth * taper at pivot 1, i.e. with the bending moment when pivot 0 is the loaded root), thickness along Z.
    ends: two dicts {"bore": d, "boss_d": D, "length": boss height along Z}. The body defaults to the thinner boss
    height, sits on the bed (z = 0), joins the bosses with root fillets, and `channel_d` cuts a wire channel along the
    neutral axis that leaves through the -Y side next to each boss.
    Returns (solid, info) with info = {"pivots": [(x, y, z) of each bore's bottom centre], "failed_fillets": [...]}."""
    from . import features as F
    if len(ends) != 2:
        raise ValueError("fork_link needs two ends")
    for e in ends:
        if e["boss_d"] - e["bore"] < 2 * MIN_WALL * 1.5:
            raise ValueError(f"boss {e['boss_d']} mm around a {e['bore']} mm bore leaves under {MIN_WALL * 1.5} mm of wall")
    if section in ("I", "T"):
        raise ValueError("fork_link prints flat (depth horizontal): use section 'box', 'C', 'rect' or 'tube'")
    th = width if width is not None else min(e["length"] for e in ends)
    bosses = None
    for i, e in enumerate(ends):
        b = Pos(i * L, 0, 0) * Cylinder(e["boss_d"] / 2, e["length"], align=(Align.CENTER, Align.CENTER, Align.MIN))
        bosses = b if bosses is None else bosses + b
    x0, x1 = ends[0]["boss_d"] / 2 * 0.6, L - ends[1]["boss_d"] / 2 * 0.6   # body runs into the bosses
    d0 = min(depth, ends[0]["boss_d"])
    d1 = min(depth * taper, ends[1]["boss_d"])
    if d1 < 2 * wall + 1 and section in ("box", "C", "tube"):
        raise ValueError(f"tapered depth {d1:.1f} mm at pivot 1 is too small for {wall} mm walls")
    dep = (lambda s: d0 + (d1 - d0) * s) if taper != 1.0 else d0
    body = beam([(x0, 0, th / 2), (x1, 0, th / 2)], section="rect", depth=dep, width=th, up=(0, 1, 0), bed=(0, 0, -1))
    solid = body + bosses
    # root fillets: where the body's flanks meet each boss (vertical lines on the boss cylinder, plus the arcs at the
    # body's top when it is thinner than the boss); not the boss's own top / bottom circles
    failed = []
    if fillet_r > 0:
        groups = []
        for i, e in enumerate(ends):
            R, cx = e["boss_d"] / 2, i * L
            ed = [g for g in solid.edges()
                  if all(abs(math.hypot(v.X - cx, v.Y) - R) < 0.05 for v in g.vertices())
                  and not (g.is_closed or all(abs(v.Z) < 0.05 or abs(v.Z - e["length"]) < 0.05 for v in g.vertices()))]
            if ed:
                groups.append((ed, fillet_r))
        solid, failed = F.safe_fillet(solid, groups)
    # hollow (box) or channel (C, open upward) between the bosses, closed by a wall at each boss
    if section != "rect":
        c0 = ends[0]["boss_d"] / 2 + wall
        c1 = L - ends[1]["boss_d"] / 2 - wall
        if c1 - c0 > 2 * wall:
            depc = (lambda s: d0 + (d1 - d0) * (c0 + (c1 - c0) * s - x0) / (x1 - x0)) if taper != 1.0 else d0
            prof = lambda dd: cavity_profile(section, dd, th, wall, False)         # noqa: E731
            cut = _sweep_or_loft([(c0, 0, th / 2), (c1, 0, th / 2)], prof, depc, up=(0, 1, 0), bed=(0, 0, -1))
            solid -= cut
    if channel_d:
        xa = ends[0]["boss_d"] / 2 + wall + channel_d
        xb = L - ends[1]["boss_d"] / 2 - wall - channel_d
        solid -= teardrop_channel([(xa, -d0 / 2 - 1, th / 2), (xa, 0, th / 2), (xb, 0, th / 2), (xb, -d1 / 2 - 1, th / 2)],
                                  channel_d)
    for i, e in enumerate(ends):
        solid -= Pos(i * L, 0, -0.5) * Cylinder(e["bore"] / 2, e["length"] + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return solid, {"pivots": [(0.0, 0.0, 0.0), (float(L), 0.0, 0.0)], "failed_fillets": failed, "thickness": th}


def teardrop_channel(points, d: float, up=(0, 0, 1)):
    """Cutter for a wire channel through straight legs between `points`, with a 45 deg roof toward `up` so a channel
    that runs horizontally on the printer needs no support. Legs overlap by d/2 at the corners."""
    if d < 0.8:
        raise ValueError(f"channel d {d} mm is below the 0.8 mm printable minimum")
    r = d / 2
    face = (Circle(r).face() + _poly([(-r * S45, r * S45), (r * S45, r * S45), (0, r / S45)])).clean().faces()[0]
    pts = [Vector(*p) for p in points]
    out = None
    for a, b in zip(pts, pts[1:]):
        t = (b - a).normalized()
        a2, b2 = a - t * r, b + t * r
        upv = Vector(*up)
        if abs(t.dot(upv.normalized())) > 0.99:              # a vertical leg: round is printable
            leg = Plane(origin=a2, z_dir=t) * extrude(Circle(r), amount=(b2 - a2).length)
        else:
            pl, _ = _frame(Polyline(a2, b2), 0.0, upv, -upv)
            leg = extrude(pl * face, amount=(b2 - a2).length, dir=t)
        out = leg if out is None else out + leg
    return out


def rib_along(face, path, h: float, t: float = 1.6):
    """A rib of height h and thickness t standing on a planar `face` along `path` (points on the face). The rib grows
    along the face's outward normal, so it prints standing when that face is on (or parallel to) the bed."""
    if t < MIN_WALL:
        raise ValueError(f"rib thickness {t} mm is below the {MIN_WALL} mm minimum")
    n = face.normal_at(face.center())
    pts = [Vector(*p) for p in path]
    if len(pts) < 2:
        raise ValueError("rib path needs at least two points")
    out = None
    for a, b in zip(pts, pts[1:]):
        d = b - a
        if d.length < 1e-6:
            continue
        side = n.cross(d).normalized()
        quad = _poly_3d([a - side * (t / 2), b - side * (t / 2), b + side * (t / 2), a + side * (t / 2)])
        seg = extrude(quad, amount=h, dir=n)
        out = seg if out is None else out + seg
    # round joints between segments: a post of diameter t at every inner vertex
    for p in pts[1:-1]:
        out += Plane(origin=p, z_dir=n) * Cylinder(t / 2, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return out


def _poly_3d(pts) -> Face:
    return make_face(Polyline(*pts, close=True))
