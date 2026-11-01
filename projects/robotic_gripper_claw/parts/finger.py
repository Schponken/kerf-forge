"""Finger, used twice: finger_l (drive: bolted to the grip horn) and finger_r (idler: turns on the idler dowel).

Finger frame: origin on the finger's gear axis at the gear's bottom face (= grip horn face height), X toward the pad
(along the claw when closed), Z up along the gear axis (claw Y), Y = -claw Z. finger_l's pad faces -Y, finger_r's +Y.
The arm is drawn once in an "inward" frame (u = toward the claw's centre line) and mirrored for the drive finger.

Load path (DESIGN.md 'Load -> section'): the object pushes the pad outward; the jaw carries it to the arm, the arm
bends back to the hub (moment 0 at the pad -> 461 N*mm at the hub), the hub hands it to the horn screws (drive) or the
dowel + gear teeth (idler). So the arm tapers from 8 mm deep at the hub to 6 mm at the jaw, 12 mm tall (= the gear),
printed flat on the gear face so it bends along the layers.

Pad geometry (DESIGN.md 'Jaw angle'): the pad face passes through the contact point P (finger_len along the finger,
dz_pad inward, 1 mm gap at the centre line when closed) and is turned pad_par degrees inward toward the tip, so the two
faces are parallel when each finger has opened pad_par degrees (a 35 mm object). The pad therefore ends AT P (its tip
end is the closest point of the two jaws when closed) and runs 20 mm back toward the palm.
"""
import importlib.util as _iu
import math
import pathlib as _pl

import numpy as np
from build123d import *
from kerf import drives, iface
from kerf.features import safe_fillet

_s = _iu.spec_from_file_location("claw_pad", _pl.Path(__file__).with_name("pad.py"))
pad = _iu.module_from_spec(_s)
_s.loader.exec_module(pad)

HORN = "servo_horns.aluminum_25T"
JAW_T = 6.5          # jaw behind the pad's back face: dovetail groove 3.9 deep + 2.6 wall (>= 2.4, ENGINEERING.md s5)
SLIDE = 0.15         # dovetail clearance all round (measured on the Clamp-On Vise, REFERENCES.md D7)
HUB_R = 11.5         # smooth hub outside the toothed sector: clears the other gear (its tips reach r 10.5 only at the mesh)
ARM_D0 = 8.0         # arm depth at the hub (at the jaw end it is set by the jaw's corners: ~6 mm)
RAMP = 8.0           # jaw top rises from the arm top (gear_w) to PAD_H over this length (45 deg-ish, prints as a slope)
MESH_MARGIN = 35.0   # deg of teeth kept beyond the meshing arc (90..90+grip_open in the inward frame): ~1.5 teeth each side
RECESS = 0.5         # extra depth over the horn centre screw's head


def tooth_phase(gear, r_tip, n):
    """Tooth-centre angles (deg, 0..360) of a placed gear: the mid-points of the tip-land edges of its bottom face."""
    bottom = gear.faces().sort_by(Axis.Z)[0]
    mids = [e.position_at(0.5) for e in bottom.outer_wire().edges()]
    tips = sorted(math.degrees(math.atan2(m.Y, m.X)) % 360 for m in mids if math.hypot(m.X, m.Y) > r_tip - 0.05)
    if len(tips) != n:
        raise ValueError(f"tooth probe found {len(tips)} tip lands, expected {n}")
    return tips


