"""Gripper body: wrist fork + grip-servo bulkhead + guide-rod head (frame G, layout.py).

Frame G: origin on the wrist axis at the wrist horn face; X forward, Y up at home, Z across the wrist fork.
- Wrist fork (the arm's interface, robot_arm/parts/gripper.py): plate A z 0..plate_t on the wrist horn (4 x M3),
  plate B z grip_w-plate_t..grip_w on the M3 pivot screw (heat-set insert in a boss), each a Ø link_h disc that
  deepens toward the bulkhead (the fork carries the wrist moment in its own plane), one printable pocket per plate.
- Bulkhead x x_bulk..x_bulk+bulk_t: the grip MG996R's case top passes its window from behind (top_through), tabs on
  its back face, 4 x M3 thread-forming. The servo drops into the bay from above (+Y, between the plates) and slides +X.
- Wings: the bulkhead carried out to both end cheeks as I-beams along Z (web = bulkhead, flanges top and bottom), so
  the wrist moment (about Z) and the grip-servo reaction (about X) reach the cheeks as in-plane flange / web loads.
- Cheeks: frames in the XY plane at the ends of the jaw travel; the front bar holds the two Ø4 guide rods (press fit,
  +Z blind, -Z through + rod_keeper) and is the open-end hard stop for the jaw carriages.
Printed on its top face (print_rot [-90, 0, 0], +Y down): the bulkhead, wings and cheeks share the top plane y = top
(the bed); every face that looks down in print is a 45 deg roof, every horizontal hole a teardrop; the one flat
ceiling is the servo window's lower edge (a 21 mm bridge, like the arm's forearm window)."""
import math

from build123d import *
from kerf import iface
from kerf.edges import sharp_inside
from kerf.features import safe_fillet, teardrop_hole

HORN = "servo_horns.aluminum_25T"
SERVO = "servos.MG996R"
ROD = "rods.ss_rod_4"
R1, R2, R4 = 1.0, 2.0, 4.0   # project style radii (project.yaml style.radii)
WEB = 2.4                    # frame member / web width (ENGINEERING.md s5: >= 1.6 structural, 2.4 at screws)
CHORD = 3.0                  # fork plate top chord
RAIL = 3.0                   # wing rail (flange) thickness
ARM = 5.0                    # cheek top arm depth / strut width
CHEEK_T = 4.0                # cheek arms + strut thickness (the front bar keeps the full cheek_t for the rod seats)
import os
FILLET3D = os.environ.get('GW_F3D') == '1'
KEEP_Y = 10.0                # rod_keeper screws at +-KEEP_Y between the rods (keeper frame)


def _poly(*pts):
    return Polygon(*pts, align=None)


def _slab(face, z0, z1):
    """XY profile extruded from z0 to z1."""
    return Pos(0, 0, z0) * extrude(face, z1 - z0, dir=(0, 0, 1))


def _xprism(face, x0, x1):
    """Profile drawn as (y, z) extruded along X from x0 to x1."""
    return extrude(Plane.YZ.offset(x0) * face, x1 - x0, dir=(1, 0, 0))


def _tangent_low(r, px, py):
    """Lower tangent point on the circle r (origin) of the line from (px, py)."""
    a = math.atan2(py, px) - math.acos(r / math.hypot(px, py))
    return r * math.cos(a), r * math.sin(a)


