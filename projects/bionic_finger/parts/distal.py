"""Distal phalanx (fingertip): child of dip. Both tendons end here on a washer stop: the line comes through a 1.2 mm hole
in a flat step into a U-slot open to the top face; an M2 flat washer sits on the step and a crimp sleeve / bead (or
knot) on the line end holds against the washer, so the line load bears on the washer's whole face, not on a bead edge.
Origin on the dip axis, fingertip at x = L3. Prints on its side."""
import importlib.util as _iu
import math
import pathlib as _pl

from build123d import *
from kerf import iface

_s = _iu.spec_from_file_location("bionic_fingerlib", _pl.Path(__file__).with_name("fingerlib.py"))
F = _iu.module_from_spec(_s)
_s.loader.exec_module(F)


def ctx_cat_washer_d2() -> float:
    from kerf import catalog
    return float(catalog.get("screws.M2")["washer_d2"])


def stop_slot(p, x0, z, up):
    """Washer seat for one line ending at the step face x = x0, line at height z (y = 0): the U-slot (washer pocket
    (catalog M2 washer OD + stop_pocket_clear) wide, round bottom on the bed side, open to the top face) and the stop_hole_d line hole through the
    stop_step thick step behind it."""
    r = (ctx_cat_washer_d2() + p.stop_pocket_clear) / 2           # ISO 7089 M2 washer OD from the catalog + clearance
    y_top = up * F.W / 2
    pl = Plane(origin=(x0, 0, z), x_dir=(0, 0, 1), z_dir=(1, 0, 0))                    # sketch y = world -Y
    prof = Circle(r) + Pos(0, -y_top / 2) * Rectangle(2 * r, abs(y_top))
    slot = extrude(pl * prof, p.stop_len)
    hole = F._tube((x0 - p.stop_step - 0.5, 0, z), (x0 + 0.5, 0, z), up, d=p.stop_hole_d, ext=0.0)
    return [slot, hole]


def build(ctx):
    p = ctx.p
    L = p.L3
    r_tip = F.H                                            # full round fingertip, tangent to the dorsal/palmar faces
    b = -F.SIDES["dip"]
    body = F.rect(0, L - r_tip, -F.H, F.H) + F.disc(L - r_tip, r_tip)
    bottom, top = F.child_end(body, p.dip_max)
    part = F.assemble(bottom, top, b)
    part -= F.pin_holes(ctx, 0.0, "dip", "child")
    up = -b
    jd = F.joint_points(0.0)
    # each line stays at its joint height until it is clear of the middle's knuckle pocket (r > RH), then turns to its
    # stop; the line is fixed in this part from there on, so the bend never slides
    x_out_f = math.ceil(2 * (math.sqrt(F.RH ** 2 - F.FLEX ** 2) + 0.3)) / 2              # 8.5 (project.yaml paths)
    x_out_e = math.ceil(2 * (math.sqrt(F.RH ** 2 - jd["ext_wc"][2] ** 2) + 0.3)) / 2     # 7.5
    x0 = p.stop_u                                          # washer seat face of both stops
    fa, ea = (x0, 0, p.flex_stop_z), (x0, 0, p.ext_stop_z)
    xs = x0 - p.stop_step                                  # the 2.2 channel ends at the step
    def to_step(a, z):          # last leg: _tube overshoots its ends by 0.4, so stop 0.4 short to end exactly at the step
        dx, dz = xs - a[0], z - a[2]
        k = 1 - 0.4 / math.hypot(dx, dz)
        return F._tube(a, (a[0] + dx * k, 0, a[2] + dz * k), up)
    bf, be = (x_out_f, 0, -F.FLEX), (x_out_e, 0, jd["ext_wc"][2])
    cut = F.runs([[jd["flex_c"], bf], [jd["ext_wc"], be]], up) + [to_step(bf, fa[2]), to_step(be, ea[2])]
    cut += F.crossing_cuts(0.0, p.dip_max, "child", up)
    for a in (fa, ea):
        cut += stop_slot(p, x0, a[2], up)
    part = F.cut_all(part, cut)
    part, _ = F.edge_chamfers(ctx, part)
    ctx.rigid("dip", F.CHILD_FRAME)
    ctx.rigid("tip", Location((L, 0, 0)))
    ctx.rigid("flex_anchor", Location(fa))
    ctx.rigid("ext_anchor", Location(ea))
    return ctx.finish(part)
