"""Wing root hub (hub_r / hub_l, side from ctx.id): the panel's root block from y = pivot_y to hub_y1, the pivot boss,
the 21 T sector gear and the spar sockets. CF-PETG, 4 perimeters, printed flat on its lower side (boss vertical):
boss bottom and sector bottom on the bed, so the pin bore prints round and the gear teeth lie in the layers.
The airfoil's lower surface is the only overhang left (tree supports): an aerodynamic surface has to be curved.

Load path: the spar tubes (8 + 6 mm CF, epoxied 54 mm deep in teardrop sockets) bring the half-wing's lift moment
into the root block. The root block is a closed airfoil box; aft of the rear spar, where the airfoil gets thin, a
V keel under the root (45 deg sides, its edge 0.6 mm above the fuselage top) and a double cone round the boss (45 deg
up and down, r 19.4 at the chord plane) keep the section deep, so the moment reaches the boss as torsion of a deep
section. The boss (r 10, z boss_z0..boss_z1) turns freely on the 4 mm steel pin, which is held top (spine arm) and
bottom (pivot deck) 43 mm apart: the moment becomes a bearing couple there, never a load on the servo.
The sector gear below the boss (inside the fuselage) carries the servo torque; its two radial end faces hit the
aft fuselage's stop posts at 0 and fold_max. The aileron lead runs from the outer face through the root block to
beside the boss and straight down through the sector web.
"""
from build123d import *
import math
import importlib.util, pathlib
from kerf import aero, iface
from kerf.sections import teardrop_channel

_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

SECTOR_MARGIN = 22.5    # deg of teeth past the meshing tooth at each end of the fold (> one 17.1 deg pitch)
KEEL_Z = -9.4           # lowest point of the root block: 0.6 above the fuselage top / spine cover (z -10)
KEEL_Y = (26.3, 45.7)   # V keel span (right side), 45 deg sides to its edge at KEEL_Z
KEEL_X = (130.0, 205.0)
LEAD_D = 4.0            # aileron lead channel: same 4 mm as the wing segments' channel (wing.py)
LEAD_R = 12.0           # lead drop beside the boss (layout lead_exit: 12 mm ahead of the pin)


def sector_deg(p):
    """Hub angles (deg, right side, CCW from +X seen from above) of the sector's two end faces. The pinion meshes at
    hub angle 180 at fold 0 and 180 + fold_max folded; aft_fuse.py puts its stop posts beside these faces."""
    return 180.0 - SECTOR_MARGIN, 180.0 + p.fold_max + SECTOR_MARGIN


def _wedge(c, a0, a1, r, z0, z1):
    n = max(3, int(abs(a1 - a0) / 10) + 2)
    pts = [(c[0], c[1])] + [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))),
                             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]
    return Pos(0, 0, z0) * extrude(Polygon(*pts, align=None), z1 - z0, dir=(0, 0, 1))


