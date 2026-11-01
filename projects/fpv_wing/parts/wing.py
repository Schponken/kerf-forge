"""One wing segment: wing_l1 / wing_r1 (inner, pod side to the split) and wing_l2 / wing_r2 (outer, split to tip).

Thin-wall print (1 wall, 3 % infill, PLA) standing on its inner end: span along the build plate's Z, so the airfoil
is the layer outline and the surfaces print without supports. The segment is a sleeve on the spar tubes: the main
tube (28 % chord, the bending spar) and the rear tube (60 % chord, holds the twist and lines the segments up) run
through both segments into the pod; the outer segment is glued to the inner one and the tube ends glued in it.
The inner segment is bolted to the pod side wall by two M3 into heat-set inserts in its root face (print them with a
100 % infill modifier around the inserts, see the maker notes). The elevon's slot (bottom hinge, top V gap) is cut
here from the same planform the elevon is cut from, so they match. The inner segment carries the elevon servo in a
pocket open to the bottom surface; the outer one has the fin's slot in its tip.
"""
from build123d import *
import numpy as np
from kerf import aero, iface

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def side_of(pid):
    return -1 if "_l" in pid else 1


def build(ctx):
    p = ctx.p
    s = side_of(ctx.id)
    inner = ctx.id.endswith("1")
    pf = L.planform(p)
    ya, yb = (p.pod_hw, p.seg_split_y) if inner else (p.seg_split_y, p.semi)
    y0, y1 = (ya, yb) if s > 0 else (-yb, -ya)
    body = aero.wing_solid(pf, y0, y1)
    # spar tubes: a slip fit (tube OD + 0.3) so the segment slides on and is glued
    for which, od in (("main", p.main_od), ("rear", p.rear_od)):
        a, b = L.tube_line(p, which, s)
        if abs(b[1]) > min(abs(y0), abs(y1)):
            body = body - ctx.cut(aero.cylinder_between(a, b, od + 0.3, extend=2.0), why=f"{which} spar tube, slip fit", kind="spar bore")
    # elevon slot: the same cut the elevon part makes, over the elevon's span (only where this segment overlaps it)
    e0, e1 = (p.elevon_y0, p.elevon_y1) if s > 0 else (-p.elevon_y1, -p.elevon_y0)
    if max(abs(y0), abs(y1)) > p.elevon_y0 and min(abs(y0), abs(y1)) < p.elevon_y1:
        body, _, (ha, hb) = aero.elevon_split(pf, body, e0, e1, p.hinge_frac, gap_deg=p.elevon_gap_deg)
        body = aero.largest(body)
        if not inner:      # the elevon turns about its hinge line, which this outer segment carries
            d = tuple((hb - ha) / np.linalg.norm(hb - ha))
            ctx.revolute("elevon", Axis(tuple(ha), d), range=(-p.elevon_throw, p.elevon_throw))
    if inner:
        root_y = s * p.pod_hw
        # two M3 heat-set inserts in the root face, screwed from inside the pod through its side wall
        loc = Location(Plane(origin=(0, root_y, 0), x_dir=(1, 0, 0), z_dir=(0, -s, 0)))
        # plane: x = world X, z = towards the pod (-s Y), so y = z x x = s * world Z
        local = [(p.root_bolt_x1, s * p.root_bolt_z1), (p.root_bolt_x2, s * p.root_bolt_z2)]
        body = body - iface.bolt_pattern(ctx, f"wing_root_{'l' if s < 0 else 'r'}", "M3", local, loc, kind="heatset", depth=40)
        ctx.rigid("root", Location())
    else:
        _f = importlib.util.spec_from_file_location("wing_fin", pathlib.Path(__file__).with_name("fin.py"))
        F = importlib.util.module_from_spec(_f); _f.loader.exec_module(F)
        _, slot = F.fin_geometry(p, s)
        body = body - ctx.cut(slot, why="the fin's tab is glued in here", kind="fin slot")
        ctx.rigid("joint", Location())
        ctx.rigid("tip", Location())
    return ctx.finish(body)
