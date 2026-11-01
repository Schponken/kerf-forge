"""One bolt-on arm (arm_1..arm_4 share this file; the item id picks the fastener groups).

Frame: X along the arm from the frame centre, arm TOP face at z = 0 (it sits under the body plate), bottom at
z = -arm_t. The root is clamped under the body by two M3 x 12 from below into nut traps in the body (nuts sunk 1 mm, tips stay under the body top); two 4.5 x 1.5 mm
ridges on the top edges sit in grooves in the body underside, so side hits load the ridges, not the two screws.
The motor sits on the top face at r = motor_r on four M3 x 10 (counterbored for a 7.5 mm grip: 2.5 mm into the
motor's ~3 mm deep threads, a screw-length tolerance short of the bottom). Prints flat, top up: bending runs along
the layers, the ridges print on top.
Motor wires: a covered channel on the top face past the body (two low rails, floor 1 mm under the top face, the
wires below the rail tops) with two cable-tie slots through the rail feet, so no slot cuts the arm at mid-depth where
the crash load's shear peaks. The rails raise the section (stiffer, about the mass the channel removes). The ridge
roots carry 0.5 mm fillets (they fit the body grooves' 0.4 mm mouth chamfer plus 0.2 mm clearance). Under the motor
pad the outer bottom edge is a 1 mm 45-degree skid chamfer: a landing or crash slides on it instead of catching the
edge; the motor screw heads sit 0.5 mm deep in their counterbores.
"""
from build123d import *
from kerf import iface, features as F

MOTOR = "drone.motors.2207_1855kv_6s"
TIP_W = 14.0                                    # arm width where it meets the motor pad (20 at the root)
RIDGE_W, RIDGE_H, RIDGE_R1 = 4.5, 1.5, 58.0     # key ridges: width, height, outer end radius (4.5 wide: a 33 N side
#                                                 hit bends the ridge root across one layer line at ~3 MPa, review round 2)
RIDGE_FILLET = 0.5          # ridge root fillet: <= body GROOVE_CH 0.4 + 0.2 clearance - 0.1 margin, so it clears the groove
WIRE_X0, WIRE_X1 = 64.0, 95.0   # wire channel: from past the body corner (r 61.7 on the arm line) to short of the motor bell
CH_W, CH_FLOOR, RAIL_W, RAIL_H = 7.0, 1.0, 2.5, 1.6   # 3 x 18 AWG silicone (~2 mm OD) side by side, 2.6 mm deep: below the rail tops
TIE_X = (68.0, 88.0)        # cable-tie slots through the rail feet (2.5 mm ties)
SKID = 1.0                  # 45 deg chamfer on the motor pad's outer bottom edge


