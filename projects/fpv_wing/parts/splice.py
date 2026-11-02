"""Splice plate (splice_l / splice_r): joins the outer wing segment to the inner one so the outer segment can be
unbolted and replaced after a crash. A 2.5 mm PETG plate under the bottom skin across the split, between the spars,
its top shaped to the skin; one M3 up into a heat-set insert in each segment (100 % infill modifier round the inserts).
The spar tubes carry the bending; the plate only keeps the outer segment from sliding off its tubes. Printed flat on
its bottom face.
"""
import math

import numpy as np
from build123d import *
from kerf import aero, iface

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

T = 3.5


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    holes = L.splice_holes(p, s)
    zb = min(h[2] for h in holes) - T
    zt = max(h[2] for h in holes) + 2.0
    yc = s * p.seg_split_y
    pf = L.planform(p)
    plate = Pos(L.SPLICE_X, yc, zb) * Box(30, 50, zt - zb, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for ya, yb in ((p.pod_hw, p.seg_split_y), (p.seg_split_y, p.semi)):   # the two segments' own lofts: exact contact
        y0, y1 = sorted((s * ya, s * yb))
        plate = plate - aero.wing_solid(pf, y0, y1)                # why: top face follows the bottom skin
    plate = aero.largest(plate)
    # edges first, holes last: a fillet / chamfer taken from an earlier shape's edges rebuilds that shape (it once
    # brought back the uncut blank and the plates shipped with no holes)
    plate = plate.fillet(2.0, plate.edges().filter_by(Axis.Z))     # why: round plan-view corners (no snag on landing)
    # why: a ramp all round the belly face, so a belly landing slides over the plate instead of catching its square step
    plate = plate.chamfer(1.5, None, plate.faces().sort_by(Axis.Z)[0].outer_wire().edges())
    for (x, y, zl) in holes:
        loc = Location(Plane(origin=(x, y, zb), x_dir=(1, 0, 0), z_dir=(0, 0, -1)))
        # the top follows the sloped skin, so the plate is thinnest on the ring's low side: that is the clamped grip
        grip = min(L.skin_z(p, x + 3.0 * math.cos(a), y + 3.0 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 24)) - zb
        plate = plate - iface.bolt_pattern(ctx, f"splice_{'l' if s < 0 else 'r'}", "M3", [(0, 0)], loc, kind="clearance",
                                           depth=grip)
        # why: the rest of the hole, up through the sliver of plate on the high side to the skin
        plate = plate - Pos(x, y, zb + grip - 0.01) * Cylinder(iface.screw_spec("M3", "PETG")["clearance"] / 2, zl - zb - grip + 0.03,
                                                             align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("base", Location())
    return ctx.finish(plate)
