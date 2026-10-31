"""Shared geometry for the bionic finger (imported by every part file, so all four agree by construction).

Frames: X runs along the finger (proximal -> distal), Z is dorsal (back of the hand, +) / palmar (-), Y is across
the finger. Every joint axis is parallel to Y. A segment's origin is on its proximal pin axis; the base's origin is
on the mcp axis. Flexion = positive rotation about +Y (+X turns toward -Z, the palm).

Knuckles are two-layer LAP joints so every part prints on its side (Y vertical) with no supports:
- the part is split into a bottom band (its knuckle side, on the bed), a 0.4 mm gap layer at y = 0 and a top band;
- at a joint the parent's knuckle disc sits in band `s` and the child's disc in band `-s`; each disc turns inside a
  concave pocket (radius Rk + clearance) of the other part, and the child keeps all other material beyond `xc` (or
  dorsal of the axis), which the joint-sweep check proves clear up to the full flexion range;
- the knuckle sides alternate (mcp -1, pip +1, dip -1) so each part has both its knuckles in its bottom band.
Tendons run in the y = 0 plane. Where a tendon crosses a joint, each part cuts the union of the tendon's straight
chord over the joint's range (10 deg steps) in its own frame, so the line stays free at every angle.
"""
from __future__ import annotations

import math

from build123d import Box, Circle, Cylinder, Location, Plane, Polygon, Pos, Rectangle, Rot, Sketch, extrude, Align, Solid, Compound

# ---- fixed design numbers (DESIGN.md explains each) ----
W = 15.6          # finger width (Y): two knuckle bands (7.6 = 38 layers of 0.2) + the gap (0.4 = 2 layers)
                  # (adult index ~16-18 mm, Aero Hand 16.4)
D = 18.0          # depth (Z) at the knuckles: room for both lines 1.6 mm clear of the inserts and >= 1.75 mm skin
H = D / 2         # half depth
GAP = 0.4         # axial gap between the two lap layers (0.2 per face, on the 0.2 mm layer grid)
BOSS = 0.2        # one-layer boss around each insert on the parent's gap face: the 8 mm shoulder spans the child's
                  # band (7.6) + the gap left at the boss (0.2) = 7.8, so the head never clamps (0.2 mm play), and the
                  # insert gets 7.6 + 0.2 = 7.8 mm of material (catalog: 6.7 deep hole + 0.8 floor)
BOSS_R = 3.4      # boss radius: 1.4 mm of wall around the 4.0 insert bore, 0.2 mm inside the closest swept groove (3.6)
RK = H            # knuckle disc radius (= H, full-depth round knuckle)
CLR = 0.4         # radial clearance between a disc and the pocket it turns in
RH = RK + CLR     # pocket radius
PIN = "motion.shoulder_4_m3"   # pivot: 4 mm shoulder screw, shoulder turns in the child, M3 thread in a heat-set insert in the parent
SIDES = {"mcp": -1, "pip": +1, "dip": -1}      # band that holds the PARENT's knuckle at each joint
TUBE_D = 2.2      # tendon channel diameter (requirement: >= 1.5 clear; line 0.5-0.8 mm)
# Channel distances from the pin axes keep every swept groove >= the catalog heat-set wall (1.6) from the 4.0 insert
# bore: insert r 2.0 + 1.6 + tube r 1.1 = 4.7 (audit C-6).
FLEX = 4.7        # flexor line distance below the axis (moment arm at home); its chord only moves away as a joint bends
FLEX_A = 4.5      # flexor channel exits this far either side of an axis
EXT = 6.15        # extensor line above the axis = wrap radius of the crown points; at full flexion (80 deg) the chord
                  # between the two crowns passes EXT cos(40 deg) = 4.71 from the axis
EXT_WRAP = 0.0    # crown angle offset from straight up (parent 90 + this, child 90 - this)
EXT_A = 5.0
ROOF = 55.0       # channel roof slope (deg from horizontal on the printer) - no supports
STEP = 10.0       # joint sampling for swept tendon cuts (deg). Between two steps the line lies between two tube axes at
                  # most 1.64 mm apart (9.4 mm from the axis, the pocket rim), so <= 0.82 mm off the nearer axis: inside
                  # its 1.1 mm radius with a 0.25 mm line radius to spare (0.5 mm line). A 0.8 mm line can brush the
                  # ridges between two steps there (DESIGN.md s10). (5 deg steps make OCC tessellate the groove floors
                  # with cracks.)
