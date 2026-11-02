"""Centre pod: the wing's centre section (between the two inner segments) merged with a fuselage that carries the
battery, ESC, flight controller, receiver, GPS and VTX; the nose (TPU, camera) bolts to its front face, the motor
mount to its rear face. PLA, printed standing on its rear face (the fuselage's long axis along the build plate's Z,
so its rounded sides print without supports); 2 walls, 15 % infill.

Inside: one cavity from the front face to the motor mount, 2.4 mm skin, split by a 2 mm shelf. Under the shelf the
battery bay: the pack slides in from the front (nose off) onto the floor and the nose closes the bay. On the shelf,
front to back: GPS (under plain PLA, nothing carbon above it), flight controller + receiver, ESC (under the spar
sleeves), VTX; its antenna leaves through the top. The spar tubes cross the cavity in printed sleeves that reach to
8 mm off the centreline (left and right tubes end apart), so a wing half's bending moment goes tube - sleeve - side
wall - pod (the pod box is ~2.3e6 mm^4 in bending: DESIGN.md). Each inner wing segment is held by two M3 from inside
the cavity through the side wall into its root inserts. Four bosses in the tail take the motor mount's M3 heat-set
inserts, four round the front opening the nose's; the boss ends facing the bed are 45 deg cones (no overhang).
"""
from build123d import *
import numpy as np
from kerf import aero, iface, sections
from kerf.features import fillet_inside

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

SKIN = 1.7            # 4 perimeters of a 0.42 mm line: solid skin, nothing left for sparse infill
SHELF_T = 1.7
SLEEVE_WALL = {"main": 4.0, "rear": 3.5}   # PLA round the tubes: main 8 -> 16 mm, rear 6 -> 13 mm (DESIGN.md)
BOSS_D = 10.0         # M3 heat-set insert (4.0 mm hole) + 3 mm wall each side (ENGINEERING.md s5: >= 2.4; s7 edge distance 1.5 d)
BOSS_L = 9.0


def shelf_z(p):
    """Top of the electronics shelf."""
    return p.bay_top + SHELF_T


def nose_bolts(p):
    """(y, z) of the nose's four M3 at the front face: two in the side frames, two in the top frame."""
    return [(-37, -27), (37, -27), (-18, 11), (18, 11)]


def mount_bolts(p):
    """(y, z) of the motor mount's four M3 in the tail (outside the motor bell, inside the tail outline)."""
    return [(sy * 16, p.tail_z + sz * 14) for sy in (-1, 1) for sz in (-1, 1)]


LEAD_HOLE_D = 8.0


def lead_hole_z(p):
    """Motor phase leads: 16 mm below the motor axis between the lower mount bolts, half under the bell's base edge,
    so the leads that leave the motor base sideways drop straight in."""
    return p.motor_z - 16.0


HATCH_X = (-5.0, 205.0)    # top hatch: where the full fuselage section starts to where the tail top starts to drop
HATCH_HW = 36.0
HATCH_CUT_Z = 17.0         # above the spar sleeves (top 14.2), below the top skin's inside


def hatch_box(p):
    return Pos(HATCH_X[0], 0, HATCH_CUT_Z) * Box(HATCH_X[1] - HATCH_X[0], 2 * HATCH_HW, 60, align=(Align.MIN, Align.CENTER, Align.MIN))


def hatch_bolts(p):
    """(x, y) of the hatch's two front M3 (vertical), over the side ledges."""
    return [(HATCH_X[0] + 9.0, -30.0), (HATCH_X[0] + 9.0, 30.0)]


def hatch_solid(p):
    """The top hatch's skin: the pod's top skin over the electronics bay."""
    return (outer(p) & hatch_box(p)) - cavity(p)


def opening(p):
    """Front opening (y half width, z bottom, z top): the battery (and hands, for the shelf) go in here."""
    return 30.0, p.pod_bottom + SKIN, 6.0


def fuselage_sections(p):
    """(x, half width, z bottom, z top, corner radius) stations of the fuselage outside."""
    hw = p.pod_hw
    return [(p.pod_x0, hw - 6, p.pod_bottom + 3, p.pod_top - 6, 14),
            (p.pod_x0 + 40, hw, p.pod_bottom, p.pod_top, 16),
            (p.pod_x1 - 90, hw, p.pod_bottom, p.pod_top, 16),
            (p.pod_x1, p.tail_hw, p.tail_z - p.tail_h / 2, p.tail_z + p.tail_h / 2, 10)]


