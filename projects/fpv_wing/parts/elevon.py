"""Elevon halves: elevon_l / elevon_r (inner, on the inner wing segment, carries the hinge joint and the horn) and
elevon_lo / elevon_ro (outer, on the outer segment). Both are cut with kerf.aero.elevon_split from the same planform
as the wing segments, so slot and surface match: bottom hinge line (hinge tape along the bottom), a V gap on top for
up-throw, ends square to the hinge with 1 mm to the wing. The two halves meet on a plane square to the hinge where the
wing segments meet, and two 3 mm carbon rods (epoxied in the inner half, a reamed push fit in the outer half) make
them one surface with no free play, so the outer half still slides off with its bolt-on wing segment. The second rod
sits further aft than the first (10 mm vs 4 mm from the hinge, where the section is still thick enough for the bore
with ~0.9 mm wall), so any clearance left in the outer bores turns into half the angle a single rod near the hinge gave.

Each half prints standing on its outboard end (square to the hinge; 120 / 180 mm tall, so 1 wall + a brim). The
control horn is its own small PETG part glued into a slot under the inner half (parts/horn.py) - a horn printed on
the standing elevon would be a flat overhang.
"""
from build123d import *
import numpy as np
from kerf import aero
from kerf.features import fillet_inside

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

HORN_SLOT = (10.0, 2.5, 4.2)     # x length, y width (horn 2.4 thick + 0.1), depth into the surface from 1 mm under the hinge
JOINER_D = 3.0                    # catalog rods.cf_rod_3
JOINER_L = 50.0
JOINER_AFT = (4.0, 8.5)            # mm aft of the hinge (in plan) of the front / aft rod
OUTER_FIT = 0.0                   # outer-half bore printed at the rod size (prints ~0.1 under), reamed 3.0 mm: push fit


def surfaces(p, s):
    """(full elevon surface, hinge start, hinge end) for one side."""
    pf = L.planform(p)
    ya, yb = p.elevon_y0 - 5, p.elevon_y1 + 5
    y0, y1 = (ya, yb) if s > 0 else (-yb, -ya)
    e0, e1 = (p.elevon_y0, p.elevon_y1) if s > 0 else (-p.elevon_y1, -p.elevon_y0)
    _, surf, (ha, hb) = aero.elevon_split(pf, aero.wing_solid(pf, y0, y1, stations=2), e0, e1, p.hinge_frac,
                                          gap_deg=p.elevon_gap_deg)
    return aero.largest(surf), ha, hb


def hinge_point(ha, hb, y):
    u = (hb - ha) / np.linalg.norm(hb - ha)
    return ha + (y - ha[1]) / u[1] * u, u


def joiner_axis(p, s, ha, hb, surf, aft_mm):
    """(start, unit dir) of a carbon joiner rod: parallel to the hinge, aft_mm aft of it in plan, centred on the split,
    at the mid-thickness of the section there (the mean over the rod's two ends and middle, so the wall is even)."""
    c, u = hinge_point(ha, hb, s * p.seg_split_y)
    aft = np.cross(u, [0, 0, 1.0])
    aft = aft if aft[0] > 0 else -aft
    centre = c + aft / np.linalg.norm(aft) * aft_mm
    mids = []
    for t in (-JOINER_L / 2, 0.0, JOINER_L / 2):
        q = centre + u * t
        bb = (surf & (Pos(*q) * Box(0.3, 0.3, 80))).bounding_box()
        mids.append((bb.min.Z + bb.max.Z) / 2 - q[2])
    centre = centre + np.array([0, 0, float(np.mean(mids))])
    return centre - u * JOINER_L / 2, u


def build(ctx):
    p = ctx.p
    s = -1 if "_l" in ctx.id else 1
    outer_half = ctx.id.endswith("o")
    surf, ha, hb = surfaces(p, s)
    c, u = hinge_point(ha, hb, s * p.seg_split_y)
    keep_dir = u if (u[1] * s > 0) == outer_half else -u               # the side of the split this half keeps
    half = Location(Plane(origin=tuple(c), z_dir=tuple(keep_dir))) * Box(2000, 2000, 2000, align=(Align.CENTER, Align.CENTER, Align.MIN))
    full = surf
    surf = aero.largest(surf & half)
    rods = [joiner_axis(p, s, ha, hb, full, x) for x in JOINER_AFT]
    for i, (a, d) in enumerate(rods):
        bore = aero.cylinder_between(a, a + d * JOINER_L, JOINER_D + (0.1 if not outer_half else OUTER_FIT), extend=0.5)
        surf = surf - ctx.cut(bore, why=("carbon joiner rod: epoxied in the inner half" if not outer_half else
                                         "carbon joiner rod: reamed push fit in the outer half (no free play, removable)")
                              + (" - the aft rod keys the outer half at twice the lever arm" if i else ""),
                              kind="joiner bore")
    keep = None
    if not outer_half:
        h, _ = hinge_point(ha, hb, s * p.horn_y)
        lx, wy, dz = HORN_SLOT
        slot = Pos(h[0] + 1.5, s * p.horn_y, h[2] - 1.0) * Box(lx, wy, dz + 1.0, align=(Align.MIN, Align.CENTER, Align.MIN))
        surf = surf - ctx.cut(slot, why="slot the control horn's tab is glued into", kind="horn slot")
        ctx.rigid("horn", Location())
        for name, (a, d) in zip(("joiner", "joiner2"), rods):
            ctx.rigid(name, Location(Plane(origin=tuple(a), z_dir=tuple(d))))
        ctx.rigid("outer", Location(Plane(origin=tuple(c), z_dir=tuple(u))))

        def keep(at):
            if abs(abs(at[1]) - p.horn_y) < 4 and abs(at[0] - h[0]) < 14:
                return "the horn's square tab sits in this slot"
            return None
    else:
        ctx.rigid("inner", Location(Plane(origin=tuple(c), z_dir=tuple(u))))
    surf, failed = fillet_inside(ctx, surf, r=1.0, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c_}" for c_ in failed]
    ctx.rigid("hinge", Axis(tuple(ha), tuple(u)).location)
    return ctx.finish(surf)
