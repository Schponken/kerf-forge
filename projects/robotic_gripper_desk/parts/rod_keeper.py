"""STUB rod keeper: small plate on the outer face of the gripper's -Z cheek over both guide-rod ends (1 x M3 into a
heat-set insert). Frame: origin on the cheek face between the rods, +Z out of the cheek."""
from build123d import *
from kerf import iface


def build(ctx):
    p = ctx.p
    body = Pos(0, 0, 2) * Box(10, 2 * p.rod_y + 8, 4)
    body -= iface.bolt_pattern(ctx, "keeper", "M3", [(0, 0)], Location((0, 0, 4)), "clearance", 4)
    ctx.rigid("origin", Location())
    return ctx.finish(body)
