"""STUB strand anchor (frame: on its notch pin axis at the rail bottom centre line)."""
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
    s = _box(-25, 25, -36, 36, p.Z_BOT - 8, -12)
    ctx.rigid("rack", Location((0, 0, 0)))
    ctx.rigid("hook_mid", Location((30, p.STRAND_Y[3], p.Z_BOT)))
    ctx.rigid("hook_out", Location((30, p.STRAND_Y[5], p.Z_BOT)))
    return ctx.finish(s)
