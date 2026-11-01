"""STUB jaw (one file, two parts: jaw_r side +1, jaw_l side -1 = the same part turned 180 deg about X).
Frame J: X forward, Y toward this jaw's rack, Z = opening direction; origin at closed on the pad face plane, on the
pinion axis line (y = 0), at the carriage's back face (gripper x = x_c0)."""
import math

from build123d import *
from kerf import drives, iface

ROD = "motion.pin_3mm"


def build(ctx):
    p = ctx.p
    side = 1 if p.side > 0 else -1
    h = p.rod_y + 4.5
    body = Pos(p.carr_x / 2, 0, p.carr_len / 2) * Box(p.carr_x, 2 * h, p.carr_len)
    body += Pos(p.carr_x + p.finger_len / 2, 0, 4) * Box(p.finger_len + 0.02, 16, 8)
    _, rack, ri = drives.rack_pinion(p.gear_m, int(p.pinion_z), int(p.rack_n), p.gear_b)
    k = round(p.s_max / 2 / p.pitch)
    z0 = -p.z_in - k * p.pitch                     # rack origin (a tooth gap): over the mesh point at closed, mod pitch
    x0 = -(p.gear_b + p.slab_gap)
    body += Pos(x0, 0, z0) * Rot(0, 90, 0) * rack
    zf = z0 - (p.rack_n * p.pitch) / 2             # far end of the rack (toward and past the centre)
    yb = ri.rack_y[1]
    body += Pos(x0 / 2, yb + 4, (zf + p.carr_len) / 2) * Box(-x0 + 0.02, 8.02, p.carr_len - zf)
    for y in (p.rod_y, -p.rod_y):
        g = ("rod_top" if y > 0 else "rod_bot") if side > 0 else ("rod_bot" if y > 0 else "rod_top")
        body -= iface.pin_hole(ctx, ROD, Location((p.carr_x / 2, y, p.carr_len)), g, depth=p.carr_len, fit="free")
    ctx.rigid("mount", Location() if side > 0 else Location((0, 0, 0), (180, 0, 0)))
    ctx.rigid("pad", Location((p.carr_x + p.finger_len - p.pad_len / 2, 0, 0)))
    return ctx.finish(body)
