"""Shared geometry for the bionic finger (imported by every part file, so all four agree by construction).

Frames: X runs along the finger (proximal -> distal), Z is dorsal (back of the hand, +) / palmar (-), Y is across
the finger. Every joint axis is parallel to Y. A segment's origin is on its proximal pin axis; the base's origin is
on the mcp axis. Flexion = positive rotation about +Y (+X turns toward -Z, the palm).

Knuckles are two-layer LAP joints so every part prints on its side (Y vertical) with no supports:
- the part is split into a bottom band (its knuckle side, on the bed), a 0.3 mm gap layer at y = 0 and a top band;
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
W = 16.0          # finger width (Y); = the stocked 16 mm dowel length
D = 15.0          # depth (Z) at the knuckles
H = D / 2         # half depth
GAP = 0.3         # axial gap between the two lap layers (0.15 per face)
RK = 7.5          # knuckle disc radius (= H, full-depth round knuckle)
CLR = 0.4         # radial clearance between a disc and the pocket it turns in
RH = RK + CLR     # pocket radius
XC = 8.5          # child keeps palmar / far-side material only beyond this distance from the axis
PIN = "M3"         # screw pivot: ISO 4762 M3 SHCS, free in the child, into a heat-set insert in the parent
SIDES = {"mcp": -1, "pip": +1, "dip": -1}      # band that holds the PARENT's knuckle at each joint
FLEX = 4.0        # flexor line distance below the axis (moment arm at home)
FLEX_A = 4.5      # flexor channel exits this far either side of an axis
EXT = 5.0         # extensor line above the axis and wrap radius
EXT_A = 5.0
TUBE_D = 2.2      # tendon channel diameter (requirement: >= 1.5 clear; line 0.5-0.8 mm)
ROOF = 55.0       # channel roof slope (deg from horizontal on the printer) - no supports
STEP = 10.0       # joint sampling for swept tendon cuts (deg)
XE = RH + 1.5     # each tendon run is also cut out of the neighbouring part's knuckle out to this distance from the axis
BAND_T = W / 2 - GAP / 2
MIN_EDGE = 1.5    # the pocket circle meets the top/bottom faces at a grazing angle: cut the band back to where the
                  # wedge between them is this thick (no knife edges)
XT = math.sqrt(RH ** 2 - (H - MIN_EDGE) ** 2)
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
    half = apex * math.tan(beta)
    pl = Plane(origin=tuple(a - t * ext), x_dir=(0, up, 0), z_dir=tuple(t))
    prof = Circle(r) + Polygon((apex, 0), (0, half), (0, -half), align=None)
    return extrude(pl * prof, L + 2 * ext)


def _rot(theta_deg, p, about_u=0.0):
    """Rotate point p (x, y, z) about the Y axis through (about_u, *, 0) by flexion angle theta."""
    c, s = math.cos(math.radians(theta_deg)), math.sin(math.radians(theta_deg))
    x, y, z = p[0] - about_u, p[1], p[2]
    return (about_u + x * c + z * s, y, -x * s + z * c)


def joint_points(lj: float):
    """Tendon waypoints at a joint whose axis is at u = lj in the parent frame (child frame axis at 0)."""
    wp = (lj + EXT * math.cos(math.radians(95)), 0, EXT * math.sin(math.radians(95)))
    wc = (EXT * math.cos(math.radians(85)), 0, EXT * math.sin(math.radians(85)))
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


def cut_all(part, cutters):
    if not cutters:
        return part
    return part - Compound(children=cutters)


def pin_holes(ctx, lj: float, joint: str, role: str):
    """The pivot of one joint: an M3 screw whose head sits on the child's outer face, turning free in the child's
    knuckle band, threaded into a heat-set insert in the parent's knuckle band (pressed in from the gap face, which is
    open on the printer). The head is what holds a lap joint together along the pin: a dowel pressed in one band
    would let the other band slide off its free end."""
    from kerf import iface
    s = SIDES[joint]
    if role == "parent":    # insert hole opens on the gap face of the parent's band (out of the material = -s)
        loc = Location((lj, s * GAP / 2, 0), (-90 if -s > 0 else 90, 0, 0))
        return iface.pin_hole(ctx, PIN, loc, group=f"pin_{joint}", depth=BAND_T, fit="heatset")
    loc = Location((0.0, -s * W / 2, 0), (-90 if -s > 0 else 90, 0, 0))   # +Z of the hole frame points out of the face
    return iface.pin_hole(ctx, PIN, loc, group=f"pin_{joint}", depth=BAND_T, fit="free")


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
    return body + disc(0, RK), (body & allowed) - pocket(0)


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
    return bottom + disc(lj, RK), top - pocket(lj) - Pos(lj, 0) * swept(theta)


def pocket(u):
    """Where the other part's knuckle disc turns (r <= RH), widened to |x - u| <= XT so no knife edge is left."""
    return disc(u, RH) + rect(u - XT, u + XT, -H - 1, H + 1)