def _loft(stations, shrink=0.0):
    secs = []
    for x, hw, zb, zt, r in stations:
        w, h = 2 * (hw - shrink), (zt - zb) - 2 * shrink
        rr = max(1.0, min(r - shrink, w / 2 - 0.5, h / 2 - 0.5))
        pl = Plane(origin=(x, 0, (zb + zt) / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        secs.append(pl * RectangleRounded(w, h, rr))
    return loft(secs, ruled=True)


def outer(p):
    pf = L.planform(p)
    centre = aero.wing_solid(pf, -p.pod_hw, p.pod_hw)
    return _loft(fuselage_sections(p)) + centre


def cavity(p):
    st = fuselage_sections(p)
    st = [(x + (SKIN if i == 0 else -SKIN if i == len(st) - 1 else 0), hw, zb, zt, r) for i, (x, hw, zb, zt, r) in enumerate(st)]
    cav = _loft(st, SKIN)
    # open to the front face, so the battery slides in with the nose off
    hw, zb, zt = opening(p)
    return cav + Pos(p.pod_x0 - 1, 0, zb) * Box(SKIN + 2, 2 * hw, zt - zb, align=(Align.MIN, Align.CENTER, Align.MIN))


def boss(x0, y, z, length, d, toward):
    """Insert boss along X from the wall at x0, `toward` = +1 / -1; a 45 deg cone at its free end."""
    from build123d import Cone
    cyl = Pos(x0 + toward * length / 2, y, z) * Rot(0, 90, 0) * Cylinder(d / 2, length)
    cone = Pos(x0 + toward * (length + d / 4), y, z) * Rot(0, 90 if toward > 0 else -90, 0) * Cone(d / 2, 0, d / 2)
    return cyl + cone


def build(ctx):
    p = ctx.p
    cav = cavity(p)
    body = outer(p) - ctx.cut(cav, why="battery and electronics bay", kind="cavity")
    # top hatch: the skin over the bay comes off (parts/hatch.py), so the shelf electronics and the wing-root bolts are
    # reached from above; side ledges under its edges carry it
    body = body - ctx.cut(hatch_box(p), why="top hatch opening: electronics and root bolts from above", kind="hatch")
    ledge = Pos(HATCH_X[0], 0, HATCH_CUT_Z - 2) * Box(HATCH_X[1] - HATCH_X[0], 2 * (HATCH_HW + 2), 12, align=(Align.MIN, Align.CENTER, Align.MIN)) \
        - Pos(HATCH_X[0], 0, 0) * Box(HATCH_X[1] - HATCH_X[0], 2 * (HATCH_HW - 4), 80, align=(Align.MIN, Align.CENTER, Align.CENTER))
    body = body + ctx.add((ledge & outer(p)) - hatch_solid(p), why="ledges the hatch rests on", kind="ledge")
    for (x, y) in hatch_bolts(p):          # ledge blocks deep enough for the hatch screws' inserts
        blk = Pos(x, y, HATCH_CUT_Z - 9) * Box(10, 10, 12, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body = body + ctx.add((blk & outer(p)) - hatch_solid(p), why="hatch insert block", kind="boss")
    top = Location(Plane(origin=(0, 0, p.pod_top - SKIN), x_dir=(1, 0, 0), z_dir=(0, 0, 1)))
    body = body - iface.bolt_pattern(ctx, "hatch", "M3", hatch_bolts(p), top, kind="heatset", depth=8, teardrop="auto")
    # battery strap: two tabs on the floor beside the pack, a 20 mm strap over its top (6 mm under the shelf)
    floor_z = p.pod_bottom + SKIN
    for s in (-1, 1):
        tab = Pos(p.bat_x, s * 31.5, floor_z - 1) * Box(30, 3, 11, align=(Align.CENTER, Align.CENTER, Align.MIN))
        tab -= Pos(p.bat_x, s * 31.5, floor_z + 3) * Box(22, 5, 3.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body = body + ctx.add(tab & outer(p), why="battery strap tab (22 x 3.5 slot)", kind="strap tab")
    # cooling: air in through the nose vents, along the bay, out through belly slots behind the shelf
    for s in (-1, 1):
        vent = Pos(p.shelf_x1 + 8, s * 14, p.pod_bottom - 1) * Box(30, 8, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body = body - ctx.cut(vent & Pos(0, 0, -200) * Box(1000, 1000, 200 + p.pod_bottom + 25, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                              why="air outlet: ESC / VTX heat leaves under the tail", kind="vent")
    # electronics shelf over the battery bay (prints standing: a vertical plate, no overhang)
    shelf = Pos(p.pod_x0 + 30, 0, p.bay_top) * Box(p.shelf_x1 - p.pod_x0 - 30, 200, SHELF_T, align=(Align.MIN, Align.CENTER, Align.MIN))
    body = body + ctx.add(shelf & _loft(fuselage_sections(p)), why="shelf: electronics above, battery bay below", kind="shelf")
    # front bosses + inserts for the nose; rear bosses + inserts for the motor mount
    for (y, z) in nose_bolts(p):
        body = body + ctx.add(boss(p.pod_x0, y, z, BOSS_L, BOSS_D, +1) & _loft(fuselage_sections(p)), why="nose insert boss", kind="boss")
    for (y, z) in mount_bolts(p):
        body = body + ctx.add(boss(p.pod_x1, y, z, BOSS_L, BOSS_D, -1) & _loft(fuselage_sections(p)), why="motor-mount insert boss", kind="boss")
    front = Location(Plane(origin=(p.pod_x0, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))     # local (u, v) = world (y, -z)
    body = body - iface.bolt_pattern(ctx, "nose", "M3", [(y, -z) for (y, z) in nose_bolts(p)], front, kind="heatset", depth=BOSS_L)
    rear = Location(Plane(origin=(p.pod_x1, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))       # local (u, v) = world (y, z)
    body = body - iface.bolt_pattern(ctx, "motor_mount", "M3", mount_bolts(p), rear, kind="heatset", depth=BOSS_L)
    # why: the motor's three phase leads pass through the rear wall (and the mount's lead hole) from the ESC
    body = body - Pos(p.pod_x1, 0, lead_hole_z(p)) * Rot(0, 90, 0) * Cylinder(LEAD_HOLE_D / 2, 12)
    # why: VTX antenna MMCX lead out through the top skin to the antenna standing on the pod
    body = body - Pos(p.ant_x, 0, p.pod_top) * Cylinder(3.5, 12)
    # spar sleeves: ONE V-shaped sleeve per tube pair, wall to wall, so a wing half's bending moment goes tube ->
    # sleeve -> the other half's tube (the side walls only see shear); teardrop section with its point toward the
    # bed (+X: the pod prints standing on its rear face), so the sleeve's underside needs no support
    hull = _loft(fuselage_sections(p))
    for which, od in (("main", p.main_od), ("rear", p.rear_od)):
        ends = []
        for s in (-1, 1):
            a, b = (np.array(v) for v in L.tube_line(p, which, s))
            u = (b - a) / np.linalg.norm(b - a)
            ends.append(a + u * ((p.pod_hw - abs(a[1])) / abs(u[1])))           # where the line meets the side face
            centre = a - u * (abs(a[1]) / abs(u[1]))                              # where it meets the centreline
        sleeve = sections.teardrop_channel([tuple(ends[0]), tuple(centre), tuple(ends[1])], od + SLEEVE_WALL[which] * 2, up=(1, 0, 0))
        body = body + ctx.add(sleeve & hull, why=f"{which} spar sleeve, wall to wall: carries the wing's root moment across", kind="sleeve")
    for s in (1, -1):
        for which, od in (("main", p.main_od), ("rear", p.rear_od)):
            a, b = L.tube_line(p, which, s)
            body = body - ctx.cut(aero.cylinder_between(a, b, od + 0.2, extend=0.0), why=f"{which} spar tube, close fit", kind="spar bore")
        # wing root bolts: from inside, through the side wall into the inner segment's inserts
        loc = Location(Plane(origin=(0, s * (p.pod_hw - SKIN), 0), x_dir=(1, 0, 0), z_dir=(0, -s, 0)))
        local = [(p.root_bolt_x1, s * p.root_bolt_z1), (p.root_bolt_x2, s * p.root_bolt_z2)]
        body = body - iface.bolt_pattern(ctx, f"wing_root_{'l' if s < 0 else 'r'}", "M3", local, loc, kind="clearance", depth=SKIN + 0.01,
                                   teardrop="auto")
        a, b = L.lead_line(p, s)
        body = body - ctx.cut(aero.cylinder_between(a, b, 8.0, extend=1.0), why="elevon servo lead into the bay", kind="wire hole")
        ctx.rigid(f"wing_{'l' if s < 0 else 'r'}", Location())
    body, failed = fillet_inside(ctx, body, r=2.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    # spar tubes: rod proxy frame = origin at one end, +Z along the tube
    for s in (1, -1):
        for which in ("main", "rear"):
            a, b = (np.array(v) for v in L.tube_line(p, which, s))
            ctx.rigid(f"{which}_{'l' if s < 0 else 'r'}", Location(Plane(origin=tuple(a), z_dir=tuple(b - a))))
    ctx.rigid("nose", Location())
    ctx.rigid("hatch", Location())
    ctx.rigid("motor_mount", Location())
    floor = p.pod_bottom + SKIN
    # battery: catalog box (length along x, width across, height up) on the bay floor
    bat = ctx.cat.get(L.BATTERY)
    bl, bh = ctx.cat.num(bat, "length"), ctx.cat.num(bat, "height")
    ctx.rigid("battery", Location((p.bat_x, 0, floor)))
    ctx.rigid("xt60", Location((p.bat_x - bl / 2 - 14, 0, floor)))
    ctx.rigid("strap", Location((p.bat_x, 0, floor + bh)))
    zs = shelf_z(p)
    ctx.rigid("gps", Location((p.pod_x0 + 50, 0, zs)))
    ctx.rigid("fc", Location((p.fc_x, -12, zs)))
    ctx.rigid("rx", Location((p.fc_x, 12, zs)))
    ctx.rigid("esc", Location((p.esc_x, 0, zs)))
    ctx.rigid("vtx", Location((p.vtx_x, 0, zs)))
    ctx.rigid("vtx_ant", Location((p.ant_x, 0, p.pod_top)))
    return ctx.finish(body)
