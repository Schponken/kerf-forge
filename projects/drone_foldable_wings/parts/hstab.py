"""Horizontal stabiliser (PLA, 1 wall, 5 %): NACA 0009 planform from L.tail_planform, one piece tip to tip, with the
elevator cut off it by kerf.aero.elevon_split along one STRAIGHT hinge line from tip to tip (the planform's 66 %
chord line at the tips; 65.4 % at the root), so the elevator is one piece across the full span. Bottom hinge (tape
along the bottom), and on top the whole V gap is on the stabiliser's side: its aft face leans forward by
elev_throw + 4 deg, the elevator's front face is square to the chord (it is the elevator's bed face), so the
elevator swings +/- elev_throw clear.

Held under the tail mount by 2 M3 from below into the mount's heat-set inserts (group `hstab`); the mount's
underside is this part's own upper surface. Print: standing on its leading edge (print_rot [0, -90, 0]): span along
the bed, layers along the span, the surfaces near vertical (no supports; brim for the narrow nose line).
"""
from build123d import *
import numpy as np
from kerf import aero, iface

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_m = importlib.util.spec_from_file_location("dfw_tail_mount", pathlib.Path(__file__).with_name("tail_mount.py"))
M = importlib.util.module_from_spec(_m); _m.loader.exec_module(M)

HINGE_GAP = 0.6       # elevator front face behind the hinge line (tape hinge)
V_MARGIN = 4.0        # deg of V gap beyond the elevator's up throw


def surfaces(p):
    """(stabiliser, elevator, hinge a, hinge b) in the aircraft frame."""
    pf = L.tail_planform(p)
    half = p.htail_span / 2
    solid = aero.wing_solid(pf, -half, half, stations=3)      # 3 sections: root chord at y 0
    wing, _, (a, b) = aero.elevon_split(pf, solid, -half, half, p.elev_hinge_frac, gap_deg=2 * (p.elev_throw + V_MARGIN))
    _, surf, _ = aero.elevon_split(pf, solid, -half, half, p.elev_hinge_frac, gap_deg=0.0, gap=HINGE_GAP)
    return aero.largest(wing), aero.largest(surf), a, b


def build(ctx):
    p = ctx.p
    stab, _, a, b = surfaces(p)
    # 2 M3 from below into the tail mount's inserts: clearance holes through the full thickness (the hole's own
    # perimeter is the tube the screw head clamps against; use a washer)
    xi, zt, zb = M.ins_points(p)
    loc = Location(Plane(origin=(xi, 0, zb), x_dir=(1, 0, 0), z_dir=(0, 0, -1)))
    stab -= iface.bolt_pattern(ctx, "hstab", "M3", [(0, M.INS_Y), (0, -M.INS_Y)], loc, kind="clearance",
                               depth=zt - zb, teardrop="auto")
    ctx.rigid("base", Location())
    d = (b - a) / np.linalg.norm(b - a)
    ctx.revolute("elevator", Axis(tuple(a), tuple(d)), range=(-p.elev_throw, p.elev_throw))
    return ctx.finish(stab)
