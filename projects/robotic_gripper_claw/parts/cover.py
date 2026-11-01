"""Cover (STUB): plate over the gears, top support of both gear axes, screwed to the palm's two posts. Claw frame."""
from build123d import *
from kerf import iface

POST_X = (15.5, 23.5)


def up(x, y, z):
    return Plane((x, y, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0)).location


def build(ctx):
    p = ctx.p
    x0, x1 = POST_X[0], p.x_g + 6.0
    z0, z1 = p.z_d - 6.0, p.z_i + 6.0
    body = Pos((x0 + x1) / 2, (p.y_c0 + p.y_c1) / 2, (z0 + z1) / 2) * Box(x1 - x0, p.cover_t, z1 - z0)
    body -= iface.pin_hole(ctx, "motion.pin_3mm", up(p.x_g, p.y_c1, p.z_d), "gr_top", depth=p.cover_t, fit="press")
    body -= iface.pin_hole(ctx, "motion.pin_3mm", up(p.x_g, p.y_c1, p.z_i), "gr_idler", depth=p.cover_t, fit="free")
    for z in (p.z_d - 2.0, p.z_i + 2.0):
        body -= iface.bolt_pattern(ctx, "cover", "M3", [(0, 0)], up(sum(POST_X) / 2, p.y_c1, z), kind="clearance", depth=p.cover_t)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
