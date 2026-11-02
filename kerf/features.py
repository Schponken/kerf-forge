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

from build123d import (Align, Box, Cylinder, Location, Plane, Polyline, Pos, Rot, Spline, Text, Vector, chamfer,
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


def bed_edges(ctx, shape, tol: float = 0.05):
    """Edges of `shape` (part frame) that lie on the print bed for the part's `print_rot`: outer outline and hole rims
    of the first layer. Use for docs/ENGINEERING.md section 5's 0.5 mm elephant's-foot chamfer."""
    rot = ((getattr(ctx, "meta", None) or {}).get("spec") or {}).get("print_rot") or [0, 0, 0]
    up = (Location((0, 0, 0), tuple(float(a) for a in rot)).inverse() * Location((0, 0, 1))).position
    h = lambda v: v.X * up.X + v.Y * up.Y + v.Z * up.Z  # noqa: E731
    z0 = min(h(v) for v in shape.vertices())
    return [e for e in shape.edges() if all(abs(h(v) - z0) < tol for v in e.vertices())
            and abs(h(e.center()) - z0) < tol]


def bed_chamfer(ctx, shape, size: float = 0.5):
    """0.5 mm chamfer on every first-layer edge (bed_edges); returns (shape, failed) like safe_fillet. Edges OCC cannot
    chamfer (slivers, edges meeting a fillet) are skipped and reported as a part note (a build warning) so the builder
    knows to deburr them."""
    edges = bed_edges(ctx, shape)
    shape, failed = safe_fillet(shape, [(edges, size)], kind="chamfer")
    if failed and getattr(ctx, "notes", None) is not None:
        ctx.notes.append(f"{len(failed)} of {len(edges)} first-layer edges could not take the {size} mm elephant's-foot "
                         f"chamfer (deburr them after printing): " + "; ".join(f.split(" chamfer")[0] for f in failed[:4])
                         + (" ..." if len(failed) > 4 else ""))
    return shape, failed


# ---------------------------------------------------------------- structural sections (kerf/sections.py)
from .sections import (beam, bending_I, cavity_profile, fork_link, rib_along, section_profile,  # noqa: E402,F401
                       teardrop_channel)
from .idioms import (boss, cable_saddle, clevis, grip_pad, servo_cradle, side_plate,  # noqa: E402,F401
                     yoke_cheek)


def _meshes(shape) -> bool:
    """True when the shape still tessellates and gmsh can mesh its surfaces at the size kerf.fea uses: fillets that run
    into each other can leave slivers that break the FEA mesh ("1D mesh not forming a closed loop")."""
    import os
    import tempfile
    try:
        shape.tessellate(0.2, 0.5)
        import gmsh
        from build123d import export_step
        bb = shape.bounding_box()
        size = max(min(bb.size.X, bb.size.Y, bb.size.Z) / 4.0, 0.6)
        with tempfile.TemporaryDirectory() as t:
            f = os.path.join(t, "p.step")
            export_step(shape, f)
            gmsh.initialize(["-noenv"])
            try:
                gmsh.option.setNumber("General.Terminal", 0)
                gmsh.model.add("p")
                gmsh.model.occ.importShapes(f)
                gmsh.model.occ.synchronize()
                gmsh.option.setNumber("Mesh.MeshSizeMax", size)
                gmsh.option.setNumber("Mesh.MeshSizeMin", size / 3)
                gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 24)
                gmsh.model.mesh.generate(2)
            finally:
                gmsh.finalize()
        return True
    except Exception:  # noqa: BLE001
        return False


def _print_up(ctx):
    """The printer's up direction in the part frame (from the part's print_rot), as bed_edges uses it."""
    rot = ((getattr(ctx, "meta", None) or {}).get("spec") or {}).get("print_rot") or [0, 0, 0]
    return (Location((0, 0, 0), tuple(float(a) for a in rot)).inverse() * Location((0, 0, 1))).position


