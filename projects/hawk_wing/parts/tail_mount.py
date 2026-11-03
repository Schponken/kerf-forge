"""Tail mount (PETG, 4 walls): the block on the end of the carbon boom that carries the whole tail.

- Boom socket: a blind bore (boom OD + 0.2, epoxied) on the boom axis from the mount's front face to the boom's rear
  end (boom_x1), closed by a 2 mm end cap. The aft face is flat: the part prints standing on it, so the bore is round.
- Stabiliser seat underneath: over the stabiliser the body reaches down to its chord plane and the stabiliser solid
  is subtracted, so the underside is the stabiliser's own upper surface (the load spreads over the whole chord). A
  wider block at 30 % chord carries two M3 heat-set inserts (group `hstab`); the screws come up from under the stab.
- Fin seat on top: a flat top with a 3 mm blade the fin's root slot is glued over (group `fin`, glued, no screws).
- Elevator and rudder servos (KST X08 Plus) lie in tandem above the boom, output sideways: elevator servo output to
  the right (its arm drives a pushrod to the horn on the elevator's top), rudder servo output to the left (pushrod to
  the horn on the rudder's left side). Each sits in a through pocket, tabs on the side face, case glued in (yaml
  held_by); the lead bump leaves through the opposite face and the lead runs forward along the boom.
Print: standing on the aft face (print_rot [0, 90, 0]); pocket ends, blade and seat-block ends are 45 deg.
"""
import math

from build123d import *
from kerf import aero, iface
from kerf.features import fillet_inside

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

WALL = 1.6            # structural wall (docs/ENGINEERING.md s5)
BORE_CLEAR = 0.2      # epoxied boom socket: OD + 0.2 (DESIGN.md)
CAP = 2.0             # end cap behind the boom's rear end
SERVO_CLEAR = 0.3     # per side round the servo case
HALF_W = 7.5          # upper body half width = servo tab faces (|y|)
CORNER_R = 3.0        # upper body section corner radius
INS_Y = 8.5           # stab screws at |y|: 2.4 mm wall to the boom bore, 4.5 (1.5 d) to the block side
INS_FRAC = 0.30       # stab screws at the section's thickest point
BLOCK_HW = 13.0       # insert block half width
INS_ABOVE = 7.5       # insert block top above the stab's upper surface at the screws (insert depth 6.7 + 0.8 floor)
BLADE_T, BLADE_H = 3.0, 10.0   # fin blade: thickness, height above the top
SLOT_CLEAR = 0.15     # fin slot over the blade, per side (glued)
FRONT = 2.5           # mount front ahead of the fin's leading edge (the fin root clears the front chamfer)
SEAT_GAP = 3.0        # seat stops this far ahead of the elevator hinge line (>= 0.5 mm to the elevator at full up)


def dims(p):
    """Numbers the tail parts share (tail_mount, hstab, fin, rudder, elevator)."""
    sd = iface.servo_dims(L.SURF_SERVO)
    pf = L.tail_planform(p)
    r_bore = (p.boom_od + BORE_CLEAR) / 2
    z_pocket0 = p.boom_z + r_bore + WALL
    z_servo = z_pocket0 + SERVO_CLEAR + sd["W"] / 2
    top = z_servo + sd["W"] / 2 + SERVO_CLEAR + WALL
    boom_top = p.boom_z + p.boom_od / 2
    x_fin_le = p.boom_x1 - p.fin_root + (top - boom_top) * math.tan(math.radians(p.fin_sweep_deg))
    half = p.htail_span / 2
    hinge_x = aero.hinge_axis(pf, -half, half, p.elev_hinge_frac)[0][0]
    return {"sd": sd, "r_bore": r_bore, "z_servo": z_servo, "top": top, "bot": p.boom_z - r_bore - WALL,
            "boom_top": boom_top, "x0": x_fin_le - FRONT, "x1": p.boom_x1 + CAP, "hinge_x": float(hinge_x),
            "seat_x1": float(hinge_x) - SEAT_GAP,
            # each servo's arm plane (|y|): 1.75 mm inside the spline tip
            "arm_y": HALF_W + sd["top"] + sd["shaft_h"] - 1.75}


