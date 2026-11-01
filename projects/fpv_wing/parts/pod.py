"""Centre pod: the wing's centre section (between the two inner segments) merged with a fuselage that carries the
battery, ESC, flight controller, receiver, GPS and VTX; the nose (TPU, camera) bolts to its front face, the motor
mount to its rear face. PLA, printed standing on its rear face (the fuselage's long axis along the build plate's Z,
so its rounded sides print without supports); 2 walls, 15 % infill.

Inside: one cavity from the front face to the motor mount, 2.4 mm skin. The battery slides in from the front
(nose off) onto the floor; the spar tubes cross the cavity in printed sleeves that reach to 8 mm off the centreline
(left and right tubes end apart), so the bending moment goes tube - sleeve - side wall. Each inner wing segment is
held by two M3 from inside the cavity through the side wall into its root inserts. The rear wall carries the motor
mount's four M3 heat-set inserts, the front face the nose's four.
"""
from build123d import *
import numpy as np
from kerf import aero, iface

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("wing_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)

SKIN = 2.4


def fuselage_sections(p):
    """(x, half width, z bottom, z top, corner radius) stations of the fuselage outside."""
    hw = p.pod_hw
    return [(p.pod_x0, hw - 8, p.pod_bottom + 10, p.pod_top - 6, 14),
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
    return cav + Pos(p.pod_x0 - 1, 0, (st[0][2] + st[0][3]) / 2) * Box(SKIN + 2, 2 * (st[0][1] - SKIN) - 8,
                                                                        (st[0][3] - st[0][2]) - 2 * SKIN - 8, align=(Align.MIN, Align.CENTER, Align.CENTER))


def build(ctx):
    p = ctx.p
    body = outer(p) - ctx.cut(cavity(p), why="battery and electronics bay", kind="cavity")
    for s in (1, -1):
        for which, od in (("main", p.main_od), ("rear", p.rear_od)):
            a, b = L.tube_line(p, which, s)
            a, b = np.array(a), np.array(b)
            u = (b - a) / np.linalg.norm(b - a)
            out_pt = a + u * ((p.pod_hw - 0.3 - (od + 6) / 2 * abs(u[0]) - abs(a[1])) / abs(u[1]))   # sleeve ends inside the side wall
            body = body + ctx.add(aero.cylinder_between(a, out_pt, od + 6.0), why=f"{which} spar sleeve: tube bending into the side wall", kind="sleeve")
            body = body - ctx.cut(aero.cylinder_between(a, b, od + 0.2, extend=0.0), why=f"{which} spar tube, close fit", kind="spar bore")
        # wing root bolts: from inside, through the side wall into the inner segment's inserts
        loc = Location(Plane(origin=(0, s * (p.pod_hw - SKIN), 0), x_dir=(1, 0, 0), z_dir=(0, -s, 0)))
        local = [(p.root_bolt_x1, s * p.root_bolt_z1), (p.root_bolt_x2, s * p.root_bolt_z2)]
        body = body - iface.bolt_pattern(ctx, f"wing_root_{'l' if s < 0 else 'r'}", "M3", local, loc, kind="clearance", depth=SKIN + 0.01,
                                   teardrop="auto")
        ctx.rigid(f"wing_{'l' if s < 0 else 'r'}", Location())
    for k in ("nose", "motor", "battery", "esc", "fc", "rx", "gps", "vtx", "servo_l", "servo_r",
              "main_l", "main_r", "rear_l", "rear_r"):
        ctx.rigid(k, Location())
    return ctx.finish(body)
