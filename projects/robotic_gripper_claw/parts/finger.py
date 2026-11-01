"""Finger (STUB), used twice: finger_l (drive: bolted to the grip horn) and finger_r (idler: turns on the idler dowel).
Finger frame: origin on the finger's gear axis at the gear's bottom face (= grip horn face height), X toward the pad
(along the claw when closed), Z up along the gear axis (claw Y), Y = -claw Z. finger_l's pad faces -Y, finger_r's +Y."""
from build123d import *
from kerf import drives, iface

HORN = "servo_horns.aluminum_25T"


def build(ctx):
    p = ctx.p
    drive = ctx.id == "finger_l"
    inward = -1.0 if drive else 1.0                 # toward the claw's centre line, in this frame's Y
    g1, g2, info = drives.spur_pair(p.gear_m, int(p.gear_z), int(p.gear_z), p.gear_w)
    gear = Rot(0, 0, -90) * (g1 if drive else g2)   # pair frame X (drive -> idler) = claw +Z = this frame's -Y
    body = gear + Pos(p.finger_len / 2, inward * p.dz_pad / 2, p.gear_w / 2) * Box(p.finger_len, 8.0, p.gear_w)
    if drive:
        body -= iface.horn_mount(ctx, HORN, Location((0, 0, p.gear_w)), group="gr_horn", plate_t=p.gear_w, kind="counterbore")
        body += Pos(0, 0, p.gear_w - 6.5) * Cylinder(3.6, 6.5, align=(Align.CENTER, Align.CENTER, Align.MIN))  # plug over the centre-screw recess
        body -= iface.pin_hole(ctx, "motion.pin_3mm", Location((0, 0, p.gear_w)), "gr_top", depth=6.0, fit="free", through=False)
        ctx.rigid("horn_mount", Location((0, 0, 0), (0, 0, 180)))
    else:
        body -= iface.pin_hole(ctx, "motion.pin_3mm", Location((0, 0, p.gear_w)), "gr_idler", depth=p.gear_w, fit="free")
        ctx.rigid("pivot", Location((0, 0, 0), (0, 0, -90)))
    y_mid = p.gear_w / 2
    ctx.rigid("tip", Location((p.finger_len, inward * p.dz_pad, y_mid)))
    ctx.rigid("pad_seat", Location((p.finger_len, inward * (p.dz_pad - p.pad_t), y_mid), (0, 0, 180 if drive else 0)))
    return ctx.finish(body)