def servo_x(p, which):
    """Body centre x of the rudder (front) and elevator (aft) servo: front wall + 45 deg pocket nose + body, tandem."""
    d = dims(p)
    sd = d["sd"]
    nose = sd["W"] / 2 + SERVO_CLEAR
    front = d["x0"] + 2.0 + nose + SERVO_CLEAR
    if which == "elev":
        front += sd["L"] + 2 * SERVO_CLEAR + WALL + nose
    return front + sd["L"] / 2


def servo_loc(p, which):
    """Servo proxy 'tabs' frame: tab underside on the side face, output sideways (elevator +Y, rudder -Y), output end aft."""
    d = dims(p)
    s = 1 if which == "elev" else -1
    return Location(Plane(origin=(servo_x(p, which), s * HALF_W, d["z_servo"]), x_dir=(1, 0, 0), z_dir=(0, s, 0)))


def ins_points(p):
    """(x, z of the stab's upper surface, z of its lower surface) at the stab screws."""
    pf = L.tail_planform(p)
    x = pf.x_le(INS_Y) + INS_FRAC * pf.chord(INS_Y)
    c = pf.chord(INS_Y)
    zu, zl = aero.mid_z(pf.section_af(INS_Y), INS_FRAC)
    te = pf.te_min / 2 * INS_FRAC
    return x, p.htail_z0 + zu * c + te, p.htail_z0 + zl * c - te


def block_top(p):
    """Insert block top: INS_ABOVE over the stab's upper surface at the screws (follows htail_z0 and the airfoil)."""
    return ins_points(p)[1] + INS_ABOVE


def blade(p, grow=0.0):
    """Fin blade on the mount top (grow > 0: the fin's slot over it). Front end vertical, aft end leaning forward at
    45 deg and a 45 deg ridge on top, so neither the mount (standing on its aft face) nor the fin (standing on its
    root) prints a flat ceiling."""
    d = dims(p)
    top = d["top"]
    c = p.fin_root - (top - d["boom_top"]) / p.fin_h * (p.fin_root - p.fin_tip)
    xle = d["x0"] + FRONT
    xa = xle + 0.18 * c - grow
    xb = xle + (p.rud_hinge_frac - 0.12) * c + grow
    h = BLADE_H + grow
    t = BLADE_T / 2 + grow
    side = Plane.XZ * Polygon((xa, top - 1), (xb + 1, top - 1), (xb, top), (xb - h, top + h), (xa, top + h), align=None)
    side = extrude(side, amount=t, both=True)
    ridge = Plane.YZ * Polygon((-t, top - 1), (t, top - 1), (t, top + h - t), (0, top + h), (-t, top + h - t), align=None)
    ridge = Pos(xa - 2, 0, 0) * extrude(ridge, amount=xb - xa + 4)
    return side & ridge


