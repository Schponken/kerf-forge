"""motor_plate: carries the bottom motor (shaft down). The motor is screwed on at the bench (M3 from the top, heads
sunk), then the plate bolts under motor_hub with three M3 screws from below into the hub's inserts.
Frame: origin on the top face (the hub's underside at home), plate below it, +Z up. Printed flat, top face down."""
import math

from build123d import *
from kerf import features, iface

MOTOR = "drone.motors.2207_1855kv_6s"
JOIN_R = 21.0


def build(ctx):
    p = ctx.p
    t = p.hub_t
    body = Pos(0, 0, -t) * Cylinder(p.hub_r - 1.0, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= iface.motor_mount(ctx, MOTOR, Location((0, 0, 0)), group="plate_motor_bottom", plate_t=t,
                              kind="counterbore", counterbore_depth=t - 3.0)
    pts = [(JOIN_R * math.cos(math.radians(a)), JOIN_R * math.sin(math.radians(a))) for a in (0, 120, 240)]
    body -= iface.bolt_pattern(ctx, "hub_plate", "M3", [(x, -y) for x, y in pts], Location((0, 0, -t), (180, 0, 0)),
                               kind="clearance", depth=t)
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("bottom_motor", Location((0, 0, -t), (180, 0, 0)))
    body, _ = features.bed_chamfer(ctx, body)                   # 0.5 mm elephant's-foot chamfer on the first layer
    return ctx.finish(body)
