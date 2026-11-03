"""Fin (PLA, 1 wall, 5 %): swept, tapered NACA 0009 (fin_h above the boom top, fin_root / fin_tip, fin_sweep_deg),
root trailing edge at the boom's rear end. Built like a wing half standing on the boom (aero.wing_solid, span turned
to +Z) and cut at the tail mount's flat top, where it sits. The rudder comes off it with kerf.aero.elevon_split at
rud_hinge_frac: hinge tape on the right side, the V gap (rud_throw + 8 deg) on the left.

Held by glue (group `fin`): a slot in the root fits over the mount's 3 mm blade (0.15 mm per side, 1.2 mm 45 deg
mouth chamfer over the blade's root fillet). Print: standing on its root (print_rot [0, 0, 0]): the slot top is a
45 deg ridge, the aft (hinge) face leans 16 deg past vertical.
"""
from build123d import *
import numpy as np
from kerf import aero
from kerf.features import fillet_inside

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_m = importlib.util.spec_from_file_location("dfw_tail_mount", pathlib.Path(__file__).with_name("tail_mount.py"))
M = importlib.util.module_from_spec(_m); _m.loader.exec_module(M)

V_MARGIN = 8.0        # deg of V gap beyond the rudder throw
MOUTH = 1.2           # slot mouth chamfer (covers the blade's r 1 root fillet)


def surfaces(p):
    """(fin, rudder, hinge a, hinge b) in the aircraft frame, before the cut at the mount top."""
    boom_top = M.dims(p)["boom_top"]
    pf = aero.Planform(span=2 * p.fin_h, root_chord=p.fin_root, tip_chord=p.fin_tip, sweep_le_deg=p.fin_sweep_deg,
                       root_airfoil=L.TAIL_AIRFOIL, x_le0=p.boom_x1 - p.fin_root, te_min=0.8)
    raw = aero.wing_solid(pf, 0.0, p.fin_h)                 # span along +Y from the boom top, thickness along Z
    wing, surf, (a, b) = aero.elevon_split(pf, raw, 0.0, p.fin_h, p.rud_hinge_frac, gap_deg=p.rud_throw + V_MARGIN)
    T = Pos(0, 0, boom_top) * Rot(90, 0, 0)                 # (x, y, z) -> (x, -z, y + boom_top): span up
    w = lambda v: np.array([v[0], -v[2], v[1] + boom_top])
    return T * aero.largest(wing), T * aero.largest(surf), w(a), w(b)


def above(z):
    return Pos(0, 0, z) * Box(2000, 2000, 1000, align=(Align.CENTER, Align.CENTER, Align.MIN))


def build(ctx):
    p = ctx.p
    d = M.dims(p)
    fin, _, a, b = surfaces(p)
    fin = fin & above(d["top"])
    g = M.SLOT_CLEAR
    slot = M.blade(p, grow=g)
    bb = M.blade(p).bounding_box()
    mouth = Pos((bb.min.X + bb.max.X) / 2, 0, d["top"]) * extrude(
        Rectangle(bb.size.X + 2 * (g + MOUTH), M.BLADE_T + 2 * (g + MOUTH)), amount=g + MOUTH, taper=45)
    fin -= ctx.cut(slot + mouth, why="slot glued over the tail mount's blade; 45 deg mouth over the blade's root fillet", kind="slot")
    fin = aero.largest(fin)

    def keep(at):
        if abs(at[1]) < 3 and bb.min.X - 2 < at[0] < bb.max.X + 2 and at[2] < bb.max.Z + 1:
            return "the tail mount's square blade sits in this slot"
        return None
    fin, failed = fillet_inside(ctx, fin, r=1.0, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    ctx.rigid("base", Location())
    u = (b - a) / np.linalg.norm(b - a)
    ctx.revolute("rudder", Axis(tuple(a), tuple(u)), range=(-p.rud_throw, p.rud_throw))
    return ctx.finish(fin)
