"""Camera bracket: a U that turns about the tilt axis, carried on both sides.
- +Y arm: bolts to the tilt servo's metal horn (4 x M2 from the inside) with an access hole for the horn's centre screw.
- -Y arm: a knuckle with an M3 pilot; the M3 pivot screw comes through the yoke's -Y wall and threads in here.
  Four 2.4 mm holes on the horn bolt circle let a 1.5 mm hex key reach the horn screws straight through this arm, and a
  2.4 mm hole through the knuckle floor lets the key reach the horn's centre screw (before the pivot screw goes in).
- Front plate: four printed standoffs (3.5 mm, clearing the parts behind the camera PCB) with M2 pilots for the camera.
The lens centre sits on the tilt axis height, so tilting barely moves the image centre.
Origin: on the tilt axis midway between the arms; X = camera view direction, Z up at tilt 0.
Printed standing on its flat bottom (z = -arm_bottom), as assembled; the knuckle and standoffs are teardrop prisms
pointing down, so nothing needs support.
"""
import math

from build123d import *
from kerf import iface, features

HORN = "servo_horns.aluminum_micro_21T"
CAM = "boards.rpi_camera_module_3"


def _slab(x0, x1, z0, z1, y0, y1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def _arm(r_hub, x_front, z_bot, y0, y1):
    hub = Pos(0, y0, 0) * Rot(-90, 0, 0) * Cylinder(r_hub, y1 - y0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return hub + _slab(0, x_front, z_bot, r_hub, y0, y1) + _slab(-r_hub, 0, z_bot, 0, y0, y1)


def _teardrop_y(r, y0, y1, x, z):
    """Horizontal boss along Y with its 45-degree point DOWN (prints without support)."""
    a = r / math.sqrt(2)
    with BuildSketch(Plane.XZ) as sk:
        Circle(r)
        Polygon((-a, -a), (a, -a), (0, -1.6 * r), align=None)   # 52 deg flanks: clearly self-supporting
    s = extrude(sk.sketch, amount=y1 - y0)            # Plane.XZ normal is -Y: extrudes toward -Y
    return Pos(x, y1, z) * s


def _standoff(r, x0, x1, y, z):
    """Round standoff along +X with a 45-degree point underneath (prints without support on a vertical plate)."""
    a = r / math.sqrt(2)
    with BuildSketch(Plane.YZ) as sk:
        Circle(r)
        Polygon((-a, -a), (a, -a), (0, -1.6 * r), align=None)   # 52 deg flanks: clearly self-supporting
    return Pos(x0, y, z) * extrude(sk.sketch, amount=x1 - x0)


def _out_minus_y(x, y, z):
    """Hole frame on a face whose outward normal is -Y: +Z = -Y, local X = bracket +Z (up when printed)."""
    return Location(Plane(origin=(x, y, z), x_dir=(0, 0, 1), z_dir=(0, -1, 0)))


def build(ctx):
    p = ctx.p
    yi, yo = p.arm_y_in, p.horn_y
    xf = p.cam_plate_x + p.cam_plate_t
    zb = -p.arm_bottom
    r_hub = iface.horn_dims(HORN)["od"] / 2 + 1.0
    body = _arm(r_hub, xf, zb, yi, yo) + _arm(r_hub, xf, zb, -yo, -yi)
    body += _slab(p.cam_plate_x, xf, zb, r_hub, -yo, yo)                     # camera plate

    # camera standoffs (teardrop prisms along X) and the camera seat frame (board x -> +Y, board y -> +Z)
    cam = ctx.cat.get(CAM)
    seat = Location(Plane(origin=(p.cam_seat_x, 0, p.cam_zc), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    holes = [tuple(h) for h in cam["holes"]]
    for (bx, by) in holes:
        so = _standoff(2.4, xf - 0.5, p.cam_seat_x, bx, p.cam_zc + by)
        body += so & Pos(0, 0, zb) * Box(200, 200, 200, align=(Align.CENTER, Align.CENTER, Align.MIN))  # point clipped at the bed
    body += _teardrop_y(4.4, -yo, p.knuckle_y, 0, 0)                          # pivot knuckle on the -Y arm

    # inside corners where the plate meets the arms (load path of the camera into the hubs)
    corners = body.edges().filter_by(Axis.Z).filter_by(
        lambda e: abs(abs(e.center().Y) - yi) < 0.05 and abs(e.center().X - p.cam_plate_x) < 0.05)
    body, bad = features.safe_fillet(body, [(corners, 1.5)])
    ctx.notes += [f"plate/arm fillet skipped: {b}" for b in bad]

    # tilt horn: 4 x M2 from the inside face of the +Y arm, plus the centre-screw access hole
    hm = Location(Plane(origin=(0, yi, 0), x_dir=(0, 0, 1), z_dir=(0, -1, 0)))
    body -= iface.horn_mount(ctx, HORN, hm, group="bracket_tilt", plate_t=p.arm_t)
    # hex-key access through the -Y arm, coaxial with each horn screw
    for (u, v) in iface.circle(4, p.horn_bc, 45.0):
        body -= _out_minus_y(-v, -yo, u) * features.teardrop_hole(2.4, yo - yi + 1, up_deg=0)
    # M3 pivot thread (screw held here, turns in the yoke wall), entering from the -Y outer face
    ploc = Location(Plane(origin=(0, -yo, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)))
    body -= iface.pin_hole(ctx, "M3", ploc, group="tilt_pivot", depth=p.knuckle_len, fit="tap")
    body -= _out_minus_y(0, -yo, 0) * features.teardrop_hole(2.4, p.knuckle_len + 1, up_deg=0)
    # 45-degree roof over the horn centre-screw access hole (horizontal hole as printed)
    body -= _out_minus_y(0, yi, 0) * features.teardrop_hole(2 * (iface.screw_spec("M2")["head_d"] / 2 + 0.75), p.arm_t + 1, up_deg=0)

    # camera: M2 pilots through standoff + plate
    body -= iface.bolt_pattern(ctx, "cam_mount", "M2", holes, seat, kind="tap", depth=p.standoff + p.cam_plate_t)

    body = chamfer(body.edges().group_by(Axis.Z)[0], 0.4)                   # bed edges

    ctx.rigid("horn_mount", Location(Plane(origin=(0, yo, 0), x_dir=(0, 0, 1), z_dir=(0, -1, 0))))
    ctx.rigid("cam_seat", seat)
    lens = cam["lens_offset"]
    t = ctx.cat.num(cam, "thickness")
    ctx.rigid("lens_base", seat * Location((lens["x"], lens["y"], t)))
    ctx.rigid("lens_front", seat * Location((lens["x"], lens["y"], t + ctx.cat.num(cam, "component_height"))))
    return ctx.finish(body)
