"""Top hatch over the forward bay: the fuselage's flat top skin from x -150 to 40, |y| < 23, with a 0.2 mm gap all
round. Off, it opens the bay for the battery (in aft of the shelf, slid forward under it), the XT60, the strap window
and the shelf electronics. A tongue at its front slides under the nose skin; two M3 at its aft end go down into
heat-set inserts in fwd_fuse's beam (group `hatch`); its side edges rest on fwd_fuse's ledges. PLA, 2 walls, printed
upside down (the flat outer face on the bed).
"""
from build123d import *
from kerf import iface

import importlib.util, pathlib
_fspec = importlib.util.spec_from_file_location("dfw_fwd_fuse", pathlib.Path(__file__).with_name("fwd_fuse.py"))
F = importlib.util.module_from_spec(_fspec); _fspec.loader.exec_module(F)

GAP = 0.2
TONGUE_L = 8.0
TONGUE_T = 1.6


def build(ctx):
    p = ctx.p
    x0, x1 = F.HATCH_X
    hw = F.HATCH_HW - GAP
    skin = F.hatch_solid(p) & Pos(x0 + GAP, 0, -100) * Box(x1 - x0 - 2 * GAP, 2 * hw, 200, align=(Align.MIN, Align.CENTER, Align.MIN))
    # front tongue: the top TONGUE_T mm of the bay just under the nose skin, 0.2 mm below it, plus a root inside the
    # opening that joins it to the hatch skin
    cav = F.cavity(p)
    th = 14.0
    slab = Pos(x0 - TONGUE_L, 0, F.HATCH_CUT_Z - 8) * Box(TONGUE_L + 3.0, 2 * th, 12, align=(Align.MIN, Align.CENTER, Align.MIN))
    band = (slab & cav) - Pos(0, 0, -TONGUE_T) * cav
    skin = skin + ctx.add(Pos(0, 0, -GAP) * band, why="tongue under the nose skin: holds the hatch's front down", kind="tongue")
    root = Pos(x0 + GAP, 0, F.HATCH_CUT_Z - 8) * Box(3.0, 2 * th, 12, align=(Align.MIN, Align.CENTER, Align.MIN))
    skin = skin + ctx.add((root & cav) - Pos(0, 0, -(TONGUE_T + GAP)) * cav, why="tongue root", kind="tongue")
    # aft: two M3 down through the skin into the beam's inserts
    top = Location(Plane(origin=(0, 0, p.fuse_top), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))
    skin = skin - iface.bolt_pattern(ctx, "hatch", "M3", F.hatch_bolts(p), top, kind="clearance", depth=F.SKIN + 0.01)
    ctx.rigid("base", Location())
    return ctx.finish(skin)
