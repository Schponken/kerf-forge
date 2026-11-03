"""STUB rear foot: staked ground plate; the rail pivots on it (rail_angle)."""
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
    s = _box(-90, 70, -60, 60, 0, 8)
    for sy in (1, -1):
        s += _box(-10, 10, sy * 18, sy * 30, 0, p.pivot_h + 8)
    ctx.revolute("rail_pivot", Axis((0, 0, p.pivot_h), (0, -1, 0)), range=(8, 14))
    ctx.rigid("pedal_spot", Location((-350, 160, 0)))
    return ctx.finish(s)
