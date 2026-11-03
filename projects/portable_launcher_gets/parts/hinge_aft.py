"""STUB fold block on the FRONT end of section `sec` = the aft side of joint `jt` (block frame, body x < 0)."""
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
    jt, sec = int(p.jt), int(p.sec)
    s = _box(-60, 0, 10, 16, -12, 18) + _box(-60, 0, -16, -10, -12, 18) + _box(-60, 0, -16, 16, -12, 0)
    t = p.LUG_T
    for sy in (1, -1):
        s += _box(-14, 0, sy * 34, sy * 40, -9, 33)
        for zl, _ in p.LUGS_AFT:
            s += _box(-14, 0, sy * 16, sy * p.pin_off, zl, zl + t) + Pos(0, sy * p.pin_off, zl) * Cylinder(8, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
            s -= iface.pin_hole(ctx, QR, Location((0, sy * p.pin_off, zl + t)), f"fold{jt}_{'pos' if sy > 0 else 'neg'}", t, fit="lock")
    s -= _tnuts(ctx, f"s{sec}_front", [-15, -45], bottom=-30)
    ctx.rigid("section", Location((0, 0, 0)))
    ctx.revolute("fold_neg", Axis((0, -p.pin_off, 0), (0, 0, 1)), range=(-180, 0))
    ctx.revolute("fold_pos", Axis((0, p.pin_off, 0), (0, 0, 1)), range=(0, 180))
    return ctx.finish(s)
