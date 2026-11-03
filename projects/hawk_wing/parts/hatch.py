"""Battery / electronics hatch: the fuselage's own top skin over the bay (x -112..-8, |y| < 27), cut from the same hull so it is
flush. A tongue at the front slides under the lip over the bulkhead; one M3 at the back goes down through the lid into a
heat-set insert in the fuselage (field: one screw, then the XT60, ESC, FC and RX are reached from above). The lid rests on
the fuselage's ledges (0.2 mm clear). PETG, 2 walls, printed outer face down (curved skin on the bed, tongue standing).
"""
from build123d import *
import importlib.util, pathlib
from kerf import iface
from kerf.features import fillet_inside

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_fspec = importlib.util.spec_from_file_location("hw_fuselage", pathlib.Path(__file__).with_name("fuselage.py"))
F = importlib.util.module_from_spec(_fspec); _fspec.loader.exec_module(F)

CLEAR = 0.3        # lid to opening edge, per side


def build(ctx):
    p = ctx.p
    hull = F.inset_solid(p, 0.0)
    skin = hull & F.opening_prism(-CLEAR) - F.inset_solid(p, F.SKIN)
    # tongue under the front lip: top touches the lid's underside inside the opening, 0.25 mm under the lip's underside in the slot
    ta = (F.inset_solid(p, F.SKIN - 0.2) - F.inset_solid(p, F.SKIN + 1.8)) & Pos(F.HATCH_X[0], -18, -5) * Box(2.4, 36, 100, align=(Align.MIN, Align.MIN, Align.MIN))
    tb = (F.inset_solid(p, F.SKIN + 0.25) - F.inset_solid(p, F.SKIN + 2.05)) & Pos(F.HATCH_X[0] - 6.0, -18, -5) * Box(6.2, 36, 100, align=(Align.MIN, Align.MIN, Align.MIN))
    skin += ctx.add(ta + tb, why="front tongue: slides under the fuselage lip, holds the front edge down", kind="tongue")
    # rear screw: a pad under the skin so the M3 head and the insert's thread have 3.2 mm of PETG, hole through both
    rx, ry = F.REAR_SCREW
    zu = L.fuse_section(p, rx)[2] - F.SKIN
    pad = (Pos(rx, ry, zu - 0.6) * Cylinder(5.0, 2.0)) & F.opening_prism(-CLEAR)
    skin += ctx.add(pad, why="pad under the skin at the screw: 3.2 mm of PETG under the M3 head", kind="pad")
    top = Location(Plane(origin=(0, 0, zu + F.SKIN), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))
    skin -= iface.bolt_pattern(ctx, "hatch", "M3", [(rx, ry)], top, kind="clearance", depth=F.SKIN + 1.6, teardrop="auto")
    ctx.rigid("base", Location())
    skin, left = fillet_inside(ctx, skin, 1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(skin)