XE = RH + 1.5     # each tendon run is also cut out of the neighbouring part's knuckle out to this distance from the axis
BAND_T = W / 2 - GAP / 2
MIN_EDGE = 1.5    # the pocket circle meets the top/bottom faces at a grazing angle: cut the band back to where the
                  # wedge between them is this thick (no knife edges)
XT = math.sqrt(RH ** 2 - (H - MIN_EDGE) ** 2)
# Hard stop at straight: a dorsal lug on each side of every knuckle (above the finger's back, z in [H, H + LUG_H]).
# The child's lug (both bands, outside the pocket radius in its top band) meets the parent's lug (its knuckle band
# only) when the joint is bent backward: STOP_GAP apart at 0 deg, touching at about -2 deg (hard_stop proves it).
LUG_H = 2.0
STOP_GAP = 0.3
# A child's joint frame: Z along the pin (+Y) and X toward +Z, because a build123d RevoluteJoint about +Y measures
# angle 0 from the parent's +Z. With this frame the child lies straight along +X at angle 0 and positive angles flex.
CHILD_FRAME = Location(Plane(origin=(0, 0, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)))


def band(sk, side: int, which: str):
    """Extrude a 2-D XZ profile (sketch in XY with y meaning Z) into one Y band: which = 'band' or 'gap'."""
    y0, y1 = (GAP / 2, W / 2) if which == "band" else (-GAP / 2, GAP / 2)
    if which == "band" and side < 0:
        y0, y1 = -W / 2, -GAP / 2
    return Rot(90, 0, 0) * Pos(0, 0, -y1) * extrude(sk, y1 - y0)


def rect(u0, u1, v0, v1):
    return Pos((u0 + u1) / 2, (v0 + v1) / 2) * Rectangle(u1 - u0, v1 - v0)


def disc(u, r):
    return Pos(u, 0) * Circle(r)


def assemble(bottom: Sketch, top: Sketch, b: int):
    """Bottom band on side b, gap layer and top band both from `top` (top footprint lies inside bottom's)."""
    return band(bottom, b, "band") + band(top, 0, "gap") + band(top, -b, "band")


# ---- tendon channels ----

def _tube(p0, p1, up, d=TUBE_D, ext=0.4):
    """Channel cutter from p0 to p1 (points in the y=0 plane) with a pointed roof toward `up` (+1/-1 along Y)."""
    import numpy as np
    a, b = np.array(p0, float), np.array(p1, float)
    L = float(np.linalg.norm(b - a))
    if L < 1e-6:
        return None
    t = (b - a) / L
    r = d / 2
    beta = math.radians(90 - ROOF)
    apex = r / math.sin(beta)
    # roof triangle on the tangent chord (not the full chord at the centre), so the cutter is exactly d wide
    tx, ty = r * math.sin(beta), r * math.cos(beta)
    pl = Plane(origin=tuple(a - t * ext), x_dir=(0, up, 0), z_dir=tuple(t))
    prof = Circle(r) + Polygon((apex, 0), (tx, ty), (tx, -ty), align=None)
    return extrude(pl * prof, L + 2 * ext)


def _rot(theta_deg, p, about_u=0.0):
    """Rotate point p (x, y, z) about the Y axis through (about_u, *, 0) by flexion angle theta."""
    c, s = math.cos(math.radians(theta_deg)), math.sin(math.radians(theta_deg))
    x, y, z = p[0] - about_u, p[1], p[2]
    return (about_u + x * c + z * s, y, -x * s + z * c)


