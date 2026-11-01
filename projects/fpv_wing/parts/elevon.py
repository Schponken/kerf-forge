"""Elevon (elevon_l / elevon_r): the wing's aft strip from elevon_y0 to elevon_y1, behind the hinge line at
hinge_frac of the local chord. Cut with kerf.aero.elevon_split from the same planform as the wing segments, so the
slot and the surface match: bottom hinge line (a strip of hinge tape or 0.5 mm TPU along the bottom), a V gap on top
for up-throw, ends square to the hinge with 1 mm to the wing. Prints standing on its inner end (square to the hinge),
so the airfoil is the layer outline. The control horn sits on the bottom surface over the servo arm.
"""
from build123d import *
import numpy as np
from kerf import aero
from kerf.features import fillet_inside

HORN_L = 10.0
HORN_T = 2.4

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    pf = L.planform(p)
    ya, yb = p.elevon_y0 - 5, p.elevon_y1 + 5
    y0, y1 = (ya, yb) if s > 0 else (-yb, -ya)
    e0, e1 = (p.elevon_y0, p.elevon_y1) if s > 0 else (-p.elevon_y1, -p.elevon_y0)
    _, surf, (ha, hb) = aero.elevon_split(pf, aero.wing_solid(pf, y0, y1, stations=2), e0, e1, p.hinge_frac,
                                          gap_deg=p.elevon_gap_deg)
    surf = aero.largest(surf)
    # control horn under the surface, in line with the servo arm: starts just behind the hinge line (anything ahead of
    # it would swing up into the wing on down-throw); the pushrod Z-bend goes through the hole 9 mm under the hinge
    u = (hb - ha) / np.linalg.norm(hb - ha)
    hy = s * p.horn_y
    t = (hy - ha[1]) / u[1]
    h = ha + t * u                                       # hinge-line point at the horn's station
    horn = Pos(h[0] + 0.5, hy, h[2] - 12) * Box(HORN_L, HORN_T, 14, align=(Align.MIN, Align.CENTER, Align.MIN))
    surf = surf + ctx.add(horn, why="control horn (pushrod from the servo arm)", kind="horn")
    # why: pushrod Z-bend hole, 1.6 mm for 1.2 mm music wire
    surf = surf - Pos(h[0] + 3.5, hy, h[2] - 9) * Rot(90, 0, 0) * Cylinder(0.8, HORN_T + 2)
    def keep(at):
        if abs(abs(at[1]) - p.horn_y) < HORN_T and abs(at[0] - h[0]) < 2.0:
            return "the horn's front face meets the hinge bevel: a fillet there would reach ahead of the hinge line and hit the wing on down-throw"
        return None
    surf, failed = fillet_inside(ctx, surf, r=1.0, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    ctx.rigid("hinge", Axis(tuple(ha), tuple(u)).location)
    return ctx.finish(surf)
