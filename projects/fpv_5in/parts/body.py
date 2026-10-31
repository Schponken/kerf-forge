"""Body plate: the centre of the frame. z = 0 bottom (arms clamp underneath), z = body_t top (stack sits on top).

- 4 arms along the diagonals (3 x 5 mm ribs on the top either side of each arm's screws stiffen the plate), each held by two M3 screws from below into nut traps whose hex pockets open on the top,
  and keyed by their two top ridges in 1.7 mm grooves in the underside (side hits go into the groove walls).
- 30.5 mm stack on M3 x 30 from the top into nut traps whose pockets open underneath, inside the arm-free centre.
- 4 posts of the top plate land on the top face; M3 x 8 from below (counterbored) into heat-set inserts in the posts.
- Camera cage at the front nose: 4 mm cheeks reaching 3 mm past the lens at any tilt, gusseted to the nose; the
  camera pivots on its two side M2 screws (teardrop holes, cheeks print upright).
"""
from build123d import *
from kerf import iface, features as F

POSTS = [(33.0, 8), (33.0, -8), (-33.0, 8), (-33.0, -8)]
RIDGE_W, RIDGE_H, RIDGE_R1 = 4.5, 1.5, 58.0     # must match parts/arm.py
CHEEK_T, CHEEK_Y0 = 4.0, 10.0                    # cheek thickness; inner face (19 mm camera + 0.5 mm each side)
CAGE_X1 = 68.0
CAM_RECESS = 1.0                                  # M2 button-head recess (ISO 7380 M2 head 3.5 mm; 4.4 mm bore)
RIB_R0, RIB_R1, RIB_Y, RIB_W, RIB_H = 34.0, 64.0, 6.0, 3.0, 5.0   # top ribs: start/end radius, offset, width, height


def _outline(h, z0, hh):
    b = Pos(0, 0, z0) * Box(2 * h, 2 * h, hh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return b.fillet(7.5, b.edges().filter_by(Axis.Z))                                   # lens front reaches x = cam_x + 16.8 = 64.8 at 34 deg tilt


def build(ctx):
    p = ctx.p
    t, h = p.body_t, p.body_half
    plate = Box(2 * h, 2 * h, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    plate = plate.fillet(8.0, plate.edges().filter_by(Axis.Z))
    nose_w = 2 * (CHEEK_Y0 + CHEEK_T + 3.0)       # room for the cheek gussets
    nose = Pos(h - 2, 0, 0) * Box(CAGE_X1 - (h - 2), nose_w, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    body = plate + nose
    # cheeks: side profile x 41..68, top 6 mm above the pivot, sloping down to 18 mm at the front (prop-disc clearance)
    ztop = p.cam_z + 6
    prof = Polyline((41, t), (41, ztop), (56, ztop), (CAGE_X1, 18), (CAGE_X1, t), close=True)
    for sy in (1, -1):
        y0 = sy * (CHEEK_Y0 + CHEEK_T / 2)
        body += Pos(0, y0 + CHEEK_T / 2, 0) * extrude(Plane.XZ * make_face(prof), amount=CHEEK_T)
        # outside gusset along the cheek root (3 mm out on the nose plate, 6 mm up the cheek), x 42..58
        body += Pos(50, 0, 0) * F.gusset((0, sy * (CHEEK_Y0 + CHEEK_T), t), (0, sy, 0), (0, 0, 1), 3.0, 6.0, t=16.0)
    cam_d = iface.screw_spec("M2")["clearance"]
    body -= Location((p.cam_x, CHEEK_Y0 + CHEEK_T + 1, p.cam_z), (-90, 0, 0)) * \
        F.teardrop_hole(cam_d, 2 * (CHEEK_Y0 + CHEEK_T) + 2, up_deg=270)
    for sy in (1, -1):   # 1 mm head recess on each cheek's outside: grip 3.5 mm, so M2 x 6 puts 2.5 mm into the camera
        body -= Location((p.cam_x, sy * (CHEEK_Y0 + CHEEK_T - CAM_RECESS / 2), p.cam_z), (90, 0, 0)) * \
            Cylinder(4.4 / 2, CAM_RECESS + 0.02)
    for k in range(4):
        th = 45 + 90 * k
        loc = Rot(0, 0, th) * Location((0, 0, 0), (180, 0, 0))
        body -= iface.bolt_pattern(ctx, f"arm_{k + 1}", "M3", [(p.arm_hole_1, 0), (p.arm_hole_2, 0)], loc, "nut_trap", depth=t)
        for sy in (1, -1):                       # key grooves for the arm ridges, 0.2 mm clearance all round
            g = Pos(p.arm_r0 - 0.2, sy * (p.arm_w / 2 - RIDGE_W / 2), -1) * \
                Box(RIDGE_R1 - p.arm_r0 + 0.4 + 10, RIDGE_W + 0.4, RIDGE_H + 0.2 + 1, align=(Align.MIN, Align.CENTER, Align.MIN))
            body -= Rot(0, 0, th) * g
        for sy in (1, -1):                       # stiffening ribs on the top either side of the arm screws
            rib = Pos(RIB_R0, sy * RIB_Y, t) * Box(RIB_R1 - RIB_R0, RIB_W, RIB_H, align=(Align.MIN, Align.CENTER, Align.MIN))
            body += (Rot(0, 0, th) * rib) & _outline(h - 0.5, t, RIB_H)   # clipped inside the plate edge
        ctx.rigid(f"arm_{k + 1}", Location((0, 0, 0), (0, 0, th)))
    body -= iface.stack_mount(ctx, "drone.stacks.fc_30_5", Location((0, 0, t)), "stack", depth=t, kind="nut_trap")
    body -= iface.bolt_pattern(ctx, "posts", "M3", [(x, -y) for x, y in POSTS], Location((0, 0, 0), (180, 0, 0)),
                               "counterbore", depth=t)
    ctx.rigid("stack", Location((0, 0, t)))
    ctx.rigid("top", Location((0, 0, t)))
    ctx.revolute("cam_tilt", Axis((p.cam_x, 0, p.cam_z), (0, -1, 0)), range=(0, 40))
    return ctx.finish(body, color="#2a2d31")
