"""Elevon control horn (horn_l / horn_r): a 2.4 mm PETG plate glued into the slot under the inner elevon half, in line
with the servo arm. Its tab goes up into the slot; three 1.3 mm holes (a snug fit on 1.2 mm music wire, little free
play) 9, 12 and 15 mm under the hinge line: 12 mm with an 8 mm servo arm gives 1.5 : 1 leverage (DESIGN.md). It starts
0.5 mm behind the hinge line, so nothing of it swings up into the wing on down-throw. Printed flat.
"""
from build123d import *
import numpy as np

import importlib.util, pathlib
_espec = importlib.util.spec_from_file_location("wing_elevon", pathlib.Path(__file__).with_name("elevon.py"))
E = importlib.util.module_from_spec(_espec); _espec.loader.exec_module(E)

T = 2.4
HOLES = (9.0, 12.0, 15.0)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    _, ha, hb = E.surfaces(p, s)
    h, _ = E.hinge_point(ha, hb, s * p.horn_y)
    lx, wy, dz = E.HORN_SLOT
    x0, y = h[0] + 1.5, s * p.horn_y
    body = Pos(x0, y, h[2] - 19) * Box(lx, T, 18.3, align=(Align.MIN, Align.CENTER, Align.MIN))          # below the surface
    body += Pos(x0, y, h[2] - 1.0) * Box(lx, T, dz + 0.8, align=(Align.MIN, Align.CENTER, Align.MIN))    # the tab in the slot
    for d in HOLES:
        # why: pushrod Z-bend holes at three leverage choices
        body -= Pos(x0 + 3.0, y, h[2] - d) * Rot(90, 0, 0) * Cylinder(0.65, T + 2)
    body = fillet(body.edges().filter_by(Axis.Y).group_by(Axis.Z)[0], 1.0)      # why: round the bottom corners (handling, no snag)
    ctx.rigid("base", Location())
    return ctx.finish(body)
