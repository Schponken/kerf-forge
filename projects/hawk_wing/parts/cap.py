"""EXPERIMENTAL raised fairing candidate for the deep hub; pending integration and flight checks.

Pivot cap (cap_r / cap_l): holds the pin's top and closes the stack; 2 M3 from its top, through the glove, into the pod.

Load path (DESIGN.md "Load -> section"): the 5.5 N m root moment is a 196 N couple on the pin; the top end goes into this
cap's boss (r 7.5, blind slip bore 8 deep) and out through two 9 mm wide, 12 mm deep spines (underside following the
glove's top skin) to the two screw pads 31 mm away. Everything has ONE flat top (z 16.5), so the cap prints upside down on
that face with no overhang: pads, spines, the roof of the hollow fairing and the boss all hang from it.
The fairing is hollow (2 mm walls, open underneath): it holds the aileron plug (15 x 8 x 4) where the hub's lead rises
from its top (r 14.3 round the pin, swinging through 65 deg) and meets the glove-side lead that comes up at (pivot_x - 6,
pivot_y - 20). Over the hub (inside the glove's r 25 notch) the underside is z 6.5, 0.5 above the hub's top and the boss's
bearings (a 0.5 mm ring touches only the top bearing's inner race); elsewhere it sits on the glove's top skin.
Field-removable: unscrew the two M3 (2.5 mm hex), lift the cap, unplug, lift the panel off the pin.
"""
from build123d import *
import math
import importlib.util, pathlib
from kerf import aero, iface, features

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

TOP_Z = 34.5             # pin top 14.5 + 2 mm roof; also the print bed face (printed upside down)
FAIR_UNDER_Z = 24.5      # deep hub torque box top + 0.5 mm running clearance
UNDER_Z = L.CAP_Z0       # underside over the hub (6.5)
WALL = 2.0
PAD_R = 6.0              # M3 head counterbore + 2.4 mm wall
SPINE_W = 9.0
BOSS_R = 7.5
FAIR_R = 21.0            # fairing round the pin: covers the lead arc (r 14.3) and the plug beside it, inside the glove notch
LOBE_R = 7.0             # lobe over the glove-side lead
RING_R = (3.1, 4.2)      # 0.5 mm ring on the underside: only the top bearing's inner race (bore 5, shoulder r ~4.3)


def _lug(a, b, r, z0, z1):
    d = math.dist(a, b)
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return Pos((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z0) * Rot(0, 0, ang) * extrude(SlotCenterToCenter(d, 2 * r), z1 - z0)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    n = "l" if s < 0 else "r"
    c = (p.pivot_x, p.pivot_y)                                   # right-side numbers; mirrored for the left cap
    lobe = (p.pivot_x - 6.0, p.pivot_y - 20.0)                   # glove-side aileron lead (glove.py)
    z0 = 3.0                                                     # just under the glove's top skin (min 2.3 here), above its lower skin

    # solid envelope: fairing hull + spines to the screw pads + pads + pin boss
    outer = extrude(Pos(*c) * Circle(FAIR_R) + Pos(*lobe) * Circle(LOBE_R), TOP_Z - z0)
    body = ctx.add(Pos(0, 0, z0) * outer, why="streamlined fairing hull round the pin and the glove-side lead: room for the aileron plug", kind="fairing")
    for (x, y) in L.cap_screw_xy(p, 1):
        body += ctx.add(_lug((x, y), (c[0] + 0.55 * (x - c[0]) , c[1] + 0.55 * (y - c[1])), SPINE_W / 2, z0, TOP_Z),
                        why="spine from the screw pad to the fairing: carries the pin's 196 N top reaction 31 mm to the screws", kind="spine")
        body += ctx.add(Pos(x, y, z0) * Cylinder(PAD_R, TOP_Z - z0, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                        why="screw pad: M3 counterbore from the top, 6 mm radius = 2.4 mm wall", kind="pad")
    # hollow the fairing from below (open underside, 2 mm walls and roof); the boss + ribs stay
    cav = Pos(0, 0, z0 - 1) * extrude(Pos(*c) * Circle(FAIR_R - WALL) + Pos(*lobe) * Circle(LOBE_R - WALL), TOP_Z - WALL - z0 + 1)
    keep = Pos(c[0], c[1], z0 - 1) * Cylinder(BOSS_R, TOP_Z - z0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for ang in (-90, 90, 0):
        keep += Pos(c[0], c[1], z0 - 1) * Rot(0, 0, ang) * Pos(FAIR_R / 2, 0, 0) * Box(FAIR_R, 2.4, TOP_Z - z0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= ctx.cut(cav - keep, why="hollow fairing (2 mm walls, open underneath, ribs keep the boss tied to the wall): the aileron plug sits in it; "
                    "its opening covers the lead's r 14.3 arc through 65 deg", kind="cavity")
    # underside: over the hub (inside the glove's notch) stay 0.5 mm above the hub top; elsewhere follow the glove's top skin
    glove = aero.wing_solid(L.planform(p), -p.pivot_y + 0.5, p.pivot_y - 0.5, stations=3) - Pos(c[0], c[1], -20) * Cylinder(L.NOTCH_R, 80, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= ctx.cut(glove, why="underside follows the glove's top skin where the cap sits on it", kind="seat")
    body -= ctx.cut(Pos(c[0], c[1], z0 - 20) * Cylinder(L.NOTCH_R, FAIR_UNDER_Z - z0 + 20, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="over the deep torque box the fairing is 0.5 mm clear; the pin boss stays at the original bearing stack", kind="clearance")
    body += ctx.add(Pos(c[0], c[1], UNDER_Z - L.GAP) * (Cylinder(RING_R[1], L.GAP, align=(Align.CENTER, Align.CENTER, Align.MIN))
                                                       - Cylinder(RING_R[0], L.GAP, align=(Align.CENTER, Align.CENTER, Align.MIN))), why="0.5 mm ring (r 3.1..4.2) touching only the top bearing's inner race: the cap's weight never rubs the hub", kind="thrust ring")
    body += ctx.add(Pos(c[0], c[1], UNDER_Z) * Cylinder(BOSS_R, TOP_Z - UNDER_Z, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                    why="boss round the pin's blind bore: 2 mm of roof over the pin top", kind="boss")

    if s < 0:
        body = mirror(body, Plane.XZ)

    body -= iface.pin_hole(ctx, L.PIN, Location((p.pivot_x, s * p.pivot_y, UNDER_Z), (180, 0, 0)), f"pivot_{n}", depth=8.0, fit="free", through=False)
    for (x, y) in L.cap_screw_xy(p, s):
        body -= iface.bolt_pattern(ctx, f"cap_{n}", "M3", [(0, 0)], Location((x, y, TOP_Z)), "counterbore", TOP_Z - L.POD_ROOF_Z)

    body, left = features.fillet_inside(ctx, body, 2.0)
    ctx.rigid("base", Location())
    return ctx.finish(body)
