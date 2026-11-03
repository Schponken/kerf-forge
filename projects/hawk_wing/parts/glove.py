"""Glove: the fixed centre wing |y| <= 149.5 (DESIGN.md "Glove"). Modelled solid: the slicer makes the closed box
(3 walls, 10 % infill; the mass check counts shell + infill), so no cavity fights the inserts and screw bores. The
contract's ribs (fuselage sides |y| ~34, round the pod / cap screws) are slicer 100 % infill modifier blocks there
(not yet in project.yaml `modifiers:`)."""
from build123d import *
import importlib.util, pathlib
from kerf import aero, iface, features

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

PAD_X0, PAD_X1, PAD_INSET = 156.0, 262.0, 38.0   # pod footprint x bounds and inward offset from pivot; hull clips x1
INSERT_DEPTH = 8.0            # M3 heat-set (5.7 long, hole 6.7 deep + 0.8 floor = 7.5)
SERVO_LEAD_D, AIL_LEAD_D, VTX_HOLE_D = 9.0, 5.0, 16.0   # 16: the 11 x 11 antenna proxy (diagonal 15.6; contract said 14); 9: a 3-pin servo plug (8 x 2.5) passes; 5: the aileron lead
SERVO_LEAD_XY = (170.0, 30.0)    # x and inward offset from pivot: stays clear of the pod screw as the glove span changes
AIL_EXIT_XY = (190.0, 24.0)       # aileron lead leaves the underside here (clear of the glove screw (200, 18))


