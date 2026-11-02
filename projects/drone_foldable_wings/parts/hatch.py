"""Top hatch over the forward bay: the fuselage's flat top skin from x -150 to 40, |y| < 23, with a 0.2 mm gap all
round. Off, it opens the bay for the battery (in aft of the shelf, slid forward under it), the XT60, the strap window
and the shelf electronics. A tongue at its front slides under the nose skin; two M3 at its aft end go down into
heat-set inserts in fwd_fuse's beam (group `hatch`); its side edges rest on fwd_fuse's ledges. PLA, 2 walls, printed
upside down (the flat outer face on the bed).
"""
from build123d import *
from kerf import iface
from kerf.features import fillet_inside

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
    # front tongue: a flat plate under the nose skin, which slopes down ahead of the opening: GAP below it at the
    # tongue's tip, more toward the root; a root block inside the opening joins it to the hatch skin
    th = 14.0
    z1 = F.inner(p, x0 - TONGUE_L)[2] - GAP
    tongue = Pos(x0 - TONGUE_L, 0, z1 - TONGUE_T) * Box(TONGUE_L + 3.0, 2 * th, TONGUE_T, align=(Align.MIN, Align.CENTER, Align.MIN))
    skin = skin + ctx.add(tongue, why="tongue under the nose skin: holds the hatch's front down", kind="tongue")
    zi = p.fuse_top - F.SKIN
    root = Pos(x0 + GAP, 0, z1 - TONGUE_T) * Box(3.0 - GAP, 2 * th, zi - z1 + TONGUE_T + 0.5, align=(Align.MIN, Align.CENTER, Align.MIN))
    skin = skin + ctx.add(root, why="tongue root (0.5 mm into the skin, so they fuse)", kind="tongue")
    # aft: two M3 down through the skin into the beam's inserts
    top = Location(Plane(origin=(0, 0, p.fuse_top), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))
    skin = skin - iface.bolt_pattern(ctx, "hatch", "M3", F.hatch_bolts(p), top, kind="clearance", depth=F.SKIN)
    skin, failed = fillet_inside(ctx, skin, r=1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    ctx.rigid("base", Location())
    return ctx.finish(skin)
