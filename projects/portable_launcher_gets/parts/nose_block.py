"""STUB nose block on section 4's front end (block frame, body x < 0, pulley ahead)."""
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
    s = _box(-60, 0, 10, 16, -12, 18) + _box(-60, 0, -16, -10, -12, 18) + _box(-60, 0, -16, 16, -12, 0) + _box(0, 8, -16, 16, -12, 40)
    for sy in (1, -1):
        s += _box(0, p.pulley_dx + 14, sy * 38, sy * 46, p.Z_MID - 14, p.Z_MID + 14) + _box(0, 8, sy * 16, sy * 46, -12, 18)
    s -= _tnuts(ctx, "s4_front", [-15, -45], bottom=-30)
    ctx.rigid("section", Location((0, 0, 0)))
    ctx.rigid("axle", Location((p.pulley_dx, 0, p.Z_MID), (-90, 0, 0)))
    ctx.rigid("pulley", Location((p.pulley_dx, 0, p.Z_MID), (-90, 0, 0)))
    ctx.rigid("strand_exit", Location((p.pulley_dx - 35, p.STRAND_Y[3], p.Z_BOT)))
    ctx.rigid("strand_exit_out", Location((p.pulley_dx - 35, p.STRAND_Y[5], p.Z_BOT)))
    return ctx.finish(s)
