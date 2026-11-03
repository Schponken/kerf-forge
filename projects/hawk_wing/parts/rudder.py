"""Rudder (PLA, 1 wall, 5 %): the fin's aft part from fin.surfaces, turning about the hinge line on the fin's right
side (tape hinge); its bottom is 1.5 mm above the tail mount's top (at full throw its left bottom edge drops ~0.8 mm).

Control horn on the left side (pushrod from the rudder servo arm, 4 mm further out, runs in at a slight angle): a horizontal plate whose underside rises 50 deg
outwards (it prints standing on the rudder's bottom, print_rot [0, 0, 0], with no flat overhang), vertical hole for
the 1.2 mm music-wire pushrod's Z-bend 14.6 mm out from the hinge line.
"""
from build123d import *
import numpy as np

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_fin", pathlib.Path(__file__).with_name("fin.py"))
F = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(F)
_m = importlib.util.spec_from_file_location("dfw_tail_mount", pathlib.Path(__file__).with_name("tail_mount.py"))
M = importlib.util.module_from_spec(_m); _m.loader.exec_module(M)

BOTTOM_GAP = 1.5      # above the tail mount's top: the left bottom edge drops ~0.8 mm at full throw
PUSHROD_HOLE = 1.3    # snug on the 1.2 mm music wire (DESIGN.md "short 1.2 mm pushrods"), as fpv_wing's horn
LEVER = 14.6          # hole out from the hinge line
HORN_UP = 20.0        # horn top above the rudder's bottom (its underside stays above the bottom face)
HORN_X = (4.0, 12.0)  # horn's chordwise extent behind the hinge line (clear of the fin's V face at full throw)
SLOPE = 1.2           # underside rise per mm outwards (50 deg)


def build(ctx):
    p = ctx.p
    d = M.dims(p)
    _, rud, a, b = F.surfaces(p)
    z0 = d["top"] + BOTTOM_GAP
    rud = rud & F.above(z0)
    u = (b - a) / np.linalg.norm(b - a)
    zt = z0 + HORN_UP
    h = a + (zt - a[2]) / u[2] * u                         # hinge point at the horn's top height
    y_hole = h[1] - LEVER
    y_tip = y_hole - 1.6
    y_root = -1.0                                          # inside the rudder, just left of its centre plane
    sec = Plane.YZ * Polygon((y_root, zt), (y_tip, zt), (y_tip, zt - 3.0), (y_root, zt - 3.0 + SLOPE * (y_tip - y_root)), align=None)
    horn = Pos(h[0] + HORN_X[0], 0, 0) * extrude(sec, amount=HORN_X[1] - HORN_X[0])
    horn -= Pos(h[0] + HORN_X[0] + 2.0, y_hole, zt) * Cylinder(PUSHROD_HOLE / 2, 20)     # why: pushrod Z-bend hole
    rud += ctx.add(horn, why="control horn in line with the rudder servo arm; underside 50 deg so it prints standing", kind="horn")
    ctx.bom_item("1.2 mm music wire pushrod with Z-bend", 1, spec="about 40 mm: rudder servo arm to the rudder horn",
                 price_key="wire:music_1.2")
    ctx.rigid("hinge", Axis(tuple(a), tuple(u)).location)
    return ctx.finish(rud)
