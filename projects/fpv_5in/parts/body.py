"""Body plate: the centre of the frame. z = 0 bottom (arms clamp underneath), z = body_t top (stack sits on top).

- 4 arms along the diagonals, each held by two M3 screws from below into nut traps whose hex pockets open on the top.
- 30.5 mm stack on M3 x 30 screws from the top into nut traps whose pockets open on the bottom (inside the arm-free
  centre, so the nuts can be fitted with the arms on).
- 4 posts of the top plate land on the top face; M3 screws from below (counterbored) into heat-set inserts in the posts.
- Camera cheeks at the front nose: the 19 mm camera pivots on its two side M2 screws (teardrop holes, print upright).
"""
from build123d import *
from kerf import iface, features as F

POSTS = [(30, 14), (30, -14), (-30, 14), (-30, -14)]


def build(ctx):
    p = ctx.p
    t, h = p.body_t, p.body_half
    plate = Box(2 * h, 2 * h, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    plate = plate.fillet(8.0, plate.edges().filter_by(Axis.Z))
    nose = Pos(h - 2, 0, 0) * Box(p.cam_x + 7 - (h - 2), 26, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    body = plate + nose
    # camera cheeks: 3 mm walls at |y| 10..13 (camera is 19 wide: 0.5 mm side gap each side)
    for sy in (1, -1):
        cheek = Pos(p.cam_x, sy * 11.5, t) * Box(14, 3, p.cam_z + 6 - t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body += cheek
    cam_d = iface.screw_spec("M2")["clearance"]
    body -= Location((p.cam_x, 14, p.cam_z), (-90, 0, 0)) * F.teardrop_hole(cam_d, 28, up_deg=270)
    # arms: nut traps from the underside (pockets open on top)
    for k in range(4):
        th = 45 + 90 * k
        loc = Rot(0, 0, th) * Location((0, 0, 0), (180, 0, 0))
        body -= iface.bolt_pattern(ctx, f"arm_{k + 1}", "M3", [(p.arm_hole_1, 0), (p.arm_hole_2, 0)], loc, "nut_trap", depth=t)
        ctx.rigid(f"arm_{k + 1}", Location((0, 0, 0), (0, 0, th)))
    # stack: nut traps from the top (pockets open underneath)
    body -= iface.stack_mount(ctx, "drone.stacks.fc_30_5", Location((0, 0, t)), "stack", depth=t, kind="nut_trap")
    # top-plate posts: counterbored from below into heat-set inserts in the posts
    body -= iface.bolt_pattern(ctx, "posts", "M3", [(x, -y) for x, y in POSTS], Location((0, 0, 0), (180, 0, 0)),
                               "counterbore", depth=t)
    ctx.rigid("stack", Location((0, 0, t)))
    ctx.rigid("top", Location((0, 0, t)))
    ctx.revolute("cam_tilt", Axis((p.cam_x, 0, p.cam_z), (0, -1, 0)), range=(0, 40))
    return ctx.finish(body, color="#2a2d31")
