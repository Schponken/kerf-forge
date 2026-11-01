"""Mechanical idioms: the recurring printed features of small robots and fixtures, each built with the detail the
engineering rules ask for (root fillets, gussets, wall around holes, support-free printing), so part code says WHAT it
needs and the idiom says HOW. Re-exported from kerf.features.

    from kerf import idioms as I
    body += I.boss(d=10, h=6, root_r=1.5)                                   # standing boss, root fillet built in
    body = I.clevis(L=110, r=13, width=40, t=4, webs=(22, 70))              # fork of two side plates + filleted webs
    body, foot_pts = I.yoke_cheek(x0, x1, z0, z1, y_in, side=+1, t=4, foot=(-35, 14, 20, 6), gussets=(-21, -8.5))
    plate, cut = I.servo_cradle(ctx, "servos.MG996R", loc, "wr_servo", plate_t=4)
    pad, cut = I.cable_saddle(cable_d=6)                                    # tie-down saddle for a lead / bundle
    add, cut = I.grip_pad(30, 20, kind="serrations")                        # jaw face: ridges or a TPU-insert pocket
"""
from __future__ import annotations

import math

from build123d import (Align, Axis, Box, BuildSketch, Circle, Cylinder, Location, Locations, Plane, Polygon, Polyline,
                       Pos, Rectangle, ThreePointArc, Wire, extrude, fillet, make_face, revolve)

from . import catalog, iface
from .sections import MIN_WALL


def safe_fillet(shape, groups):
    from .features import safe_fillet as sf      # features re-exports this module: import at call time
    return sf(shape, groups)

TIE = "wire.cable_tie_2_5"
TIE_CLEAR = 0.35        # mm per side around a tie in its slot (FDM sliding fit, docs/ENGINEERING.md section 6)


# ---------------------------------------------------------------- boss
def boss(d: float, h: float, bore: float = 0.0, root_r: float = 1.0):
    """A cylindrical boss of diameter d standing h mm on a face at z = 0 (+Z up), with a concave root fillet of radius
    root_r built into its foot (revolved, so it never depends on a fillet succeeding on the merged body). It reaches
    0.01 mm below z = 0 so it fuses with the face. bore > 0: a through bore along its axis (the boss only; cut the face
    under it yourself, e.g. with iface). Prints standing: the fillet faces up, the bore is vertical and round."""
    if h <= 0 or d <= 0:
        raise ValueError("boss needs d > 0 and h > 0")
    if bore and (d - bore) / 2 < MIN_WALL:
        raise ValueError(f"boss wall {(d - bore) / 2:.2f} mm around a {bore} mm bore is below {MIN_WALL} mm")
    R, rr = d / 2, max(0.0, min(root_r, h))
    if rr > 0:                                            # profile in (radius, height), then stood up in XZ
        c = (R + rr, rr)
        m = (c[0] - rr * math.sqrt(0.5), c[1] - rr * math.sqrt(0.5))
        w = Wire([*Polyline((0, -0.01), (R + rr, -0.01), (R + rr, 0)).edges(), ThreePointArc((R + rr, 0), m, (R, rr)),
                  *Polyline((R, rr), (R, h), (0, h), (0, -0.01)).edges()])
    else:
        w = Polyline((0, -0.01), (R, -0.01), (R, h), (0, h), close=True)
    solid = revolve(Plane.XZ * make_face(w), Axis.Z, 360)
    if bore:
        solid -= Pos(0, 0, -0.5) * Cylinder(bore / 2, h + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return solid


# ---------------------------------------------------------------- clevis (fork of two side plates)
def side_plate(L: float, r: float, x_end: float, t: float):
    """Link side plate in XY, t thick from z = 0: rounded (radius r) around the pivots at x = 0 and x = L, straight
    out to x_end when that is further, its far corners rounded r/2."""
    with BuildSketch() as sk:
        Circle(r)
        with Locations((L, 0)):
            Circle(r)
        with Locations(((max(L, x_end)) / 2, 0)):
            Rectangle(max(L, x_end), 2 * r)
    s = extrude(sk.sketch, t)
    if x_end > L + r:
        s = fillet(s.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().X > L + r), r * 0.5)
    return s