def build(ctx):
    p = ctx.p
    drive = ctx.id == "finger_l"
    s = -1.0 if drive else 1.0                      # inward (toward the claw's centre line) in this frame's Y
    if abs(pad.PAD_H - p.pad_h) > 1e-9:
        raise ValueError(f"pad.py PAD_H {pad.PAD_H} != layout pad_h {p.pad_h}")
    H, gw = pad.PAD_H, p.gear_w

    # ---- gear: the pair from kerf.drives (pair X = drive -> idler = claw +Z = this frame's -Y)
    g1, g2, info = drives.spur_pair(p.gear_m, int(p.gear_z), int(p.gear_z), gw)
    gear = Rot(0, 0, -90) * (g1 if drive else g2)
    pitch = 360.0 / p.gear_z
    teeth = tooth_phase(gear, info.tip_d[0] / 2, int(p.gear_z))        # finger-frame angles
    teeth_u = sorted((s * a) % 360 for a in teeth)                                  # the same, inward frame
    gaps_u = [(a + pitch / 2) % 360 for a in teeth_u]
    lo, hi = 90.0 - MESH_MARGIN, 90.0 + p.grip_open + MESH_MARGIN                   # meshing arc + margin
    a0 = max(g for g in gaps_u if g <= lo)                                          # sector edges in tooth gaps
    a1 = min(g for g in gaps_u if g >= hi)

    # ---- pad / jaw geometry in the inward frame (X, u)
    th = math.radians(p.pad_par)
    d = np.array([math.cos(th), math.sin(th)])      # along the pad face, toward the tip
    n = np.array([-math.sin(th), math.cos(th)])     # out of the pad face, toward the object
    P = np.array([p.finger_len, p.dz_pad])          # contact point = the pad's tip end
    O = P - pad.PAD_L / 2 * d - p.pad_t * n         # pad back-face centre (pad origin)
    A_b = P - pad.PAD_L * d - p.pad_t * n           # jaw root, front (pad back face) corner
    A_k = A_b - JAW_T * n                           # jaw root, back corner
    jaw_loc = Location((O[0], O[1], 0), (0, 0, p.pad_par))

    def wedge2d(r=40.0):
        return make_face(Polyline((0, 0), *[(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
                                           for a in np.linspace(a0, a1, 24)], close=True))

    # plan of hub + arm (inward frame): smooth hub outside the toothed sector, arm tapering to the jaw root
    arm2d = make_face(Polyline((0, -ARM_D0 / 2), tuple(A_k), tuple(A_b), (0, ARM_D0 / 2), close=True))
    plan = Sketch() + Circle(HUB_R) + arm2d - wedge2d()
    roots = plan.vertices().filter_by(lambda v: 9.0 < math.hypot(v.X, v.Y) < 12.5 and abs(v.Y) < ARM_D0 / 2 + 0.1)
    plan = fillet(roots, 2.0)                       # why: r 2 where the arm leaves the hub (peak bending moment)
    arm = extrude(plan, gw)
    top = [e for e in arm.edges() if abs(e.center().Z - gw) < 1e-6 and math.hypot(e.position_at(0.5).X, e.position_at(0.5).Y) > HUB_R - 0.6]
    arm, failed = safe_fillet(arm, [(top, 0.6)], kind="chamfer")   # why: edge break on the arm's top edges
    if failed:
        raise ValueError(f"arm edge break failed: {failed}")

    # jaw: plate behind the pad, PAD_H tall; its top ramps up from the arm so no step stands at the root
    side = Polygon((-pad.PAD_L / 2, 0), (pad.PAD_L / 2, 0), (pad.PAD_L / 2, H), (-pad.PAD_L / 2 + RAMP, H),
                   (-pad.PAD_L / 2, gw), align=None)
    jaw = extrude(Plane.XZ * side, JAW_T)           # Plane.XZ extrudes toward -Y: behind the pad's back face
    nose = jaw.edges().filter_by(Axis.Z).filter_by(lambda e: e.center().X > pad.PAD_L / 2 - 0.01 and e.center().Y < -JAW_T + 0.01)
    jaw = fillet(nose, 3.0)                         # why: round nose at the tip's outside corner (no sharp corner on objects)
    jaw_top = [e for e in jaw.edges() if e.center().Z > gw - 0.01 and not (abs(e.center().X + pad.PAD_L / 2) < 0.01)]
    jaw, failed = safe_fillet(jaw, [(jaw_top, 0.6)], kind="chamfer")   # why: edge break on the jaw's top and ramp
    if failed:
        raise ValueError(f"jaw edge break failed: {failed}")
    body_u = arm + jaw_loc * jaw

    # dovetail groove for the pad's tongue: open at the top (the pad slides down), floor STOP above the bed face
    a = pad.TONGUE[0] + SLIDE
    mouth = make_face(Polyline((-a - 0.75, 0.2), (a + 0.75, 0.2), (a, -0.75), (-a, -0.75), close=True))
    groove = extrude(Sketch() + pad.tongue_profile(SLIDE) + mouth, H - pad.STOP + 1.0)   # mouth: clears the pad's r 0.5 neck fillet
    floor = groove.edges().filter_by(lambda e: abs(e.center().Z) < 1e-6 and e.center().Y < -0.5)
    groove = fillet(floor, 0.6)                     # why: r 0.6 in the groove floor corners; the tongue's 0.8 lead-in clears it
    body_u -= jaw_loc * Pos(0, 0, pad.STOP) * groove   # why: dovetail that holds the TPU pad (no glue, no screws)

    teeth_sector = gear & extrude(wedge2d(), gw) if not drive else gear & mirror(extrude(wedge2d(), gw), Plane.XZ)
    body = (mirror(body_u, Plane.XZ) if drive else body_u) + teeth_sector   # why: teeth only on the arc that meshes (0..grip_open + margin)

    if drive:
        # why: 4 x M3 into the grip horn, heads on the gear's top face; holes centred under teeth (most root material)
        start = teeth[0] % 90.0                     # teeth repeat every 90 / 4 deg, so all 4 holes land under one
        body -= iface.horn_mount(ctx, HORN, Location((0, 0, gw)), group="gr_horn", plate_t=gw, kind="clearance", start_deg=start)
        rec = p.head_h + RECESS
        body += Cylinder(iface.screw_spec("M3")["head_d"] / 2 + 0.85, gw - rec, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location((0, 0, rec)))  # why: closes the centre-screw access above the horn screw's head recess (the top dowel bore needs the material)
        # why: blind bore for the cover's top dowel: the second support of the drive axis (span 7 + 0.5 + bore = 12.5)
        body -= iface.pin_hole(ctx, "motion.pin_3mm", Location((0, 0, gw)), "gr_top", depth=p.top_bore, fit="free", through=False)
        ctx.rigid("horn_mount", Location((0, 0, 0), (0, 0, 180)))
    else:
        # why: turns on the idler dowel (pressed in the palm pedestal below, running in the cover above)
        body -= iface.pin_hole(ctx, "motion.pin_3mm", Location((0, 0, gw)), "gr_idler", depth=gw, fit="free")
        ctx.rigid("pivot", Location((0, 0, 0), (0, 0, -90)))
    ctx.rigid("tip", Location((P[0], s * P[1], H / 2)))
    if drive:
        ctx.rigid("pad_seat", Location((O[0], -O[1], H / 2), (0, 0, 180 - p.pad_par)))
    else:
        ctx.rigid("pad_seat", Location((O[0], O[1], H / 2), (0, 0, p.pad_par)))
    return ctx.finish(body)
