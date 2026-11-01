"""STUB pinion: 20 T module 1.5 spur pinion bolted to the grip servo's aluminium horn (4 x M3).
Frame: origin on the horn face on the servo axis, +Z forward (away from the horn), a tooth on +Y at angle 0."""
from build123d import *
from kerf import drives, iface

HORN = "servo_horns.aluminum_25T"


def build(ctx):
    p = ctx.p
    pin, _, _ = drives.rack_pinion(p.gear_m, int(p.pinion_z), int(p.rack_n), p.gear_b)
    pin -= iface.horn_mount(ctx, HORN, Location((0, 0, p.gear_b)), group="gr_horn", plate_t=p.gear_b)
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    return ctx.finish(pin)
