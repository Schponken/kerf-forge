"""Base plate: carries the bracket on four M3 heat-set inserts; four counterbored M4 holes to screw it to a bench."""
from build123d import *
from kerf import iface


def build(ctx):
    p = ctx.p
    y_back = p.bracket_y0 - p.servo_tab_t - p.servo_tab_z - 12   # room behind the wall for the servo body
    y_front = p.bracket_y0 + p.wall_t + p.foot_d + 14
    L = p.wall_w + 40
    W = y_front - y_back
    yc = (y_front + y_back) / 2
    plate = Pos(0, yc, 0) * Box(L, W, p.base_t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    plate = fillet(plate.edges().filter_by(Axis.Z), 6)
    plate = chamfer(plate.edges().group_by(Axis.Z)[-1], 0.8)
    pts = [(sx * p.foot_hx, p.bracket_y0 + y) for sx in (-1, 1) for y in (p.foot_y1, p.foot_y2)]
    plate -= iface.bolt_pattern(ctx, "base_bracket", "M3", pts, Location((0, 0, p.base_t)), kind="heatset", depth=p.base_t)
    # bench-mount holes: plain counterbored M4 clearance, nothing mates with them inside this assembly
    m4 = iface.screw_spec("M4")
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = Pos(sx * (L / 2 - 9), yc + sy * (W / 2 - 9), 0)
            plate -= c * Cylinder(m4["clearance"] / 2, p.base_t * 3, align=(Align.CENTER, Align.CENTER, Align.CENTER))
            plate -= c * Pos(0, 0, p.base_t - m4["head_h"] - 0.3) * Cylinder(m4["head_d"] / 2 + 0.3, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("bracket_seat", Location((0, p.bracket_y0, p.base_t)))
    # desk spots for the off-rig electronics (z = 0 is the desk the plate stands on): 5 V adapter behind the rig,
    # barrel-jack terminal adapter and Arduino Nano beside it, plugs facing +X away from the plate
    ctx.rigid("desk_psu", Location((0, y_back - 45, 0)))
    ctx.rigid("desk_jack", Location((L / 2 + 30, p.bracket_y0 - 40, 0)))
    ctx.rigid("desk_nano", Location((L / 2 + 35, p.bracket_y0 + 10, 0)))
    return ctx.finish(plate)
