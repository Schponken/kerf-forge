"""Top hatch: the pod's top skin over the electronics bay, removable so the shelf electronics (GPS, FC, RX, ESC, VTX)
and the wing-root bolts are reached from above. It rests on the pod's side ledges; a tongue at its rear slides under
the pod's skin (notched round the VTX antenna's lead, so it goes on with the antenna fitted), and four M3 (a pair at
the front, a pair at mid-length) go down into heat-set inserts in the pod's ledge blocks. Two shallow ribs along its
underside stiffen the thin skin against the suction over the pod top. PLA, 2 walls; printed flat on its outer face
(smooth visible side on the bed, the ribs standing up).
"""
from build123d import *
from kerf import iface
from kerf.features import fillet_inside

import importlib.util, pathlib
_pspec = importlib.util.spec_from_file_location("wing_pod", pathlib.Path(__file__).with_name("pod.py"))
POD = importlib.util.module_from_spec(_pspec); _pspec.loader.exec_module(POD)

TONGUE_L = 8.0
TONGUE_T = 1.6
RIB_Y = 18.0          # inside the screw blocks (|y| 23-37) and over the ESC / FC stack's sides
RIB_W = 2.0           # >= 1.6 mm structural wall (ENGINEERING.md), ~5 perimeters' worth: solid
RIB_H = 3.0           # below the skin; the sleeves' tops (z ~14) stay > 2 mm under the rib (kerf check proves it)
ANT_CLEAR = 1.0       # tongue notch radius = antenna hole radius + this


def build(ctx):
    p = ctx.p
    skin = POD.hatch_solid(p)
    x0, x1 = POD.HATCH_X
    hw = POD.HATCH_HW - 6
    under = p.pod_top - POD.SKIN                    # the skin's underside (flat over |y| <= 34)
    # tongues: under the pod's skin past each end of the opening, 0.2 mm below the skin's inside (cavity top there)
    cav = POD.cavity(p)
    for xa, xb in ((x1 - 1.0, x1 + TONGUE_L),):
        slab = Pos(xa, 0, POD.HATCH_CUT_Z - 6) * Box(xb - xa, 2 * hw, 12, align=(Align.MIN, Align.CENTER, Align.MIN))
        band = (slab & cav) - Pos(0, 0, -TONGUE_T) * cav           # the top TONGUE_T mm of the bay's inside there
        skin = skin + ctx.add(Pos(0, 0, -0.2) * band, why="tongue under the pod skin: holds the hatch end down", kind="tongue")
    for xa in (x1 - 3.0,):        # root of the tongue, inside the opening, up against the hatch skin
        root = Pos(xa, 0, POD.HATCH_CUT_Z - 6) * Box(3.0, 2 * hw, 12, align=(Align.MIN, Align.CENTER, Align.MIN))
        skin = skin + ctx.add((root & cav) - Pos(0, 0, -(TONGUE_T + 0.2)) * cav, why="tongue root", kind="tongue")
    # the VTX antenna's lead stands up through the pod skin at ant_x: the tongue is notched round it (open to the rear)
    notch = Pos(p.ant_x, 0, under - 10) * Cylinder(3.5 + ANT_CLEAR, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)) \
        + Pos(p.ant_x, 0, under - 10) * Box(20, 2 * (3.5 + ANT_CLEAR), 20, align=(Align.MIN, Align.CENTER, Align.MIN))
    skin = skin - ctx.cut(notch & Pos(x1, 0, 0) * Box(50, 100, 200, align=(Align.MIN, Align.CENTER, Align.CENTER)),
                          why="antenna lead passes the tongue: the hatch fits with the antenna installed", kind="notch")
    # stiffening ribs along x under the skin: the panel spans ~130 mm between screw pairs under ~1 kPa suction
    for s in (-1, 1):
        rib = Pos(x0 + 4.0, s * RIB_Y, under - RIB_H) * Box(x1 - 7.0 - (x0 + 4.0), RIB_W, RIB_H + 0.5,
                                                            align=(Align.MIN, Align.CENTER, Align.MIN))
        skin = skin + ctx.add(rib, why="longitudinal rib: bending stiffness of the 1.7 mm skin (no flutter)", kind="rib")
    # four M3 down through the skin into inserts in the pod's ledge blocks (front pair + mid-length pair)
    top = Location(Plane(origin=(0, 0, p.pod_top), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))
    skin = skin - iface.bolt_pattern(ctx, "hatch", "M3", POD.hatch_bolts(p), top, kind="clearance", depth=POD.SKIN + 0.01,
                                     teardrop="auto")
    skin, failed = fillet_inside(ctx, skin, r=1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    ctx.rigid("base", Location())
    return ctx.finish(skin)
