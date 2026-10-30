"""Place parts with joints, then check the assembly: interference, motion sweeps, fastener alignment."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
from build123d import LinearJoint, Location, RevoluteJoint, RigidJoint

from . import geom
from .project import Project, ProjectError

STANDARD_SCREW_LENGTHS = [3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 30, 35, 40, 45, 50, 55, 60]


@dataclass
class Edge:
    name: str
    parent: str
    pjoint: str
    child: str
    cjoint: str
    kind: str = "rigid"
    range: tuple = (0.0, 0.0)
    home: float = 0.0


@dataclass
class Assembly:
    proj: Project
    root: str
    edges: list
    by_child: dict = field(default_factory=dict)
    children: dict = field(default_factory=dict)

    @property
    def movable(self):
        return [e for e in self.edges if e.kind != "rigid" and e.range[1] > e.range[0]]

    def subtree(self, item: str) -> set:
        out, stack = set(), [item]
        while stack:
            n = stack.pop()
            out.add(n)
            stack.extend(self.children.get(n, []))
        return out


def _split(ref: str):
    if "." not in ref:
        raise ProjectError(f"joint reference '{ref}' must look like item.joint_label")
    a, b = ref.split(".", 1)
    return a, b


def plan(proj: Project) -> Assembly:
    a = proj.data["assembly"]
    root = a.get("root")
    if root not in proj.items:
        raise ProjectError(f"assembly.root '{root}' is not a part")
    edges = []
    for j in a.get("joints") or []:
        p, pj = _split(j["parent"])
        c, cj = _split(j["child"])
        for item in (p, c):
            if item not in proj.items:
                raise ProjectError(f"joint {j} refers to unknown item '{item}'")
        edges.append(Edge(name=j.get("name", c), parent=p, pjoint=pj, child=c, cjoint=cj,
                          range=tuple(j["range"]) if "range" in j else (0.0, 0.0), home=float(j.get("home", 0.0))))
    asm = Assembly(proj, root, edges)
    for e in edges:
        if e.child in asm.by_child:
            raise ProjectError(f"'{e.child}' is attached twice; every item needs exactly one parent joint")
        asm.by_child[e.child] = e
        asm.children.setdefault(e.parent, []).append(e.child)
    unattached = [i for i in proj.items if i != root and i not in asm.by_child]
    if unattached:
        raise ProjectError(f"not attached to the assembly: {unattached}")
    # type each edge from the parent joint object, check labels exist
    for e in edges:
        ps, cs = proj.items[e.parent].shape, proj.items[e.child].shape
        if ps is None or cs is None:
            continue
        if e.pjoint not in ps.joints:
            raise ProjectError(f"{e.parent} has no joint '{e.pjoint}' (has {sorted(ps.joints)})")
        if e.cjoint not in cs.joints:
            raise ProjectError(f"{e.child} has no joint '{e.cjoint}' (has {sorted(cs.joints)})")
        pj = ps.joints[e.pjoint]
        if not isinstance(cs.joints[e.cjoint], RigidJoint):
            raise ProjectError(f"child joint {e.child}.{e.cjoint} must be rigid (put moving joints on the parent)")
        if isinstance(pj, RevoluteJoint):
            e.kind = "revolute"
            if e.range == (0.0, 0.0):
                e.range = tuple(pj.angular_range)
        elif isinstance(pj, LinearJoint):
            e.kind = "linear"
            if e.range == (0.0, 0.0):
                e.range = tuple(pj.linear_range)
        if e.kind != "rigid" and not (e.range[0] <= e.home <= e.range[1]):
            raise ProjectError(f"joint {e.name}: home {e.home} outside range {e.range}")
    order = _topo(asm)
    asm.edges = order
    return asm


def _topo(asm: Assembly):
    out, queue = [], [asm.root]
    while queue:
        n = queue.pop(0)
        for c in asm.children.get(n, []):
            out.append(asm.by_child[c])
            queue.append(c)
    return out


def solve(asm: Assembly, values: dict | None = None):
    """Move every item into place. values: {joint_name: angle_deg_or_mm}."""
    values = values or {}
    items = asm.proj.items
    items[asm.root].shape.location = Location()
    for e in asm.edges:
        pj = items[e.parent].shape.joints[e.pjoint]
        cj = items[e.child].shape.joints[e.cjoint]
        v = float(values.get(e.name, e.home))
        if e.kind == "revolute":
            pj.connect_to(cj, angle=v)
        elif e.kind == "linear":
            pj.connect_to(cj, position=v)
        else:
            pj.connect_to(cj)


def _allowed(asm: Assembly) -> dict:
    out = {}
    for a in asm.proj.data["assembly"].get("allow_overlap") or []:
        x, y = a["pair"]
        out[frozenset((x, y))] = (float(a.get("max_mm3", 0.0)), a.get("why", ""))
    for kid, it in asm.proj.items.items():
        if it.role == "keepout" and it.spec.get("owner"):
            out[frozenset((kid, it.spec["owner"]))] = (float("inf"), "keepout of its owner")
    return out


def interference(asm: Assembly, pairs=None) -> list:
    items = asm.proj.items
    allow = _allowed(asm)
    ids = [i for i, it in items.items() if it.shape is not None]
    pairs = pairs if pairs is not None else itertools.combinations(ids, 2)
    hits = []
    for a, b in pairs:
        if items[a].role == "keepout" and items[b].role == "keepout":
            continue
        v = geom.overlap(items[a].shape, items[b].shape)
        lim, why = allow.get(frozenset((a, b)), (geom.OVERLAP_TOL_MM3, ""))
        if v > max(lim, geom.OVERLAP_TOL_MM3):
            hits.append({"a": a, "b": b, "volume_mm3": round(v, 3)})
    return hits


def sweeps(asm: Assembly, samples: int = 9) -> list:
    """Move each joint through its range (others at home) and look for collisions."""
    results = []
    ids = [i for i, it in asm.proj.items.items() if it.shape is not None]
    custom = {s["joint"]: s for s in (asm.proj.data["assembly"].get("sweeps") or []) if "joint" in s}
    # geared/belted joints: {joint: j2, follows: j1, ratio: r} turns j2 = r * j1 whenever j1 is swept, never alone
    follow = {j: (s["follows"], float(s.get("ratio", 1.0))) for j, s in custom.items() if "follows" in s}
    edge_by_name = {e.name: e for e in asm.movable}
    for j, (lead, _) in follow.items():
        if j not in edge_by_name or lead not in edge_by_name:
            raise ProjectError(f"sweep coupling {j} follows {lead}: both must be moving joints")
    for e in asm.movable:
        if e.name in follow:
            continue
        n = int(custom.get(e.name, {}).get("samples", samples))
        followers = [(edge_by_name[j], r) for j, (lead, r) in follow.items() if lead == e.name]
        groups = [asm.subtree(e.child)] + [asm.subtree(f.child) for f, _ in followers]
        key = lambda i: tuple(i in g for g in groups)  # noqa: E731
        pairs = [(a, b) for a in ids for b in ids if a < b and key(a) != key(b)]
        worst, collisions = 0.0, []
        for v in np.linspace(e.range[0], e.range[1], n):
            solve(asm, {e.name: float(v), **{f.name: r * float(v) for f, r in followers}})
            hits = interference(asm, pairs)
            for h in hits:
                worst = max(worst, h["volume_mm3"])
                collisions.append({**h, "at": round(float(v), 2)})
        results.append({"joint": e.name, "kind": e.kind, "range": list(e.range), "samples": n,
                        "clear": not collisions, "worst_mm3": round(worst, 3), "collisions": collisions[:12]})
    # coupled poses (e.g. all finger joints together)
    for s in asm.proj.data["assembly"].get("sweeps") or []:
        if "poses" not in s:
            continue
        coll = []
        for pose in s["poses"]:
            solve(asm, pose)
            coll += [{**h, "pose": pose} for h in interference(asm)]
        results.append({"joint": s.get("name", "poses"), "kind": "poses", "samples": len(s["poses"]),
                        "clear": not coll, "collisions": coll[:12]})
    solve(asm)
    return results


def fasteners(asm: Assembly) -> tuple[list, list]:
    """Check every bolted joint lines up, and size the screws. Returns (joints, problems)."""
    from .iface import screw_spec

    groups: dict[str, list] = {}
    for iid, it in asm.proj.items.items():
        if it.shape is None:
            continue
        loc = it.shape.location
        for s in getattr(it.shape, "kerf_sites", []):
            w = loc * s.loc
            o = geom.world_point(w, (0, 0, 0))
            z = geom.world_dir(w, (0, 0, 1))
            groups.setdefault(s.group, []).append((iid, s, o, z))
    joints, problems = [], []
    for g, sites in sorted(groups.items()):
        males = [x for x in sites if x[1].role == "male"]
        females = [x for x in sites if x[1].role == "female"]
        used = set()
        for (mi, ms, mo, mz) in males:
            best = None
            for k, (fi, fs, fo, fz) in enumerate(females):
                if k in used or fi == mi:
                    continue
                ang = np.degrees(np.arccos(np.clip(np.dot(mz, fz), -1, 1)))
                off = np.linalg.norm(np.cross(fo - mo, mz))
                along = float(np.dot(mo - fo, mz))
                if ang < 1.0 and off < 0.15 and along > -0.01:
                    if best is None or along < best[1]:
                        best = (k, along)
            if best is None:
                problems.append(f"fastener group '{g}': {ms.screw} hole in {mi} at {np.round(mo, 2).tolist()} has no matching receiver hole (aligned within 0.15 mm)")
                continue
            k, along = best
            used.add(k)
            fi, fs, fo, fz = females[k]
            gap = along - ms.grip
            spec = screw_spec(ms.screw)
            need_min = along + (fs.min_engage or min(fs.engage, spec["min_engage"]))
            need_max = along + fs.engage
            length = next((L for L in STANDARD_SCREW_LENGTHS if need_min - 1e-3 <= L <= need_max + 1e-3), None)
            j = {"group": g, "screw": ms.screw, "male": mi, "female": fi, "head": ms.kind, "receiver": fs.kind,
                 "grip_mm": round(along, 2), "gap_mm": round(gap, 2), "length_mm": length}
            if abs(gap) > 0.3:
                problems.append(f"fastener group '{g}': {mi} sits {gap:.2f} mm off {fi} along the screw axis (parts not clamped together)")
            if length is None:
                problems.append(f"fastener group '{g}': no standard {ms.screw} length fits grip {along:.1f} mm + engagement {fs.engage:.1f} mm in {fi}")
            joints.append(j)
        for k, (fi, fs, fo, fz) in enumerate(females):
            if k not in used:
                problems.append(f"fastener group '{g}': {fs.screw} {fs.kind} hole in {fi} at {np.round(fo, 2).tolist()} has no screw coming through a matching hole")
    return joints, problems
