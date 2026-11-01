"""Pinion: 20-tooth module-1.5 spur pinion (pitch dia 30, face 12) bolted to the grip servo's aluminium 25T horn with
4 counterbored M3; it drives both jaws' racks (kerf.drives.rack_pinion phases it with them).
Frame: origin on the horn face on the servo axis, +Z forward (away from the horn), a tooth on +Y at angle 0.
Printed flat on its back face (teeth in the layer plane: the tooth roots bend along the layers)."""
from build123d import *
from kerf import drives, iface

HORN = "servo_horns.aluminum_25T"


def build(ctx):
    p = ctx.p
    b = p.gear_b
    pin, _, info = drives.rack_pinion(p.gear_m, int(p.pinion_z), int(p.rack_n), b)
    # why: 0.5 mm 45-degree break on both faces' tooth tips - no elephant's-foot lip on the bed face, no burr at the mesh
    k = 0.5
    with BuildSketch(Plane.XZ) as prof:
        Polygon((0, 0), (info.tip_r - k, 0), (info.tip_r + 0.01, k + 0.01), (info.tip_r + 0.01, b - k - 0.01),
                (info.tip_r - k, b), (0, b), align=None)
    pin &= revolve(prof.sketch, Axis.Z)
    # why: registration rim round the horn's Ø20 disc - centres the pinion on the horn (a 4-screw clearance pattern
    # alone lets it sit 0.2 mm off, most of the 0.3 mm mesh backlash); 1.8 deep so it clears the horn hub
    hd = iface.horn_dims(HORN)
    rim_r = info.root_r - 1.0
    pin += Pos(0, 0, -1.8) * Cylinder(rim_r, 1.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pin -= Pos(0, 0, -1.8 - 0.01) * Cylinder(hd["od"] / 2 + 0.2, 1.8 + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # why: 4 x M3 into the horn's threaded holes, heads counterbored below the front face (the jaw carriages slide
    # 0.6 mm in front of it); the horn_mount call also cuts the driver access to the horn's centre screw
    pin -= iface.horn_mount(ctx, HORN, Location((0, 0, b)), group="gr_horn", plate_t=b, kind="counterbore")
    ctx.rigid("horn_mount", Location((0, 0, 0)))
    return ctx.finish(pin)