def joint_points(lj: float):
    """Tendon waypoints at a joint whose axis is at u = lj in the parent frame (child frame axis at 0)."""
    a_p, a_c = math.radians(90 + EXT_WRAP), math.radians(90 - EXT_WRAP)
    wp = (lj + EXT * math.cos(a_p), 0, EXT * math.sin(a_p))
    wc = (EXT * math.cos(a_c), 0, EXT * math.sin(a_c))
    return {
        "flex_p": (lj - FLEX_A, 0, -FLEX), "flex_c": (FLEX_A, 0, -FLEX),
        "ext_p": (lj - EXT_A, 0, wp[2]), "ext_wp": wp, "ext_wc": wc, "ext_c": (EXT_A, 0, wc[2]),
        # run ends far enough from the axis to be clear of the other part's knuckle disc
        "flex_pp": (lj - XE, 0, -FLEX), "flex_cc": (XE, 0, -FLEX), "ext_pp": (lj - XE, 0, wp[2]), "ext_cc": (XE, 0, wc[2]),
    }


def crossing_cuts(lj: float, rng: float, role: str, up: int):
    """Swept cutters for both tendons across one joint, in the parent ('parent') or child ('child') frame: the chord
    between the two parts' waypoints, plus the other part's straight runs near the axis (they pass through this
    part's knuckle disc in the 0.3 mm lap gap), each at every STEP over the joint's range."""
    j = joint_points(lj)
    out = []
    n = int(round(rng / STEP))

    def to_parent(th, q):    # child-frame point -> parent frame at joint angle th
        r = _rot(th, q)
        return (r[0] + lj, 0, r[2])

    def to_child(th, q):     # parent-frame point -> child frame at joint angle th
        return _rot(-th, (q[0] - lj, 0, q[2]))

    for k in range(n + 1):
        th = rng * k / n
        if role == "parent":   # child points move with the joint
            fc, wc = to_parent(th, j["flex_c"]), to_parent(th, j["ext_wc"])
            out += [_tube(j["flex_p"], fc, up), _tube(j["ext_wp"], wc, up),
                    _tube(fc, to_parent(th, j["flex_cc"]), up),
                    _tube(wc, to_parent(th, j["ext_c"]), up), _tube(to_parent(th, j["ext_c"]), to_parent(th, j["ext_cc"]), up)]
        else:                  # parent points seen from the child: inverse rotation about the child axis (u = 0)
            fp, wp = to_child(th, j["flex_p"]), to_child(th, j["ext_wp"])
            out += [_tube(fp, j["flex_c"], up), _tube(wp, j["ext_wc"], up),
                    _tube(to_child(th, j["flex_pp"]), fp, up), _tube(to_child(th, j["ext_pp"]), wp, up)]
    return [s for s in out if s is not None]


def runs(points_list, up):
    """Straight channel runs inside one part: list of polylines (lists of points)."""
    out = []
    for pts in points_list:
        for a, b in zip(pts, pts[1:]):
            s = _tube(a, b, up)
            if s is not None:
                out.append(s)
    return out


def cut_all(part, cutters, chunk: int = 12):
    """Subtract the cutters in chunks: one boolean with ~100 overlapping tools runs out of memory."""
    for i in range(0, len(cutters), chunk):
        part = part - Compound(children=cutters[i:i + chunk])
    return part


def pin_holes(ctx, lj: float, joint: str, role: str):
    """The pivot of one joint: an M3 screw whose head sits on the child's outer face, turning free in the child's
    knuckle band, threaded into a heat-set insert in the parent's knuckle band (pressed in from the gap face, which is
    open on the printer). The head is what holds a lap joint together along the pin: a dowel pressed in one band
    would let the other band slide off its free end."""
    from kerf import iface
    s = SIDES[joint]
    if role == "parent":    # insert hole opens on the boss face (insert_boss) of the parent's band (out of the material = -s)
        loc = Location((lj, s * (GAP / 2 - BOSS), 0), (-90 if -s > 0 else 90, 0, 0))
        return iface.pin_hole(ctx, PIN, loc, group=f"pin_{joint}", depth=BAND_T + BOSS, fit="heatset")
    loc = Location((0.0, -s * W / 2, 0), (-90 if -s > 0 else 90, 0, 0))   # +Z of the hole frame points out of the face
    return iface.pin_hole(ctx, PIN, loc, group=f"pin_{joint}", depth=BAND_T, fit="free")


def insert_boss(lj: float, joint: str):
    """The one-layer boss (BOSS thick, BOSS_R radius) on the parent's gap face around its insert: the shoulder bottoms
    on it, so the shoulder length sets the axial play, and the child's band turns against it."""
    s = SIDES[joint]
    return Pos(lj, s * (GAP / 2 - BOSS / 2), 0) * Rot(90, 0, 0) * Cylinder(BOSS_R, BOSS)


