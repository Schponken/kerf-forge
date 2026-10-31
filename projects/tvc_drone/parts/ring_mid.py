"""ring_mid: the middle mast ring; the three tubes pass through it and are locked with radial M3 screws. The flight
stack (20 x 20, M2) sits on its flat top on four heat-set inserts.
Frame: origin on the underside centre, +Z up. Printed flat, top face down? No: top face up (bosses hang below)."""
import math

from build123d import *
from kerf import iface

STACK = "drone.stacks.fc_20"


def build(ctx):
    p = ctx.p
    t = 8.0                                     # deep enough for an M2 x 18 through the 14.2 mm stack
    body = Cylinder(p.rod_r + 9, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body += Pos(c[0], c[1], -10) * Cylinder(6.0, 10.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body -= Pos(c[0], c[1], -20) * Cylinder(2.75, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body -= Pos(c[0], c[1], -5) * Rot(0, 0, a) * Rot(0, 90, 0) * Cylinder(
            iface.screw_spec("M3")["tap"] / 2, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # wire passes between the tubes (motor/servo leads up to the stack)
    for a in p.rod_angles:
        body -= Rot(0, 0, a + 60) * Pos(p.rod_r + 1, 0, -1) * Box(6, 12, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= iface.stack_mount(ctx, STACK, Location((0, 0, t)), group="mid_stack", depth=t, kind="tap")  # M2 thread-forming
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("stack_seat", Location((0, 0, t)))
    return ctx.finish(body)
