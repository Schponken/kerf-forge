"""Yoke: the part the pan servo turns. A plate screwed to the pan horn (4 x M2) with two side walls:
- +Y wall: the tilt SG90 bolts to its OUTER face from outside (top_through: only the case top passes the window, the
  tab tops press on the wall, two M2 screws from outside into pilot holes). Output points -Y, toward the camera.
- -Y wall: the M3 pivot hole on the tilt axis (free fit); the screw threads into the bracket knuckle.
A ledge under the tilt servo stiffens the +Y wall and carries a cable-tie point for the servo lead.
Origin: pan axis on the plate underside (the pan-horn face). Printed on the plate, as assembled.
"""
from build123d import *
from kerf import iface, features

SERVO = "servos.SG90"
HORN = "servo_horns.aluminum_micro_21T"


def _block(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def build(ctx):
    p = ctx.p
    t = p.yoke_t
    win_hw = (p.servo_W + 0.6) / 2
    wall_hw = win_hw + 5.6                                     # 5.6 mm beside the servo window (wall stiffness)
    hole_top = p.tilt_body_z + p.servo_hx / 2                   # upper tab screw height
    ledge = p.wall_out + 14.0

    # plate: from the pivot wall to under the tilt servo; narrow in X so the camera clears it when tilted down
    plate = _block(-12.0, 12.0, p.pin_wall_out - 6.5, p.wall_out, 0, t)      # -Y end carries the pivot-wall gussets
    plate += _block(-15.0, 15.0, p.horn_y + 3.0, p.wall_out, 0, t)            # wider outside the camera view
    plate += _block(-wall_hw, wall_hw, p.wall_out - 1, ledge, 0, t)
    corners = plate.edges().filter_by(Axis.Z).filter_by(lambda e: abs(e.center().Y - p.wall_out) > 1.5 and abs(e.center().Y - p.horn_y - 3.0) > 0.5)
    body, bad = features.safe_fillet(plate, [(corners, 2.5)])
    ctx.notes += [f"plate corner fillet skipped: {b}" for b in bad]

    # +Y wall (tilt servo)
    wall = _block(-wall_hw, wall_hw, p.wall_in, p.wall_out, 0, hole_top + 4.0)
    wall = fillet(wall.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 3.0)
    body += wall
    # -Y wall (pivot), round top around the pivot
    pw_hw = 7.0
    pw = _block(-pw_hw, pw_hw, p.pin_wall_out, p.pin_wall_in, 0, p.tilt_h)
    pw += Pos(0, p.pin_wall_in, p.tilt_h) * Rot(90, 0, 0) * Cylinder(pw_hw, p.wall_t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += pw
    # inside corners where the walls meet the plate: the whole tilt load path runs through them
    roots = body.edges().filter_by(Axis.X).filter_by(
        lambda e: abs(e.center().Z - t) < 0.05 and min(abs(e.center().Y - y) for y in (p.wall_in, p.pin_wall_in, p.pin_wall_out)) < 0.05)   # not wall_out: the servo tab ends sit 0.6 mm above the plate there
    body, bad = features.safe_fillet(body, [(roots, 1.5)])
    ctx.notes += [f"wall root fillet skipped: {b}" for b in bad]

    # gussets: both sides of the +Y wall, outside of the -Y wall (its inside is where the bracket swings), all standing on the plate (print without support)
    for sx in (-1, 1):
        body += features.gusset((sx * (wall_hw - 1.25), p.wall_in, t), (0, -1, 0), (0, 0, 1), 7.0, 9.0, 2.5)
        body += features.gusset((sx * (wall_hw - 1.25), p.wall_out, t), (0, 1, 0), (0, 0, 1), 12.0, 4.0, 2.5)
        body += features.gusset((sx * (pw_hw - 1.25), p.pin_wall_out, t), (0, -1, 0), (0, 0, 1), 6.0, 12.0, 2.5)

    # pan horn: 4 x M2 clearance + centre-screw access through the plate
    body -= iface.horn_mount(ctx, HORN, Location((0, 0, t)), group="yoke_pan", plate_t=t)

    # tilt servo from outside: window + 2 pilot holes in the +Y wall
    loc = Location(Plane(origin=(0, p.wall_out, p.tilt_body_z), x_dir=(0, 0, 1), z_dir=(0, -1, 0)))
    body -= iface.servo_mount(ctx, SERVO, loc, group="yoke_tilt", plate_t=p.wall_t, kind="tap", top_through=True)
    # relief for the SG90's round gear boss (~14 mm, catalog note) where the case top sits just inside the window
    case_top = p.wall_out - (p.servo_top - p.servo_tab_t)
    body -= Pos(0, p.wall_in - 1.0, p.tilt_h) * Rot(-90, 0, 0) * Cylinder(7.0, case_top + 0.3 - p.wall_in + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # tilt pivot: M3 screw, free fit in this wall (head outside); horizontal hole -> teardrop pointing up (+Z)
    ploc = Location(Plane(origin=(0, p.pin_wall_out, p.tilt_h), x_dir=(1, 0, 0), z_dir=(0, -1, 0)))
    body -= iface.pin_hole(ctx, "M3", ploc, group="tilt_pivot", depth=p.wall_t, fit="free", teardrop=90)

    # FPC notch in the plate's front edge, outside the pan horn (r 10): the camera ribbon drops through it to its loop
    body -= Pos(12.0, 0, -1) * Box(3.0, 18.0, t + 2)
    # cable-tie point on the ledge for the tilt servo lead: two vertical slots for a 2.5 mm tie
    for sx in (-1, 1):
        body -= Pos(sx * 3.5, ledge - 4.0, -1) * Box(1.8, 3.2, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))

    body = chamfer(body.edges().group_by(Axis.Z)[0], 0.5)       # bed edges
    body -= features.label("PT1", 5.0, depth=0.6, loc=Location((0, ledge - 9.5, t), (0, 0, 90)), emboss=False)

    ctx.rigid("horn_mount", Location((0, 0, 0)))
    ctx.rigid("tilt_seat", loc * Location((0, 0, -p.servo_tab_t)))
    return ctx.finish(body)
