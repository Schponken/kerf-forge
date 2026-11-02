"""STUB forward fuselage."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    body = Pos(p.fuse_x0, -p.fuse_hw, p.fuse_bottom) * Box(p.fuse_joint_x - p.fuse_x0, 2 * p.fuse_hw, p.fuse_top - p.fuse_bottom, align=(Align.MIN,) * 3)
    for k in ("aft", "hatch", "motor_mount"):
        ctx.rigid(k, Location())
    z = p.fuse_bottom + 2.5
    ctx.rigid("battery", Location((p.bat_x, 0, z)))
    ctx.rigid("xt60", Location((p.bat_x - 55, 0, z)))
    ctx.rigid("esc", Location((-100, 0, -40)))
    ctx.rigid("fc", Location((-40, 0, -40)))
    ctx.rigid("rx", Location((-5, 0, -40)))
    return ctx.finish(body)
