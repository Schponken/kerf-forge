"""Anchor rack under section 2 (frame: its first notch on the rail bottom centre line, z = 0 = rail bottom).

A 20 mm wide bar under the bottom slot with 5 notch holes for the anchor's QR pin. The strand pull (up to 474 N, +X)
enters the rack at the notch pin and runs forward in compression to rack_a's front end, which butts the aft hinge block
(rack_b butts rack_a's rear end): the load never goes through the T-nut screws. The M5 screws only hold the bar up
(counterbored from below so the anchor slides under it with a clear underside).
"""
from build123d import *
from kerf import catalog, features, iface

QR = "motion.qr_pin_6mm"
BALL_POCKET_D, BALL_POCKET_H = 8.0, 3.5     # the pin's balls (6.85 dia) sit in this pocket on the rack's rail side, not in the T-slot throat
FRONT_A = 40.0                              # rack_a's front end: rail x 1440, the aft hinge block's rear face


def _cyl(x, r, z0, z1):
    return Pos(x, 0, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def build(ctx):
    p = ctx.p
    first = int(p.first_notch)
    a = first == 1
    pitch = float(p.notch_pitch)
    sp = iface.screw_spec("M5")
    cb = sp["head_h"] + 0.3
    R = cb + p.TNUT_GRIP                                       # head counterbore + 6 mm grip under it
    x_front = FRONT_A if a else pitch / 2                      # rack_b's front end butts rack_a's rear end exactly
    x_rear = -4.5 * pitch                                      # half a pitch of bar behind the last notch
    W = p.W

    body = Pos((x_front + x_rear) / 2, 0, -R / 2) * Box(x_front - x_rear, W, R)
    ctx.add(body, why="bar under the bottom slot: compression strut from the notch pin to the aft hinge block", kind="bar")

    # why: T-nut screws from below, heads sunk flush so the anchor slides under; groups match sec2's rack sites
    group = "s2_rack_a" if a else "s2_rack_b"
    for x in ((-175, -25) if a else (-200, -50)):
        body -= iface.bolt_pattern(ctx, group, "M5", [(0, 0)], Location((x, 0, -R), (180, 0, 0)), "counterbore", R)

    # why: notch holes. The registered one (param notch) is the QR pin's rack hole; the rest are plain slip holes.
    pd = iface.pin_dims(QR)
    plain_d = pd["d"] + catalog.get("fdm_fits.pin")["free_allowance_d"]
    pin_depth = R - BALL_POCKET_H                              # balls bear on the pocket floor: the pin's grip ends there
    for k in range(5):
        x, num = -k * pitch, first + k
        if num == int(p.notch):
            body -= iface.pin_hole(ctx, QR, Location((x, 0, -R), (180, 0, 0)), "anchor_notch", pin_depth, fit="lock")
        else:
            body -= _cyl(x, plain_d / 2, -R - 1, 0)   # why: plain slip hole, the pin can be moved here
        body -= _cyl(x, BALL_POCKET_D / 2, -BALL_POCKET_H, 1)   # why: ball pocket, the pin's balls must not sit in the T-slot throat
        # why: notch number embossed on both side faces, readable from beside the rail (right way up from either side)
        txt = features.label(str(num), 6.0, 0.8)
        body += Location((x, -W / 2, -R / 2), (90, 0, 0)) * txt   # why: readable notch number, -y side
        body += Location((x, W / 2, -R / 2), (90, 0, 180)) * txt   # why: readable notch number, +y side

    if a:
        ctx.linear("slide", Axis((0, 0, 0), (-1, 0, 0)), range=(0, 9 * pitch))
    ctx.rigid("section", Location((0, 0, 0)))
    body, left = features.fillet_inside(ctx, body, 1.0)
    print("LEFT", left)
    return ctx.finish(body)
