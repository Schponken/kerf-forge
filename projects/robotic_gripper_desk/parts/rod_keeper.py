"""Rod keeper: a slim bar on the outer face of the gripper's -Z cheek over both guide-rod ends, 2 x M3 into heat-set
inserts in the cheek's front bar (between the rods). The rods are a press fit; the keeper only stops one walking out
under vibration (axial load ~0), so it is a 3 mm bar, not a structural part.
Frame: origin on the cheek face between the rods, +Z out of the cheek, Y along the cheek's front bar (rods at +-rod_y).
Printed flat on its cheek face (print_rot [0, 0, 0])."""
from build123d import *
from kerf import iface
from kerf.features import bed_chamfer, safe_fillet

KEEP_Y = 10.0      # screw positions: must equal gripper.py KEEP_Y (heat-set inserts between the rods)
T = 3.0            # bar thickness: 3 mm of PETG over the rod ends; the screw heads clamp it
W = 9.0            # = the cheek front bar's width (x_rod +- 4.5): the keeper does not overhang the cheek
R2 = 2.0           # project style radius


def build(ctx):
    p = ctx.p
    L = 2 * p.rod_y + 8.0                                            # rods' 4 mm ends + 2 mm lip past each
    bar = Pos(0, 0, T / 2) * Box(W, L, T)
    bar, _ = safe_fillet(bar, [(bar.edges().filter_by(Axis.Z), R2)])  # why: R2 plan corners (style), no sharp tips to catch
    bar, _ = safe_fillet(bar, [(bar.edges().group_by(Axis.Z)[-1], 0.6)], kind="chamfer")   # why: 0.6 edge break on the top (style)
    body = ctx.add(bar, why="covers both guide-rod ends on the -Z cheek so a pressed rod cannot walk out", kind="body")
    body -= iface.bolt_pattern(ctx, "keeper", "M3", [(0, KEEP_Y), (0, -KEEP_Y)], Location((0, 0, T)), "clearance", T)  # why: 2 x M3 into the cheek inserts (two screws: it cannot swing off)
    body, _ = bed_chamfer(ctx, body, 0.5)                            # why: elephant's-foot chamfer on the first layer
    ctx.rigid("origin", Location())
    return ctx.finish(body)
