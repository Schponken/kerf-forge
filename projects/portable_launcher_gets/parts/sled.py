"""STUB sled (frame: rail top centre line under the sled's middle)."""
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
    hl = p.SLED_HALF
    s = _box(-hl, hl, -30, 30, 2, 12) + _box(hl - 14, hl, -34, 34, 2, p.Z_TOP - p.H + 8)
    ctx.rigid("carriage", Location((0, 0, 0)))
    wz = p.WHEEL_Z - p.WHEEL_W / 2 - p.H
    for i, (x, y) in enumerate([(50, p.WHEEL_Y), (-50, p.WHEEL_Y), (50, -p.WHEEL_Y), (-50, -p.WHEEL_Y)], 1):
        ctx.rigid(f"wheel_{i}", Location((x, y, wz)))
    ctx.rigid("tail_pin", Location((-hl + 6, 0, 10), (-90, 0, 0)))
    ctx.rigid("tail_roller", Location((-hl + 6, -2.5, 10), (-90, 0, 0)))
    ctx.rigid("strands", Location((p.TOW_DX, 0, p.Z_TOP - p.H)))
    ctx.rigid("cradle", Location((0, 0, 12)))
    return ctx.finish(s)