def _cyl(c, r, z0, z1):
    return Pos(c[0], c[1], z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def right_body(ctx):
    """The right hub without its pin bore (the left one is its mirror image)."""
    p = ctx.p
    pf = L.planform(p)
    c = (p.pivot_x, p.pivot_y)
    body = ctx.add(aero.wing_solid(pf, p.pivot_y, p.hub_y1), why="root block: the wing root airfoil, closed box", kind="block")
    # V keel under the root aft of the rear spar: depth where the airfoil thins out (torsion to the boss)
    ym = sum(KEEL_Y) / 2
    v = Plane(origin=(KEEL_X[0], 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)) * Polygon(
        (KEEL_Y[0], 0.3), (KEEL_Y[1], 0.3), (ym, KEEL_Z), align=None)
    keel = extrude(v, KEEL_X[1] - KEEL_X[0], dir=(1, 0, 0))
    front = Plane(origin=(0, 60, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)) * Polygon(
        (KEEL_X[0], 0.5), (KEEL_X[1] + 1, 0.5), (KEEL_X[1] + 1, KEEL_Z - 1), (KEEL_X[0] + 0.5 - KEEL_Z + 1, KEEL_Z - 1), align=None)
    keel &= extrude(front, 40, dir=(0, -1, 0))
    body += ctx.add(keel, why="V keel: section depth for the root moment between rear spar and boss", kind="keel")
    # double cone round the boss (45 deg both ways), only where it never swings over the spine ridge
    h = -KEEL_Z
    bicone = Pos(c[0], c[1], KEEL_Z) * Cone(p.boss_r, p.boss_r + h, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bicone += Pos(c[0], c[1], 0) * Cone(p.boss_r + h, p.boss_r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    keep = Pos(c[0], c[1] - p.boss_r, -50) * Box(100, 100, 100, align=(Align.MAX, Align.MIN, Align.MIN))
    keep += Pos(c[0], c[1], -50) * Box(p.pivot_back, 100, 100, align=(Align.MIN, Align.MIN, Align.MIN))
    body += ctx.add(bicone & keep, why="boss collar: blends the boss into the root block at 45 deg", kind="collar")
    body += ctx.add(_cyl(c, p.boss_r, p.boss_z0, p.boss_z1), why="pivot boss, free on the steel pin", kind="boss")
    # sector gear: L.gears() sector (phased to the pinion), its bottom extended to the boss bottom so both sit on
    # the bed; teeth over sector_deg plus the web back to the boss
    _, g = L.gears()
    gface = g.faces().sort_by(Axis.Z)[0]
    gear = Pos(c[0], c[1], p.boss_z0) * extrude(gface, p.sector_z1 - p.boss_z0, dir=(0, 0, 1))
    a0, a1 = sector_deg(p)
    body += ctx.add(gear & _wedge(c, a0, a1, p.sector_ro + 5, p.boss_z0 - 1, p.sector_z1 + 1),
                    why="21 T sector gear (module 2): servo torque into the wing; end faces are the stop faces", kind="gear")
    # spar sockets: blind teardrop bores from spar_y0 (tube end) out through the outer face
    for which, od in (("main", p.main_od), ("rear", p.rear_od)):
        a, b = L.tube_line(p, which, 1)
        u = [(bb - aa) / (b[1] - a[1]) for aa, bb in zip(a, b)]          # per mm of y

        def at(y):
            return tuple(aa + uu * (y - a[1]) for aa, uu in zip(a, u))
        r = (od + 0.2) / 2
        body -= ctx.cut(teardrop_channel([at(p.spar_y0 - 0.5 + r), at(p.hub_y1 + 1.0 - r)], od + 0.2),
                        why=f"{which} spar socket, OD + 0.2, epoxied, {p.hub_y1 - p.spar_y0:.0f} mm engagement", kind="socket")
    # aileron lead: outer face (lead_root) -> under the root -> beside the boss -> down through the sector web
    lr = L.lead_root(p, 1)
    le = L.lead_exit(p, 1)
    zr = float(lr[2])
    path = [(float(lr[0]), p.hub_y1 + 2.0, zr), (float(lr[0]), p.hub_y1 - 10.0, 0.6), (float(lr[0]), p.spar_y0 + 4, 0.6), le]
    body -= ctx.cut(teardrop_channel(path, LEAD_D), why="aileron servo lead channel", kind="wire channel")
    body -= ctx.cut(_cyl((le[0], le[1]), LEAD_D / 2, p.boss_z0 - 1, le[2] + 0.5),
                    why="aileron lead drops into the fuselage through the sector web", kind="wire channel")
    return body


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    n = "l" if s < 0 else "r"
    body = right_body(ctx)
    if s < 0:
        body = mirror(body, Plane.XZ)
    top = Location((p.pivot_x, s * p.pivot_y, p.boss_z1))
    body -= iface.pin_hole(ctx, L.PIN, top, f"pivot_{n}", depth=p.boss_z1 - p.boss_z0, fit="free", teardrop="auto")
    ctx.rigid("pivot", L.pivot_axis(p, s).location)
    ctx.rigid("wing", Location())
    ctx.rigid("main", L.tube_loc(p, "main", s))
    ctx.rigid("rear", L.tube_loc(p, "rear", s))
    return ctx.finish(body)
