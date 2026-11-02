"""Sweep pinion (pinion_r / pinion_l): the 13 T, module 2 gear from L.gears() (phased to the hub's sector), bolted
flat on the MG996R's aluminium 25T disc horn by its 4 M3 (heads on top, 14 mm bolt circle) with a hole over the horn's
centre screw. PETG 100 % infill, printed flat (bottom face on the bed: teeth in the layers). It carries only the servo
torque (the wing's moments go into the pivot pin, DESIGN.md); the left one is the mirror image so both pairs mesh
the same way."""
from build123d import *
import importlib.util, pathlib
from kerf import iface

_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    s = -1 if ctx.id.endswith("_l") else 1
    g, _ = L.gears()
    if s < 0:
        g = mirror(g, Plane.XZ)
    at = (p.pinion_x, s * p.pivot_y, L.PINION_Z0)
    body = ctx.add(Pos(*at) * g, why="13 T pinion, module 2, 11 mm wide (sector 10.5)", kind="gear")
    top = Location((at[0], at[1], at[2] + L.PINION_W))
    body -= iface.horn_mount(ctx, L.SWEEP_HORN, top, f"pinion_{'l' if s < 0 else 'r'}", L.PINION_W, kind="clearance")
    ctx.rigid("horn", Location(at))
    return ctx.finish(body)
