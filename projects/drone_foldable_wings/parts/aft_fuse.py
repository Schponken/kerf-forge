"""STUB aft fuselage (contract only; the part-designer replaces the geometry)."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    body = Pos(p.fuse_joint_x, -p.fuse_hw_wing, p.fuse_bottom) * Box(p.fuse_x1 - p.fuse_joint_x, 2 * p.fuse_hw_wing, p.fuse_top - p.fuse_bottom, align=(Align.MIN,) * 3)
    for k in ("fwd", "spine", "tail"):
        ctx.rigid(k, Location())
    ctx.rigid("boom", L.boom_loc(p))
    for s, n in ((1, "r"), (-1, "l")):
        ctx.revolute(f"pivot_{n}", L.pivot_axis(p, s), range=(0, p.fold_max))
        ctx.rigid(f"sweep_servo_{n}", L.sweep_servo_loc(p, s))
    return ctx.finish(body)
