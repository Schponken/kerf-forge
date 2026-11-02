"""Top hatch: the pod's top skin over the electronics bay, removable so the shelf electronics (GPS, FC, RX, ESC, VTX)
and the wing-root bolts are reached from above. It rests on the pod's side ledges; a tongue at its rear slides under
the pod's skin, and two M3 at its front go down into heat-set inserts in the pod's ledge blocks. PLA, 2 walls; printed standing on its side edge
(the skin vertical: no overhangs).
"""
from build123d import *
from kerf import iface

import importlib.util, pathlib
_pspec = importlib.util.spec_from_file_location("wing_pod", pathlib.Path(__file__).with_name("pod.py"))
POD = importlib.util.module_from_spec(_pspec); _pspec.loader.exec_module(POD)

TONGUE_L = 8.0
TONGUE_T = 1.6


def build(ctx):
    p = ctx.p
    skin = POD.hatch_solid(p)
    x0, x1 = POD.HATCH_X
    hw = POD.HATCH_HW - 6
    # tongues: under the pod's skin past each end of the opening, 0.2 mm below the skin's inside (cavity top there)
    cav = POD.cavity(p)
    for xa, xb in ((x1 - 1.0, x1 + TONGUE_L),):
        slab = Pos(xa, 0, POD.HATCH_CUT_Z - 6) * Box(xb - xa, 2 * hw, 12, align=(Align.MIN, Align.CENTER, Align.MIN))
        band = (slab & cav) - Pos(0, 0, -TONGUE_T) * cav           # the top TONGUE_T mm of the bay's inside there
        skin = skin + ctx.add(Pos(0, 0, -0.2) * band, why="tongue under the pod skin: holds the hatch end down", kind="tongue")
    for xa in (x1 - 3.0,):        # root of the tongue, inside the opening, up against the hatch skin
        root = Pos(xa, 0, POD.HATCH_CUT_Z - 6) * Box(3.0, 2 * hw, 12, align=(Align.MIN, Align.CENTER, Align.MIN))
        skin = skin + ctx.add((root & cav) - Pos(0, 0, -(TONGUE_T + 0.2)) * cav, why="tongue root", kind="tongue")
    # front: two M3 down through the skin into inserts in the pod's ledge blocks
    top = Location(Plane(origin=(0, 0, p.pod_top), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))
    skin = skin - iface.bolt_pattern(ctx, "hatch", "M3", POD.hatch_bolts(p), top, kind="clearance", depth=POD.SKIN + 0.01)
    ctx.rigid("base", Location())
    return ctx.finish(skin)
