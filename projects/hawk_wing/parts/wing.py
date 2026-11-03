"""Wing skin segments: wing_r1 / wing_l1 (inner, hub_y1 .. seg_split_y) and wing_r2 / wing_l2 (outer, seg_split_y ..
the rounded tip). Adapted from projects/fpv_wing/parts/wing.py: same thin-wall approach and kerf.aero helpers.

Thin-wall print (PLA, 1 wall, 3 % infill) standing on its inner end (root / joint face on the bed, span = print Z), so
the airfoil is the layer outline and the skins print without supports. A segment is a sleeve on the two carbon spar
tubes (main 28 % chord = the bending spar, rear 60 % = holds the twist and lines the segments up): bores OD + 0.3
along L.tube_line, epoxied. The inner segment's root face is the hub's section at hub_y1 (same L.planform), the two
segments meet flush at seg_split_y; both joints are glued faces + the tubes.

Outer segment: aileron slot (aero.elevon_split, bottom tape hinge at ail_hinge_frac, top V gap ail_gap_deg, ends
square to the hinge) from ail_y0 to ail_y1; aileron servo (KST X08 Plus, 8 mm thick) lying flat between the spars
just inboard-forward of the aileron's horn, output inboard, in a pocket open to the bottom skin (servo in from below,
glued, taped over); its arm hangs out of the pocket and a 1.2 mm Z-bend pushrod runs under the bottom skin to the
horn on the aileron's inner end. Rounded tip: the leading edge curves back on a quarter ellipse over the last
TIP_R mm (trailing edge stays straight; same airfoil, thickness scaled with the chord).

Servo lead: the X08's lead leaves the case bottom (outboard end) heading outboard, and the rear spar lies between the
pocket and the lead's way out (L.lead_root is aft of the rear spar), so the channel runs outboard past the rear tube's
end, crosses aft at 45 deg (prints without bridging) and runs inboard aft of the rear spar through both segments to
L.lead_root on the inner segment's root face, where the hub carries it on.
"""
from build123d import *
import numpy as np
from kerf import aero, iface
from kerf.features import fillet_inside

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

TIP_R = 40.0          # spanwise length of the rounded tip
TIP_K = 0.35          # chord left at the very tip (fraction of the local chord); TE kept straight
TIP_N = 9             # tip sections (quarter ellipse)
END_GAP = 1.0         # aero.elevon_split default: aileron ends to the slot ends
LEAD_D = 4.0          # lead channel: 3-wire servo lead, pins threaded out of their housing (see notes)
LEAD_TURN_Y = (400.0, 442.0)   # |y| where the lead channel crosses aft past the rear tube's end (spar_rear_y1 + 2 bore extend)
LEAD_BEND_R = 10.0    # lead channel bend radius
LEAD_AFT_X = 209.0    # channel x at the crossing's aft end (rear tube 198.5 + 3 at y 442 .. aileron V gap ~216)
POCKET_CLR = 0.5      # servo pocket clearance per side (glued in; servo tape round the case)
TOP_SKIN = 1.4        # plastic kept over the pocket under the top skin
ARM_R = 8.0           # servo arm hole radius used (pushrod); horn hole HORN_R below the hinge -> servo +-25 deg for +-20
HORN_R = 10.0
HORN_T = 3.0          # horn plate thickness (spanwise)


def side_of(pid):
    return -1 if "_l" in pid else 1


def surface_z(pf, x, y, upper):
    """World z of the upper / lower skin at plan point (x, |y|)."""
    ya = abs(y)
    frac = (x - pf.x_le(ya)) / pf.chord(ya)
    mid = aero.spar_point(pf, ya, frac)
    return float(mid[2] + (0.5 if upper else -0.5) * aero.depth_at(pf, ya, frac))


def tip_section(pf, y, k):
    """Section at station y with the chord scaled by k about the trailing edge (TE straight, TE thickness te_min,
    airfoil t/c and the local twist kept)."""
    full = pf.section(y)
    c = pf.chord(y) * k
    small = aero.Planform(span=2 * abs(y), root_chord=c, tip_chord=c, twist_tip_deg=pf.twist(y),
                          root_airfoil=pf.root_airfoil, te_min=pf.te_min).section(y)
    te = lambda pts: (pts[0] + pts[-1]) / 2
    return small + (te(full) - te(small))


