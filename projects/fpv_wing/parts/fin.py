"""Wingtip fin (fin_l / fin_r), TPU: yaw stability for the tailless wing and the first thing to touch the ground in
a wingtip landing, so it flexes instead of breaking. A swept, tapered NACA 0008 plate standing on the outer wing's
upper surface near the tip. Its root follows the wing's upper surface exactly (the wing is subtracted from it) and a
tab continues down into a matching slot in the outer wing segment, where it is glued (TPU-safe CA or contact glue).
"""
from build123d import *
from kerf import aero

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def fin_geometry(p, s):
    """(fin part, slot to cut from the outer wing segment) for side s (+1 right, -1 left)."""
    pfw = L.planform(p)
    yc = s * (p.semi - p.fin_inset)                              # fin centre plane
    c = pfw.chord(p.semi - p.fin_inset)
    x_le = pfw.x_le(p.semi - p.fin_inset) + c - p.fin_root          # fin TE flush with the wing TE
    pf = aero.Planform(span=2 * (p.fin_h + 6), root_chord=p.fin_root, tip_chord=p.fin_tip,
                       sweep_le_deg=p.fin_sweep_deg, root_airfoil="naca0008", te_min=0.8)
    raw = aero.wing_solid(pf, 0.0, p.fin_h + 6)                   # span along +Y from its root, thickness along Z
    raw = Pos(x_le, yc, -6.0) * (Rot(90, 0, 0) * raw)             # span up (+Z) from 6 mm below the chord plane
    wing = aero.wing_solid(pfw, *((p.seg_split_y, p.semi) if s > 0 else (-p.semi, -p.seg_split_y)))
    tab_box = Pos(x_le + 0.2 * p.fin_root, yc, -6.0) * Box(0.55 * p.fin_root, 40, 40, align=(Align.MIN, Align.CENTER, Align.MIN))
    slot = raw & wing & tab_box
    fin = (raw - wing) + slot
    return aero.largest(fin) if hasattr(fin, "solids") else fin, slot


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    fin, _ = fin_geometry(p, s)
    ctx.rigid("tip", Location())
    return ctx.finish(fin)
