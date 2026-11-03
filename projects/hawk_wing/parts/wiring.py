"""Electrical route coordinates tied to the Hawk's existing channels and moving panels."""
import importlib.util
from pathlib import Path

from kerf import aero, iface


def _module(name):
    spec = importlib.util.spec_from_file_location("hawk_wire_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def route_params(p):
    L, W, H, T = (_module(n) for n in ("layout", "wing", "hub", "tail_mount"))
    pf = L.planform(p)
    mid = lambda x, y: float(aero.spar_point(pf, abs(y), (x - pf.x_le(abs(y))) / pf.chord(abs(y)))[2])
    surface = lambda x, y, upper: W.surface_z(pf, x, y, upper)
    paths = {}
    items = L.item_locs(p)
    fc, esc = items["fc"].position, items["esc"].position
    paths["main"] = [(-110, -26, -17), (fc.X, -26, -17)]
    paths["esc"] = [(fc.X, -2, -10), (esc.X, -2, -10)]
    paths["phases"] = [(-95, 20, -14), (p.nose_x1 + 6, 0, p.motor_z), (p.nose_x1 - 6, 0, p.motor_z)]
    paths["gps"] = [(0, -10, -15), (L.GPS_X, 0, -10)]
    paths["rx"] = [(fc.X, -16, -8), (items["rx"].position.X, -16, -8)]
    paths["vtx"] = [(0, -10, -15), (175, -10, -35), (L.VTX_X, -10, -40)]
    paths["camera"] = [(-95, -10, -14), (p.nose_x1 + 6, 0, p.motor_z), (p.nose_x1 - 6, 0, p.motor_z),
                       (p.nose_x0 + 20, 0, -5)]
    sd = iface.servo_dims(L.SWEEP_SERVO)
    for s, suffix in ((1, "r"), (-1, "l")):
        # These points follow glove.py's existing centre-of-section channels.
        lx, ly = 170.0, s * (p.pivot_y - 30.0)
        ex, ey = 165.0, s * 26.0
        glove_sweep = [(lx, ly, L.POD_PAD_Z - 4), (lx, ly, L.POD_PAD_Z + 1),
                       (lx - 2, s * 100, mid(lx - 2, s * 100)),
                       (ex + 2, s * 60, mid(ex + 2, s * 60)), (ex, ey, mid(ex, ey)),
                       (ex, ey, surface(ex, ey, False) - 4)]
        loc = L.sweep_servo_loc(p, s).position
        bx = loc.X + sd["L"] / 2 + 4
        bz = loc.Z - sd["tab_z"] + 5.2
        paths["sweep_" + suffix] = [(0, -10, -15), (ex, ey, -15), *reversed(glove_sweep),
                                    (bx, s * (p.pivot_y - 15), bz), (bx, s * p.pivot_y, bz)]
        ax, ay = p.pivot_x - 6, s * (p.pivot_y - 20)
        glove_ail = [(ax, ay, surface(ax, ay, True) + 3), (ax - 8, ay - s * 4, 0.5),
                     (205, s * 100, mid(205, s * 100)), (200, s * 60, mid(200, s * 60)),
                     (196, s * 32, mid(196, s * 32)), (190, s * 24, surface(190, s * 24, False) - 4)]
        paths["ail_fixed_" + suffix] = [(0, -10, -15), (190, s * 24, -15), *reversed(glove_ail)]
        hub = [(x, s * y, z) for x, y, z in H._lead_pts(p)]
        paths["ail_hub_" + suffix] = list(reversed(hub))
        _, sv = W.servo_frame(p, s)
        paths["ail_wing_" + suffix] = list(reversed(W.lead_path(p, s, sv)))
    td = T.dims(p)
    for which, sign in (("elev", 1), ("rud", -1)):
        # Leave via the side service opening; the boom's cross-screw blocks an internal lead route.
        xlead = T.servo_x(p, which) - td["sd"]["L"] / 2 + 3
        paths[which] = [(0, -10, -15), (180, 20, -38), (190, 20, -38), (190, 35, -38),
                        (p.fuse_x1 + 8, 35, -38), (p.fuse_x1 + 8, 0, p.boom_z - 8),
                        (td["x0"] - 8, 0, p.boom_z - 8), (td["x0"] - 8, -sign * 14, td["z_servo"]),
                        (xlead, -sign * 14, td["z_servo"]), (xlead, -sign * 8, td["z_servo"])]
    return {f"wire_{name}_{i}_{axis}": float(value) for name, points in paths.items()
            for i, point in enumerate(points) for axis, value in zip("xyz", point)}