def build(ctx):
    p = ctx.p
    n = ctx.id.split("_")[1]
    t, w = p.arm_t, p.arm_w
    pad_d = 32.0                                    # motor bell 29.1 mm + margin: a solid pad under the whole motor base
    # full width over the clamped root and the key ridges, then tapered toward the motor pad: the crash moment falls
    # linearly to zero at the motor, so the outer arm needs less section (audit F3: mass for T/W >= 6)
    x_pad = p.motor_r - pad_d / 2 + 1.0
    outline = Polyline((p.arm_r0, -w / 2), (RIDGE_R1, -w / 2), (x_pad, -TIP_W / 2), (p.motor_r, -TIP_W / 2),
                       (p.motor_r, TIP_W / 2), (x_pad, TIP_W / 2), (RIDGE_R1, w / 2), (p.arm_r0, w / 2), close=True)
    body = Pos(0, 0, -t) * extrude(make_face(outline), t)
    body += Pos(p.motor_r, 0, -t) * Cylinder(pad_d / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += Pos(p.arm_r0, 0, -t) * Cylinder(w / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN))  # rounded root
    body, failed = F.safe_fillet(body, [(body.edges().filter_by(Axis.Z).filter_by_position(Axis.X, p.motor_r - pad_d / 2 - 2, p.motor_r), 4.0)])
    for f in failed:
        ctx.notes.append(f"fillet skipped: {f}")
    # skid: the pad's outer bottom edge (beyond the motor centre) chamfered 45 deg, printable on the bed face
    skid = [e for e in body.edges().filter_by_position(Axis.Z, -t - 0.01, -t + 0.01) if e.center().X > p.motor_r + 1]
    body, failed = F.safe_fillet(body, [(skid, SKID)], kind="chamfer")
    for f in failed:
        ctx.notes.append(f"skid chamfer skipped: {f}")
    for sy in (1, -1):                              # key ridges along both top edges under the body
        body += ctx.add(Pos(p.arm_r0, sy * (w / 2 - RIDGE_W / 2), 0) * Box(RIDGE_R1 - p.arm_r0, RIDGE_W, RIDGE_H,
                                                                          align=(Align.MIN, Align.CENTER, Align.MIN)),
                        why="side hits go into the body's groove walls, not the two arm screws", kind="key ridge")
    roots = [e for e in body.edges().filter_by_position(Axis.Z, -0.01, 0.01)
             if (abs(abs(e.center().Y) - (w / 2 - RIDGE_W)) < 0.01 and e.center().X < RIDGE_R1)
             or (abs(e.center().X - RIDGE_R1) < 0.01 and abs(abs(e.center().Y) - (w / 2 - RIDGE_W / 2)) < 0.01)]
    body, failed = F.safe_fillet(body, [(roots, RIDGE_FILLET)])
    for f in failed:
        ctx.notes.append(f"ridge root fillet skipped: {f}")
    # covered wire channel: rails up, floor down. Rails: 60 deg outer flanks (no sharp root), 45 deg ramps at the ends;
    # channel: 45 deg ramps at the ends so the wires bend gently in and out, floor corners filleted
    cw = CH_W + 2 * RAIL_W
    fl = RAIL_H / 1.732                              # 60 deg flank: base half-width cw/2 + 0.7 (arm half-width >= 7.2)
    sec = Polyline((-cw / 2 - fl, 0), (-cw / 2, RAIL_H), (cw / 2, RAIL_H), (cw / 2 + fl, 0), close=True)
    side = Polyline((WIRE_X0, 0), (WIRE_X0 + RAIL_H, RAIL_H), (WIRE_X1 - RAIL_H, RAIL_H), (WIRE_X1, 0), close=True)
    rails = (Pos(WIRE_X0 - 1, 0, 0) * extrude(Plane.YZ * make_face(sec), amount=WIRE_X1 - WIRE_X0 + 2)) & \
        extrude(Plane.XZ * make_face(side), amount=cw, both=True)
    body += ctx.add(rails, why="raise the section over the channel (stiffer) and keep the motor wires below the rail tops",
                    kind="wire rails")
    top = RAIL_H + 1
    cside = Polyline((WIRE_X0 - CH_FLOOR, 0), (WIRE_X0, -CH_FLOOR), (WIRE_X1, -CH_FLOOR), (WIRE_X1 + CH_FLOOR, 0),
                     (WIRE_X1 + CH_FLOOR, top), (WIRE_X0 - CH_FLOOR, top), close=True)
    chan = extrude(Plane.XZ * make_face(cside), amount=CH_W / 2, both=True)
    body -= ctx.cut(chan, why="motor phase wires ride in a channel near the top face, out of the mid-depth shear zone",
                    kind="wire channel")
    yt = cw / 2 + fl + CH_FLOOR                # tie notch: through the rail feet, ramping up 45 deg past them
    tside = Polyline((-yt, 0), (-yt + CH_FLOOR, -CH_FLOOR), (yt - CH_FLOOR, -CH_FLOOR), (yt, 0), (yt, 0.4), (-yt, 0.4), close=True)
    for x in TIE_X:
        body -= ctx.cut(Pos(x - 1.5, 0, 0) * extrude(Plane.YZ * make_face(tside), amount=3.0),
                        why="cable tie under the wires and over the rails; cuts only the rail feet near the top face",
                        kind="tie slot")
    under = Location((0, 0, -t), (180, 0, 0))       # bottom face, +Z toward the screw heads (down)
    body -= iface.bolt_pattern(ctx, f"arm_{n}", "M3", [(p.arm_hole_1, 0), (p.arm_hole_2, 0)], under, "counterbore",
                               depth=t, counterbore_depth=t - 6.0)  # grip 6 -> M3 x 12 into the sunk body nut
    body -= iface.motor_mount(ctx, MOTOR, Location((p.motor_r, 0, -t), (180, 0, 0)), f"motor_{n}", plate_t=t,
                              kind="counterbore", counterbore_depth=t - 7.5)  # grip 7.5 -> M3 x 10, 2.5 mm in the motor
    # why: every remaining sharp inside corner rounded (r 0.5, the channel's scale; ENGINEERING.md s5). Left square: the
    # tie slots' own corners (3 mm slots the tie bears on, in the outer arm where the crash moment is at most 74 % of its
    # value at the outer clamp screw) and the ridges' inner ends (against the body groove's closed end)
    def keep(at):
        x, y, z = at
        if min(abs(x - xt) for xt in TIE_X) < 1.6 and z > -CH_FLOOR - 0.05:
            return "cable-tie slot corner: the tie bears on it; outer arm, at most 74 % of the clamp-screw crash moment"
        if abs(x - p.arm_r0) < 0.3 and z > -0.05:
            return "key ridge's inner end, square against the body groove's closed end"
        if abs(z) < 0.05 and min(abs(x - WIRE_X0), abs(x - WIRE_X1)) < 1.6 and abs(y) > CH_W / 2:
            return ("rail end: an open 135-degree corner where the 45-degree end ramp meets the arm top beside the 60-degree "
                    "flank; OCC cannot fillet the junction (the mirror one takes it); outer arm, compression side")
        return None
    body, left = F.fillet_inside(ctx, body, 0.5, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    ctx.rigid("root", Location((0, 0, 0)))
    ctx.rigid("motor", Location((p.motor_r, 0, 0)))
    return ctx.finish(body, color="#2a2d31")
