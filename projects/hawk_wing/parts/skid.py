"""Wingtip skid skid_r / skid_l (break-first, glued): a flat-bottomed PETG shoe under the rounded tip of wing_x2, filling
the space between the tip's lower skin and a flat plane SKID_H below its lowest point, so on a wing-low landing the shoe
(the outermost, lowest point) touches the grass first, not the skin or the aileron (which ends 15 mm inboard). Plan
footprint = the tip's own outline pulled in FOOT_IN, a middle chord band, front/rear/inboard ends ramped up (grass
doesn't catch). Modelled in place (joint "base" = Location(), the wing's joint "skid" = Location()); the glue face is the
wing's lower surface cut from wing.outer_solid, so the two match by construction; nothing is cut from the wing.
Prints flat on the bed (print_rot 0): the flat sole is the first layer, the curved glue face is the last (no overhang).
Break-first: 2 walls, 15 % infill; it tears off or snaps before the wing skin does, and is reprinted in minutes.
"""
from build123d import *
import numpy as np
import importlib.util, pathlib

_here = pathlib.Path(__file__)
def _load(name, f):
    spec = importlib.util.spec_from_file_location(name, _here.with_name(f))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m
L = _load("hw_layout", "layout.py")
W = _load("hw_wing", "wing.py")

SKID_H = 3.0          # sole below the lowest point of the tip's lower skin
LEN_Y = 45.0          # spanwise length of the shoe from the tip inward (the tip proper is W.TIP_R 40)
FOOT_IN = 1.5         # footprint pulled in from the skin outline: the shoe never overhangs the wing
BAND = (0.30, 0.62)   # chord band at the mid of the shoe
RAMP = 1.8            # 45 deg chamfer at the front, rear and inboard ends (grass does not catch), leaves >= 1.2 of the 3 mm sole


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    pf = L.planform(p)
    raw = W.outer_solid(p, 1)                                   # right-hand frame; mirrored at the end for the left
    y_in = p.semi - LEN_Y
    y_t0 = p.semi - W.TIP_R
    ph = np.linspace(0.0, np.pi / 2, W.TIP_N)
    stations = [(y_in, 1.0), (y_t0, 1.0)] + [(y_t0 + W.TIP_R * np.sin(f), 1 - (1 - W.TIP_K) * (1 - np.cos(f))) for f in ph[1:]]
    xs = [(float((q := W.tip_section(pf, y, k))[:, 0].min()), float(q[:, 0].max()), y) for y, k in stations]
    # why: plan outline of the tip (leading / trailing edge per station) -> footprint, pulled in so the shoe sits inside it
    outline = [(a, y) for a, _, y in xs] + [(b, y) for _, b, y in xs][::-1]
    foot = offset(Face(Wire.make_polygon([(x, y) for x, y in outline], close=True)), -FOOT_IN)

    zlow = (raw & (Pos(0, (y_in + p.semi) / 2, 0) * Box(2000, LEN_Y, 200))).bounding_box().min.Z   # why: lowest skin point under the shoe
    zb = float(zlow) - SKID_H
    ym = p.semi - LEN_Y / 2
    xa, xb = (pf.x_le(ym) + pf.chord(ym) * f for f in BAND)
    h = 20.0
    # why: front / rear ramps (XZ profile) and inboard / outboard-free ramp (YZ profile): flat sole, no square toes
    prof_x = extrude(Plane.XZ * Polygon((xa, zb + RAMP), (xa + RAMP, zb), (xb - RAMP, zb), (xb, zb + RAMP), (xb, zb + h), (xa, zb + h),
                                        align=None), amount=-1000, both=True)
    prof_y = extrude(Plane.YZ * Polygon((y_in, zb + RAMP), (y_in + RAMP, zb), (p.semi + 5, zb), (p.semi + 5, zb + h), (y_in, zb + h),
                                        align=None), amount=1000, both=True)
    prism = extrude(Pos(0, 0, zb - 1) * foot, amount=h + 2, dir=(0, 0, 1))
    shoe = prof_x & prof_y & prism       # why: ramped solid inside the pulled-in footprint
    shoe = shoe - raw     # why: glue face = the wing's lower skin, nothing cut from the wing
    shoe = ctx.add(max(shoe.solids(), key=lambda q: q.volume), why="tip shoe: flat sole SKID_H below the lowest skin point, glued to the lower skin", kind="skid")
    if s < 0:
        shoe = shoe.mirror(Plane.XZ)
    ctx.rigid("base", Location())
    return ctx.finish(shoe)
