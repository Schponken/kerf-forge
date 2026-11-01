"""URDF export (out/<project>.urdf + out/urdf_meshes/*.stl) for simulators: PyBullet, MuJoCo, Gazebo, Isaac.

Links are the groups of items that move together (rigid joints and zero-range joints merge into their parent's link);
every moving joint of the joint tree becomes a URDF revolute / prismatic joint with its range as limits, and a geared
or belted joint (`assembly.sweeps: {joint, follows, ratio}`) becomes a <mimic> of the joint it follows.

Frames: every link frame is parallel to the assembly frame with all joints at 0, its origin on its parent joint's
axis, so a joint's origin is a pure translation and its axis is the assembly-frame axis direction.
Inertials: each item's mass (printed: the infill/perimeter estimate of `kerf check`; purchased: catalog weight) spread
uniformly over its mesh, giving its centre of mass and inertia tensor (trimesh); a link sums its items with the
parallel-axis theorem. Visual and collision geometry: one STL per item in its link frame (millimetres, scale 0.001).
Keep-out volumes are left out. SI units throughout (m, kg, rad).
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from build123d import Location

from . import assembly as A, checks, geom

MESH_DIR = "urdf_meshes"
EFFORT_NM, VELOCITY = 10.0, 3.0     # URDF requires <limit effort velocity>; not used for kinematics (see notes)


def _world_axis(shape, joint):
    """(point, unit direction) of a revolute / linear joint in the assembly frame, at the shape's current location."""
    ax = joint.relative_axis
    loc = shape.location
    p = (loc * Location(ax.position)).position
    d = (loc * Location(ax.direction)).position - loc.position
    d = np.array([d.X, d.Y, d.Z])
    return np.array([p.X, p.Y, p.Z]), d / np.linalg.norm(d)


def _links(asm):
    """{item: link name}, the link tree [(edge, parent_link, child_link)], and each link's root item."""
    moving = {e.name for e in asm.movable}
    link_of = {asm.root: asm.root}
    tree = []
    for e in asm.edges:                       # topological order: parents first
        if e.name in moving:
            link_of[e.child] = e.child
            tree.append((e, link_of[e.parent], e.child))
        else:
            link_of[e.child] = link_of[e.parent]
    return link_of, tree


def _inertial(V_mm, F, mass_kg):
    """(centre of mass m, 3x3 inertia about it kg m^2) of a mesh carrying mass_kg uniformly; a box when not closed."""
    import trimesh
    V = V_mm / 1000.0
    m = trimesh.Trimesh(V, F, process=True)
    if mass_kg <= 0:
        return m.bounds.mean(axis=0), np.zeros((3, 3))
    if m.is_volume and m.volume > 1e-12:
        m.density = mass_kg / m.volume
        return np.array(m.center_mass), np.array(m.moment_inertia)
    lo, hi = m.bounds                                         # open mesh: solid box of its bounds
    s = hi - lo
    return (lo + hi) / 2, mass_kg / 12 * np.diag([s[1] ** 2 + s[2] ** 2, s[0] ** 2 + s[2] ** 2, s[0] ** 2 + s[1] ** 2])


def _f(x) -> str:
    return f"{float(x):.9g}"


def _v(xs) -> str:
    return " ".join(_f(x) for x in xs)


