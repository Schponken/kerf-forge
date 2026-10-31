"""motor_hub: the pitch frame of the gimbal. A disc the top motor screws onto (M3 from below, heads sunk), with an
arm along +Y to the pitch servo's horn and an arm along -Y to the pitch dowel (free fit). The motor_plate with the
bottom motor bolts under it (3 heat-set M3 inserts). Both motors' thrust enters here.
Frame: world at home (origin = gimbal centre, thrust along +Z). Printed upside down: the disc top (the top motor's
seat) is on the bed, and the arms and horn lug are flush with it (z 8) so nothing hangs below the first layer."""
import math

from build123d import *
from kerf import iface

HORN = "servo_horns.aluminum_micro_21T"
MOTOR = "drone.motors.2207_1855kv_6s"
PIN = "motion.pin_3mm"
JOIN_R = 21.0          # radius of the hub-to-plate screws (outside the 29 mm motor bells)


def build(ctx):
    p = ctx.p
    t = p.hub_t
    body = Cylinder(p.hub_r, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    y0 = p.hub_r - 0.5                                   # arms start outside motor_plate's disc
    lug_t = 10.0
    yl = p.pitch_face - lug_t
    # +Y arm is a fork (two side bars) so a hex key can reach the horn screws along the axis between them
    for sx in (-1, 1):
        body += Pos(sx * 10.25, (20 + yl) / 2, 1) * Box(4.5, yl - 20 + 0.02, 14)
    body += Pos(0, (yl + p.pitch_face) / 2, -1) * Box(25, lug_t, 18)
    ye = p.ring_r_in - 1.5                               # -Y arm end, 1.5 mm inside the ring
    body += Pos(0, -(y0 + ye) / 2, 1) * Box(14, ye - y0, 14)
    # the arm roots reach into the disc
    body += Pos(0, -(y0 + 1) / 2, 1) * Box(14, y0 + 1, 14)        # -Y arm root (the +Y fork joins the disc directly)
    # nothing below the disc inside motor_plate's radius (the plate sits there)
    body -= Pos(0, 0, -20) * Cylinder(p.hub_r - 0.5, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # pitch horn: screws from the arm side (heads on the -Y face of the lug) into the horn
    hloc = Location(Plane(origin=(0, yl, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)))
    body -= iface.horn_mount(ctx, HORN, hloc, group="pitch_horn", plate_t=lug_t, teardrop=iface.print_up_deg(ctx, hloc))
    # pitch dowel, free fit, from the -Y end face
    ploc = Location(Plane(origin=(0, -ye, 0), z_dir=(0, -1, 0)))
    body -= iface.pin_hole(ctx, PIN, ploc, group="pitch_pin", depth=10.0, fit="free", teardrop=iface.print_up_deg(ctx, ploc))
    # top motor: M3 x 5 (picked by the fastener check) from below, heads sunk 4 mm so they sit inside the hub (motor_plate covers them)
    under = Location((0, 0, 0), (180, 0, 0))
    body -= iface.motor_mount(ctx, MOTOR, under, group="hub_motor_top", plate_t=t, kind="counterbore",
                              counterbore_depth=t - 3.0)
    # motor_plate joins from below into three heat-set inserts
    pts = [(JOIN_R * math.cos(math.radians(a)), JOIN_R * math.sin(math.radians(a))) for a in (0, 120, 240)]
    body -= iface.bolt_pattern(ctx, "hub_plate", "M3", [(x, -y) for x, y in pts], under, kind="heatset", depth=t)
    ctx.rigid("pitch_horn", Location(Plane(origin=(0, p.pitch_face, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))))
    ctx.rigid("top_motor", Location((0, 0, t)))
    ctx.rigid("plate_seat", Location((0, 0, 0)))
    return ctx.finish(body)
