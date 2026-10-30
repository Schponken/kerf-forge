"""Retainer washer under the lower yaw bearing's inner race: an M3 screw into the spindle's heat-set insert pulls it
up, so the turntable cannot lift off. Origin: centre of the top face (touches the inner race); disc hangs below."""
from build123d import *
from kerf import iface

T = 3.0


def build(ctx):
    p = ctx.p
    od = p.brg_d + 4.0                       # 16 mm: on the inner race only (inner race land ~12-16.7 mm)
    s = Pos(0, 0, -T) * Cylinder(od / 2, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    s = chamfer(s.edges().group_by(Axis.Z)[0], 0.5)
    s -= iface.bolt_pattern(ctx, "retainer", "M3", [(0, 0)], Location((0, 0, -T), (180, 0, 0)), kind="clearance", depth=T)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(s)
