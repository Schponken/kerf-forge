"""Strand anchor (frame: on its QR pin axis at the rail bottom centre line, z = 0 = rail bottom).

Slides under the anchor rack and is pinned in a notch by a QR pin. Six hook tabs hang from the plate at x = 30 (their
front face is the hook point: the strand loops bear on it, 79 N each, +X); everything is behind x = 30 so the strand
channel in front of the hooks stays open. The strand pull goes tab -> plate -> pin hole (bearing, in-layer) -> rack.
Printed upside down (plate top on the bed): the tabs and the pin boss grow upward with no overhang.
"""
from build123d import *
from kerf import features, iface

QR = "motion.qr_pin_6mm"
GAP = 0.5               # sliding clearance under the rack
TAB_W, TAB_D = 6.0, 12.0   # hook tab: width across the strand (y) and depth along the pull (x); 12 deep keeps the root bending low
X_HOOK = 30.0
X_REAR, HALF_W = -25.0, 32.0
BOSS_X, BOSS_HW = 14.0, 14.0


def _box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def build(ctx):
    p = ctx.p
    cb = iface.screw_spec("M5")["head_h"] + 0.3
    R = cb + p.TNUT_GRIP                                     # rack thickness (same formula as anchor_rack.py)
    pocket = 3.5                                             # rack ball pocket (anchor_rack.py BALL_POCKET_H)
    grip = 25.0                                              # QR pin grip chosen: anchor + gap + rack hole = 25
    z_top = -(R + GAP)
    z_bot = z_top - (grip - (R - pocket) - GAP)              # bottom of the pin boss: the pin head bears here
    z_plate = z_top - 9.2                                    # plate bottom; the hook tabs hang from it

    body = _box(X_REAR, X_HOOK, -HALF_W, HALF_W, z_plate, z_top)
    ctx.add(body, why="plate carrying the six hook tabs' pull across to the pin, 9.2 mm thick, clear of the rack by 0.5", kind="plate")
    boss = _box(X_REAR, BOSS_X, -BOSS_HW, BOSS_HW, z_bot, z_plate + 0.01)
    body += ctx.add(boss, why="pin boss: thickens the stack to the stocked 25 mm QR grip and gives the pin head a flat seat", kind="boss")

    for y in p.STRAND_Y:
        tab = _box(X_HOOK - TAB_D, X_HOOK, y - TAB_W / 2, y + TAB_W / 2, p.Z_BOT - 5.5, z_plate + 0.01)
        tab = chamfer(tab.edges().filter_by(Axis.Y).group_by(Axis.Z)[0].group_by(Axis.X)[0], 1.0) if False else tab
        body += ctx.add(tab, why="open hook tab: a strand-end loop drops over it from below and bears on its front face at x=30", kind="hook")

    # why: QR pin through the anchor, same group as the rack hole of the current notch
    body -= iface.pin_hole(ctx, QR, Location((0, 0, z_bot), (180, 0, 0)), "anchor_notch", z_top - z_bot, fit="lock")

    ctx.rigid("rack", Location((0, 0, 0)))
    ctx.rigid("hook_mid", Location((X_HOOK, p.STRAND_Y[3], p.Z_BOT)))
    ctx.rigid("hook_out", Location((X_HOOK, p.STRAND_Y[5], p.Z_BOT)))
    body, left = features.fillet_inside(ctx, body, 2.0)
    return ctx.finish(body)