def _fillet_faces_down(shape, e, up) -> bool:
    """True when a fillet on concave edge e would face more than 45 degrees down on the printer (an overhang): its
    surface normals sweep from one face's normal to the other's."""
    fs = [f for f in shape.faces() if any(e.is_same(x) for x in f.edges())]
    if len(fs) != 2:
        return False
    c = e.center()
    n1, n2 = fs[0].normal_at(c), fs[1].normal_at(c)
    for k in range(11):
        t = k / 10
        v = n1 * (1 - t) + n2 * t
        if v.length > 1e-9 and v.normalized().dot(up) < -0.7072:
            return True
    return False


def fillet_inside(ctx, shape, r: float = 1.0, keep=None, occ: bool = False):
    """Round every sharp inside corner the build check would report (kerf.edges.sharp_inside: straight concave edges
    between flat faces, the corners of interface features exempt) with radius r, then r / 2 on those whose faces are
    too short for r. The fillets are boolean coves (kerf.coves: the fillet's material added by union), not OCC's fillet
    operator, which can crash the process on bodies built from many unions. Coves that leave a body gmsh (kerf.fea's
    mesher) cannot mesh are dropped (the set is split until the bad ones are found). A corner whose fillet would face
    more than 45 degrees down as printed (the corner under a ceiling) is left square and declared: rounding it would
    add an overhang. keep(at) -> a reason string leaves a corner sharp on purpose (a mating part's square corner sits
    in it); it is declared with ctx.keep_sharp, so the report lists it with that reason instead of warning.
    occ=True tries OCC's real fillet first (it blends into the neighbouring faces where a cove has to stop short,
    which matters at a stressed corner) and coves only what it leaves; use it on bodies where it has been seen to
    work, since OCC can crash the process outright on others.
    Returns (shape, failed): the corners left sharp that were not declared, as "(x, y, z)" strings for ctx.notes."""
    from . import coves
    from . import edges as E
    sites = getattr(ctx, "sites", None) or []
    up = _print_up(ctx)
    DOWN = "a fillet here would face down as printed (an overhang under a ceiling); left square"

    def why_kept(s, c, e):
        if keep is not None:
            w = keep(c["at"])
            if w:
                return w
        return DOWN if e is not None and _fillet_faces_down(s, e, up) else None

    def edge_of(s, c):
        at = Vector(*c["at"])
        e = min(s.edges(), key=lambda x: (x.center() - at).length + abs(x.length - c["len"]))
        return e if (e.center() - at).length < 0.1 else None

    def pick(s):
        out = []
        for c in E.sharp_inside(s, sites):
            e = edge_of(s, c)
            if e is not None and not why_kept(s, c, e):
                out.append(e)
        return out

    def apply(s, prisms):
        """Union the cove prisms; if the result does not mesh or splits, keep every half of the set that works."""
        if not prisms:
            return s
        new = s
        for cv in prisms:
            new = new + cv
        if len(new.solids()) == len(s.solids()) and new.is_valid and _meshes(new):
            return new
        if len(prisms) == 1:
            return s
        half = len(prisms) // 2
        return apply(apply(s, prisms[:half]), prisms[half:])

    def occ_apply(s, todo, size):
        new, _ = safe_fillet(s, [(todo, size)])
        if _meshes(new):
            return new
        if len(todo) == 1:
            return s
        half = len(todo) // 2
        s = occ_apply(s, todo[:half], size)
        return occ_apply(s, [_match(s, e) for e in todo[half:]], size)

    for size in ((r, r / 2) if occ else ()):
        todo = pick(shape)
        if todo:
            shape = occ_apply(shape, todo, size)
    for size in (r, r / 2):
        todo = pick(shape)
        if not todo:
            break
        prisms = []
        for e in todo:
            # (a cove stopped short of an interrupted end was tried and dropped: its end step made a worse notch than
            # the sharp corner - the pan_tilt yoke knock peak went 17 -> 44 MPa; such corners stay sharp and reported)
            cv = coves.cove(shape, e, size)
            if cv is not None and cv.volume > 0:
                prisms.append(cv)
        shape = apply(shape, prisms)
    if hasattr(ctx, "keep_sharp"):
        for c in E.sharp_inside(shape, sites):
            w = why_kept(shape, c, edge_of(shape, c))
            if w:
                ctx.keep_sharp(c["at"], w)
    return shape, [f"({e.center().X:.1f}, {e.center().Y:.1f}, {e.center().Z:.1f})" for e in pick(shape)]
