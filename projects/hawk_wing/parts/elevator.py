"""Elevator (PLA, 1 wall, 5 %): one piece across the full tail span, cut from the same solid as the stabiliser
(hstab.surfaces), turning about the straight bottom hinge line (tape hinge along the bottom). Its front face is
square to the chord, 0.9 mm behind the hinge line; the V gap is all on the stabiliser's side.

Control horn: a 2.4 mm plate on the top skin in line with the elevator servo's arm (tail_mount dims arm_y), hole
for the 1.2 mm music-wire pushrod's Z-bend 13 mm above the hinge line. Print: standing on its front face
(print_rot [0, -90, 0]); the horn then sticks out sideways, so its front edge is raked 45 deg (no flat overhang).
"""
from build123d import *
import numpy as np

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_hstab", pathlib.Path(__file__).with_name("hstab.py"))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)
_m = importlib.util.spec_from_file_location("dfw_tail_mount", pathlib.Path(__file__).with_name("tail_mount.py"))
M = importlib.util.module_from_spec(_m); _m.loader.exec_module(M)

HORN_T = 2.4          # horn plate thickness
PUSHROD_HOLE = 1.3    # snug on the 1.2 mm music wire (DESIGN.md "short 1.2 mm pushrods"), as fpv_wing's horn
HOLE_UP, HOLE_TOP = 13.0, 15.0   # pushrod hole height above the hinge line, horn top


def build(ctx):
    p = ctx.p
    _, surf, a, b = H.surfaces(p)
    d = (b - a) / np.linalg.norm(b - a)
    xh, zh = float(a[0]), float(a[2])
    y = M.dims(p)["arm_y"]
    z_front = 6.0           # height above the hinge where the horn's raked front edge leaves the top skin
    x_front = H.HINGE_GAP + 0.6
    pts = [(x_front, 1.0), (x_front, z_front), (x_front + HOLE_TOP - z_front, HOLE_TOP),
           (x_front + HOLE_TOP - z_front + 4.0, HOLE_TOP), (x_front + 16.0, 3.0), (x_front + 16.0, 2.0)]
    horn = Plane.XZ * Polygon(*[(xh + u, zh + v) for u, v in pts], align=None)
    horn = Pos(0, y, 0) * extrude(horn, amount=HORN_T / 2, both=True)
    hx = xh + x_front + (HOLE_UP - z_front) + 2.0       # 2 mm of plate in front of the hole
    horn -= Pos(hx, y, zh + HOLE_UP) * Rot(90, 0, 0) * Cylinder(PUSHROD_HOLE / 2, HORN_T + 2)    # why: pushrod Z-bend hole
    surf += ctx.add(horn, why="control horn in line with the elevator servo arm; front edge 45 deg so it prints standing", kind="horn")
    ctx.bom_item("1.2 mm music wire pushrod with Z-bend", 1, spec="about 50 mm: elevator servo arm to the elevator horn",
                 price_key="wire:music_1.2")
    ctx.rigid("hinge", Axis(tuple(a), tuple(d)).location)
    return ctx.finish(surf)
