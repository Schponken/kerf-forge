"""Detailed-modeling helpers for printed parts. Each returns build123d solids (or cutters) in a simple local frame and
refuses inputs that would not print or would break, with the reason. Sources for every rule are given inline.

    from kerf import features as F
    body -= F.channel([(0, 0, 0), (10, 0, 5), (20, 5, 5)], d=1.6)          # tendon / wire channel cutter
    body = F.shell(body, wall=1.6, open_faces=body.faces().sort_by(Axis.Z)[-1:])
    body += F.gusset((0, 0, 0), (1, 0, 0), (0, 0, 1), 12, 12, t=2.4)
    body -= Location((0, 0, 10), (90, 0, 0)) * F.teardrop_hole(3.4, 20)
    rod = F.threaded_rod(10, 1.5, 20); nut = F.threaded_hole(nut_blank, Location((0, 0, 8)), 10, 1.5, 8)
    g1, g2, info = F.gear_pair(1.5, 12, 36, 6)                            # = kerf.drives.spur_pair
    hook, info = F.snap_hook(length=16, t=2, width=6, undercut=1, material="PETG")
    hinge, info = F.living_hinge(length=6, width=10, t=0.5, angle_deg=90, material="PETG")
    body += F.label("KF v1", size=6, depth=0.6, loc=Location((0, 0, 4)))
    body -= F.pockets(60, 30, depth=4, cell=12, web=2.0, loc=Location((0, 0, 6)))
    body, failed = F.safe_fillet(body, [(body.edges().filter_by(Axis.Z), 1.0)])
"""
from __future__ import annotations

import math

from build123d import (Align, Axis, Box, Cylinder, Location, Plane, Polyline, Pos, Rot, Spline, Text, Vector, chamfer,
                       extrude, fillet, make_face, sweep, Circle, offset)

from . import catalog, drives, iface

MIN_FEATURE = 0.8   # mm, two 0.4 mm nozzle widths (docs/ENGINEERING.md section 5)
MIN_WALL = 1.2      # mm, minimum wall anywhere (ENGINEERING.md section 5)
MIN_EMBOSS = 0.6    # mm, text height/depth (ENGINEERING.md section 5)
THREAD_CLEARANCE_D = 0.4  # mm on diameter between printed mating threads: CCI Bambu sliding fit 0.15-0.2 per side
# (https://wiki.cci.arts.ac.uk/books/digital-fabrication-lab/page/design-the-clearance-and-tolerance)


# ---------------------------------------------------------------- channels
def channel(points, d: float, extend: float = 1.0):
    """Cutter for a round internal channel (tendon, wire) along a smooth 3D spline through `points` (>= 2).
    The ends are extended `extend` mm along the end tangents so the channel breaks cleanly through the surface."""
    if len(points) < 2:
        raise ValueError("channel needs at least two points")
    if d < MIN_FEATURE:
        raise ValueError(f"channel d {d} mm is below the {MIN_FEATURE} mm printable minimum")
    pts = [Vector(*p) for p in points]
    path = Spline(*pts) if len(pts) > 2 else Polyline(*pts)
    t0, t1 = path.tangent_at(0), path.tangent_at(1)
    a, b = pts[0] - t0 * extend, pts[-1] + t1 * extend
    edges = [Polyline(a, pts[0]).edges()[0], *path.edges(), Polyline(pts[-1], b).edges()[0]]
    from build123d import Wire
    w = Wire(edges)
    prof = Plane(origin=a, z_dir=t0) * Circle(d / 2)
    return sweep(prof, path=w, transition=__import__("build123d").Transition.ROUND)


# ---------------------------------------------------------------- shells, ribs, holes
def shell(shape, wall: float, open_faces=None):
    """Hollow `shape` to a uniform `wall` (inward), leaving `open_faces` (list of faces of shape) open."""
    if wall < MIN_WALL:
        raise ValueError(f"shell wall {wall} mm is below the {MIN_WALL} mm minimum")
    return offset(shape, amount=-wall, openings=list(open_faces or []))


