"""STUB bipod leg socket on one side of section 3 (frame: rail bottom centre at the mount)."""
import math
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
    sd = int(p.side)
    s = _box(-30, 30, sd * 10, sd * 16, -12, 18) if sd > 0 else _box(-30, 30, -16, -10, -12, 18)
    s -= _tnuts_one(ctx, sd)
    ctx.rigid("section", Location((0, 0, 0)))
    ctx.rigid("leg", Location((0, sd * p.SOCK_Y, p.sock_z), (180 + sd * p.leg_splay, 0, 0)))
    return ctx.finish(s)


def _tnuts_one(ctx, sd):
    cut = None
    for x in (-15, 15):
        loc = Location((x, sd * 16, 10), (-90 * sd, 0, 0))
        c = iface.bolt_pattern(ctx, "s3_bipod", "M5", [(0, 0)], loc, "clearance", 6)
        cut = c if cut is None else cut + c
    return cut
