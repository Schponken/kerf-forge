"""Nose cap (break-first, field repair): camera fairing from nose_x0 to the bulkhead round the motor stand-off, flush with the
fuselage at x -120. 2 perimeters + 2 mm shell; the cheap part that breaks in a nose-in crash. Held by 2 M3 along X from lugs
inside its rim into the bulkhead inserts (group nose), a groove in the belly lets a hex key reach the heads. The 19 mm RunCam
sits in a cradle (floor + two cheeks) at L.camera_locs, lens forward, held by 2 x M2 through the side walls into its side holes.
The camera sits above the stand-off, so the top of the fairing rises to cover it (z 28 at the tip, blending to the fuselage).
"""
from build123d import *
import importlib.util, pathlib
from kerf import iface
from kerf.features import fillet_inside

_spec = importlib.util.spec_from_file_location("hw_layout", pathlib.Path(__file__).with_name("layout.py"))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
_fspec = importlib.util.spec_from_file_location("hw_fuselage", pathlib.Path(__file__).with_name("fuselage.py"))
F = importlib.util.module_from_spec(_fspec); _fspec.loader.exec_module(F)

WALL = 2.0
LUG_L = 12.0


def _sec(x, hw, zb, zt, r, k=0.0):
    hw, zb, zt = hw - k, zb + k, zt - k
    return Plane(origin=(x, 0, (zb + zt) / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0)) * RectangleRounded(2 * hw, zt - zb, max(1.0, min(r - k, hw - 0.1, (zt - zb) / 2 - 0.1)))


def build(ctx):
    p = ctx.p
    x0, x1, zc = p.nose_x0, p.nose_x1, p.motor_z
    fh, fb, ft, fr = L.fuse_section(p, x1)
    xm = x0 + 25.0
    st = [(x0, 20.0, zc - 22.0, 28.0, 9.0), (xm, 27.0, zc - 32.0, 27.0, 11.0), (x1, fh, fb, ft, fr)]
    outer = loft([_sec(*s) for s in st], ruled=True)
    inner = loft([_sec(x0 - 1.0, *st[0][1:], k=WALL)] + [_sec(*s, k=WALL) for s in st[1:]] + [_sec(x1 + 1.0, *st[2][1:], k=WALL)], ruled=True)
    body = outer - ctx.cut(inner, why="hollow fairing, 2 mm walls, open at both ends: stand-off through the middle, camera in the top", kind="shell")

    # camera cradle: floor + cheeks, screws M2 through the side walls into the camera's side holes
    cam, lens = L.camera_locs(p)
    cx, cz = cam.position.X, cam.position.Z               # box bottom centre; box is 19 x 19 x 19
    cat = ctx.cat.get("drone.cameras.micro_19mm")
    w = float(cat["width"]); d = float(cat["depth"]); hole_x = cx - d / 2 + (d - float(cat["mount_hole_from_front"]))
    cradle = Pos(cx, 0, cz - 1.0) * Box(d, 60.0, 2.0)
    for s in (-1, 1):
        cradle += Pos(cx, s * (w / 2 + 0.3 + 8.0), cz + w / 2) * Box(d - 2, 16.0, w)   # cheek: 0.3 mm off the camera side, out to the wall
    body += ctx.add(cradle & outer, why="camera cradle: floor + two cheeks; side screws bite the cheeks and the camera's M2 holes", kind="cradle")
    body -= ctx.cut(Pos(hole_x, 0, cz + w / 2) * Rot(90, 0, 0) * Cylinder(1.25, 80.0), why="camera M2 screws (clearance) through wall and cheeks", kind="screw hole")

    # nose screws: lug at the rim, hole along X into the bulkhead insert, key groove forward through the belly
    face = Location(Plane(origin=(x1 - LUG_L, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    for (y, z) in F.NOSE_SCREWS:
        lug = Pos(x1 - LUG_L / 2, (y + (fh if y > 0 else -fh)) / 2, (z - 12.0 + z + 5.5) / 2) * Box(LUG_L, abs(fh - abs(y)) + 5.5, 17.5)   # block from the screw out to the wall and down to the skin
        body += ctx.add(lug & outer, why="screw lug on the rim: 12 mm of grip for the M3", kind="lug")
        key = Pos(x1 - LUG_L, y, z) * Rot(0, -90, 0) * Cylinder(3.75, 40.0, align=(Align.CENTER, Align.CENTER, Align.MIN)) \
            + Pos(x1 - LUG_L - 20.0, y, z - 20.0) * Box(40.0, 7.5, 40.0)
        body -= ctx.cut(key, why="hex-key groove from the belly to the screw head", kind="tool access")
    body -= iface.bolt_pattern(ctx, "nose", "M3", [(y, -z) for y, z in F.NOSE_SCREWS], face, kind="clearance", depth=LUG_L)

    ctx.rigid("base", Location())
    ctx.rigid("camera", cam)
    ctx.rigid("lens", lens)
    def keep(at):
        if abs(at[1]) < w / 2 + 2.0 and cz - 2.5 < at[2] < cz + w + 1 and abs(at[0] - cx) < d / 2 + 1:
            return "the camera's square body sits in the cradle"
        return None
    body, left = fillet_inside(ctx, body, 1.0, keep=keep)
    ctx.notes += [f"inside corner left sharp at {c}" for c in left]
    return ctx.finish(body)
