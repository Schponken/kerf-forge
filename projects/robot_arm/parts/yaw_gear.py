"""Yaw drive gear (36 T, module 1.5) bolted to the yaw servo's aluminium horn; meshes with the 24 T gear under the
turntable at the standard centre distance (kerf.drives.spur_pair). Origin: horn face on the servo axis; z up."""
from build123d import *
from kerf import drives, iface

HORN = "servo_horns.aluminum_25T"


def build(ctx):
    p = ctx.p
    _, g2, info = drives.spur_pair(p.gear_m, int(p.gear_z_tt), int(p.gear_z_yaw), p.gear_w)
    ctx.notes += info.warnings
    g = Rot(0, 0, 180) * g2                  # the pair is built with gear 2 at +X; here it sits at -X of the turntable
    g -= iface.horn_mount(ctx, HORN, Location((0, 0, p.gear_w)), group="yaw_horn", plate_t=p.gear_w)
    ctx.rigid("mount", Location((0, 0, 0)))
    return ctx.finish(g)
