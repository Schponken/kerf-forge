"""Sled: the wheeled carriage the strands throw down the rail (frame: rail top centre line under the sled's middle,
rail z = 40 -> sled z = 0; X toward the nose).

Load path (DESIGN.md "Load cases"): six strand loops (79 N each, 474 N) hold on the tow comb at the front -> comb wall and
gussets -> deck + spine + side ribs (tension, ~1 MPa) -> tail lugs -> tail pin -> rollers -> trigger hook. The brake cord
pushes the bumper wall (860 N) straight back into the same deck/ribs. The four wheel bosses carry the wheel clamp loads
into the ribs. Printed UPRIGHT (bed = rib/boss bottoms at z = Z0): ribs and walls stand vertically, the 4 mm deck bridges
12 mm gaps, the comb slots open upward, horizontal pin holes are teardrops.
"""
from build123d import *
from kerf import features, iface

WHEEL = "motion.vwheel_delrin_solid"
TAIL_PIN = "rods.ss_rod_5"
CRADLE_PIN = "rods.ss_rod_4"
Z0 = 1.115          # underside = wheel top (-4.885) + 6 mm spacer: the spacer seat over each wheel
Z_DECK0, Z_SEAT = 8.0, 12.0   # deck 4 mm; its top is the cradle seat (cradle frame z = 0)
X_REAR, X_COMB = -66.0, 72.0  # deck rear end (tail hook zone behind it); comb wall rear face
RIB_T = 3.2


def _box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