def build(ctx):
    p = ctx.p
    d = dims(p)
    sd = d["sd"]
    x0, x1, top, bot = d["x0"], d["x1"], d["top"], d["bot"]
    # upper body: rounded section round the boom and the two servo pockets
    sec = Plane.YZ.offset(x0) * Pos(0, (top + bot) / 2) * RectangleRounded(2 * HALF_W, top - bot, CORNER_R)
    body = extrude(sec, amount=x1 - x0)
    body = chamfer(body.faces().sort_by(Axis.X)[0].edges(), 2.0)       # why: front face eased into the airflow
    # over the stabiliser: down to its chord plane, then the stab subtracted -> the seat follows its upper surface
    pf = L.tail_planform(p)
    seat = Pos(p.htail_x_le0, 0, p.htail_z0) * Box(d["seat_x1"] - p.htail_x_le0, 2 * HALF_W, bot - p.htail_z0 + 1.0,
                                                    align=(Align.MIN, Align.CENTER, Align.MIN))
    body += ctx.add(seat, why="seat on the stabiliser's upper surface over its chord (spreads the stab load)", kind="seat")
    xi, zt, _ = ins_points(p)
    BLOCK_TOP = block_top(p)
    blk = Plane.XZ * Polygon((xi - 10, p.htail_z0), (xi + 10 + (BLOCK_TOP - p.htail_z0), p.htail_z0), (xi + 10, BLOCK_TOP),
                             (xi - 10, BLOCK_TOP), align=None)
    blk = extrude(blk, amount=BLOCK_HW, both=True)
    blk = fillet(blk.edges().filter_by(Axis.X).group_by(Axis.Z)[-1], 1.0)     # why: outside edges broken (handling)
    body += ctx.add(blk, why="block for the two stab-screw heat-set inserts (aft end 45 deg: prints standing)", kind="boss")
    stab = aero.wing_solid(pf, -BLOCK_HW - 5, BLOCK_HW + 5, stations=3)
    body -= ctx.cut(stab, why="the stabiliser sits here: the seat is its own upper surface", kind="seat")
    # boom socket: blind bore to the boom's rear end
    bore = Pos(x0 - 1, 0, p.boom_z) * Rot(0, 90, 0) * Cylinder(d["r_bore"], p.boom_x1 - x0 + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= ctx.cut(bore, why="boom socket, OD + 0.2, epoxied", kind="socket")
    # fin blade
    body += ctx.add(blade(p), why="blade the fin's root slot is glued over", kind="tab")
    # servo pockets: through in Y (servo slides in output-last from the tab side), lead bump through the far face,
    # nose of the pocket a 45 deg chevron (no flat ceiling standing on the aft face)
    lead_h = ctx.cat.num(ctx.cat.get(L.SURF_SERVO), "lead_bump_h")
    lead_l = ctx.cat.num(ctx.cat.get(L.SURF_SERVO), "lead_bump_l")
    hz = sd["W"] / 2 + SERVO_CLEAR
    for which in ("rud", "elev"):
        s = 1 if which == "elev" else -1
        xc = servo_x(p, which)
        xf, xb = xc - sd["L"] / 2 - SERVO_CLEAR, xc + sd["L"] / 2 + SERVO_CLEAR
        y_in = s * (HALF_W - sd["tab_z"] - SERVO_CLEAR)
        y_out = s * (HALF_W + 1.0)
        pocket = Pos(xf, min(y_in, y_out), d["z_servo"] - hz) * Box(xb - xf, abs(y_out - y_in), 2 * hz, align=(Align.MIN, Align.MIN, Align.MIN))
        y_far = -s * (HALF_W + 1.0)
        bump = Pos(xf, min(y_in, y_far), d["z_servo"] - hz) * Box(lead_l + 2 * SERVO_CLEAR, abs(y_in - y_far), 2 * hz,
                                                                   align=(Align.MIN, Align.MIN, Align.MIN))
        nose = Plane.XZ * Polygon((xf + 0.01, d["z_servo"] - hz), (xf + 0.01, d["z_servo"] + hz), (xf - hz, d["z_servo"]), align=None)
        nose = extrude(nose, amount=HALF_W + 1.0, both=True)
        name = "elevator" if which == "elev" else "rudder"
        body -= ctx.cut(pocket + bump + nose, why=f"{name} servo pocket (case glued), its lead exit through the far face", kind="pocket")
        ctx.rigid(f"{which}_servo", servo_loc(p, which))
    # stab screws: 2 M3 from below into heat-set inserts
    loc = Location(Plane(origin=(xi, 0, zt), x_dir=(1, 0, 0), z_dir=(0, 0, -1)))
    body -= iface.bolt_pattern(ctx, "hstab", "M3", [(0, INS_Y), (0, -INS_Y)], loc, kind="heatset",
                               depth=BLOCK_TOP - zt, teardrop="auto")

    def keep(at):
        if abs(at[2] - d["z_servo"]) < 6 and abs(abs(at[1]) - HALF_W) < 12:
            return "the servo's square case sits in the pocket"
        return None
    body, failed = fillet_inside(ctx, body, r=1.0, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    for k in ("base", "hstab", "fin"):
        ctx.rigid(k, Location())
    return ctx.finish(body)