def outer_solid(p, s):
    """Outer segment's raw wing (seg_split_y to the rounded tip), one ruled loft. Shared with aileron.py so the
    aileron is cut from exactly this surface."""
    pf = L.planform(p)
    y_t0 = p.semi - TIP_R
    phi = np.linspace(0.0, np.pi / 2, TIP_N)
    secs = [(p.seg_split_y, 1.0)] + [(y_t0 + TIP_R * np.sin(f), 1 - (1 - TIP_K) * (1 - np.cos(f))) for f in phi]
    pts = [tip_section(pf, s * y, k) for y, k in secs]
    if s < 0:
        pts = pts[::-1]          # lofts run towards +Y
    return Solid.make_loft([aero._section_face(q).outer_wire() for q in pts], ruled=True)


def servo_frame(p, s):
    """(tabs Location, numbers) of the aileron servo: lying flat (8 mm across the thickness), body length along X with
    the output end aft, output axis spanwise and inboard, centred chordwise between the two spar bores, spline placed
    so the arm lines up with the aileron horn at the aileron's inner end."""
    pf = L.planform(p)
    sd = iface.servo_dims(L.SURF_SERVO)
    horn_y = p.ail_y0 + END_GAP + HORN_T / 2                       # |y| of the horn plate's mid plane = arm plane
    tip_y = horn_y - 1.0                                          # spline tip just inboard of the arm's mid plane
    tab_y = tip_y + sd["top"] + sd["shaft_h"]
    xm = aero.spar_point(pf, tab_y, p.spar_main_frac)[0] + p.main_od / 2
    xr = aero.spar_point(pf, tab_y, p.spar_rear_frac)[0] - p.rear_od / 2
    sx = (xm + xr) / 2
    half = sd["span"] / 2 + POCKET_CLR
    # centre the 8 mm case on the thickness centre, lowered if needed to keep TOP_SKIN under the top skin at the aft end
    mid = aero.spar_point(pf, tab_y, (sx - pf.x_le(tab_y)) / pf.chord(tab_y))[2]
    sz = min(float(mid), surface_z(pf, sx + half, tab_y, True) - TOP_SKIN - sd["W"] / 2 - POCKET_CLR)
    loc = Location(Plane(origin=(sx, s * tab_y, sz), x_dir=(1, 0, 0), z_dir=(0, -s, 0)))
    return loc, {"sx": sx, "sz": sz, "tab_y": tab_y, "tip_y": tip_y, "horn_y": horn_y, "half": half, "sd": sd,
                 "gap_main": sx - half - xm, "gap_rear": xr - (sx + half)}


def lead_path(p, s, sv):
    """Lead channel polyline (world points), pocket end first."""
    pf = L.planform(p)
    sd = sv["sd"]
    lead_x = sv["sx"] - sd["L"] / 2 + _cat_num("lead_bump_l") / 2       # lead bump: case bottom, end away from the output
    y_bump = sv["tab_y"] + sd["tab_z"] + _cat_num("lead_bump_h")
    mid = lambda x, y: (x, s * y, float(aero.spar_point(pf, y, (x - pf.x_le(y)) / pf.chord(y))[2]))
    return [mid(lead_x, y_bump - 3.0), mid(lead_x, LEAD_TURN_Y[0]), mid(LEAD_AFT_X, LEAD_TURN_Y[1]),
            tuple(map(float, L.lead_root(p, s)))]


def _cat_num(key):
    from kerf import catalog
    return catalog.num(catalog.get(L.SURF_SERVO), key)