def gusset(corner, dir1, dir2, leg1: float, leg2: float, t: float):
    """Triangular rib/gusset in the corner between two faces: right-angle legs `leg1` along `dir1` and `leg2` along
    `dir2` from `corner`, thickness `t` centred on the plane of the two directions."""
    if t < MIN_WALL:
        raise ValueError(f"gusset thickness {t} mm is below the {MIN_WALL} mm minimum")
    c, u, v = Vector(*corner), Vector(*dir1).normalized(), Vector(*dir2).normalized()
    n = u.cross(v)
    if n.length < 1e-6:
        raise ValueError("gusset directions are parallel")
    n = n.normalized()
    face = make_face(Polyline(c, c + u * leg1, c + v * leg2, close=True))
    return Pos(n * (-t / 2)) * extrude(face, amount=t, dir=n)


def teardrop_hole(d: float, length: float, up_deg: float = 90.0):
    """Horizontal-hole cutter: circle d with a 45 deg roof toward `up_deg` (direction that is UP on the printer, in the
    hole's XY plane). Axis Z, from z = +1 down to z = -length (same frame as iface holes)."""
    return iface._teardrop(d / 2, -length, iface.EXTRA, up_deg)


# ---------------------------------------------------------------- threads
def _thread_checks(d, pitch):
    if pitch * 0.6134 < MIN_EMBOSS:  # ISO basic thread depth H1 = 0.5413 P; external 0.6134 P
        raise ValueError(f"pitch {pitch} mm gives a {pitch * 0.6134:.2f} mm thread depth: too fine to print; use pitch "
                         f">= 1.0 or a heat-set insert / metal screw")
    if d < 6:
        raise ValueError(f"printed threads below M6 strip; use a heat-set insert for d={d}")


