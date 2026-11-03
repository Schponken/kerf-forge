"""Panel root hub (hub_r / hub_l): the swing-wing panel's root fitting, turning on the pivot pin in two 625 bearings.

Load path (DESIGN.md "Load -> section"): the two CF spar tubes (epoxied in teardrop sockets from y 156) bring the 5.5 N m
root moment into the airfoil block; aft of the rear spar the airfoil is only 3-6 mm deep, so a raised closed box (top z 6,
flat underside z -2, tapering out into the airfoil at y 194) keeps the section 8 mm deep all the way to the boss, and the
moment reaches the boss as torsion + bending of that box (the sibling's hub failed exactly there). The boss (r 11, z -27..6)
carries two bearings 28 mm apart (centre to centre), so the moment becomes a bearing couple on the 5 mm pin, never a load
on the servo. The 21 T sector below the wing carries only servo torque; its tooth-less ears are the stop faces.
Elbow disc r 24 round the pin: the inboard half turns in the glove's r 25 notch, and the corner of the block between the
disc and the trailing edge is cut away (the 'bite') so nothing swings into the glove's trailing edge over the sweep.
PETG 50 %, printed flat (boss vertical): the sockets and lead channel run horizontally, so they have teardrop roofs.
"""
from build123d import *
import math
import importlib.util, pathlib
from kerf import aero, iface, features
from kerf.sections import teardrop_channel

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

BOX_X0 = 180.0           # raised box starts here: 1.5 mm aft of the rear spar socket's wall (tube x 171..175 + r 3.1)
BOX_TOP = 6.0            # = boss top: the cap sits at 6.5
DISC_TOP_IN = 2.5        # inboard half of the disc, inside the glove notch: just under the glove's top skin there (3.6..4.6)
BOX_TAPER_FROM_ROOT = 32.0      # the box's top and underside close in from here to a point at y 194, inside the airfoil
BITE_CLR = 0.5           # the hub keeps this far off the glove's trailing edge at the end of the sweep
RELIEF_DEG = 2.3         # > stop over-travel (2.2 deg) + the 0.5 mm glove gap; the main socket mouth (x 100) is then at y 155.5, tube end 156
LEAD_D = 4.0
LEAD_Z = 2.6             # lead channel height in the box (underside -2, top 6: 4.6 mm / 1.4 mm of wall above its roof)
EAR = 4.0                # deg of tooth-less sector past the teeth at each end: the stop faces


def _wedge(c, a0, a1, r, z0, z1):
    n = max(3, int(abs(a1 - a0) / 10) + 2)
    pts = [(c[0], c[1])] + [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))),
                             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]
    return Pos(0, 0, z0) * extrude(Polygon(*pts, align=None), z1 - z0, dir=(0, 0, 1))


