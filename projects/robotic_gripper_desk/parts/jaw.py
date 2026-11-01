"""Jaw (one file, two parts: jaw_r side +1, jaw_l side -1 = the same STL turned 180 deg about X).

Frame J: X forward, Y toward this jaw's rack, Z = opening direction; origin at closed on the pad face plane, on the
pinion axis line (y = 0), at the carriage's back face (gripper x = x_c0).

Load path (DESIGN.md 'Load -> section', one jaw blocked alone at grip-servo stall, 61.5 N): the object pushes the pad
+Z; the finger carries it as a cantilever (moment F x lever, zero at the tip, largest at the root) into the carriage
web, which twists it out to the two rod bosses; the rack teeth pull -Z at the mesh point, and the separating force
(22 N, +Y) bends the rack bar as a cantilever from the carriage, so its backbone is deep in Y right behind the teeth.

Print: print_rot [-90, 0, 0] = part +Y on the bed: carriage, bottom rod boss and rack backbone stand on the bed face
y = +h, the rack teeth point up (tooth profile in the layer plane's normal section, full face width every layer),
the pad face is vertical and its grip grooves run up the layers. The finger floats over the bed (its |y| <= 8.5
envelope is the gripper's keep-out), so its underside is a 45 deg chamfer down to a 1 mm strip: one line of support.
"""
import math

from build123d import *
from kerf import drives, features as F, iface
from kerf.coves import cove_fillets
from kerf.edges import sharp_inside

ROD = "rods.ss_rod_4"
R1, R2, R4 = 1.0, 2.0, 4.0          # project style radii (project.yaml style.radii)
FW = 8.5                            # finger half-width in Y: the gripper's keep-out envelope for the fingers
H_TIP = 5.0                         # finger depth in Z (bending direction) at the tip; at the root = carr_len
FLAT = 2.0                          # finger underside strip left under the 45 deg chamfer (the only supported line)
G_PITCH, G_D = 1.5, 0.5            # grip grooves: pitch, depth = radius (1.0 wide at the face, 0.5 mm lands)
LEAD = 1.0                          # lead-in chamfer at the finger tip


def _yz(pts, x0, x1):
    """Prism of the (y, z) polygon pts between x0 and x1."""
    return Pos(x0, 0, 0) * extrude(Plane.YZ * Polygon(*pts, align=None), x1 - x0, dir=(1, 0, 0))


def _xz(pts, y0, y1):
    """Prism of the (x, z) polygon pts between y0 and y1."""
    return Pos(0, y0, 0) * extrude(Plane.XZ * Polygon(*pts, align=None), y1 - y0, dir=(0, 1, 0))