def build(proj, asm=None, masses: dict | None = None):
    """The URDF tree (ElementTree root) and {item: (V_mm, F)} meshes in link frames. Leaves the assembly solved at home."""
    asm = asm or A.plan(proj)
    zero = {e.name: 0.0 for e in asm.movable}
    A.solve(asm, zero)
    items = proj.items
    link_of, tree = _links(asm)
    origin = {asm.root: np.zeros(3)}
    axis = {}
    for e, pl, cl in tree:                    # the child link frame sits on its joint axis (assembly frame at zero)
        p, d = _world_axis(items[e.parent].shape, items[e.parent].shape.joints[e.pjoint])
        origin[cl], axis[e.name] = p, d
    follow = {s["joint"]: (s["follows"], float(s.get("ratio", 1.0)))
              for s in (proj.data["assembly"].get("sweeps") or []) if "joint" in s and "follows" in s}
    robot = ET.Element("robot", name=proj.dir.name)
    meshes, per_link = {}, {}
    for iid, it in items.items():
        if it.role == "keepout" or it.shape is None or iid not in link_of:
            continue
        V, F = geom.mesh(it.shape)
        V = np.asarray(V, float) - origin[link_of[iid]]       # into the link frame (mm, assembly-frame axes)
        meshes[iid] = (V, np.asarray(F, np.int64))
        mass = (masses or {}).get(iid)
        mass_kg = (checks.item_mass_g(it) if mass is None else float(mass)) / 1000.0
        c, I = _inertial(V, meshes[iid][1], mass_kg)
        per_link.setdefault(link_of[iid], []).append((iid, mass_kg, c, I))
    for link in [asm.root] + [cl for _, _, cl in tree]:
        el = ET.SubElement(robot, "link", name=link)
        parts = per_link.get(link, [])
        M = sum(m for _, m, _, _ in parts)
        if M > 0:
            C = sum(m * c for _, m, c, _ in parts) / M
            I = np.zeros((3, 3))
            for _, m, c, Ii in parts:
                d = c - C
                I += Ii + m * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
            ine = ET.SubElement(el, "inertial")
            ET.SubElement(ine, "origin", xyz=_v(C), rpy="0 0 0")
            ET.SubElement(ine, "mass", value=_f(M))
            ET.SubElement(ine, "inertia", ixx=_f(I[0, 0]), ixy=_f(I[0, 1]), ixz=_f(I[0, 2]),
                          iyy=_f(I[1, 1]), iyz=_f(I[1, 2]), izz=_f(I[2, 2]))
        for iid, _, _, _ in parts:
            for tag in ("visual", "collision"):
                g = ET.SubElement(ET.SubElement(el, tag, name=iid), "geometry")
                ET.SubElement(g, "mesh", filename=f"{MESH_DIR}/{iid}.stl", scale="0.001 0.001 0.001")
    for e, pl, cl in tree:
        kind = "revolute" if e.kind == "revolute" else "prismatic"
        j = ET.SubElement(robot, "joint", name=e.name, type=kind)
        ET.SubElement(j, "parent", link=pl)
        ET.SubElement(j, "child", link=cl)
        ET.SubElement(j, "origin", xyz=_v((origin[cl] - origin[pl]) / 1000.0), rpy="0 0 0")
        ET.SubElement(j, "axis", xyz=_v(axis[e.name]))
        lo, hi = (math.radians(e.range[0]), math.radians(e.range[1])) if kind == "revolute" else (e.range[0] / 1000, e.range[1] / 1000)
        ET.SubElement(j, "limit", lower=_f(lo), upper=_f(hi), effort=_f(EFFORT_NM), velocity=_f(VELOCITY))
        if e.name in follow:
            lead, ratio = follow[e.name]
            ET.SubElement(j, "mimic", joint=lead, multiplier=_f(ratio), offset="0")
    A.solve(asm)
    return robot, meshes, {"links": [asm.root] + [cl for _, _, cl in tree], "joints": [e.name for e, _, _ in tree],
                           "origin_mm": {k: v.tolist() for k, v in origin.items()}, "link_of": link_of}


def write(proj, out: Path, asm=None, masses: dict | None = None) -> dict:
    """Write out/<project>.urdf and its meshes; validate with cadgen. Returns {path, links, joints, findings}."""
    import trimesh
    robot, meshes, info = build(proj, asm, masses)
    (out / MESH_DIR).mkdir(parents=True, exist_ok=True)
    for iid, (V, F) in meshes.items():
        trimesh.Trimesh(V, F, process=False).export(out / MESH_DIR / f"{iid}.stl")
    ET.indent(robot)
    path = out / f"{proj.dir.name}.urdf"
    path.write_text('<?xml version="1.0"?>\n' + ET.tostring(robot, encoding="unicode") + "\n", encoding="utf-8")
    import zipfile
    zp = out / f"{proj.dir.name}_urdf.zip"              # one download: the URDF with its meshes beside it
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(path, path.name)
        for iid in meshes:
            z.write(out / MESH_DIR / f"{iid}.stl", f"{MESH_DIR}/{iid}.stl")
    return {"path": path.name, "zip": zp.name, **{k: info[k] for k in ("links", "joints")}, "findings": validate(path)}


def validate(path: Path) -> list:
    """cadgen's URDF validator (inertia tensors, mesh files, limits, axes): [(severity, code, message)]."""
    from cadgen.urdf_source import validate_urdf_file
    _, rep = validate_urdf_file(path)
    return [(f.severity, f.code, f.message) for f in [*rep.errors, *rep.warnings]]
