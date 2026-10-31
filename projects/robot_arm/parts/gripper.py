"""Gripper body: two side plates on the wrist axis (plate A on the wrist horn, plate B on the wrist pivot screw),
a palm the grip servo (MG996R) hangs under (inserted top-first from below), and the fixed finger.
Frame: wrist horn face on the wrist axis; X forward, Y up (home), Z across (world -Y). The moving finger turns about
the grip servo's axis (vertical at home) and closes against the fixed finger's jaw.
Printed standing on the plates' flat lower edges (print_rot [90,0,0]; a 25 mm flat foot at y = -r under the wrist
discs, then a 45-degree rise); the palm and the fixed finger's jaw print on support."""
from build123d import *
from kerf import iface
from kerf.features import safe_fillet

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"
FOOT_L = 25.0                                      # flat bed edge of the side plates, from the wrist axis
PALM_T = 7.0                                       # = plate_t: 7 mm gives the M3 pilot holes an 8 mm screw


def grip_geom(p):
    """Positions shared with the finger and the requirements (gripper frame)."""
    x_gs = 45.0                                    # grip servo body centre
    x_g = x_gs + p.gr_out_x                        # grip servo axis
    z_c = p.w_g / 2
    y_f = p.face_gr                                # finger underside (horn face) above the palm underside (y = 0)
    return {"x_gs": x_gs, "x_g": x_g, "z_c": z_c, "y_f": y_f, "z_jaw": z_c + 5.0 + 0.5}


def build(ctx):
    p = ctx.p
    t, W, r = p.plate_t, p.w_g, p.link_h / 2
    g = grip_geom(p)
    x_end = 80.0
    with BuildSketch() as sk:
        Circle(r)
        with Locations((x_end / 2, 0)):
            Rectangle(x_end, 12.0)
        # flat foot: the plates' lower edge runs at y = -r for the first FOOT_L mm and rises at 45 deg to y = -6, so
        # the part stands on two flat 7 mm edges (print_rot [90,0,0]), not on the round bottoms of the wrist discs
        Polygon((0, -r), (FOOT_L, -r), (FOOT_L + r - 6.0, -6.0), (0, -6.0), align=None)
    pa = extrude(sk.sketch, t)
    body = pa + Pos(0, 0, W - t) * pa
    body += Pos((14.0 + x_end) / 2, PALM_T / 2, W / 2) * Box(x_end - 14.0, PALM_T, W)
    body += Pos(0, 0, W - t - 3.0) * Cylinder(6.5, 3.01, align=(Align.CENTER, Align.CENTER, Align.MIN))   # pivot boss
    # fixed finger: a post up from the palm's front, then a jaw forward at the moving finger's height
    zj0, zj1 = g["z_jaw"], g["z_jaw"] + 10.0          # 10 mm thick: the stall load bends it across this thickness
    tip_x = g["x_g"] + p.finger_len + 2.0
    body += Pos(x_end - 3.0, (PALM_T + g["y_f"] + 6.0) / 2, (zj0 + zj1) / 2) * Box(6.0, g["y_f"] + 6.0 - PALM_T + 0.02, zj1 - zj0)
    with BuildSketch(Plane.XY.offset(zj0)) as jaw:
        Polygon((x_end - 6.0, PALM_T), (x_end, PALM_T), (tip_x, g["y_f"]), (tip_x, g["y_f"] + 6.0), (x_end - 6.0, g["y_f"] + 6.0),
                align=None)
    body += extrude(jaw.sketch, zj1 - zj0)
    # 2 mm (1.5 at the upper side) fillets where the jaw post stands on the palm (docs/ENGINEERING.md section 5): the jaw load bends it there
    def at_post_base(e):
        c = e.center()
        return abs(c.Y - PALM_T) < 0.05 and x_end - 6.05 < c.X < x_end + 0.05 and zj0 - 0.05 < c.Z < zj1 + 0.05
    # (3 edges round the post base + the re-entrant corner under the jaw where it leaves the palm's front face)
    base_edges = [e for e in body.edges() if at_post_base(e) and abs((e % 0.5).Y) < 1e-6]
    back = [e for e in base_edges if abs(e.center().X - x_end) >= 0.05]
    body, failed = safe_fillet(body, [(back, 2.0)])
    if failed:                                   # the edge 2 mm from the palm's side face takes 1.5 mm at most
        body, failed = safe_fillet(body, [([e for e in body.edges() if at_post_base(e) and abs((e % 0.5).Y) < 1e-6
                                             and abs(e.center().X - x_end) >= 0.05 and abs(e.center().Z - zj1) < 0.05], 1.5)])
    # the re-entrant corner under the jaw (palm front face -> sloped jaw underside): OCC can't fillet it, so fill it
    # with a 4 mm wedge, which turns the sharp corner into two obtuse ones
    slope = (g["y_f"] - PALM_T) / (tip_x - x_end)
    with BuildSketch(Plane.XY.offset(zj0)) as wedge:
        Polygon((x_end - 0.01, PALM_T - 4.0), (x_end - 0.01, PALM_T + 0.01), (x_end + 4.0, PALM_T + 4.0 * slope + 0.01), align=None)
    body += extrude(wedge.sketch, zj1 - zj0)
    if failed or len(base_edges) != 4:
        raise ValueError(f"jaw post fillets: {len(base_edges)} edges, failed {failed}")
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="wr_horn", plate_t=t,
                               teardrop=iface.print_up_deg(ctx, Location((0, 0, t))))
    loc = Location((g["x_gs"], 0, g["z_c"]), (-90, 0, 0))   # palm underside; +Z up through the palm
    body -= iface.servo_mount(ctx, SERVO, loc, group="gr_servo", plate_t=PALM_T, kind="tap", top_through=True,
                              teardrop=iface.print_up_deg(ctx, loc))   # tab pilots print horizontal
    body -= iface.pin_hole(ctx, "M3", Location((0, 0, W)), "wr_pivot", depth=t + 3.0, fit="heatset",
                           teardrop=iface.print_up_deg(ctx, Location((0, 0, W))))
    for (hx, hy) in iface.circle(4, iface.horn_dims(HORN)["bc"], 45.0):     # hex-key access to the horn screws
        body -= Pos(hx, hy, W - t - 4) * Cylinder(2.0, t + 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    # servo-lead waypoints (wiring routes): along the outside of plate A, above the plate's top edge
    ctx.rigid("lead_1", Location((0, 30, -3)))
    ctx.rigid("lead_2", Location((40, -10, -3)))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.gr_tab_t)))
    ctx.rigid("tcp", Location((g["x_g"] + p.finger_len - 5.0, g["y_f"] + 3.0, g["z_jaw"] - 0.25)))
    ctx.rigid("fixed_tip", Location((tip_x, g["y_f"] + 3.0, (zj0 + zj1) / 2)))
    return ctx.finish(body)
