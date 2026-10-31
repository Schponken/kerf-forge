"""PSU hood: the mains end of the MEAN WELL LRS-100-5. A closed box over the supply's terminal block that carries the
SCHURTER DD11 fused + switched IEC inlet in its end wall, so the arm plugs into the wall with an ordinary C13 cord and
no live screw terminal is ever exposed (the LRS terminals are open from the top; MEAN WELL asks for a terminal cover
or an enclosure).

Frame (= the supply's frame, attached at psu.term_end): origin on the desk at the supply's terminal-block end face,
+X into the supply, Y across it (the supply's datasheet y = 0 side, with its tapped side holes, is at y = -48.5),
Z up. The supply's case is x 0..129, y -48.5..48.5, z 0..30 (catalog, +/-1 mm).

- Sleeve: side walls slide over the first 42 mm of the case; the -Y wall bears on the case face and one M3 x 6 goes
  through it into the supply's tapped side hole (catalog holes_side_m3 [32, 15], max depth 5), so the hood cannot be
  pulled off with the mains wiring live. The +Y side has 1 mm of the case's +/-1 mm tolerance as clearance.
  The top covers only the terminal block (x 0..20) and leaves the rest of the case's top open for cooling.
- Extension: 62 mm beyond the terminal end, floor 2 mm, for the inlet body (30 mm behind its flange) and the three
  L/N/PE jumpers. The inlet fits the 47.1 x 28.1 cut-out in the 3 mm end wall (catalog panel range 2.5-8 mm) and is
  held by its two flange screws in heat-set inserts in bosses behind the wall (2.5 mm wall around each insert).
- DC exit: a teardrop hole in the -Y wall; the output bundle is tied to a bridge on the floor right inside it, so a
  pull on the leads loads the tie, not the screw terminals.
- The top has a 7 mm hole over the supply's output-voltage pot (SVR1) and a 2.5 mm light hole over its LED (1.25 mm
  web between them, about three extrusion lines), so the
  5.4 V trim is set and checked with the hood on; a window in the -Y wall keeps the supply's side vent slots open.
Printed standing on its end wall (print_rot [0, -90, 0]): the insert holes print vertical and the inlet window is a
plain opening in the first layers; the side screw hole and the DC exit are the only horizontal holes (the exit is a
teardrop, roof toward +X = printer up)."""
from build123d import *
from kerf import iface

T = 3.0                      # walls
Y_IN_N, Y_IN_P = -48.5, 49.5  # inner faces: -Y bears on the case, +Y leaves 1 mm for the case tolerance
ZC = 32.0                    # ceiling (case 30 + its 1 mm tolerance + 1 mm over the terminal screws)
SLEEVE = 42.0                # side walls reach this far over the case
TOP_TO = 20.0                # the top covers the terminal block only (block ~14.7 deep)
EXT = 62.0                   # extension beyond the terminal end (inner)
FLOOR = 2.0
Z_INLET = (FLOOR + ZC) / 2   # inlet centre height
SCREW_HOLE = (32.0, 15.0)    # supply side hole (x, z) on the y = -48.5 face
X_EXIT, Z_EXIT, R_EXIT = -12.0, 12.0, 5.0


