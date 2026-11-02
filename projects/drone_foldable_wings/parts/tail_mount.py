"""STUB tail mount."""
from build123d import *
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("dfw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)


def build(ctx):
    p = ctx.p
    body = Pos(p.htail_x_le0 - 20, 0, p.boom_z) * Box(p.boom_x1 - p.htail_x_le0 + 30, 22, 22, align=(Align.MIN, Align.CENTER, Align.CENTER))
    for k in ("base", "hstab", "fin"):
        ctx.rigid(k, Location())
    ctx.rigid("elev_servo", Location(Plane(origin=(p.htail_x_le0 + 10, 0, p.boom_z - 12), x_dir=(1, 0, 0), z_dir=(0, 1, 0))))
    ctx.rigid("rud_servo", Location(Plane(origin=(p.htail_x_le0 + 40, 0, p.boom_z - 12), x_dir=(1, 0, 0), z_dir=(0, -1, 0))))
    return ctx.finish(body)