def _cyl(x, y, r, z0, z1):
    return Pos(x, y, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _prism_xz(pts, y0, y1):
    """Polygon given in (x, z), extruded between y0 and y1."""
    s = extrude(make_face(Polyline(*pts, close=True)), y1 - y0)
    return Pos(0, y1, 0) * (Rot(90, 0, 0) * s)


def build(ctx):
    p = ctx.p
    wh = ctx.cat.get(WHEEL)
    hl, tow_x = p.SLED_HALF, p.TOW_DX
    z_t = p.Z_TOP - p.H                         # strand centre line, sled frame (28)
    wy, wx = p.WHEEL_Y, 50.0                    # wheel axle positions (contract: +-50, +-WHEEL_Y)
    ys = p.STRAND_Y
    pitch = p.STRAND_PITCH
    z_slot = z_t - 4.0                          # slot floor: tubing OD 7.94 centred on the strand line
    ecc = float(wh["eccentric_spacer"]["plate_hole_d"])

    # --- deck (cradle seat), spine, side ribs, edge walls, cross ribs, wheel bosses
    body = _box(X_REAR, X_COMB, -36, 36, Z_DECK0, Z_SEAT)   # why: cradle seat + roof of the rib grid
    body += ctx.add(_box(X_REAR, X_COMB, -5, 5, Z0, Z_DECK0), "spine rib: carries the strand pull front to back and the cradle pin holes", "rib")
    for s in (1, -1):
        body += ctx.add(_box(X_REAR, X_COMB, s * wy - RIB_T, s * wy + RIB_T, Z0, Z_DECK0), "side rib through the wheel axles: wheel clamp loads into the deck", "rib")
        body += ctx.add(_box(X_REAR, X_COMB, s * 34.4 - 0.8, s * 36, Z0, Z_DECK0), "edge wall: stiffens the deck edge", "rib")
    for x in (-wx, 0.0, wx, X_COMB - 1.5):
        body += ctx.add(_box(x - 1.5, x + 1.5, -36, 36, Z0, Z_DECK0), "cross rib: closes the grid, braces the wheel bosses", "rib")
    for sx in (1, -1):
        for sy in (1, -1):
            body += ctx.add(_cyl(sx * wx, sy * wy, 8.0, Z0, Z_DECK0), "wheel boss: M5 axle, spacer seat at the underside", "boss")

    # --- bumper wall (brake cord 860 N) + tow comb (6 x 79 N)
    body += ctx.add(_box(X_COMB, hl, -36, 36, Z0, 16.0), "bumper wall: the brake cord pushes it at z 7; backed by the deck ribs", "bumper")
    body += ctx.add(_box(X_COMB, tow_x, -36, 36, 16.0, z_slot), "tow wall under the comb: strand loops bear on its rear face", "wall")
    divs = [(i - 3) * pitch for i in range(7)]            # 7 dividers between 6 slots
    for yd in divs:
        body += ctx.add(_box(X_COMB, tow_x, yd - 2.5, yd + 2.5, z_slot, z_t + 8.0),
                        "comb divider: holds the neighbouring strand loops (open slots, loops drop in from above)", "hook")
        body += ctx.add(_prism_xz([(X_COMB - 6, Z_SEAT), (X_COMB, Z_SEAT), (X_COMB, 20.0)], yd - 2, yd + 2),
                        "gusset behind the comb: takes the strand pull bending out of the wall root", "gusset")

    # --- tail lugs: the pin carries the trigger hook's 474 N
    for s in (1, -1):
        ya, yb = (6.0, 11.5) if s > 0 else (-11.5, -6.0)
        lug = _box(-87.0, X_REAR + 4, ya, yb, Z0, 10.0)
        lug += Pos(-79.0, (ya + yb) / 2, 10.0) * Rot(90, 0, 0) * Cylinder(8.0, yb - ya)
        body += ctx.add(lug, "tail lug: rounded around the pin, flat bottom for the bed; plate loaded in-plane", "lug")

    # --- cuts
    # tail pin (press) through both lugs; horizontal -> teardrop (printed upright)
    for s in (1, -1):
        ya, yb = (6.0, 11.5) if s > 0 else (-11.5, -6.0)
        loc = Location((-79.0, yb if s > 0 else ya, 10.0), (-90 * s, 0, 0)) if False else Location((-79.0, yb if s > 0 else ya, 10.0), (-90, 0, 0) if s > 0 else (90, 0, 0))
        body -= ctx.cut(iface.pin_hole(ctx, TAIL_PIN, loc, "tail_pin", yb - ya, fit="press"), "tail pin press fit through the lug", "pin hole")
    # cradle pins: free in the sled, 10 deep from the seat
    for x in (60.0, -60.0):
        body -= ctx.cut(iface.pin_hole(ctx, CRADLE_PIN, Location((x, 0, Z_SEAT)), "cradle_pins", 10.0, fit="free", through=False),
                        "cradle locating pin hole (the pin is pressed in the cradle)", "pin hole")
    # wheel axles: M5 from the top, screw head recessed under the cradle; wheels 3, 4 get the eccentric spacer hole
    for i, (sx, sy) in enumerate([(1, 1), (-1, 1), (1, -1), (-1, -1)], 1):
        c = iface.bolt_pattern(ctx, "wheel_axles", "M5", [(0, 0)], Location((sx * wx, sy * wy, Z_SEAT)), "counterbore", Z_SEAT - Z0)
        if i >= 3:
            c += _cyl(sx * wx, sy * wy, ecc / 2, Z0 - 1, Z_SEAT - 5.5)   # eccentric spacer rim seat (catalog plate_hole_d)
        body -= ctx.cut(c, f"wheel {i} axle hole" + (" with eccentric spacer seat" if i >= 3 else ""), "axle")
    # snap windows: the cradle's two snap noses go through the deck and catch under its underside (lip)
    for s in (1, -1):
        y0, y1 = sorted((s * 9.5, s * 13.4))
        body -= ctx.cut(_box(-48.0, -36.0, y0, y1, Z_DECK0 - 0.1, Z_SEAT + 0.1), "window for the cradle snap nose; its underside edge is the catch lip", "snap window")

    ctx.rigid("carriage", Location((0, 0, 0)))
    wz = p.WHEEL_Z - p.WHEEL_W / 2 - p.H
    for i, (x, y) in enumerate([(wx, wy), (-wx, wy), (wx, -wy), (-wx, -wy)], 1):
        ctx.rigid(f"wheel_{i}", Location((x, y, wz)))
    ctx.rigid("tail_pin", Location((-79.0, 0, 10.0), (-90, 0, 0)))
    ctx.rigid("tail_roller_1", Location((-79.0, -5, 10.0), (-90, 0, 0)))
    ctx.rigid("tail_roller_2", Location((-79.0, 0, 10.0), (-90, 0, 0)))
    ctx.rigid("strands", Location((tow_x, 0, z_t)))
    ctx.rigid("cradle", Location((0, 0, Z_SEAT)))
    body, left = features.fillet_inside(ctx, body, 1.0)
    return ctx.finish(body)
