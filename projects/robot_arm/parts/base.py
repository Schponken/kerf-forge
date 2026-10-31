"""Base: desk plate, bearing tower for the turntable spindle (two 6001 bearings, 25 mm apart, so the arm's tipping
moment never reaches the servo), and the open-bottomed pocket the yaw servo (MG996R) is pushed up into from below,
output up, 45 mm behind the yaw axis (it goes in before the base is bolted to the desk).
Origin: yaw axis on the desk (underside of the plate); z up; the arm points +X at home.
Printed upright; the servo shelf and the bearing-bore ceiling need supports (supports: allowed)."""
import math

from build123d import *
from kerf import catalog, iface

YAW = "servos.MG996R"
BRG = "bearings.6001"
DRV = "boards.pca9685_adafruit"
DRV_Z = 95.0                     # driver board centre height on the post


def build(ctx):
    p = ctx.p
    d = iface.servo_dims(YAW)
    DRV_HOLES = [tuple(h) for h in catalog.get(DRV)["holes"]]
    xc = -p.yaw_c - p.yaw_out_x                    # yaw servo body centre (output end toward the tower)
    shelf_t = 7.0                                  # < case top above the tab tops (7.7): the case top passes it
    r_tower = p.brg_D / 2 + 6.0
    body = Pos(-29, 0, 0) * Box(138, 100, p.base_floor, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = fillet(body.edges().filter_by(Axis.Z), 8.0)
    body += Cylinder(r_tower, p.z_tt, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # servo housing, open at the bottom: the servo goes in from BELOW (top_through), case top up through the shelf
    # window, tab tops pressed against the shelf's underside, 4 screws from below. Coming from below, the cable boss
    # (low on the output end) never has to pass the shelf, so the shelf is solid round all four tab holes.
    z_tabtop = p.z_shelf + d["tab_t"]
    boss_x1 = xc + d["L"] / 2 + 6.6 + 0.6
    cav_x0, cav_x1 = xc - d["span"] / 2 - 0.6, max(boss_x1, xc + d["span"] / 2 + 0.6)   # the tabs pass it on the way up
    hx0, hx1 = cav_x0 - 4.0, cav_x1 + 4.0
    hw = d["W"] / 2 + 0.5 + 4.0
    body += Pos((hx0 + hx1) / 2, 0, 0) * Box(hx1 - hx0, 2 * hw, z_tabtop + shelf_t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ax0 = xc + d["L"] / 2 - 6.0                    # widened key-access part of the pocket (below), housing round it
    body += Pos((ax0 - 4.0 + hx1) / 2, 0, 0) * Box(hx1 - ax0 + 4.0, 2 * 26.0, z_tabtop + shelf_t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos((cav_x0 + cav_x1) / 2, 0, -1.0) * Box(cav_x1 - cav_x0, d["W"] + 1.0, z_tabtop + 1.0,
                                                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    # the output-end tab screws sit either side of the cable boss: a hex key can only reach them tilted sideways, so
    # the pocket is widened (y +-22) under those tabs, from the floor up to the tab undersides (the shelf stays whole)
    body -= Pos((ax0 + cav_x1) / 2, 0, -1.0) * Box(cav_x1 - ax0, 2 * 22.0, p.z_shelf - 0.5 + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= iface.servo_mount(ctx, YAW, Location((xc, 0, z_tabtop)), group="yaw_servo", plate_t=shelf_t, kind="tap",
                              top_through=True)
    # yaw lead exit: through the widened pocket's -Y wall, at floor level, toward the gear guard's floor hole
    body -= Pos((ax0 + cav_x1) / 2, -24.0, p.base_floor) * Box(8.0, 6.0, 8.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("yaw_lead_exit", Location(((ax0 + cav_x1) / 2, -24.0, p.base_floor + 4.0)))
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
    # cable hole through the guard ring's -Y side at floor level: the yaw servo lead leaves the housing's front exit,
    # runs back along the housing inside the ring and out here
    body -= Pos(-p.yaw_c, -(r_tip + 2.75), p.base_floor) * Box(12.0, 6.0, 10.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # cable post on the rear pad, outside the circle the turntable sweeps (r ~68); the lead bundle spans from the
    # turntable's cable mast to here above the arm, so it never drapes near the gears
    post_top = 132.0                                            # level with the turntable's cable mast
    body += Pos(-92.0, 0, p.base_floor - 0.01) * Box(10.0, 26.0, post_top - p.base_floor, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # post root: a knock or a yank on the bundle bends it at its across-layer root. Its front face is tied to the
    # servo housing (the 1 mm slot between them filled up to the shelf), so a pull toward the arm bends it above the
    # housing, not at the plate; 4 mm root gussets along its two sides (its rear face is flush with the plate's edge).
    if hx0 > -87.0:
        body += Pos((-87.0 + hx0) / 2, 0, p.base_floor - 0.01) * Box(hx0 - (-87.0) + 0.02, 26.0, p.z_shelf - p.base_floor,
                                                                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sy in (-1, 1):            # 4 mm triangular root gussets along both sides of the post foot
        tri = Polygon((sy * 12.99, p.base_floor - 0.01), (sy * 17.0, p.base_floor - 0.01), (sy * 12.99, p.base_floor + 4.0), align=None)
        body += Plane.YZ.offset(-92.0) * extrude(tri, 5.0, both=True)
    # servo driver (Adafruit PCA9685, 62 x 25 board) on 4 bosses on the post's rear face, long side vertical, parts
    # facing away from the arm; M2 screws tapped into the bosses (iface + board proxy share group 'driver')
    drv = Location((-100.0, 0, DRV_Z), (0, -90, 0))              # boss faces at x = -100; +Z (board up) = world -X
    for (hx, hy) in DRV_HOLES:
        body += drv * Pos(hx, hy, -0.01) * Cylinder(3.0, 3.02, align=(Align.CENTER, Align.CENTER, Align.MAX))
    body -= iface.bolt_pattern(ctx, "driver", "M2", DRV_HOLES, drv, kind="tap", depth=7.0)
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
    ctx.rigid("driver_seat", drv)
    # off the base, on the desk behind it (where the arm never reaches): supply, the two WAGO power buses, the Nano
    ctx.rigid("desk_psu", Location((-225.0, 0, 0)))
    ctx.rigid("desk_bus_arm", Location((-112.0, -5.0, 0)))
    ctx.rigid("desk_bus_yaw", Location((-112.0, -37.0, 0)))
    ctx.rigid("desk_nano", Location((-125.0, 40.0, 0), (0, 0, 90)))   # USB end toward +Y, free to plug in
    return ctx.finish(body)
