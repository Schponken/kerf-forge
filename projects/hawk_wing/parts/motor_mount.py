"""Motor mount: hollow stand-off from the front bulkhead to a motor plate at nose_x0 - 6, PETG, 4 perimeters, printed per print_rot
with the tube wall vertical.

Load path: thrust 21 N (axial) and motor torque enter the 6 mm plate through 4 M3 (motor screwed on first, on the bench, heads on
the plate's aft face inside the tube), run down the 28 mm tube (closed ring: best for torsion + bending in a crash) into a
42 mm flange with 4 M3 (heads in front, outside the tube, reached by a hex key past it) into the bulkhead inserts. The
tube is hollow: the phase leads and the camera lead pass inside it.
"""
from build123d import *
import importlib.util, pathlib
from kerf import iface
from kerf.features import fillet_inside

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_fspec = importlib.util.spec_from_file_location("hw_fuselage", pathlib.Path(__file__).with_name("fuselage.py"))
F = importlib.util.module_from_spec(_fspec); _fspec.loader.exec_module(F)

TUBE_OD, TUBE_WALL = 28.0, 2.4       # >= 1.6 structural; ID 23.2 clears the screw heads at r 9.5 and the leads
PLATE_T = 6.0                        # 3 mm counterbore + 3 mm motor thread depth (catalog max_screw_depth)
FLANGE_T, FLANGE_W = 4.0, 42.0       # screws at (+-15, +-15) clear the tube by 4 mm for a hex key


def build(ctx):
    p = ctx.p
    zc = p.motor_z
    xp0, xp1 = p.nose_x0 - PLATE_T, p.nose_x0          # plate -181..-175
    xf0 = p.nose_x1 - FLANGE_T                         # flange -124..-120
    plate = Pos((xp0 + xp1) / 2, 0, zc) * Rot(0, 90, 0) * extrude(RectangleRounded(34, 34, 6), PLATE_T / 2, both=True)
    tube = Pos(xp1, 0, zc) * Rot(0, 90, 0) * extrude(Circle(TUBE_OD / 2), xf0 - xp1)
    flange = Pos((xf0 + p.nose_x1) / 2, 0, zc) * Rot(0, 90, 0) * extrude(RectangleRounded(FLANGE_W, FLANGE_W, 6), FLANGE_T / 2, both=True)
    body = plate + ctx.add(tube, why="closed ring stand-off: thrust, torque and crash bending in one tube", kind="tube") \
        + ctx.add(flange, why="flange to the bulkhead: 4 M3 outside the tube", kind="flange")
    body -= ctx.cut(Pos(xp1 - 0.01, 0, zc) * Rot(0, 90, 0) * extrude(Circle(TUBE_OD / 2 - TUBE_WALL), xf0 - xp1 + FLANGE_T + 0.02),
                    why="hollow: phase and camera leads pass inside", kind="wire hole")
    # motor screws from the plate's aft face (inside the tube), motor on the front face
    aft = Location(Plane(origin=(xp1, 0, zc), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    body -= iface.motor_mount(ctx, L.MOTOR, aft, "motor", PLATE_T, kind="counterbore", counterbore_depth=3.0, center_hole=8.0)
    # flange screws, heads on the flange's front face
    fr = Location(Plane(origin=(xf0, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    body -= iface.bolt_pattern(ctx, "motor_mount", "M3", [(dy, -(zc + dz)) for dy, dz in F.FRONT_INSERTS], fr, kind="clearance", depth=FLANGE_T)
    ctx.rigid("base", Location())
    ctx.rigid("motor", Location(Plane(origin=(xp0, 0, zc), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    body, left = fillet_inside(ctx, body, 2.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(body)
