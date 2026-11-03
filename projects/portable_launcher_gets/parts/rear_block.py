"""STUB rear block on section 1's rear end (rail frame)."""
from build123d import *
from kerf import iface

QR = "motion.qr_pin_6mm"


def _box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


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


def build(ctx):
    p = ctx.p
    ctx.stub("contract stub")
    s = _box(-12, 0, -16, 16, -32, 40) + _box(0, 60, 10, 16, -12, 18) + _box(0, 60, -16, -10, -12, 18)
    s += _box(0, 60, -16, 16, -12, 0) + _box(-12, 12, -14, 14, 40, 75)
    s -= _tnuts(ctx, "s1_rear", [15, 45], bottom=30)
    ctx.rigid("pivot", Location((p.pivot_x, 0, p.pivot_z), (90, 0, -90)))
    ctx.rigid("section", Location((0, 0, 0)))
    ctx.revolute("trigger", Axis((0, 0, 60), (0, 1, 0)), range=(-25, 0))
    ctx.linear("sled_travel", Axis((p.X_S0, 0, p.H), (1, 0, 0)), range=(0, p.TRAVEL_MAX))
    return ctx.finish(s)
