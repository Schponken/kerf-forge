"""TPU grip pad (STUB), used twice (pad_l, pad_r). Pad frame: origin at the centre of its back face (on the jaw),
X along the finger, Y out of the grip face (toward the object), Z up (it slides down into the jaw along -Z)."""
from build123d import *


def build(ctx):
    p = ctx.p
    body = Pos(0, p.pad_t / 2, 0) * Box(18.0, p.pad_t, 12.0)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