def build(ctx):
    p = ctx.p
    s = side_of(ctx.id)
    inner = ctx.id.endswith("1")
    pf = L.planform(p)
    if inner:
        y0, y1 = (p.hub_y1, p.seg_split_y) if s > 0 else (-p.seg_split_y, -p.hub_y1)
        body = aero.wing_solid(pf, y0, y1)
    else:
        body = outer_solid(p, s)

    # spar tubes: slip fit (OD + 0.3), epoxied; only where the tube reaches into this segment
    y_in = p.hub_y1 if inner else p.seg_split_y
    for which, od in (("main", p.main_od), ("rear", p.rear_od)):
        a, b = L.tube_line(p, which, s)
        if abs(b[1]) > y_in:
            body = body - ctx.cut(aero.cylinder_between(a, b, od + 0.3, extend=2.0),
                                  why=f"{which} spar tube, slip fit, epoxied", kind="spar bore")

    sv_loc, sv = servo_frame(p, s)
    # servo lead channel (both segments cut the same polyline; it opens on the root face at L.lead_root)
    path = lead_path(p, s, sv)
    a, b = np.array(path[-2]), np.array(path[-1])
    path[-1] = tuple(b + (b - a) / np.linalg.norm(b - a) * 1.5)        # through the root face
    rail = FilletPolyline(*path, radius=LEAD_BEND_R)
    lead = sweep(Plane(origin=path[0], z_dir=rail % 0) * Circle(LEAD_D / 2), path=rail)
    body = body - ctx.cut(lead, why="aileron servo lead from the pocket, round the rear tube's end, to the hub", kind="wire channel")

    if inner:
        ctx.rigid("root", Location())
    else:
        sd = sv["sd"]
        # pocket: open to the bottom skin; from the arm's swing room inboard of the spline to past the lead bump
        ya = sv["tip_y"] - 3.0
        yb = sv["tab_y"] + sd["tab_z"] + _cat_num("lead_bump_h") + POCKET_CLR
        top = sv["sz"] + sd["W"] / 2 + POCKET_CLR
        pocket = Pos(sv["sx"], (ya + yb) / 2, top) * Box(2 * sv["half"], yb - ya, 50.0, align=(Align.CENTER, Align.CENTER, Align.MAX))
        # outboard end (the ceiling as printed) slopes 45 deg from the top of the pocket down to the bottom skin
        roof_n = np.array([0, 1.0, 1.0]) / np.sqrt(2)
        roof = aero._halfspace((sv["sx"], yb, top), (1, 0, 0), roof_n)
        pocket = pocket - roof
        if s < 0:
            pocket = pocket.mirror(Plane.XZ)
        body = body - ctx.cut(pocket, why="aileron servo pocket between the spars, open to the bottom skin (servo in "
                                           "from below, arm out); outboard end at 45 deg so it prints without support",
                              kind="pocket")
        ctx.rigid("servo", sv_loc)
        # aileron slot: the same cut aileron.py makes
        e0, e1 = (p.ail_y0, p.ail_y1) if s > 0 else (-p.ail_y1, -p.ail_y0)
        body, _, (ha, hb) = aero.elevon_split(pf, body, e0, e1, p.ail_hinge_frac, gap_deg=p.ail_gap_deg, end_gap=END_GAP)
        body = aero.largest(body)
        d = tuple((hb - ha) / np.linalg.norm(hb - ha))
        ctx.revolute("aileron", Axis(tuple(ha), d), range=(-p.ail_throw, p.ail_throw))
        ctx.rigid("joint", Location())
        ctx.rigid("skid", Location())
        # pushrod: servo arm hole (ARM_R below the output axis) to the horn hole (HORN_R below the hinge line)
        arm = np.array([sv["sx"] + sd["out_x"], sv["horn_y"], sv["sz"] - ARM_R])
        u = (hb - ha) / (hb[1] - ha[1])
        hh = ha + u * (s * sv["horn_y"] - ha[1])
        rod = float(np.hypot(hh[0] - arm[0], hh[2] - HORN_R - arm[2]))
        ctx.bom_item("1.2 mm music wire pushrod with Z-bends", qty=1, price_key="wire:music_1.2",
                     spec=f"{rod:.0f} mm between bends: servo arm hole {ARM_R:.0f} mm from the axis to the aileron horn hole",
                     note="runs under the bottom skin; Z-bend into the horn first, then into the arm")
        ctx.notes += [f"aileron linkage: servo arm hole {ARM_R:.0f} mm from the axis, horn hole {HORN_R:.0f} mm under the "
                      f"hinge (servo about +-25 deg for +-{p.ail_throw:.0f} deg); the lead goes through a {LEAD_D:.0f} mm "
                      f"channel: pull it with a string from the pocket to the root face, plug pins lifted out of the housing"]

    def keep(at):
        if not inner and abs(at[0] - sv["sx"]) < sv["half"] + 2 and sv["tip_y"] - 6 < abs(at[1]) < sv["tab_y"] + 30:
            return "the servo's square case, tabs and lead exit sit in the pocket's corners"
        return None
    body, failed = fillet_inside(ctx, body, r=1.0, keep=keep, occ=True)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    return ctx.finish(body)