def build(ctx):
    p = ctx.p
    side = 1 if p.side > 0 else -1
    cx, cl, ry = p.carr_x, p.carr_len, p.rod_y
    h = ry + 4.5                                  # carriage half-height: 2.3 mm boss wall past the rod bore, |y| <= 25.5
    yb = ry - 4.5                                 # inner edge of each rod boss
    x_tip = cx + p.finger_len

    # ---- carriage: two rod bosses (full carr_len, the bearing length and the open-end stop face) joined by a web
    body = Pos(cx / 2, 0, cl / 2) * Box(cx, 2 * h, cl)                     # why: carriage block on the two guide rods

    # ---- rack bar in the pinion slab, pitch line at y = +r_p, teeth along Z pointing at the pinion axis (-Y)
    _, rack, ri = drives.rack_pinion(p.gear_m, int(p.pinion_z), int(p.rack_n), p.gear_b)
    x0 = -(p.gear_b + p.slab_gap)
    n = int(p.rack_n)
    k_hi = math.floor((n - 1) / 2 - 1.5)                     # rack copy reaching 1.5 pitches past the mesh at closed
    k_lo = math.ceil(p.s_max / p.pitch + 1.5 - (n + 1) / 2)  # rack copy reaching 1.5 pitches past it fully open
    for k in range(k_hi, k_lo + 1):
        body += Pos(x0, 0, -p.z_in - k * p.pitch) * Rot(0, 90, 0) * rack  # why: whole pitches keep the verified phase; drives' odd rack is asymmetric, one 9-tooth copy leaves only 1 pitch at closed
    bb = body.bounding_box()
    z_far = bb.min.Z                                                       # far end of the teeth (toward the centre)
    y_root = ri.rack_y[1]
    body += Pos(x0 / 2 - p.slab_gap / 2, (y_root + h) / 2, (z_far + cl) / 2) * Box(p.gear_b, h - y_root, cl - z_far)  # why: 8.7 mm backbone behind the tooth roots: the separating force must not spring the rack off the pinion
    body += Pos(-p.slab_gap / 2, (y_root + h) / 2, cl / 2) * Box(p.slab_gap + 0.02, h - y_root, cl)  # why: bridge over the slab gap joins the rack to the bottom rod boss, above the pinion tip circle

    # ---- finger: cantilever from the carriage front face to the tip, pad face in z = 0, tapered with the moment
    fing = _xz([(cx - 1, 0), (x_tip, 0), (x_tip, H_TIP), (cx, cl), (cx - 1, cl)], -FW, FW)  # why: depth falls linearly with the moment F x (tip - x); stress stays ~even along it
    fing -= _yz([(FW + 0.1, FLAT - 0.1), (FW + 0.1, cl + 2), (FLAT - cl - 2 + FW, cl + 2)], cx - 1, x_tip + 1)  # why: 45 deg underside, prints over air without a ceiling
    body += fing

    # ---- fillets on the load path (before the grooves and holes, so the edges are simple)
    def edge_at(x=None, y=None, z=None, tol=0.05, along=None):
        es = body.edges()
        if along is not None:
            es = es.filter_by(along)
        return [e for e in es if all(v is None or abs(getattr(e.center(), a) - v) < tol
                                     for a, v in (("X", x), ("Y", y), ("Z", z)))]

    root = edge_at(x=cx, y=-FW, along=Axis.Z) + [e for e in body.edges() if abs(e.center().X - cx) < 0.05
                                                  and abs(e.center().Y + e.center().Z - (FW + FLAT)) < 0.05
                                                  and e.length > 2]
    body, bad = F.safe_fillet(body, [(root, R4)])  # why: finger root, the highest bending moment, into the carriage
    # why: bridge root and rack bar into the bridge; 0.5 = what the 0.6 slab gap allows. OCC's fillet fails on the
    # rack-bar edge (it meets the tooth flanks), so that one is a boolean cove (kerf/coves.py)
    body, bad2 = F.safe_fillet(body, [(edge_at(x=0, y=y_root, along=Axis.Z), 0.5)])
    body, bad2b = cove_fillets(body, edge_at(x=-p.slab_gap, z=0, along=Axis.Y), 0.5)
    bad2 += bad2b
    body, bad3 = F.safe_fillet(body, [(edge_at(x=0, y=-h, along=Axis.Z) + edge_at(x=cx, y=-h, along=Axis.Z), R4),  # why: round the top boss over the rod (style r4)
                                      (edge_at(x=x_tip, z=H_TIP, along=Axis.Y), R2)])  # why: blunt fingertip back corner
    body, bad4 = F.safe_fillet(body, [(edge_at(x=x_tip, z=0, along=Axis.Y), LEAD)], kind="chamfer")  # why: lead-in at the tip, slides over an object instead of stubbing on it
    # why: rack tooth roots get the ISO 53 basic-rack root fillet (0.38 x module): the root corner is where a tooth
    # cracks when one jaw is blocked at stall (rack_teeth); the pinion tip clearance (0.25 m) is the standard one for it
    body, bad5 = cove_fillets(body, [e for e in edge_at(y=y_root, along=Axis.X) if e.center().X < 0], 0.38 * p.gear_m)
    # why: every other junction left sharp (rack end into the bridge, finger side into the carriage): R2, else R1
    for rr in (R2, R1):
        pts = [Vector(*c["at"]) for c in sharp_inside(body)]
        body, _ = cove_fillets(body, [e for e in body.edges() if any((e.center() - c).length < 0.15 for c in pts)
                                      and not (e.center().X < 0 and abs(e.center().Y - y_root) < 0.05)], rr)
    bad4 += bad5

    # ---- grip pad: round-bottom grooves across the last pad_len of the pad face, ridge lands stay in z = 0
    x_p = x_tip - p.pad_len
    n_g = int((p.pad_len - LEAD) / G_PITCH)
    for i in range(n_g):
        xg = x_p + G_PITCH / 2 + i * G_PITCH
        # why: grip texture that bites into card / wood / foam; round roots (r = depth = 0.5, 1.0 wide) leave no sharp
        # inside corner to start a crack; grooves run along Y = up the layers, so they print crisp
        body -= Pos(xg, 0, 0) * Rot(90, 0, 0) * Cylinder(G_D, 2 * FW + 2)

    # ---- guide-rod bores (free fit: the jaw slides on the rods), horizontal in print -> teardrops
    for y in (ry, -ry):
        g = ("rod_top" if y > 0 else "rod_bot") if side > 0 else ("rod_bot" if y > 0 else "rod_top")
        loc = Location((cx / 2, y, cl))
        body -= iface.pin_hole(ctx, ROD, loc, g, depth=cl, fit="free", teardrop=iface.print_up_deg(ctx, loc))  # why: linear bearing on each 4 mm guide rod

    body, bad5 = F.bed_chamfer(ctx, body, 0.5)  # why: elephant's-foot chamfer on the first layer
    for b in bad + bad2 + bad3 + bad4:
        ctx.notes.append(f"fillet skipped: {b}")

    ctx.rigid("mount", Location() if side > 0 else Location((0, 0, 0), (180, 0, 0)))
    ctx.rigid("pad", Location((x_tip - p.pad_len / 2, 0, 0)))
    return ctx.finish(body)
