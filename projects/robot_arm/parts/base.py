"""Base: desk plate, bearing tower for the turntable spindle (two 6001 bearings, 25 mm apart, so the arm's tipping
moment never reaches the servo), and the pocket the yaw servo (MG996R) hangs in, output up, 45 mm behind the yaw axis.
Origin: yaw axis on the desk (underside of the plate); z up; the arm points +X at home.
Printed upright; the servo shelf and the bearing-bore ceiling need supports (supports: allowed)."""
import math

from build123d import *
from kerf import iface

YAW = "servos.MG996R"
BRG = "bearings.6001"


def build(ctx):
    p = ctx.p
    d = iface.servo_dims(YAW)
    xc = -p.yaw_c - p.yaw_out_x                    # yaw servo body centre (output end toward the tower)
    shelf_t = 8.0
    r_tower = p.brg_D / 2 + 6.0
    body = Pos(-29, 0, 0) * Box(138, 100, p.base_floor, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = fillet(body.edges().filter_by(Axis.Z), 8.0)
    body += Cylinder(r_tower, p.z_tt, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # servo housing: walls round the hanging body, a shelf the tabs rest on, room for the cable boss at the output end
    boss_x1 = xc + d["L"] / 2 + 6.6 + 0.6
    hx0, hx1 = xc - d["span"] / 2 - 4.0, max(boss_x1 + 4.0, xc + d["span"] / 2 + 4.0)
    hw = d["W"] / 2 + 0.5 + 4.0
    body += Pos((hx0 + hx1) / 2, 0, 0) * Box(hx1 - hx0, 2 * hw, p.z_shelf, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cav_x0, cav_x1 = xc - d["L"] / 2 - 0.5, boss_x1
    body -= Pos((cav_x0 + cav_x1) / 2, 0, p.base_floor) * Box(cav_x1 - cav_x0, d["W"] + 1.0, p.z_shelf - shelf_t - p.base_floor,
                                                             align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= iface.servo_mount(ctx, YAW, Location((xc, 0, p.z_shelf)), group="yaw_servo", plate_t=shelf_t, kind="tap")
    # slot so the cable boss (low on the output-end face) passes the shelf when the servo drops in
    body -= Pos((xc + d["L"] / 2 - 1.0 + boss_x1) / 2, 0, p.z_shelf - shelf_t - 1) * Box(boss_x1 - xc - d["L"] / 2 + 1.0, 9.0, shelf_t + 2,
                                                                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
    # cable exit through the housing's front wall, at floor level
    body -= Pos(boss_x1 + 2.0, 0, p.base_floor) * Box(8.0, 10.0, 10.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # bearing seats: lower 6001 pushed up from below to a shoulder, upper 6001 dropped in from the top
    body -= iface.bearing_seat(ctx, BRG, Location((0, 0, 0), (180, 0, 0)), fit="press", depth=p.z_blo + p.brg_B,
                               through=p.z_bhi - p.z_blo - p.brg_B, shaft_clear=4.0)
    # shaft_clear 4 -> 20 mm bore between the seats: clears the turning inner races (land ~16.7 mm) and still
    # supports the outer races (inner edge ~24 mm)
    body -= iface.bearing_seat(ctx, BRG, Location((0, 0, p.z_tt)), fit="press", depth=p.brg_B, through=1.0, shaft_clear=4.0)
    body = chamfer(body.edges().filter_by(GeomType.CIRCLE).filter_by(lambda e: abs(e.center().Z - p.z_tt) < 0.01
                                                                          and e.radius > p.brg_D / 2 + 1), 1.0)
    # gear guard: a wall round the outside of the yaw gear (open only toward the mesh) so cable loops cannot get in
    r_tip = p.gear_m * (p.gear_z_yaw + 2) / 2
    with BuildSketch(Plane.XY.offset(p.base_floor - 0.01)) as gs:
        with Locations((-p.yaw_c, 0)):
            Circle(r_tip + 4.0)
            Circle(r_tip + 1.5, mode=Mode.SUBTRACT)
        with Locations((-p.yaw_c + 60, 0)):
            Rectangle(80, 80, mode=Mode.SUBTRACT)          # open toward the turntable gear (mesh side)
        with Locations((-p.yaw_c - r_tip - 10, 0)):
            Rectangle(30, 30, mode=Mode.SUBTRACT)          # behind: the servo case itself closes that side
    guard = extrude(gs.sketch, p.z_plat0 - 0.5 - p.base_floor + 0.01)
    body += guard
    # side walls from the guard's open ends past the turntable gear, so the mesh can't be reached from +-Y
    # (they clear the 24 T tip circle by ~2.9 mm and the 36 T one by >= 1.2 mm; tops 0.5 mm under the platform)
    y0 = math.sqrt((r_tip + 1.5) ** 2 - 20.0 ** 2) + 0.05      # ring inner face where the guard is cut (20 mm ahead of its centre)
    for sy in (-1, 1):
        body += Pos(-2.75, sy * (y0 + 1.6), p.base_floor - 0.01) * Box(45.5, 3.2, p.z_plat0 - 0.5 - p.base_floor + 0.01,
                                                                       align=(Align.CENTER, Align.CENTER, Align.MIN))
    # cable post on the rear pad, outside the circle the turntable sweeps (r ~68); the lead bundle spans from the
    # turntable's cable mast to here above the arm, so it never drapes near the gears
    post_top = 132.0                                            # level with the turntable's cable mast
    body += Pos(-92.0, 0, p.base_floor - 0.01) * Box(10.0, 16.0, post_top - p.base_floor, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sy in (-5.0, 5.0):                                       # tie slots through the post (front to back)
        body -= Pos(-92.0, sy, post_top - 5.0) * Box(12.0, 1.8, 3.2)
    # desk mounting: 4 x M4 through-holes (bolt or wood-screw down) at the corners; the rear 20 mm is a clamp pad
    for x in (-88.0, 30.0):
        for y in (-40.0, 40.0):
            c, *_ = iface.hole("M4", "clearance", p.base_floor)
            body -= Pos(x, y, p.base_floor) * c
    ctx.revolute("yaw", Axis((0, 0, 0), (0, 0, 1)), range=(-90, 90))
    ctx.rigid("brg_lo", Location((0, 0, p.z_blo)))
    ctx.rigid("brg_hi", Location((0, 0, p.z_bhi)))
    ctx.rigid("yaw_servo_seat", Location((xc, 0, p.z_shelf)))
    ctx.rigid("cable_post", Location((-92.0, 0, post_top + 3.5)))   # bundle tied across the post top
    return ctx.finish(body)