def _cyl(c, r, z0, z1):
    return Pos(c[0], c[1], z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _lead_pts(p):
    lr = L.lead_root(p, 1)
    ex = (p.pivot_x + L.LEAD_EXIT_D[0], p.pivot_y + L.LEAD_EXIT_D[1])
    return [(float(lr[0]), p.hub_y1 + 1.0, float(lr[2])), (0.5 * (float(lr[0]) + ex[0]), 0.5 * (p.hub_y1 + ex[1]), LEAD_Z),
            (ex[0], ex[1], LEAD_Z), (ex[0], ex[1], BOX_TOP + 1.0)]


def _channels(p):
    """(name, radius, polyline) of the right hub's bores, for the teardrop roofs declared in the fillet pass."""
    out = [(f"{w} spar socket", (od + 0.2) / 2, list(L.tube_line(p, w, 1))) for w, od in (("main", p.main_od), ("rear", p.rear_od))]
    out.append(("aileron lead channel", LEAD_D / 2, _lead_pts(p)))
    return out


def _in_channel(p, q):
    import numpy as np
    q = np.array(q, float)
    for name, r, pts in _channels(p):
        for a, b in zip(pts, pts[1:]):
            a, b = np.array(a, float), np.array(b, float)
            t = np.clip(np.dot(q - a, b - a) / np.dot(b - a, b - a), 0, 1)
            if np.linalg.norm(q - (a + t * (b - a))) <= r * 1.5 + 0.3:
                return name
    return None


def right_body(ctx):
    p = ctx.p
    pf = L.planform(p)
    c = (p.pivot_x, p.pivot_y)
    R = L.DISC_R - 0.05                                       # 0.05 off the trailing edge's tangent (a tangent solid is non-manifold)
    a_max = p.fold_max + 3.0                                  # the sweep plus the stop over-travel (stop_fold beyond 68)
    body = ctx.add(aero.wing_solid(pf, p.pivot_y, p.hub_y1), why="root block: the wing's root airfoil (y 150..195), meets wing_x1 flush at 195", kind="block")

    # raised closed box aft of the rear spar (top z 6, flat underside z -2), tapering out into the airfoil at y 194
    prof = Plane(origin=(BOX_X0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)) * Polygon(
        (p.pivot_y, L.HUB_DISC_Z0), (p.pivot_y + BOX_TAPER_FROM_ROOT, L.HUB_DISC_Z0), (p.hub_y1 - 1, 1.4), (p.pivot_y + BOX_TAPER_FROM_ROOT, BOX_TOP), (p.pivot_y, BOX_TOP), align=None)
    box = extrude(prof, c[0] + p.pivot_back - BOX_X0 + 1.0, dir=(1, 0, 0))
    body += ctx.add(box, why="raised closed box aft of the rear spar: keeps the section 8 mm deep (airfoil is 3-6 mm there) so the 5.5 N m "
                    "root moment reaches the boss as torsion + bending of a deep section (sibling hub's weak point)", kind="box")

    # the bite: the block's corner between the disc and the trailing edge would sweep into the glove's TE over the fold
    x_te = c[0] + p.pivot_back
    d2 = R + BITE_CLR
    ta = math.radians(a_max)
    p_te = (x_te, c[1] + (d2 - p.pivot_back * math.cos(ta)) / math.sin(ta))
    q = (c[0] + d2 * math.cos(ta), c[1] + d2 * math.sin(ta))
    bite = Pos(0, 0, -20) * extrude(Polygon(c, (x_te + 1, c[1]), (x_te + 1, p_te[1]), p_te, q, align=None), 60, dir=(0, 0, 1))
    body -= ctx.cut(bite, why=f"corner of the block between the disc and the trailing edge: swept {a_max:.0f} deg it would hit the glove's TE "
                    f"(kept {BITE_CLR} mm off it)", kind="clearance")

    # root-face relief: the flat root face (y 150, 0.5 mm off the glove) would hit the glove after 0.2 deg of the spread
    # stop's over-travel (136 mm lever at the main spar); a face raised by tan(2.3 deg) per mm ahead of the pin lets the
    # panel reach the stop (2.2 deg past spread) first. The spar socket mouths (y 156) stay in material.
    t = math.tan(math.radians(RELIEF_DEG))
    relief = Pos(0, 0, -20) * extrude(Polygon((c[0], p.pivot_y - 1.0), (c[0] - 220.0, p.pivot_y - 1.0), (c[0] - 220.0, p.pivot_y + 220.0 * t),
                                              (c[0], p.pivot_y), align=None), 60, dir=(0, 0, 1))
    body -= ctx.cut(relief, why=f"root face tilted {RELIEF_DEG} deg (plane through the pin): the spread stop, not the glove, ends the panel's travel", kind="clearance")

    # elbow disc round the pin: inboard half (turns in the glove's r 25 notch) low, outboard half full height
    disc = _cyl(c, R, L.HUB_DISC_Z0, DISC_TOP_IN)
    disc += _cyl(c, R, L.HUB_DISC_Z0, BOX_TOP) & Pos(c[0], c[1] + 1.0 + 50, 0) * Box(100, 100, 100, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    body += ctx.add(disc, why=f"elbow disc r {R:g} round the pin, flat underside z {L.HUB_DISC_Z0}: turns inside the glove's r {L.NOTCH_R:g} notch", kind="disc")

    # boss with the two bearings' seats: the pin's bearing couple
    body += ctx.add(_cyl(c, L.BOSS_R, L.BOSS_Z0, L.BOSS_Z1), why="pivot boss r 11: 3 mm wall round the 625 bearings, 28 mm apart", kind="boss")

    # sector gear (phased to the pinion by L.gears), teeth over L.sector_deg + tooth-less ears whose radial faces are the stops
    _, g = L.gears()
    a0, a1 = L.sector_deg(p)
    sec = Pos(c[0], c[1], L.SECTOR_Z0) * g & _wedge(c, a0, a1, 40, L.SECTOR_Z0 - 1, L.SECTOR_Z0 + L.GEAR_W + 1)
    r_ear = 18.4              # inside the root circle (18.5): the pinion's tip circle passes 19 from the pin, so the ears never touch it
    for lo, hi in ((a0 - EAR, a0), (a1, a1 + EAR)):
        sec += _cyl(c, r_ear, L.SECTOR_Z0, L.SECTOR_Z0 + L.GEAR_W) & _wedge(c, lo, hi, 40, L.SECTOR_Z0 - 1, L.SECTOR_Z0 + L.GEAR_W + 1)
    body += ctx.add(sec, why="21 T sector (module 2) on the boss; servo torque into the panel. The tooth-less ears' radial end faces "
                    "are the stop faces (spread / folded) the pod's posts meet", kind="gear")

    # spar sockets: blind teardrop bores from spar_y0 out through the outer face
    for which, od in (("main", p.main_od), ("rear", p.rear_od)):
        a, b = L.tube_line(p, which, 1)
        u = [(bb - aa) / (b[1] - a[1]) for aa, bb in zip(a, b)]

        def at(y):
            return tuple(aa + uu * (y - a[1]) for aa, uu in zip(a, u))
        r = (od + 0.2) / 2
        body -= ctx.cut(teardrop_channel([at(p.spar_y0 - 0.5 + r), at(p.hub_y1 + 1.0 - r)], od + 0.2),
                        why=f"{which} spar socket, OD + 0.2, epoxied, {p.hub_y1 - p.spar_y0:.0f} mm engagement", kind="socket")
    # aileron lead: outer face -> across the box -> straight up out of the hub top beside the boss (under the cap)
    body -= ctx.cut(teardrop_channel(_lead_pts(p), LEAD_D), why="aileron servo lead from the wing joint to the hub top, where its plug sits in the cap", kind="wire channel")

    # the two 625 bearings: pressed into the boss ends; the pin bore between them is loose (1 mm per side)
    dep = iface.bearing_dims(L.BEARING)["B"]
    span = L.BOSS_Z1 - L.BOSS_Z0
    body -= ctx.cut(iface.bearing_seat(ctx, L.BEARING, L.pin_loc(p, 1, L.BOSS_Z1), fit="press", depth=dep, through=span - 2 * dep + 1.0),
                    why="top bearing seat (press) + pin bore through the boss", kind="bearing seat")
    body -= ctx.cut(iface.bearing_seat(ctx, L.BEARING, Location((c[0], c[1], L.BOSS_Z0), (180, 0, 0)), fit="press", depth=dep),
                    why="bottom bearing seat (press): 28 mm from the top one", kind="bearing seat")
    return body


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    body = right_body(ctx)
    if s < 0:
        body = mirror(body, Plane.XZ)

    def keep(at):
        what = _in_channel(p, (at[0], s * at[1], at[2]))
        if what:
            return f"teardrop roof of the {what}: printed without support, the {what.split()[0]} part lies in it"
        if math.hypot(at[0] - p.pivot_x, abs(at[1]) - p.pivot_y) < L.BOSS_R + 0.5 and abs(at[2] - L.BOSS_Z1) < 0.1:
            return "bearing seat edge at the boss top: the 625's square outer race sits in it"
        return None
    body, left = features.fillet_inside(ctx, body, 2.0, keep=keep)
    ctx.rigid("pivot", L.pivot_axis(p, s).location)
    ctx.rigid("wing", Location())
    for w in ("main", "rear"):
        ctx.rigid(w, L.tube_loc(p, w, s))
    ctx.rigid("bear_top", L.pin_loc(p, s, L.BOSS_Z1 - 5.0))
    ctx.rigid("bear_bot", L.pin_loc(p, s, L.BOSS_Z0))
    return ctx.finish(body)
