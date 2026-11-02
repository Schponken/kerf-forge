"""Motor mount: a 6 mm PETG plate on the pod's rear face that carries the pusher motor.

The motor (catalog 19 mm bolt circle, M3) is screwed to the plate first, from the plate's front face: the heads sit in
counterbores so the plate lies flat on the pod. The plate then bolts to the pod's tail with four M3 from the aft
face into heat-set inserts in the tail bosses (outside the motor bell, so a hex key reaches them past the motor).
The centre hole clears the motor's shaft clip; the phase leads go through the hole below it into the pod. PETG for the motor's heat; printed flat
on its aft face (holes vertical, counterbores on top).
"""
from build123d import *
from kerf import iface

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_pspec = importlib.util.spec_from_file_location("wing_pod", pathlib.Path(__file__).with_name("pod.py"))
POD = importlib.util.module_from_spec(_pspec); _pspec.loader.exec_module(POD)

PLATE_T = 6.0
CB = 3.0          # motor screw counterbore: 3 mm grip + the motor's 3 mm thread depth = a stock M3 x 6


def build(ctx):
    p = ctx.p
    x0 = p.pod_x1
    # the tail's outline (the motor axis sits level with the CG, so a full-throttle launch doesn't pitch the nose
    # down; the prop can touch on a belly landing - an accepted trade-off, DESIGN.md)
    w = 2 * p.tail_hw
    zlo, zhi = p.tail_z - p.tail_h / 2, max(p.tail_z + p.tail_h / 2, p.motor_z + 21.0)
    plate = Pos(x0 + PLATE_T / 2, 0, (zlo + zhi) / 2) * Rot(0, 90, 0) * extrude(RectangleRounded(zhi - zlo, w, 10), PLATE_T / 2, both=True)
    # why: break the aft face's outer edge (handling, and the edge that meets grass in a belly landing)
    plate = chamfer(plate.faces().sort_by(Axis.X)[-1].outer_wire().edges(), 0.8)
    # four M3 into the pod's tail inserts, heads on the aft face
    aft = Location(Plane(origin=(x0 + PLATE_T, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))      # local (u, v) = world (y, z)
    plate = plate - iface.bolt_pattern(ctx, "motor_mount", "M3", POD.mount_bolts(p), aft, kind="clearance", depth=PLATE_T)
    # motor base pattern, heads sunk in the front face
    front = Location(Plane(origin=(x0, 0, p.motor_z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    plate = plate - iface.motor_mount(ctx, L.MOTOR, front, "motor", PLATE_T, kind="counterbore", counterbore_depth=CB,
                                      center_hole=8.0)
    # why: the motor's phase leads leave its base sideways and go through here into the pod (same hole in the tail)
    plate = plate - Pos(x0, 0, POD.lead_hole_z(p)) * Rot(0, 90, 0) * Cylinder(POD.LEAD_HOLE_D / 2, 2 * PLATE_T + 2)
    ctx.rigid("motor", Location(Plane(origin=(x0 + PLATE_T, 0, p.motor_z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    ctx.rigid("base", Location())
    return ctx.finish(plate)
