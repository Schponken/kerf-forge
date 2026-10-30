"""Moving finger: bolted to the grip servo's horn (4 x M3), swings open about the servo axis away from the fixed jaw.
Frame: horn face on the grip axis; X toward the tip, Z up (home); the fixed jaw is on the -Y side."""
from build123d import *
from kerf import iface

HORN = "servo_horns.aluminum_25T"
T = 6.0


def build(ctx):
    p = ctx.p
    with BuildSketch() as sk:
        Circle(12.0)
        with Locations((p.finger_len / 2, 0)):
            Rectangle(p.finger_len, 8.0)
        with Locations((p.finger_len, 0)):
            Circle(4.0)
    s = extrude(sk.sketch, T)
    s = chamfer(s.edges().group_by(Axis.Z)[-1], 0.6)
    s -= iface.horn_mount(ctx, HORN, Location((0, 0, T)), group="gr_horn", plate_t=T)
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    ctx.rigid("tip", Location((p.finger_len, 0, T / 2)))
    return ctx.finish(s)
