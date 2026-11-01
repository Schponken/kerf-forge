"""Nose: TPU cone that closes the battery bay and carries the FPV camera.

Its rear face matches the pod's front face; four M3 go from lugs on its outside, along X, into the heat-set inserts
round the pod's front opening (screw heads on washers: TPU). Each lug has a driver channel in front of it, so a hex
key reaches the head along the screw axis. The camera (19 mm micro) sits against the inside of the tip, looking out
through a lens hole, held by two M2 through the side cheeks into its side holes. TPU 95A takes the landings and
belly-slides; printed standing on its rear face (walls lean in less than 30 deg, the 2 mm tip is a short bridge).
"""
from build123d import *
from kerf import iface
from kerf.features import fillet_inside

import importlib.util, pathlib
_pspec = importlib.util.spec_from_file_location("wing_pod", pathlib.Path(__file__).with_name("pod.py"))
POD = importlib.util.module_from_spec(_pspec); _pspec.loader.exec_module(POD)

WALL = 2.4
NOSE_L = 55.0
LUG_L = 12.0
LUG_D = 10.0
CAM = 19.0               # catalog drone.cameras.micro_19mm width / height / depth
CAM_HOLE_BACK = 13.9     # catalog mount_hole_from_front: side M2 holes behind the lens front


def stations(p):
    x0, hw, zb, zt, r = POD.fuselage_sections(p)[0]
    zc = cam_z(p)
    return [(x0, hw, zb, zt, r),
            (x0 - 30, hw - 10, zb + 12, zt - 8, 12),
            (x0 - NOSE_L, 15, zc - 15, zc + 15, 8)]


def cam_z(p):
    x0, hw, zb, zt, r = POD.fuselage_sections(p)[0]
    return (zb + zt) / 2


def build(ctx):
    p = ctx.p
    st = stations(p)
    x0 = st[0][0]
    outer = POD._loft(st)
    inner = POD._loft([(x + (0.01 if i == 0 else WALL if i == 2 else 0), hw, zb, zt, r) for i, (x, hw, zb, zt, r) in enumerate(st)], WALL)
    body = outer - ctx.cut(inner, why="hollow shell: camera and wires inside, the bay behind", kind="shell")
    zc = cam_z(p)
    xt = x0 - NOSE_L + WALL                       # inside of the tip = camera front
    # camera cheeks: fill the gap between the camera sides and the tip walls round the side screws
    cheeks = Pos(xt + CAM / 2, 0, zc) * Box(CAM, 40, 14) - Pos(xt + CAM / 2, 0, zc) * Box(CAM + 2, CAM + 0.4, 16)
    body = body + ctx.add(cheeks & outer, why="camera cheeks: side screws into the camera's M2 holes", kind="cheek")
    # why: lens window through the tip
    body = body - Pos(x0 - NOSE_L - 1, 0, zc) * Rot(0, 90, 0) * Cylinder(7.5, WALL + 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # why: camera side screws (M2 clearance) through cheeks and walls, at the camera's side holes
    body = body - Pos(xt + CAM_HOLE_BACK, 0, zc) * Rot(90, 0, 0) * Cylinder(1.25, 60)
    # bolt lugs on the outside of the rear rim, screws along +X into the pod inserts
    for (y, z) in POD.nose_bolts(p):
        lug = Pos(x0 - LUG_L / 2, y, z) * Rot(0, 90, 0) * Cylinder(LUG_D / 2, LUG_L)
        body = body + ctx.add(lug, why="screw lug (12 mm of grip on a TPU rim)", kind="lug")
        reach = Pos(x0 - LUG_L, y, z) * Rot(0, -90, 0) * Cylinder(3.75, NOSE_L, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body = body - ctx.cut(reach, why="hex-key channel to the lug's screw head", kind="tool access")
    face = Location(Plane(origin=(x0 - LUG_L, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))    # local (u, v) = world (y, -z)
    body = body - iface.bolt_pattern(ctx, "nose", "M3", [(y, -z) for (y, z) in POD.nose_bolts(p)], face, kind="clearance", depth=LUG_L)
    body, failed = fillet_inside(ctx, body, r=1.0)
    ctx.notes += [f"inside corner left sharp at {c}" for c in failed]
    ctx.rigid("camera", Location((xt + CAM / 2, 0, zc - CAM / 2)))
    ctx.rigid("base", Location())
    return ctx.finish(aero_largest(body))


def aero_largest(s):
    from kerf import aero
    return aero.largest(s)