def clevis(L: float, r: float, width: float, t: float, webs, web_t: float = 4.0, web_r: float = 1.5,
           x_end_a: float | None = None, x_end_b: float | None = None):
    """A fork link: two side plates (A at z = 0..t, B at z = width - t..width) between pivots x = 0 and x = L, joined
    by webs (x positions, web_t thick, full plate height) with web_r fillets on all eight web-to-plate edges (the
    webs carry plate B's share of the load). Plate A / B may run on to x_end_a / x_end_b (a servo seat beyond the
    pivot). Raises if any web fillet fails, so a fork never ships with sharp web roots."""
    if width - 2 * t < web_t:
        raise ValueError(f"clevis gap {width - 2 * t:.1f} mm is too narrow")
    a = side_plate(L, r, x_end_a if x_end_a is not None else L, t)
    b = Pos(0, 0, width - t) * side_plate(L, r, x_end_b if x_end_b is not None else L, t)
    body = a + b
    for wx in webs:
        body += Pos(wx, 0, t - 0.01) * Box(web_t, 2 * r, width - 2 * t + 0.02, align=(Align.CENTER, Align.CENTER, Align.MIN))
    corners = body.edges().filter_by(Axis.Y).filter_by(
        lambda e: any(abs(abs(e.center().X - wx) - web_t / 2) < 0.05 for wx in webs)
        and min(abs(e.center().Z - t), abs(e.center().Z - (width - t))) < 0.05)
    body, failed = safe_fillet(body, [(corners, web_r)])
    if failed or len(corners) != 4 * len(webs):
        raise ValueError(f"clevis web fillets: {len(corners)} edges found, failed {failed}")
    return body


