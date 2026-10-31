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
PIN = "motion.pin_3mm"
SIDES = {"mcp": -1, "pip": +1, "dip": -1}      # band that holds the PARENT's knuckle at each joint
FLEX = 4.0        # flexor line distance below the axis (moment arm at home)
FLEX_A = 4.5      # flexor channel exits this far either side of an axis
EXT = 5.0         # extensor line above the axis and wrap radius
EXT_A = 5.0
TUBE_D = 2.2      # tendon channel diameter (requirement: >= 1.5 clear; line 0.5-0.8 mm)
ROOF = 55.0       # channel roof slope (deg from horizontal on the printer) - no supports
REACH = RK + 1.0  # how far from an axis a neighbour's run is swept over this part's knuckle
STEP = 10.0       # joint sampling for swept tendon cuts (deg)
BAND_T = W / 2 - GAP / 2
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
    }


def crossing_cuts(lj: float, rng: float, role: str, up: int):
    """Swept cutters for both tendons across one joint, in the parent ('parent') or child ('child') frame."""
    j = joint_points(lj)
    out = []
    n = int(round(rng / STEP))
    for k in range(n + 1):
        th = rng * k / n
        if role == "parent":   # child points move with the joint
            m = lambda q: (lambda r: (r[0] + lj, 0, r[2]))(_rot(th, q))  # noqa: E731
            fc, wc = m(j["flex_c"]), m(j["ext_wc"])
            out += [_tube(j["flex_p"], fc, up), _tube(j["ext_wp"], wc, up),
                    # the child's own runs pass over this part's knuckle disc: groove the disc face for them too
                    _tube(fc, m((REACH, 0, -FLEX)), up), _tube(wc, m((REACH, 0, j["ext_wc"][2])), up)]
        else:                  # parent points seen from the child: inverse rotation about the child axis (u = 0)
            m = lambda q: _rot(-th, (q[0] - lj, 0, q[2]))  # noqa: E731
            fp, wp = m(j["flex_p"]), m(j["ext_wp"])
            out += [_tube(fp, j["flex_c"], up), _tube(wp, j["ext_wc"], up),
                    _tube(fp, m((lj - REACH, 0, -FLEX)), up), _tube(wp, m((lj - REACH, 0, j["ext_wp"][2])), up)]
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
    """The dowel hole of one joint: pressed in the parent's knuckle band, free in the child's."""
    from kerf import iface
    s = SIDES[joint]
    if role == "parent":
        y, fit, sign = s * W / 2, "press", s
        u = lj
    else:
        y, fit, sign = -s * W / 2, "free", -s
        u = 0.0
    loc = Location((u, y, 0), (-90 if sign > 0 else 90, 0, 0))   # +Z of the hole frame points out of the face
    return iface.pin_hole(ctx, PIN, loc, group=f"pin_{joint}", depth=BAND_T, fit=fit)


def child_end(body: Sketch):
    """Proximal end of a segment (child side of its proximal joint): returns (bottom, top) profiles."""
    keep_bottom = rect(0, XC, 0, H) + rect(XC, 1e3, -H, H)
    keep_top = rect(XC, 1e3, -H, H)
    return (body & keep_bottom) + disc(0, RK), body & keep_top


def parent_end(bottom: Sketch, top: Sketch, lj: float):
    """Distal end of a segment (parent side of the joint at u = lj): knuckle disc on the bottom, pocket on top."""
    return bottom + disc(lj, RK), top - disc(lj, RH)
