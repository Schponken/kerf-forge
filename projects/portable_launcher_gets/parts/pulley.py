"""Nose pulley: six latex-strand grooves on two 608 bearings (frame: centre, +Z = axle axis = rail +Y).

Load path (DESIGN.md "Nose pulley"): each strand presses its groove floor with 2 x T/6 radially; the rim (floor ring r 41..44)
carries the ring compression, six spokes carry the net 948 N to the hub tube, the hub's two 7 mm seats hand it to the
608 outer races and so to the 8 mm axle. Grooves are 8.4 wide with vertical walls (printed axle-up, flat: no ceilings),
bottom corners chamfered 45 deg, floor r = R_P - tubing radius so the strand centre line is at R_P.
"""
import math

from build123d import *
from kerf import catalog, features, iface

BRG = "bearings.608"
W = 69.0                 # full width, |z| <= 34.5: 1 mm either side to the nose block's axle cheeks (inner face |y| 35.5)
R_FLANGE = 54.0          # outer flange radius (contract)
G_W = 8.4                # groove width: tubing OD 7.94 + 0.46 slack
G_CH = 1.2               # 45 deg chamfer on the groove floor corners
R_IN = 41.0              # rim inner radius: 3 mm of floor under the groove (groove floor 44.03)
HUB_R = 15.0             # hub tube outer radius: 608 seat r 11.0 + 4 mm wall
N_SPOKE = 6
SPOKE_T = 6.0            # spoke thickness (tangential), full width along the axle


def _rev(pts):
    """Revolve a polygon given in (r, z) about the Z axis."""
    w = Wire.make_polygon([Vector(r, 0, z) for r, z in pts], close=True)
    return Solid.revolve(Face(w), 360, Axis.Z)


def build(ctx):
    p = ctx.p
    tube_r = float(catalog.get("motion.latex_tubing")["od"]) / 2
    r_floor = p.R_P - tube_r
    brg = iface.bearing_dims(BRG)
    h = W / 2

    body = ctx.add(Cylinder(R_FLANGE, W) - Cylinder(R_IN, W + 2),
                   why="rim: ridges guide the six strands, the 3 mm floor ring under the grooves carries the strand pressure as hoop compression", kind="rim")
    for z in p.STRAND_Y:   # why: one groove per strand at the contract z
        body -= ctx.cut(_rev([(R_FLANGE + 2, z - G_W / 2), (r_floor + G_CH, z - G_W / 2), (r_floor, z - G_W / 2 + G_CH),
                              (r_floor, z + G_W / 2 - G_CH), (r_floor + G_CH, z + G_W / 2), (R_FLANGE + 2, z + G_W / 2)]),
                        why=f"groove for the strand at z={z:+.2f}: vertical walls, 45 deg floor chamfers (prints without ceilings)", kind="groove")
    body += ctx.add(Cylinder(HUB_R, W), why="hub tube round the two 608 seats", kind="hub")
    for k in range(N_SPOKE):   # why: spokes take the 948 N from the rim to the bearings (full width, so the load stays in-layer)
        a = 360.0 * k / N_SPOKE
        body += ctx.add(Rot(0, 0, a) * Pos((HUB_R + R_IN) / 2, 0, 0) * Box(R_IN - HUB_R + 2, SPOKE_T, W),
                        why="spoke: radial strut from the bearings' hub to the rim, load in-layer when printed flat", kind="spoke")
    # 608 seats at both ends, a shoulder between that supports only the outer races (bore r 8 clears the inner races)
    body -= ctx.cut(iface.bearing_seat(ctx, BRG, Location((0, 0, -h), (180, 0, 0)), "press", through=W, shaft_clear=8 - brg["d"] / 2),
                    why="608 seat 1 (press) + clear through-bore so only the outer race touches the shoulder", kind="bearing seat")
    body -= ctx.cut(iface.bearing_seat(ctx, BRG, Location((0, 0, h)), "press"), why="608 seat 2 (press)", kind="bearing seat")

    body, left = features.fillet_inside(ctx, body, 1.0)
    ctx.rigid("hub", Location((0, 0, 0)))
    ctx.rigid("brg_1", Location((0, 0, -h)))
    ctx.rigid("brg_2", Location((0, 0, h - brg["B"])))
    return ctx.finish(body)
