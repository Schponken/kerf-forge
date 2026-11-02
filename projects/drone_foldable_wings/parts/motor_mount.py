"""Motor mount: a 6 mm PETG plate on the fuselage nose face that carries the tractor 2806.5.

Its outline is the nose section (L.section_face at fuse_x0), so it sits flush. The motor (catalog 19 mm bolt circle,
M3) is screwed to the plate first, on the bench, from the plate's AFT face: the heads sit in 3 mm counterbores so the
plate lies flat on the nose (3 mm grip + the motor's 3 mm max thread depth = a stock M3 x 6). The plate then bolts to
the nose with four M3 from its front face into the nose's heat-set inserts, at (+-15, +-15) from the motor axis:
outside the 35 mm bell, so a straight hex key reaches them past the motor. The 8 mm centre hole clears the shaft
clip; the phase leads go through the hole above the motor axis (same hole in the nose plate). PETG for the motor's
heat; printed standing on its aft face (every hole vertical, counterbores open to the bed).
"""
from build123d import *
from kerf import iface

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_fspec = importlib.util.spec_from_file_location("dfw_fwd_fuse", pathlib.Path(__file__).with_name("fwd_fuse.py"))
F = importlib.util.module_from_spec(_fspec); _fspec.loader.exec_module(F)

PLATE_T = 6.0
CB = 3.0          # motor screw counterbore: leaves 3 mm of grip


def build(ctx):
    p = ctx.p
    x0 = p.fuse_x0
    plate = Pos(-PLATE_T, 0, 0) * extrude(L.section_face(p, x0), PLATE_T)     # x0 - 6 .. x0
    plate = chamfer(plate.faces().filter_by(Axis.X).edges(), 0.6)      # edge break round both faces' outlines
    zc = p.motor_z
    # four M3 into the nose inserts, heads on the front face (the same points fwd_fuse cuts its inserts at)
    front = Location(Plane(origin=(x0 - PLATE_T, 0, zc), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    pts = [(sy * F.MOUNT_BOLT, sz * F.MOUNT_BOLT) for sy in (-1, 1) for sz in (-1, 1)]
    plate = plate - iface.bolt_pattern(ctx, "motor_mount", "M3", pts, front, kind="clearance", depth=PLATE_T)
    # motor base pattern: loc on the face away from the motor (aft), heads sunk into it
    aft = Location(Plane(origin=(x0, 0, zc), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    plate = plate - iface.motor_mount(ctx, L.MOTOR, aft, "motor", PLATE_T, kind="counterbore", counterbore_depth=CB)
    # why: the motor's phase leads leave its base and go through here into the bay (same hole in the nose plate)
    plate = plate - Pos(x0, 0, zc + F.LEAD_UP) * Rot(0, 90, 0) * Cylinder(F.LEAD_D / 2, 2 * PLATE_T + 2)
    ctx.rigid("base", Location())
    ctx.rigid("motor", Location(Plane(origin=(x0 - PLATE_T, 0, zc), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    return ctx.finish(plate)
