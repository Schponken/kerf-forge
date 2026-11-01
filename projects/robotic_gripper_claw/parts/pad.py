"""TPU 95A grip pad, used twice (pad_l, pad_r), slid down into a dovetail groove in each finger's jaw.

Pad frame: origin at the centre of its back face (on the jaw), X along the finger, Y out of the grip face (toward the
object), Z up = the way it slides out (it goes in along -Z). The pad is symmetric in X, so one part serves both jaws:
finger_l seats it turned 180 deg about Z.

Why TPU (DESIGN.md 'Grip force', REFERENCES.md decision 6): friction holds the 150 g payload within half the servo's
stall only with an elastomer face; ribs across the slip direction grip better than a smooth face (P1: 0.69-0.79 vs
0.46-0.61). Retention (REFERENCES.md decision 7, numbers from the vise D7): 2 mm base under the ribs, a 3.75 mm
dovetail tongue whose neck 5.06 widens to 6.96; finger.py cuts the groove from `tongue_profile(SLIDE)` (0.15 mm all
round). The groove is closed at the bottom, so the pad's weight and an object sliding down both push it onto that stop.
Prints standing on its TOP end (print_rot [180, 0, 0]): the dovetail profile is in the layers, and the tongue, which
starts STOP above the pad's bottom, grows from the bed instead of overhanging it.
"""
from build123d import *

PAD_L, PAD_H = 20.0, 20.0          # grip face along the finger x height (claw Y)
TONGUE = (2.53, 3.48, 3.75)        # dovetail half-width at the back face, half-width at its root, depth (vise D7)
TONGUE_R = 1.0                     # root corner radius: no sharp corner left in the jaw's groove
NECK_R = 0.5                       # tongue-to-plate fillet (the jaw's groove lips are chamfered 0.6 to clear it)
STOP = 2.0                         # tongue starts this far above the pad's bottom: the jaw's groove floor fills it
LEAD = 1.2                         # chamfer on the tongue's leading (bottom) end: lead-in, clears the floor's r 1 fillet
RIB_H, RIB_P, RIB_C = 1.0, 2.5, 0.2   # grip ribs: height, pitch, crest half-width (2 mm base under them, as D7)


def tongue_profile(clear: float = 0.0):
    """Dovetail section in the pad's XY plane (back face at Y = 0, the jaw at Y < 0), grown by `clear` all round."""
    a, b, t = TONGUE
    f = make_face(Polyline((-a, 0), (a, 0), (b, -t), (-b, -t), close=True))
    f = fillet(f.vertices().filter_by(lambda v: v.Y < -t + 0.01), TONGUE_R)
    return offset(f, clear, kind=Kind.INTERSECTION) if clear else f


def build(ctx):
    p = ctx.p
    base, half = p.pad_t - RIB_H, PAD_H / 2
    # side section (Y out of the face, Z up): 2 mm base + ribs whose flanks run 43.6 deg off vertical (no support)
    pts = [(0.0, -half), (base, -half)]
    for k in range(int(PAD_H // RIB_P)):
        zk = -half + RIB_P / 2 + k * RIB_P
        pts += [(p.pad_t, zk - RIB_C), (p.pad_t, zk + RIB_C), (base, zk + RIB_P / 2)]
    pts += [(0.0, half)]
    side = make_face(Polyline(*pts, close=True))
    valleys = side.vertices().filter_by(lambda v: abs(v.X - base) < 1e-6 and abs(v.Y) < half - 0.01)
    side = fillet(valleys, 0.4)                                          # why: no notch at the rib roots (TPU tears there)
    side = fillet(side.vertices().filter_by(lambda v: v.X > p.pad_t - 1e-6), 0.3)   # why: round crests, gentle on objects
    # why: the plate the object presses on, ribs across the slip direction (objects sliding down) for friction
    body = Plane.YZ * extrude(side, PAD_L / 2, both=True)
    tongue = Pos(0, 0, -half + STOP) * extrude(tongue_profile(), PAD_H - STOP)
    lead = tongue.edges().filter_by(lambda e: e.center().Z < -half + STOP + 0.01 and e.center().Y < -0.01)
    tongue = chamfer(lead, LEAD)                # why: lead-in for sliding the pad down into the groove
    body += tongue                              # why: dovetail that holds the pad on the jaw (no glue, no screws)
    neck = body.edges().filter_by(lambda e: abs(e.center().Y) < 0.01 and abs(abs(e.center().X) - TONGUE[0]) < 0.01)
    body = fillet(neck, NECK_R)                 # why: the tongue's root carries the pad's pull-off load
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