def build(ctx):
    p = ctx.p
    t, W, r = p.plate_t, p.grip_w, p.link_h / 2
    zc = p.z_c
    xb0, xb1 = p.x_bulk, p.x_bulk + p.bulk_t
    zl_in, zr_in = zc - p.z_stop, zc + p.z_stop          # cheek inner faces (jaw open-end stops)
    zl, zr = zl_in - p.cheek_t, zr_in + p.cheek_t        # cheek outer faces
    top = p.rod_y + 6.0                                   # why: one flat top plane 6 mm over the rods = the print bed
    yb = p.rod_y + 4.5                                    # wings / cheeks bottom: 2.4 mm wall under the lower rod seat
    y_tab = p.y_s - p.mg_hx / 2                           # lower tab screws
    y_bot = y_tab - 5.0                                   # why: bulkhead bottom 5 mm under the lower tab screws (s7 edge distance)
    xr1 = p.x_p0 - 1.1                                    # wing rails reach 0.5 mm short of the rack slab (x_p0 - 0.6)
    x_fb0, x_fb1 = p.x_rod - 4.5, p.x_rod + 4.5           # cheek front bar: 2.4 mm walls round the rod seats / keeper inserts

    # ---- fork plates (XY outline, extruded) ----------------------------------------------------------------
    a = r / math.sqrt(2)
    plate = Circle(r)                                                                   # why: wrist disc Ø link_h (arm interface)
    plate += _poly((-a, a), (top - 2 * a, top), (xb1, top), (xb1, y_bot), (-y_bot, y_bot), (a, -a), (0, 0))   # why: fork fans out at 45 deg (prints without support) to the full bulkhead depth
    # two pockets per plate, split by a diagonal from the top chord near the disc to the bulkhead's bottom corner (a
    # truss: the wrist moment reaches the bulkhead as chord + diagonal forces); every pocket edge that faces down in
    # print is vertical, steep or a 45 deg floor, so they print without support
    c, x_pr, y_fl = WEB * math.sqrt(2), xb0 - WEB, y_bot + WEB + 3.0   # (flat floor >= 4 mm long so its corners take R2)
    d0, d1 = (r + 11.0, top), (xb0, y_bot)               # diagonal centre line (pocket tops >= 6 mm for their R2 corners)
    k = (d1[0] - d0[0]) / (d0[1] - d1[1])                # dx per mm of -y
    hw = WEB / 2 * math.hypot(1, k)                      # half its width, measured along x
    dx = lambda y, side: d0[0] + k * (d0[1] - y) + side * hw   # noqa: E731
    y_r = d0[1] - (x_pr - hw - d0[0]) / k                # where the diagonal's right edge meets the post
    pk_r = _poly((dx(top - CHORD, 1), top - CHORD), (x_pr, top - CHORD), (x_pr, y_r))
    y_l = (c - d0[0] - k * d0[1] + hw) / (1 - k)         # diagonal left edge meets the 45 deg floor x + y = c
    pk_l = _poly((r + 3.0, top - CHORD), (dx(top - CHORD, -1), top - CHORD), (dx(y_l, -1), y_l), (r + 3.0, c - r - 3.0))
    plate -= fillet(pk_r.vertices(), R2) + fillet(pk_l.vertices(), R2)                  # why: weight where the fork is deep; R2 corners
    body = _slab(plate, 0, t) + _slab(plate, W - t, W)

    # ---- bulkhead between the plates + top rail ahead of it ------------------------------------------------
    sec = _poly((xb0, y_bot), (xb1, y_bot), (xb1, top - RAIL), (xr1, top - RAIL), (xr1, top), (xb0, top))
    sec = fillet(sec.vertices().filter_by(lambda v: abs(v.X - xb1) < 0.05 and abs(v.Y - top + RAIL) < 0.05), R2)
    body += _slab(sec, 0, W)                                                            # why: servo bulkhead (tab screws) + top rail tying the wings together

    # ---- wings: I-beams along Z from the plates to the cheeks (rails = flanges, thin web flush with the bulkhead front)
    xw0 = xb1 - WEB
    g0, g1 = xw0 - xb0, xr1 - xb1                         # 45 deg gussets under the bottom rail (print roof)
    wing = _poly((xw0, -yb + RAIL + g0), (xw0, top - RAIL), (xb0, top - RAIL), (xb0, top), (xr1, top), (xr1, top - RAIL),
                 (xb1, top - RAIL), (xb1, -yb + RAIL + g1), (xr1, -yb + RAIL), (xr1, -yb), (xb0, -yb), (xb0, -yb + RAIL))
    wing = fillet(wing.vertices().filter_by(lambda v: abs(v.X - xw0) < 0.05 or abs(v.X - xb1) < 0.05), R2)   # why: web/rail roots
    zlt, zrt = zl_in - CHEEK_T, zr_in + CHEEK_T           # outer faces of the cheeks' thin members
    body += _slab(wing, zlt, 0) + _slab(wing, W, zrt)                                   # why: wrist moment (rail couple) + servo reaction (web shear) out to the cheeks
    for z0, z1 in ((zl_in + WEB, -WEB), (W + WEB, zr_in - WEB)):
        hw = (z1 - z0) / 2
        y_lo, y_hi = -yb + RAIL + g1 + WEB, top - RAIL - WEB
        win = _poly((y_hi, z0), (y_hi, z1), (y_lo + hw, z1), (y_lo, z0 + hw), (y_lo + hw, z0))
        body -= _xprism(fillet(win.vertices(), R2), xw0 - 1, xb1 + 1)                  # why: weight; rails carry the moment, the web frame the shear

    # ---- cheeks: front bar (rod seats, keeper inserts, jaw hard stop) + thin top arm and 45 deg strut to the wing
    vh = (x_fb0 - xb1) / 2                                # window floor: a 45 deg V (K-truss struts) so it prints without support
    win = _poly((xb1, top - ARM), (x_fb0, top - ARM), (x_fb0, -yb + ARM + vh), ((xb1 + x_fb0) / 2, -yb + ARM), (xb1, -yb + ARM + vh))
    frame = _poly((xw0, -yb), (x_fb1, -yb), (x_fb1, top), (xw0, top)) - fillet(win.vertices(), R2)   # why: top + bottom arms carry the rail couple to the rod bar
    bar = _poly((x_fb0, -yb), (x_fb1, -yb), (x_fb1, top), (x_fb0, top))
    body += _slab(frame, zlt, zl_in) + _slab(bar, zl, zl_in)                            # why: -Z cheek: rod seats + keeper + open-end stop
    body += _slab(frame, zr_in, zrt) + _slab(bar, zr_in, zr)                            # why: +Z cheek: blind rod seats + open-end stop

    # ---- pivot boss on plate B's inner face (the M3 insert needs t + 3) ------------------------------------
    rb = 6.5
    boss = Circle(rb) + _poly((-rb / math.sqrt(2), rb / math.sqrt(2)), (rb / math.sqrt(2), rb / math.sqrt(2)), (0, rb * math.sqrt(2)))
    body += _slab(boss, W - t - 3.0, W - t + 0.01)                                     # why: insert depth; 45 deg keel prints without support

    # ---- inside-corner fillets on the 3D junctions (not where the servo tabs sit against the bulkhead) ------
    def tab_corner(c):
        return abs(c.X - xb0) < 0.2 and (abs(c.Z - t) < 0.2 or abs(c.Z - (W - t)) < 0.2)
    corners = [Vector(*c["at"]) for c in sharp_inside(body)]
    edges = [e for e in body.edges() if any((e.center() - c).length < 0.15 for c in corners) and not tab_corner(e.center())]
    failed = []
    if FILLET3D:
        body, failed = safe_fillet(body, [(edges, R2)])                                     # why: stress raisers on the load path
    if failed:
        left = [Vector(*c["at"]) for c in sharp_inside(body)]
        body, failed = safe_fillet(body, [([e for e in body.edges() if any((e.center() - c).length < 0.15 for c in left)
                                            and not tab_corner(e.center())], R1)])

    # ---- interfaces ---------------------------------------------------------------------------------------
    la = Location((0, 0, t))
    body -= iface.horn_mount(ctx, HORN, la, group="wr_horn", plate_t=t, teardrop=iface.print_up_deg(ctx, la))   # why: wrist horn (arm interface)
    lb = Location((0, 0, W))
    body -= iface.pin_hole(ctx, "M3", lb, "wr_pivot", depth=t + 3.0, fit="heatset", teardrop=iface.print_up_deg(ctx, lb))   # why: wrist pivot screw insert
    for (hx, hy) in iface.circle(4, p.horn_bc, 45.0):
        lk = Location((hx, hy, W))
        body -= lk * teardrop_hole(4.0, t + 4.0, iface.print_up_deg(ctx, lk))          # why: hex-key access to the wr_horn screws through plate B
    loc = Location(Plane((p.x_bulk, p.y_s, zc), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    body -= iface.servo_mount(ctx, SERVO, loc, group="gr_servo", plate_t=p.bulk_t, kind="tap", top_through=True,
                              teardrop=iface.print_up_deg(ctx, loc))                   # why: grip servo, case top through the bulkhead
    for g, y in (("rod_top", p.rod_y), ("rod_bot", -p.rod_y)):
        lr = Location((p.x_rod, y, zr_in), (180, 0, 0))
        body -= iface.pin_hole(ctx, ROD, lr, g, depth=p.cheek_t - 1.5, fit="press", through=False,
                               teardrop=iface.print_up_deg(ctx, lr))                   # why: +Z cheek: blind rod seat from the inner face
        ll = Location((p.x_rod, y, zl), (180, 0, 0))
        body -= iface.pin_hole(ctx, ROD, ll, g, depth=p.cheek_t, fit="press", teardrop=iface.print_up_deg(ctx, ll))   # why: -Z cheek: rod pressed in from outside
    lkp = Location((p.x_rod, 0, zl), (180, 0, 0))
    body -= iface.bolt_pattern(ctx, "keeper", "M3", [(0, KEEP_Y), (0, -KEEP_Y)], lkp, "heatset", p.cheek_t,
                               teardrop=iface.print_up_deg(ctx, lkp))                  # why: rod_keeper screws (2: it cannot swing off)
    if failed:
        ctx.notes.append(f"gripper: {len(failed)} inside corner(s) could not take a fillet: " + "; ".join(failed[:3]))

    ctx.rigid("horn_mount", Location((0, 0, 0)))
    ctx.rigid("servo_seat", loc * Location((0, 0, -p.mg_tab_t)))
    ctx.linear("jaw_r_slide", Axis((p.x_c0, 0, zc + p.z_in), (0, 0, 1)), range=(0, p.s_max))
    ctx.linear("jaw_l_slide", Axis((p.x_c0, 0, zc - p.z_in), (0, 0, -1)), range=(0, p.s_max))
    ctx.rigid("keeper_seat", lkp)
    ctx.rigid("tcp", Location((p.x_tcp, 0, zc)))
    ctx.rigid("lead_1", Location((p.x_case0 + 6.5, 24, zc)))      # grip-servo lead rises out of the bay over its cable boss
    ctx.rigid("lead_2", Location((0, 30, -3)))                      # over the wrist outside plate A (forearm lead_4 lands here)
    return ctx.finish(body)