# ---------------------------------------------------------------- yoke cheek (a pivot / servo cheek on a foot)
def yoke_cheek(x0: float, x1: float, z0: float, z1: float, y_in: float, side: int, t: float, top_r: float = 8.0,
               foot=(-35.0, 14.0, 20.0, 6.0), gussets=(), gusset=(3.0, 24.0, 5.0), root_r: float = 2.0,
               end_r: float = 4.0):
    """A vertical cheek (an XZ plate x0..x1, z0..z1, t thick, inner face at y = y_in, growing toward `side` = +1/-1)
    standing on a foot plate that runs inward (toward -side) under the fork, with the load-path details built in:
    top corners rounded top_r, a root_r fillet in the cheek-to-foot inside corner, an end_r fillet where the foot ends
    against the cheek (the cheek's bending stress peaks at that step), and triangular gussets (at x positions
    `gussets`; gusset = (inset from the foot edge, height, thickness)) carrying the cheek's tipping moment.
    foot = (x start, x end, width, thickness). Returns the body (raises if a load-path fillet fails)."""
    y_out = y_in + side * t
    cheek = Pos((x0 + x1) / 2, (y_in + y_out) / 2, z0) * Box(x1 - x0, t, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cheek = fillet(cheek.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], top_r)
    fx0, fx1, foot_w, foot_t = foot
    fy0 = y_in - side * foot_w
    foot_s = Pos((fx0 + fx1) / 2, (y_in + fy0) / 2, z0) * Box(fx1 - fx0, foot_w, foot_t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = cheek + foot_s
    corner = body.edges().filter_by(Axis.X).filter_by(lambda e: abs(e.center().Y - y_in) < 0.05 and
                                                      abs(e.center().Z - (z0 + foot_t)) < 0.05 and e.center().X > x0)
    body, failed = safe_fillet(body, [(corner, root_r)])
    if failed or len(corner) != 1:
        raise ValueError(f"yoke cheek-to-foot fillet failed: {failed or 'edge not found'}")
    end = body.edges().filter_by(Axis.Z).filter_by(lambda e: abs(e.center().X - fx1) < 0.05 and abs(e.center().Y - y_in) < 0.05)
    body, failed = safe_fillet(body, [(end, end_r)])
    if failed or not end:
        raise ValueError(f"yoke foot-end fillet failed: {failed or f'{len(end)} edges'}")
    inset, gh, gt = gusset
    zt = z0 + foot_t - 0.01
    for gx in gussets:
        tri = Polygon((y_in + side * 0.01, zt), (y_in - side * (foot_w - inset), zt), (y_in + side * 0.01, zt + gh), align=None)
        body += Plane.YZ.offset(gx) * extrude(tri, gt / 2, both=True)
    return body


# ---------------------------------------------------------------- servo cradle
def servo_cradle(ctx, servo: str, loc: Location, group: str, plate_t: float, margin: float = 3.0,
                 kind: str = "tap", top_through: bool = False, teardrop: float | None = None):
    """A mounting plate for a catalog servo: just big enough for the tab screws (margin beyond the tab span and the
    wall the screw holes need) and its window and tab holes (iface.servo_mount, which registers the fastener sites).
    Same frame and top_through meaning as iface.servo_mount. Returns (plate to add, cutter to subtract)."""
    d = iface.servo_dims(servo)
    sp = iface.screw_spec(d["screw"])
    hole_r = max(sp.get("insert_hole") or 0.0, sp["tap"], sp["clearance"]) / 2
    wall = max(margin, iface.MIN_WALL_AROUND_HOLE + hole_r)
    px = max(d["span"], d["hx"] + 2 * wall)
    py = d["W"] + 2 * max(margin, 2 * MIN_WALL)
    if d["hy"]:
        py = max(py, d["hy"] + 2 * wall)
    z0 = -plate_t if not top_through else 0.0
    plate = loc * (Pos(0, 0, z0) * Box(px, py, plate_t, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    cut = iface.servo_mount(ctx, servo, loc, group, plate_t, kind=kind, top_through=top_through, teardrop=teardrop)
    return plate, cut


# ---------------------------------------------------------------- cable saddle / strain relief
def cable_saddle(cable_d: float, length: float | None = None, base_t: float = 2.0, tie: str = TIE):
    """Tie-down saddle for a lead or bundle on a face at z = 0 (+Z up): a pad with a round groove the cable lies in
    (along X, its axis on the pad top) and a tunnel under the groove for a catalog cable tie, which comes up both sides
    and closes over the cable, so a tug on the lead loads the saddle, not the solder joints.
    Returns (pad to add, cutter: groove + tie tunnel + risers). Prints without support: the groove faces up and the
    tunnel has a 45 deg peaked roof."""
    e = catalog.get(tie)
    tw = catalog.num(e, "width") + 2 * TIE_CLEAR
    tt = catalog.num(e, "thickness") + 2 * TIE_CLEAR
    r = cable_d / 2 + 0.2
    L = length or tw + 4 * MIN_WALL
    W = 2 * r + 2 * (tt + MIN_WALL)
    zc = base_t + tt + tw / 2 + MIN_WALL + r              # cable axis = pad top
    pad = Pos(0, 0, -0.01) * Box(L, W, zc + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    groove = Pos(-L / 2 - 1, 0, zc) * (Plane.YZ * Cylinder(r, L + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    roof = make_face(Polyline((-tw / 2, 0), (tw / 2, 0), (tw / 2, tt), (0, tt + tw / 2), (-tw / 2, tt), close=True))
    tunnel = Pos(0, -W / 2 - 1, base_t) * (Plane.XZ.rotated((0, 0, 0)) * extrude(roof, -(W + 2)))
    riser = Box(tw, tt, zc, align=(Align.CENTER, Align.CENTER, Align.MIN))
    yr = r + tt / 2 + 0.3
    risers = Pos(0, -yr, base_t) * riser + Pos(0, yr, base_t) * riser
    return pad, groove + tunnel + risers


# ---------------------------------------------------------------- grip pad
def grip_pad(w: float, h: float, kind: str = "serrations", pitch: float = 1.6, insert_t: float = 2.0, lip: float = 1.0):
    """Gripper jaw face in the XY plane at z = 0, facing +Z. kind="serrations": 90 deg ridges across Y every `pitch`
    (pitch / 2 high: a 90 deg V, 45 deg flanks, prints facing up or standing), returned as material to add;
    kind="tpu_pocket": a pocket for a TPU pad printed separately (insert_t deep, a dovetail lip of `lip` mm under the
    rim holds it), returned as a cutter. Returns (add, cut); one of them is None."""
    if kind == "serrations":
        if pitch < 2 * 0.4 * 2:
            raise ValueError(f"serration pitch {pitch} mm is below two nozzle widths per flank")
        depth = pitch / 2
        n = int(h // pitch)
        if n < 2:
            raise ValueError("grip pad too short for two serrations")
        y0 = -n * pitch / 2
        pts = [(y0, 0)]
        for i in range(n):
            pts += [(y0 + (i + 0.5) * pitch, depth), (y0 + (i + 1) * pitch, 0)]
        pts = [(y0, -0.5)] + pts + [(-y0, -0.5)]               # 0.5 mm root below z = 0 fuses with the jaw
        prof = make_face(Polyline(*pts, close=True))
        return Plane.YZ * extrude(prof, w / 2, both=True), None
    if kind == "tpu_pocket":
        if insert_t < 1.2:
            raise ValueError("TPU insert thinner than 1.2 mm tears out")
        inner = Pos(0, 0, -insert_t) * Box(w - 2 * lip, h - 2 * lip, insert_t + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # 45 deg dovetail: the pocket widens by `lip` from its mouth down to the floor (prints as a 45 deg roof)
        dove = Pos(0, 0, -insert_t) * extrude(Rectangle(w, h), amount=lip, taper=45)
        return None, inner + dove
    raise ValueError("grip_pad kind is 'serrations' or 'tpu_pocket'")
