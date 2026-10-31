"""gimbal_outer: the roll ring. A flat annulus around the props' hub plane that turns about world X (roll): its +X lug
bolts to the roll servo's horn, its -X pad turns on the roll dowel. It carries the pitch servo on a +Y pad (tabs on
the inner face, body out through a window) and holds the pitch dowel pressed into its -Y pad.
Frame: world at home (origin = gimbal centre). Printed flat (ring plane on the bed)."""
from build123d import *
from kerf import iface

SERVO = "servos.MG90S"
HORN = "servo_horns.aluminum_micro_21T"
PIN = "motion.pin_3mm"


def build(ctx):
    p = ctx.p
    ri, ro, h = p.ring_r_in, p.ring_r_out, p.ring_h
    ring = Cylinder(ro, h) - Cylinder(ri, h + 2)
    li = ri - 2.0                                                         # lugs/pads stand 2 mm proud inside
    lug_t = p.roll_face - li                                              # roll horn lug, radial thickness
    roll_lug = Pos(li + lug_t / 2, 0, 0) * Box(lug_t, 20, h)        # pads as tall as the ring: one flat face on the bed
    pin_pad_x = Pos(-(li + ro) / 2, 0, 0) * Box(ro - li, 14, h)
    ox = p.servo_out_x
    x_lo, x_hi = -ox - p.servo_span / 2 - 4.0, -ox + p.servo_span / 2 + 4.0
    servo_pad = Pos((x_lo + x_hi) / 2, (ri + ro) / 2, 0) * Box(x_hi - x_lo, ro - ri, h)
    pin_pad_y = Pos(0, -(ri - 0.5 + ro) / 2, 0) * Box(14, ro - ri + 0.5, h)
    body = ring + roll_lug + pin_pad_x + servo_pad + pin_pad_y
    # the ring's inner curve bulges inside the flat servo pad face toward its ends: cut it back so the tabs seat flat
    body -= Pos((x_lo + x_hi) / 2, ri - 4.0, 0) * Box(x_hi - x_lo, 8.0, h + 2)
    # roll horn: screws from inside the ring (heads on x = ri face) into the horn's threaded holes
    hloc = Location(Plane(origin=(li, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    body -= iface.horn_mount(ctx, HORN, hloc, group="roll_horn", plate_t=lug_t, teardrop=iface.print_up_deg(ctx, hloc))
    # roll dowel: free fit, entering from the outer face (pin comes from the ring_low -X plate)
    rloc = Location(Plane(origin=(-ro, 0, 0), z_dir=(-1, 0, 0)))
    body -= iface.pin_hole(ctx, PIN, rloc, group="roll_pin", depth=ro - li, fit="free", teardrop=iface.print_up_deg(ctx, rloc))
    # pitch servo: tabs rest on the inner face of the +Y pad, body goes out through the window
    tab = Location(Plane(origin=(-ox, p.pitch_tab_y, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)))
    body -= iface.servo_mount(ctx, SERVO, tab, group="ring_servo", plate_t=ro - ri, kind="tap",
                              teardrop=iface.print_up_deg(ctx, tab))
    # pitch dowel: pressed into the -Y pad from the inner face
    ploc = Location(Plane(origin=(0, -(ri - 0.5), 0), z_dir=(0, 1, 0)))
    body -= iface.pin_hole(ctx, PIN, ploc, group="pitch_pin", depth=ro - ri + 0.5, fit="press",
                           teardrop=iface.print_up_deg(ctx, ploc))
    ctx.rigid("roll_horn", Location(Plane(origin=(p.roll_face, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    ctx.rigid("pitch_servo", tab)
    return ctx.finish(body)