def threaded_rod(d: float, pitch: float, length: float, clearance: float = THREAD_CLEARANCE_D):
    """Printed external ISO-profile thread (bd_warehouse) of nominal diameter d, shrunk by clearance/2 so it mates
    a `threaded_hole` of the same d. Axis Z, from z=0 to z=length."""
    from bd_warehouse.thread import IsoThread
    _thread_checks(d, pitch)
    th = IsoThread(d - clearance / 2, pitch, length, external=True, end_finishes=("fade", "fade"))
    core = Cylinder(th.min_radius, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return core + th


def threaded_hole(shape, loc: Location, d: float, pitch: float, depth: float, clearance: float = THREAD_CLEARANCE_D):
    """Cut a printed internal ISO thread into `shape`. loc on the entry face, +Z out of the material. A threaded_rod of
    the same d and pitch with its z=0 at the hole bottom meshes with it."""
    from bd_warehouse.thread import IsoThread
    _thread_checks(d, pitch)
    D = d + clearance / 2
    th = IsoThread(D, pitch, depth, external=False, end_finishes=("fade", "fade"))
    hole = Cylinder(D / 2, depth + 2 * iface.EXTRA, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # bd_warehouse starts internal threads half a pitch out of phase with external ones; turn it 180 deg so a
    # threaded_rod whose z=0 sits at the hole bottom (loc z = -depth) meshes with no overlap
    return shape - loc * Pos(0, 0, -depth - iface.EXTRA) * hole + loc * Pos(0, 0, -depth) * Rot(0, 0, 180) * th


# ---------------------------------------------------------------- gears
def gear_pair(module: float, z1: int, z2: int, width: float, **kw):
    """Spur gear pair at the correct centre distance (py_gearworks). See kerf.drives.spur_pair."""
    return drives.spur_pair(module, z1, z2, width, **kw)


# ---------------------------------------------------------------- compliant features
def allowable_strain(material: str, frequent: bool = False) -> float:
    """Permissible bending strain for snap-fits/flexures: ~70% of yield strain for amorphous plastics, x0.6 for
    frequent separation (Bayer 'Snap-Fit Joints for Plastics', section B and Table 2,
    https://fab.cba.mit.edu/classes/S62.12/people/vernelle.noel/Plastic_Snap_fit_design.pdf). Yield strain is taken as
    catalog XY strength / modulus (linear, so conservative for plastics whose curve flattens before yield)."""
    m = catalog.get(f"materials.{material}")
    s = catalog.num(m, "tensile_strength_xy_mpa", "tensile_strength_mpa")
    e = catalog.num(m, "youngs_modulus_mpa", "youngs_modulus")
    return 0.7 * s / e * (0.6 if frequent else 1.0)


def snap_hook(length: float, t: float, width: float, undercut: float, material: str = "PETG", taper: bool = True,
              frequent: bool = False, lead_deg: float = 30.0, ret_deg: float = 90.0):
    """Cantilever snap hook. Beam along +X from the root at x=0 (attach the root face to your part), bending in Z,
    thickness t at the root (tapered to t/2 at the hook if taper), hook of height `undercut` on +Z at the tip.
    Strain check (Bayer manual): eps = y h / (0.67 l^2) constant section, y h / (1.09 l^2) tapered to h/2.
    Raises if eps exceeds allowable_strain(material, frequent). Print with the beam flat on the bed (bending along
    layers). Returns (solid, info)."""
    if t < MIN_FEATURE or width < 2 * MIN_FEATURE:
        raise ValueError("snap hook thinner than two nozzle widths")
    k = 1.09 if taper else 0.67
    eps = undercut * t / (k * length ** 2)
    allow = allowable_strain(material, frequent)
    info = {"strain": round(eps, 5), "allowable": round(allow, 5), "ok": eps <= allow,
            "min_length_mm": round(math.sqrt(undercut * t / (k * allow)), 2)}
    if not info["ok"]:
        raise ValueError(f"snap hook strain {eps * 100:.2f}% exceeds the {allow * 100:.2f}% allowed for {material}; "
                         f"lengthen the beam to >= {info['min_length_mm']} mm or thin it")
    tip = t / 2 if taper else t
    if tip < MIN_FEATURE:
        raise ValueError(f"hook tip {tip} mm thinner than {MIN_FEATURE} mm; thicken or use taper=False")
    run = undercut / math.tan(math.radians(lead_deg))          # lead-in ramp
    back = undercut / math.tan(math.radians(ret_deg)) if ret_deg < 89.9 else 0.0  # retention face slope
    hb = MIN_FEATURE + run                                     # hook length on the beam (0.8 mm flat top + ramp)
    beam = make_face(Polyline((0, 0), (length, 0), (length, tip), (0, t), close=True))
    hook = make_face(Polyline((length - hb - back, tip), (length - hb, tip + undercut), (length - hb + MIN_FEATURE, tip + undercut),
                              (length, tip), close=True))
    solid = Pos(0, width / 2, 0) * extrude(Plane.XZ * (beam + hook), amount=width)  # sketch y -> world Z
    return solid, info


def living_hinge(length: float, width: float, t: float, angle_deg: float, material: str = "PETG", pad: float = 6.0,
                 pad_t: float = 3.0, frequent: bool = True):
    """Thin flexure joining two pads. Bending the web of length `length` by angle theta uniformly gives strain
    eps = t * theta / (2 * length) (curvature theta / length, strain = curvature x t / 2). Raises if eps exceeds
    allowable_strain(material, frequent). Pads lie along X either side of the web; all on the bed (z=0..pad_t),
    web z=0..t. Returns (solid, info)."""
    if t < 0.4:
        raise ValueError("living hinge web below one 0.4 mm layer-line width")
    eps = t * math.radians(angle_deg) / (2 * length)
    allow = allowable_strain(material, frequent)
    info = {"strain": round(eps, 5), "allowable": round(allow, 5), "ok": eps <= allow,
            "max_angle_deg": round(math.degrees(allow * 2 * length / t), 1)}
    if not info["ok"]:
        raise ValueError(f"living hinge strain {eps * 100:.2f}% at {angle_deg} deg exceeds {allow * 100:.2f}% for "
                         f"{material}; max {info['max_angle_deg']} deg - lengthen or thin the web")
    a = Pos(-length / 2 - pad, 0, 0) * Box(pad, width, pad_t, align=(Align.MIN, Align.CENTER, Align.MIN))
    b = Pos(length / 2, 0, 0) * Box(pad, width, pad_t, align=(Align.MIN, Align.CENTER, Align.MIN))
    web = Box(length + 2, width, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return a + b + web, info


# ---------------------------------------------------------------- text and pockets
def label(text: str, size: float, depth: float = MIN_EMBOSS, loc: Location | None = None, emboss: bool = True):
    """Embossed (add) or debossed (subtract) text. loc on the face, +Z out of it. Font size >= 5 mm keeps strokes over
    0.8 mm; depth >= 0.6 mm (ENGINEERING.md section 5)."""
    if depth < MIN_EMBOSS:
        raise ValueError(f"text depth {depth} mm < {MIN_EMBOSS} mm")
    if size < 5.0:
        raise ValueError(f"font size {size} mm makes strokes thinner than {MIN_FEATURE} mm; use >= 5 mm")
    sk = Text(text, size)
    s = extrude(sk, depth) if emboss else Pos(0, 0, -depth) * extrude(sk, depth + iface.EXTRA)
    return (loc or Location()) * s


def pockets(w: float, h: float, depth: float, cell: float, web: float = 2.0, corner_r: float = 1.0,
            loc: Location | None = None, floor: float | None = None):
    """Grid of rounded-rectangle lightening pockets filling a w x h region (centred on loc, +Z out of the face, cut
    into -Z by `depth`), keeping every web between pockets and to the region edge >= `web`."""
    if web < MIN_WALL:
        raise ValueError(f"web {web} mm < {MIN_WALL} mm minimum wall")
    nx, ny = max(1, int((w - web) // cell)), max(1, int((h - web) // cell))
    px, py = (w - web) / nx - web, (h - web) / ny - web
    if px < 2 * corner_r or py < 2 * corner_r:
        raise ValueError("region too small for any pocket with that web")
    from build123d import RectangleRounded
    cut = None
    for i in range(nx):
        for j in range(ny):
            x = -w / 2 + web + px / 2 + i * (px + web)
            y = -h / 2 + web + py / 2 + j * (py + web)
            p = Pos(x, y, -depth) * extrude(RectangleRounded(px, py, corner_r), depth + iface.EXTRA)
            cut = p if cut is None else cut + p
    return (loc or Location()) * cut


# ---------------------------------------------------------------- safe edge treatment
def safe_fillet(shape, groups, kind: str = "fillet"):
    """Apply fillets (or chamfers) group by group: groups = [(edges, size), ...]. A group OCC can't do is retried
    edge by edge; edges that still fail are skipped and reported. Returns (shape, failed: list[str])."""
    op = fillet if kind == "fillet" else chamfer
    failed = []
    for gi, (edges, size) in enumerate(groups):
        edges = list(edges)
        try:
            shape = _apply(op, shape, edges, size)
            continue
        except Exception:  # noqa: BLE001
            pass
        for k, e in enumerate(edges):
            try:
                shape = _apply(op, shape, [_match(shape, e)], size)
            except Exception as ex:  # noqa: BLE001
                c = e.center()
                failed.append(f"group {gi} edge {k} at ({c.X:.1f}, {c.Y:.1f}, {c.Z:.1f}) {kind} {size}: {type(ex).__name__}")
    return shape, failed


def _apply(op, shape, edges, size):
    r = shape.fillet(size, edges) if op is fillet else shape.chamfer(size, None, edges)
    if not r.is_valid:
        raise ValueError("invalid result")
    return r


def _match(shape, e):
    """The edge of `shape` closest to edge e (edges change identity after each operation)."""
    c = e.center()
    return min(shape.edges(), key=lambda x: (x.center() - c).length + abs(x.length - e.length))
