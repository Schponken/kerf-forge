"""Ailerons ail_r / ail_l: cut with kerf.aero.elevon_split from the outer wing segment's own surface (wing.outer_solid,
same planform and rounded tip), so slot and surface match: bottom hinge line at ail_hinge_frac (clear tape along the
bottom), a V gap of ail_gap_deg on top (more than the up-throw ail_throw, so the surface swings clear; down-throw opens
the gap), 0.6 mm at the hinge, ends 1 mm from the slot ends. Adapted from projects/fpv_wing/parts/elevon.py.

Prints standing on its inner end (print_rot [+-90, 0, 0]): the inner end is trimmed square to Y (the hinge is swept
~2.4 deg, so the slot's end plane is not; the aileron loses a sliver at its trailing edge and the end gap grows from
1 mm at the hinge to ~2.7 mm at the TE), and the control horn is a 3 mm plate on that end, flat on the bed with it:
no overhang, layers in the horn's own plane (full XY strength), and it gives the tall thin part a real first layer.
Horn hole HORN_R below the hinge line (equal throw both ways) for the 1.2 mm Z-bend pushrod, axis spanwise = vertical
as printed, so it prints round.
"""
from build123d import *
import numpy as np
from kerf import aero
from kerf.features import safe_fillet

import importlib.util, pathlib
_here = pathlib.Path(__file__)
_spec = importlib.util.spec_from_file_location("hw_layout", _here.with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_wspec = importlib.util.spec_from_file_location("dfw_wing", _here.with_name("wing.py"))
W = importlib.util.module_from_spec(_wspec); _wspec.loader.exec_module(W)

ROD_HOLE = 1.2 + 0.3          # music wire pushrod (wire:music_1.2) + free running clearance (ENGINEERING s6)
HORN_ROOT = (1.2, 15.0)       # horn root along the aileron's bottom, mm aft of the hinge line
HORN_TIP_W = 5.6              # horn width round the hole


def build(ctx):
    p = ctx.p
    s = W.side_of(ctx.id)
    pf = L.planform(p)
    e0, e1 = (p.ail_y0, p.ail_y1) if s > 0 else (-p.ail_y1, -p.ail_y0)
    _, surf, (ha, hb) = aero.elevon_split(pf, W.outer_solid(p, s), e0, e1, p.ail_hinge_frac, gap_deg=p.ail_gap_deg,
                                          end_gap=W.END_GAP)
    surf = aero.largest(surf)
    d = (hb - ha) / np.linalg.norm(hb - ha)
    u = (hb - ha) / (hb[1] - ha[1])                       # hinge line per mm of y
    y_end = p.ail_y0 + W.END_GAP * abs(d[1])                # |y| of the hinge point on the inner end
    # inner end square to Y (flat on the bed as printed)
    keep_out = Pos(0, s * (y_end - 500.0), 0) * Box(2000, 1000, 2000)
    surf = aero.largest(surf - ctx.cut(keep_out, why="inner end square to Y: flat on the bed as printed", kind="trim"))

    # control horn: plate in the XZ plane on the inner end, hanging under the hinge line
    h = ha + u * (s * y_end - ha[1])                       # hinge point at the inner end
    aft = np.array([1.0, 0, 0]) - d * d[0]
    aft /= np.linalg.norm(aft)
    up = np.cross(d, aft)
    up = up if up[2] > 0 else -up
    r0, r1 = HORN_ROOT
    loc2d = [(r0, 1.0), (r1, 1.0), (HORN_TIP_W / 2, -(W.HORN_R + 3.0)), (-HORN_TIP_W / 2, -(W.HORN_R + 3.0))]
    pts = [tuple(map(float, h + aft * a + up * b)) for a, b in loc2d]
    face = Face(Wire.make_polygon([(x, s * y_end, z) for x, _, z in pts], close=True))
    horn = extrude(face, amount=W.HORN_T, dir=(0, s, 0))
    hole_c = h - up * W.HORN_R
    hole = Pos(float(hole_c[0]), s * (y_end + W.HORN_T / 2), float(hole_c[2])) * Rot(90, 0, 0) * Cylinder(ROD_HOLE / 2, W.HORN_T + 2)
    surf = surf + ctx.add(horn, why="control horn on the inner end, printed flat on the bed with it", kind="horn")
    surf = surf - ctx.cut(hole, why="1.2 mm Z-bend pushrod, free fit, hole HORN_R under the hinge line", kind="pushrod hole")
    # horn root fillet (load path): the horn's two plate faces meet the curved bottom skin
    root = [e for e in surf.edges() if abs(abs(e.center().Y) - (y_end + W.HORN_T)) < 0.05
            and e.center().Z > hole_c[2] + W.HORN_R - 1.5 and abs(e.center().Z - h[2]) < 2.5]
    surf, failed = safe_fillet(surf, [(root, 1.0)])
    ctx.notes += [f"horn root fillet not applied: {f}" for f in failed]
    ctx.rigid("hinge", Axis(tuple(ha), tuple(d)).location)
    return ctx.finish(aero.largest(surf))
