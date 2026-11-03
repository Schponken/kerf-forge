"""Fold block on the REAR end of section `sec` = the forward side of joint `jt` (block frame, body x > 0).

Load path (joint bending +-40 N m, rail ends butt on one face, the two pins 44 mm out take ~500 N each in +-x):
pin -> lug disc (r 8, layers in the lug plane) -> arm -> outboard web (|y| 34..40, a plate in the x-z plane that is tall
at the joint and tapers away) -> bottom flange (z -9..0, |y| <= 40) -> cheeks (|y| 10..16, 6 mm under the T-nut screw
heads) and the bottom plate -> 5 tee-nut screws into the rail. Everything sits in x <= 0 except the lug discs, and keeps
>= 8.5 mm from the other block's pin axes in the z layers where the other block has lugs, so it swings 180 deg clear.
"""
from build123d import *
from kerf import features, iface

QR = "motion.qr_pin_6mm"
S = 1                         # body side: -1 aft (x < 0), +1 forward
REACH = 60.0                  # block length along the rail (T-nuts at 15, 30, 45 from the joint plane)
WEB_IN, WEB_OUT = 34.0, 40.0  # outboard web |y|: 1 mm outside the wheel envelope (|y| <= 33)
HOLD = 8.5                    # radial clearance round the other block's lugs (lug r 8 + 0.5)


def _box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((S * x0, S * x1))
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, abs(y1 - y0), abs(z1 - z0))


def _tnuts(ctx, group, xs, z=10.0, bottom=None, grip=6.0, y_face=10.0):
    """M5 tee-nut screws: side screws at xs on both rail faces (heads out), optional bottom screw at x=bottom."""
    cut = None
    for x in xs:
        for sy in (1, -1):
            loc = Location((x, sy * (y_face + grip), z), (-90 * sy, 0, 0))
            c = iface.bolt_pattern(ctx, group, "M5", [(0, 0)], loc, "clearance", grip)
            cut = c if cut is None else cut + c
    if bottom is not None:
        loc = Location((bottom, 0, -grip), (180, 0, 0))
        cut += iface.bolt_pattern(ctx, group, "M5", [(0, 0)], loc, "clearance", grip)
    return cut


def _web(sy, top_z):
    """Plate in the x-z plane at |y| 34..40: tall at the lugs (arm end x=15), sloping down along the rail."""
    pts = [(9, -9), (REACH, -9), (REACH, 14), (24, top_z), (9, top_z)]
    sk = Plane.XZ * Polygon(*[(S * x, z) for x, z in pts], align=None)
    w = extrude(sk, amount=WEB_OUT - WEB_IN)          # Plane.XZ normal is -y: runs y 0 -> -6
    return Pos(0, (-WEB_IN if sy > 0 else WEB_OUT), 0) * w


def build(ctx):
    p = ctx.p
    jt, sec = int(p.jt), int(p.sec)
    t, off = p.LUG_T, p.pin_off
    lugs = p.LUGS_AFT if S < 0 else p.LUGS_FWD
    top = lugs[-1][1]
    s = _box(0, REACH, 10, 16, -9, 20) + _box(0, REACH, -16, -10, -9, 20)      # why: cheeks on the lower side faces carry the T-nut screws
    s += _box(0, 9, -33, 33, -9, 0) + _box(9, REACH, -WEB_OUT, WEB_OUT, -9, 0)  # why: flange ties cheeks to webs; x<9 stops 8.5 mm clear of the other block's lug discs
    for sy in (1, -1):
        s += _web(sy, top)                                                       # why: outboard web carries lug force to the flange, outside the sled's wheel envelope
        for zl, zt in lugs:
            s += _box(0, 15, sy * WEB_IN, sy * off, zl, zt)                      # why: arm from web to lug
            s += Pos(0, sy * off, zl) * Cylinder(8, t, align=(Align.CENTER, Align.CENTER, Align.MIN))  # why: lug r 8 round the pin
            s -= iface.pin_hole(ctx, QR, Location((0, sy * off, zt)), f"fold{jt}_{'pos' if sy > 0 else 'neg'}", t, fit="lock")
    s -= _tnuts(ctx, f"s{sec}_rear", [15, 45], bottom=30)
    ctx.rigid("section", Location((0, 0, 0)))
    ctx.rigid("pin_neg", Location((0, -off, 0)))
    ctx.rigid("pin_pos", Location((0, off, 0)))
    s, left = features.fillet_inside(ctx, s, 2.0)
    return ctx.finish(s)