def build(ctx):
    p = ctx.p
    pf = L.planform(p)
    pad_y0 = p.pivot_y - PAD_INSET
    body = aero.wing_solid(pf, -p.pivot_y + 0.5, p.pivot_y - 0.5, stations=3)
    env = body                                     # untouched airfoil: probes + pad hull
    cache = {}

    def zr(x, y):                                  # (lower, upper) surface z of the airfoil at (x, y)
        k = (round(x, 2), round(y, 2))
        if k not in cache:
            bb = (env & (Pos(x, y, 0) * Box(0.02, 0.02, 80))).bounding_box()
            cache[k] = (bb.min.Z, bb.max.Z)
        return cache[k]

    def mid(x, y):
        a, b = zr(x, y)
        return (a + b) / 2

    # ---- pod pads: flat underside at POD_PAD_Z (the pod bolts flat to it)
    zp = L.POD_PAD_Z
    for s in (1, -1):
        y0, y1 = sorted((s * pad_y0, s * p.pivot_y))
        region = Pos((PAD_X0 + PAD_X1) / 2, (y0 + y1) / 2, 0) * Box(PAD_X1 - PAD_X0, y1 - y0, 60)
        low = Pos((PAD_X0 + PAD_X1) / 2, (y0 + y1) / 2, zp - 20) * Box(PAD_X1 - PAD_X0, y1 - y0, 40)  # z -43..-3
        # why: aft the airfoil's lower skin is above z -3: fill down to the flat (union of the airfoil shifted down
        # in 1 mm steps, clipped to the airfoil's own upper surface and the pad box)
        fill = None
        for k in range(0, 6):
            piece = (Pos(0, 0, -k) * env) & region & (Pos(0, 0, zp / 2 + 10) * Box(400, 400, 20 - zp))
            fill = piece if fill is None else fill + piece
        body += ctx.add(fill, why="pod pad: fills the aft lower skin down to the flat z -3 the pod roof bolts to", kind="pad")
        # why: forward the lower skin dips below z -3: trim it flat so the pod sits flush
        body -= ctx.cut(low, why="pod pad: trims the forward lower skin flat at z -3 over the pod footprint", kind="pad")
        # why: the hub's elbow disc turns in this round notch (r 25 = disc 24 + 1 mm running clearance), full height
        body -= ctx.cut(Pos(p.pivot_x, s * p.pivot_y, 0) * Cylinder(L.NOTCH_R, 80),
                        why="pivot notch round the pin: the hub's elbow disc turns inside it over the 0..65 deg sweep", kind="notch")

        # pod screws: heat-set inserts from below (the pod's screws come up into them)
        pts = [(x, -y) for x, y in L.pod_screw_xy(p, s)]    # loc is flipped about X: local y = -world y
        body -= ctx.cut(iface.bolt_pattern(ctx, f"pod_{'r' if s > 0 else 'l'}", "M3", pts,
                                           Location((0, 0, zp), (180, 0, 0)), kind="heatset", depth=INSERT_DEPTH, teardrop="auto"),
                        why="2 M3 heat-set inserts from below: the pod's front flange screws bolt up into them", kind="insert")
        # cap screws: clearance through the glove from the cap above down into the pod's inserts
        # plain holes, no fastener site: the cap's counterbore carries the whole grip (cap + glove) to the pod's
        # insert, and the fastener check pairs one clearance site with one receiver
        for x, y in L.cap_screw_xy(p, s):
            top = zr(x, y)[1]
            body -= ctx.cut(Pos(x, y, zp - 1.0) * Cylinder(1.7, top - zp + 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                            why="cap screw passes through the glove into the pod roof insert (carries the pin's upper reaction)",
                            kind="screw hole")

        # servo lead: from the pod pad up into the glove, inboard to the fuselage (plug passes: 9 mm)
        lx, ly = SERVO_LEAD_XY[0], s * (p.pivot_y - SERVO_LEAD_XY[1])
        ex, ey = 165.0, s * 26.0
        pts3 = [(lx, ly, zp - 4), (lx, ly, zp + 1), (lx - 2, s * 100.0, mid(lx - 2, s * 100.0)),
                (ex + 2, s * 60.0, mid(ex + 2, s * 60.0)), (ex, ey, mid(ex, ey)), (ex, ey, zr(ex, ey)[0] - 4)]
        body -= ctx.cut(features.channel(pts3, SERVO_LEAD_D),
                        why="sweep-servo lead (with its plug) from the pod pad inboard to the fuselage", kind="lead channel")

        # aileron lead: from the top skin inside the cap's footprint, forward off the thin aft skin, inboard to the fuselage
        ax, ay = p.pivot_x - 6.0, s * (p.pivot_y - 20.0)
        ail = [(ax, ay, zr(ax, ay)[1] + 3), (ax - 8, ay + s * -4, 0.5), (205.0, s * 100.0, mid(205.0, s * 100.0)),
               (200.0, s * 60.0, mid(200.0, s * 60.0)), (AIL_EXIT_XY[0] + 6, s * 32.0, mid(AIL_EXIT_XY[0] + 6, s * 32.0)),
               (AIL_EXIT_XY[0], s * AIL_EXIT_XY[1], zr(AIL_EXIT_XY[0], AIL_EXIT_XY[1])[0] - 4)]
        body -= ctx.cut(features.channel(ail, AIL_LEAD_D),
                        why="aileron lead from the cap's plug inboard through the glove to the fuselage", kind="lead channel")

    # ---- fuselage screws: counterbored from the top into the saddle rim inserts
    for x, y in L.GLOVE_SCREWS:
        zs = [zr(x + dx, y)[1] for dx in (-4, 0, 4)]
        top, bot = max(zs), zr(x, y)[0]
        body -= ctx.cut(iface.bolt_pattern(ctx, "glove", "M3", [(x, y)], Location((0, 0, top)), kind="counterbore",
                                           depth=top - bot),
                        why="M3 from the top into the fuselage saddle-rim insert (holds the glove down)", kind="screw hole")

    # ---- GPS pocket under the top skin, open from below (board installed before the glove goes on)
    gps = ctx.cat.get("drone.gps.m9n_5883")
    gl, gw, gh = (ctx.cat.num(gps, k) for k in ("length", "width", "height"))
    g = L.gps_loc(p)
    ztop = g.position.Z + gh + 0.5
    pocket = Pos(g.position.X, g.position.Y, (ztop - 15) / 2 + 0) * Box(gl + 0.5, gw + 0.5, ztop + 15)
    body -= ctx.cut(pocket,
                    why="GPS pocket (board + 0.5 mm) under the top skin, open below so the board is fitted before the glove",
                    kind="pocket")
    # ---- VTX antenna through the trailing-edge skin
    body -= ctx.cut(Pos(L.VTX_X, 0, 0) * Cylinder(VTX_HOLE_D / 2, 60),
                    why="VTX antenna (MMCX lollipop) stands up through the glove here", kind="hole")

    # ---- the pinion's two inboard horn screws sit under the glove (heads reach z -2.5): a key hole straight over each
    for s in (1, -1):
        for hx, hy in iface.horn_holes(L.SWEEP_HORN):
            if hy < 0:      # inboard of the root face: under the glove
                body -= ctx.cut(Pos(p.pinion_x + hx, s * (p.pivot_y + hy), 0) * Cylinder(3.0, 60),
                                why="hex-key access + head relief for the pinion's horn screw, which sits under the glove", kind="key hole")

    pk = pocket.bounding_box()
    body, left = features.fillet_inside(ctx, body, 1.0, keep=lambda at: (
        "GPS board's square edges sit in the pocket" if pk.min.X - 1 <= at[0] <= pk.max.X + 1 and abs(at[1]) <= pk.max.Y + 1 and at[2] > -14
        else "pad step tapers to nothing (<= 1.7 mm): the pod's flat flange covers it" if abs(at[2] - zp) < 0.1 and abs(abs(at[1]) - pad_y0) < 0.1
        else "the pod flange's square front edge sits against the step" if abs(at[2] - zp) < 0.1 and abs(at[0] - PAD_X0) < 0.1
        else None))
    for k in ("base", "pod_r", "pod_l", "cap_r", "cap_l"):
        ctx.rigid(k, Location())
    ctx.rigid("gps", L.gps_loc(p))
    return ctx.finish(body)