def build(ctx):
    x0, x1 = -EXT - T, SLEEVE
    yo_n, yo_p = Y_IN_N - T, Y_IN_P + T
    body = Pos((x0 + x1) / 2, (yo_n + yo_p) / 2, 0) * Box(x1 - x0, yo_p - yo_n, ZC + T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # extension cavity (with a floor) and the sleeve (open below, over the case)
    body -= Pos((-EXT + 0.0) / 2, (Y_IN_N + Y_IN_P) / 2, FLOOR) * Box(EXT + 0.02, Y_IN_P - Y_IN_N, ZC - FLOOR, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos(SLEEVE / 2, (Y_IN_N + Y_IN_P) / 2, -1) * Box(SLEEVE + 0.02, Y_IN_P - Y_IN_N, ZC + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos((TOP_TO + SLEEVE) / 2 + 0.01, (Y_IN_N + Y_IN_P) / 2, ZC - 1) * Box(SLEEVE - TOP_TO + 0.02, Y_IN_P - Y_IN_N, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # inlet window + insert bosses behind the end wall
    e = ctx.cat.get("electronics.connectors.iec_inlet_fused_switched_schurter_dd11")
    cw, ch, sp = float(e["panel_cutout_w"]), float(e["panel_cutout_h"]), float(e["screw_hole_spacing"])
    panel = Plane(origin=(x0, 0, Z_INLET), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)).location   # inlet frame: X along Y
    window = panel * Pos(0, 0, -T - 1) * extrude(RectangleRounded(cw, ch, float(e.get("panel_cutout_corner_r", 1.0))), T + 2)
    body -= window
    boss_l = 6.0
    for sx in (-sp / 2, sp / 2):
        body += panel * Pos(sx, 0, -T + 0.01) * Cylinder(4.6, boss_l, align=(Align.CENTER, Align.CENTER, Align.MAX))
    body -= iface.bolt_pattern(ctx, "inlet", "M3", [(-sp / 2, 0), (sp / 2, 0)], panel, kind="heatset", depth=T + boss_l)
    # side screw into the supply's tapped hole
    side = Plane(origin=(SCREW_HOLE[0], Y_IN_N - T, SCREW_HOLE[1]), x_dir=(1, 0, 0), z_dir=(0, -1, 0)).location
    body -= iface.bolt_pattern(ctx, "psu_side", "M3", [(0, 0)], side, kind="clearance", depth=T,
                               teardrop=iface.print_up_deg(ctx, side))
    # DC exit (teardrop, roof toward +X) and the tie slots in the floor beside it
    exit_frame = Plane(origin=(X_EXIT, Y_IN_N, Z_EXIT), x_dir=(1, 0, 0), z_dir=(0, -1, 0)).location
    body -= exit_frame * iface._teardrop(R_EXIT, -1.0, T + 1.0, 0.0)
    # tie bridge on the floor beside the exit: a block with a tunnel (along X) the cable tie threads through
    tie_y, tie_h = Y_IN_N + 8.0, 5.0
    body += Pos(X_EXIT, tie_y, FLOOR - 0.01) * Box(8.0, 6.0, tie_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos(X_EXIT, tie_y, FLOOR + 1.0) * Box(8.2, 3.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # output-voltage pot SVR1 and the power LED under the top (catalog, scaled): a screwdriver hole and a light hole,
    # so the supply is trimmed and checked with the hood on (the pot is beside terminal 7, +V; the mains pins 1-3 are
    # 50+ mm away, out of reach of a trim screwdriver through this hole)
    e_psu = ctx.cat.get("electronics.supplies.meanwell_lrs100_5")
    sx_, sy_ = e_psu["svr_xy_scaled"]
    lx, ly = e_psu["led_xy_scaled"]
    y0 = Y_IN_N                                                # datasheet y = 0 side
    body -= Pos(sx_, y0 + sy_, ZC - 1) * Cylinder(float(e_psu["svr_d_scaled"]) / 2 + 0.5, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body -= Pos(lx, y0 + ly, ZC - 1) * Cylinder(1.25, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # the supply's own side vent slots (datasheet side view, x ~15-25 near the base) stay open: window in the -Y wall
    body -= Pos(20.0, Y_IN_N - T / 2, 2.0) * Box(14.0, T + 2, 10.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("origin", Location((0, 0, 0)))
    ctx.rigid("inlet", panel)
    ctx.rigid("dc_exit", Location((X_EXIT, Y_IN_N - T - 2.0, Z_EXIT)))
    ctx.rigid("dc_tie", Location((X_EXIT, Y_IN_N + 8.0, FLOOR + tie_h + 3.0)))
    return ctx.finish(body)