def child_end(body: Sketch, theta: float = 80.0):
    """Proximal end of a segment (child side of its proximal joint, range [0, theta] deg): returns (bottom, top).
    Bottom (knuckle) band: the full body plus the knuckle disc; this is where the segment's bending moment is largest,
    so it keeps its whole depth, and the parent's top band is cut away where it swings (`swept`, see parent_end).
    Top band: faces the parent's knuckle band, which holds material behind the axis (x < 0) within |z| <= H and the
    disc (r <= RK). A child point at radius r >= RH and angle a below the X axis reaches |z| = r sin(a + theta) at full
    flexion, so palmar material is kept where x sin(theta) + |z| cos(theta) >= RH (clear of the parent's palmar face
    by CLR); dorsal material ahead of the axis only swings forward; everything stays outside r = RH."""
    s, c = math.sin(math.radians(theta)), math.cos(math.radians(theta))
    zb = -H - 1
    x0, x1 = RH / s, (RH + zb * c) / s
    # one simple polygon (a union of two touching shapes split along z = 0 non-deterministically in OCC)
    allowed = Polygon((0, H + 1), (200, H + 1), (200, zb), (x1, zb), (x0, 0), (0, 0), align=None)
    lug = rect(STOP_GAP / 2, XT + 2, H - 0.5, H + LUG_H)       # overlaps the body by 0.5: no near-coincident faces
    return body + disc(0, RK) + lug, ((body & allowed) - pocket(0)) + (lug - disc(0, RH))


def swept(theta: float, R: float = 80.0):
    """Region a child's full-depth knuckle band (half-strip x >= 0, |z| <= H + CLR) sweeps over flexion [0, theta],
    in the joint frame: the strip at 0, the strip at theta and the wedge between them (one convex polygon)."""
    h = H + CLR
    s, c = math.sin(math.radians(theta)), math.cos(math.radians(theta))
    n = (s, c)                                           # the rotated strip's dorsal normal
    arc = [(R * math.cos(math.radians(-a)), R * math.sin(math.radians(-a))) for a in range(0, int(theta) + 1, 5)]
    d = (c, -s)
    pts = [(0, h), (R, h)] + arc + [(R * d[0] - n[0] * h, R * d[1] - n[1] * h), (-n[0] * h, -n[1] * h)]
    return Polygon(*pts, align=None)


def parent_end(bottom: Sketch, top: Sketch, lj: float, theta: float = 80.0):
    """Distal end of a segment (parent side of the joint at u = lj, range [0, theta]): knuckle disc on the bottom;
    on top the pocket the child's disc turns in, and the region the child's full-depth knuckle band sweeps."""
    lug = rect(lj - XT - 2, lj - STOP_GAP / 2, H - 0.5, H + LUG_H)
    return bottom + disc(lj, RK) + lug, top - pocket(lj) - Pos(lj, 0) * swept(theta)


def pocket(u):
    """Where the other part's knuckle disc turns (r <= RH), widened to |x - u| <= XT so no knife edge is left."""
    return disc(u, RH) + rect(u - XT, u + XT, -H - 1, H + 1)


def edge_chamfers(ctx, part, size: float = 0.5):
    """ENGINEERING.md s5 outside edges: the 0.5 mm elephant's-foot chamfer on the first layer (features.bed_chamfer)
    and the same chamfer on the top (last-layer) outline, which faces up and prints without support."""
    from kerf import features
    bed = features.bed_edges(ctx, part)
    y_top = -math.copysign(W / 2, bed[0].center().Y)
    part, failed = features.bed_chamfer(ctx, part, size)
    top = [e for e in part.edges() if abs(e.center().Y - y_top) < 0.05 and all(abs(v.Y - y_top) < 0.05 for v in e.vertices())]
    part, f2 = features.safe_fillet(part, [(top, size)], kind="chamfer")
    if f2 and getattr(ctx, "notes", None) is not None:
        ctx.notes.append(f"{len(f2)} of {len(top)} top-face edges could not take the {size} mm chamfer (deburr them)")
    return part, failed + f2
