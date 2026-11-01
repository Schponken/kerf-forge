"""Elevon (elevon_l / elevon_r): the wing's aft strip from elevon_y0 to elevon_y1, behind the hinge line at
hinge_frac of the local chord. Cut with kerf.aero.elevon_split from the same planform as the wing segments, so the
slot and the surface match: bottom hinge line (a strip of hinge tape or 0.5 mm TPU along the bottom), a V gap on top
for up-throw, ends square to the hinge with 1 mm to the wing. Prints standing on its inner end (square to the hinge),
so the airfoil is the layer outline. The control horn sits on the bottom surface over the servo arm.
"""
from build123d import *
import numpy as np
from kerf import aero

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
    ctx.rigid("hinge", Axis(tuple(ha), tuple((hb - ha) / np.linalg.norm(hb - ha))).location)
    return ctx.finish(surf)
