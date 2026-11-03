"""Boom clamp: plate over the boom in the fuselage's socket seat. ONE M3 from above passes the plate, a round rib that rests on the
boom, the boom's 3.2 mm cross hole (drilled 25 mm from its front end) and screws into the heat-set insert under the bore: the
boom can neither slide nor roll, and the tail incidence returns after a field swap. The plate's rear tongue slides under the
fuselage's lip (tilt it in, press the front down, screw). PETG, 4 walls, printed flat on its back.
"""
from build123d import *
import importlib.util, pathlib
from kerf import iface
from kerf.features import fillet_inside

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_fspec = importlib.util.spec_from_file_location("hw_fuselage", pathlib.Path(__file__).with_name("fuselage.py"))
F = importlib.util.module_from_spec(_fspec); _fspec.loader.exec_module(F)

PLATE_T, GAP, W = 3.0, 0.15, 16.0


def build(ctx):
    p = ctx.p
    bz, br = p.boom_z, p.boom_od / 2
    z0 = F.SEAT_Z + GAP                                   # plate underside
    xa, xb = F.SEAT_X[0] + 0.5, F.SEAT_X[1] - 2.0
    plate = Pos((xa + xb) / 2, 0, z0) * extrude(RectangleRounded(xb - xa, W, 4.0), PLATE_T)
    body = ctx.add(plate, why="clamp plate on the seat: carries the screw tension to the rib and the tongue", kind="plate")
    bore_r = (p.boom_od + 0.2) / 2
    rib = Pos(F.CLAMP_X, 0, bz + br - 2.0) * Cylinder(4.0, z0 - (bz + br - 2.0) + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    rib = rib & (Pos(F.CLAMP_X, 0, 0) * Box(10, 6.8, 100))
    rib -= Pos(F.CLAMP_X, 0, bz) * Rot(0, 90, 0) * Cylinder(br, 60.0)
    body += ctx.add(rib, why="round rib down the seat pocket: saddles on the boom and carries the screw", kind="rib")
    tz = F.SEAT_Z - 0.2
    tx1 = F.SEAT_X[0] + 2.5
    tongue = Pos((F.TONGUE_X0 + tx1) / 2, 0, tz - 2.0) * Box(tx1 - F.TONGUE_X0, 13.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    riser = Pos(tx1 - 1.0, 0, tz - 2.0) * Box(2.0, 13.0, z0 + PLATE_T - (tz - 2.0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += ctx.add(tongue + riser, why="tongue under the fuselage lip: holds the front end down", kind="tongue")
    stiff = Pos((xa + F.CLAMP_X) / 2, 0, z0 + PLATE_T) * Box(F.CLAMP_X - xa - 6.0, 2.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += ctx.add(stiff, why="top rib stiffens the plate between the lip and the screw", kind="rib")
    # the hole runs on down to the insert under the bore (through the boom's cross hole), so the checker sees the whole stack
    body -= iface.bolt_pattern(ctx, "boom_clamp", "M3", [(F.CLAMP_X, 0)], Location((0, 0, z0 + PLATE_T)), kind="clearance",
                               depth=z0 + PLATE_T - (bz - bore_r))
    ctx.rigid("base", Location())
    body, left = fillet_inside(ctx, body, 1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(body)
