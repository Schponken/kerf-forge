"""ring_low: the root of the airframe. A spider plate under the mast with three tube bosses, three leg lugs, and two
yoke arms hanging down to the gimbal: +X carries the roll servo (window + 2 tapped M2 tab holes), -X holds the roll
pivot dowel (press fit). Printed upside down (print_rot [180, 0, 0]): the tube bosses, bridge webs and lug ribs stand
on the bed with the yoke arms pointing up; the plate between them prints on supports (~15 %). Every horizontal hole is
a teardrop pointing up in that orientation (iface.print_up_deg)."""
import math

from build123d import *
from kerf import iface

SERVO = "servos.MG90S"
PIN = "motion.pin_3mm"
LUG_W = 22.0          # leg lug width; the two leg inserts sit on its centre line, 11 mm from each edge
LUG_RIB, LUG_RIB_W = 10.0, 10.0   # T-rib on each lug (height, width): landing pries the lug (lug_fea); 7x the plain lug's I
LEG_SCREWS = [(-22.0, 0.0), (-13.0, 0.0)]   # leg screw sites, radially inboard of the attachment (leg.py has the same)


def build(ctx):
    p = ctx.p
    z0, t = p.ring_low_z, 8.0                     # plate underside and thickness
    yoke_t = 5.0                                  # +X servo plate thickness (tapped M2 needs >= 3.8 mm)
    pin_t = 8.0                                   # -X pin plate thickness
    gap = 1.0                                     # roll pin plate to outer ring
    # --- plate: centre disc + leg lugs + yoke bridges
    plate = Pos(0, 0, z0) * Cylinder(p.rod_r + 9, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.leg_angles:
        lug = Pos((p.leg_r0 + 12) / 2, 0, z0) * Box(p.leg_r0 + 12, LUG_W, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        r0 = 10.5                                 # T-rib on top of the lug, from the wire pass out to the lug end (it also
                                                  # stiffens the disc between the tubes, where the landing load crosses)
        rib = Pos((r0 + p.leg_r0 + 12) / 2, 0, z0 + t - 0.01) * Box(p.leg_r0 + 12 - r0, LUG_RIB_W, LUG_RIB,
                                                                   align=(Align.CENTER, Align.CENTER, Align.MIN))
        plate += Rot(0, 0, a) * (lug + rib)
    ox = p.servo_out_x
    y_lo, y_hi = -ox - p.servo_span / 2 - 4.0, -ox + p.servo_span / 2 + 4.0     # yoke plate covers the tab span
    xp = p.roll_tab_x + yoke_t
    plate += Pos(xp / 2, (y_lo + y_hi) / 2, z0) * Box(xp, y_hi - y_lo, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    xm = p.ring_r_out + gap + pin_t
    plate += Pos(-xm / 2, 0, z0) * Box(xm, 18, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # --- +X yoke: vertical plate in the YZ plane from the servo down to the plate
    zb = -p.servo_W / 2 - 4.0
    arm_p = Pos(p.roll_tab_x, y_lo, zb) * Box(yoke_t, y_hi - y_lo, z0 + t - zb, align=(Align.MIN, Align.MIN, Align.MIN))
    # --- -X yoke: pin plate
    arm_m = Pos(-xm, -9, -9) * Box(pin_t, 18, z0 + t + 9, align=(Align.MIN, Align.MIN, Align.MIN))
    body = plate + arm_p + arm_m
    # stiffening gussets between each yoke arm and the plate (inside corner of the load path)
    for x0, x1, sgn in ((p.roll_tab_x, p.roll_tab_x - 22, 1), (-xm + pin_t, -xm + pin_t + 22, -1)):
        tri = Polygon((x0, z0 + 0.5), (x1, z0 + 0.5), (x0, z0 - 22), align=None)
        for yy in ((y_lo + 2, y_hi - 2) if sgn > 0 else (-7, 7)):
            body += Pos(0, yy, 0) * (Plane.XZ * extrude(tri, 1.5, both=True))
    # webs on top of the two yoke bridges: the thrust from the pivots bends the bridges back to the tubes
    for yy in (y_lo + 2.5, y_hi - 2.5):
        body += Pos(0, yy - 2.0, z0 + t - 0.01) * Box(xp - 2.0, 4.0, 18.0, align=(Align.MIN, Align.MIN, Align.MIN))
    for yy in (-6.5, 6.5):
        body += Pos(-xm + 2.0, yy - 2.0, z0 + t - 0.01) * Box(xm - 2.0, 4.0, 18.0, align=(Align.MIN, Align.MIN, Align.MIN))
    # --- tube bosses (up), bores 5.5 (0.5 mm clearance on the 5 mm tube), radial M3 lock holes
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body += Pos(c[0], c[1], z0 + t - 0.01) * Cylinder(6.0, 14.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for a in p.rod_angles:
        c = (p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)))
        body -= Pos(c[0], c[1], p.rod_z0) * Cylinder(2.75, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
        lock = Pos(c[0], c[1], z0 + t + 7) * Rot(0, 0, a) * Rot(0, 90, 0) * Pos(0, 0, 14)   # +Z radially outward
        body -= lock * iface.hole("M3", "tap", 14, teardrop=iface.print_up_deg(ctx, lock))[0]
    body -= Cylinder(10, 400)                                            # wire pass + mass
    # two cable-tie slots through the +X yoke plate near its +Y edge: the motor and servo leads run down beside it
    for zt in (15.0, 40.0):
        body -= Pos(p.roll_tab_x - 1, y_hi - 3.0, zt) * Box(yoke_t + 2, 1.6, 3.0, align=(Align.MIN, Align.CENTER, Align.CENTER))
    # --- roll servo: tabs rest on the yoke plate's inner face (x = roll_tab_x), body through the window outward
    tab = Location(Plane(origin=(p.roll_tab_x, -ox, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    body -= iface.servo_mount(ctx, SERVO, tab, group="yoke_servo", plate_t=yoke_t, kind="tap",
                              teardrop=iface.print_up_deg(ctx, tab))
    # --- roll pivot pin, pressed into the -X plate (outer face of the hole on the ring side)
    ploc = Location(Plane(origin=(-(p.ring_r_out + gap), 0, 0), z_dir=(1, 0, 0)))
    body -= iface.pin_hole(ctx, PIN, ploc, group="roll_pin", depth=pin_t, fit="press", teardrop=iface.print_up_deg(ctx, ploc))
    # --- leg lugs: two heat-set M3 inserts each, from below, on the lug centre line inboard of the leg strut
    for i, a in enumerate(p.leg_angles, start=1):
        r = Rot(0, 0, a)
        body -= iface.bolt_pattern(ctx, "leg", "M3", LEG_SCREWS, r * Location((p.leg_r0, 0, z0), (180, 0, 0)),
                                   kind="heatset", depth=t)
        ctx.rigid(f"leg_{i}", r * Location((p.leg_r0, 0, z0)))
    for i, a in enumerate(p.rod_angles, start=1):
        ctx.rigid(f"rod_{i}", Location((p.rod_r * math.cos(math.radians(a)), p.rod_r * math.sin(math.radians(a)), p.rod_z0)))
    ctx.rigid("mid_seat", Location((0, 0, p.mid_z)))
    ctx.rigid("top_seat", Location((0, 0, p.ring_top_z)))
    ctx.rigid("roll_servo", tab)
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(body)
