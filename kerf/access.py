"""Assembly-access checks: can the screws be driven, and can parts be put in place?

(a) hex-key reach: from the head of every male screw site, a straight hex key (across-corners envelope, L-key long-arm
    reach from catalog tools.hex_key) along the screw axis must clear every item. If it doesn't but a ball-end key at up
    to 25 deg does, that's a warning (buy a ball-end driver); if neither, it's a problem.
(b) insertion paths: an item declared with `insert: {direction: [x, y, z], distance: mm}` (direction = the way it moves
    as it goes IN, in the item's own frame) is slid in from `distance` away and must not hit anything on the way
    (its own subtree moves with it; allow_overlap allowances still apply). With `assembly.order`, items installed
    later than it (in its subtree or not) are not there yet: they neither move with it nor block it; subtree items
    installed in an EARLIER step are already in place and block it (a servo slid in last onto a mounted horn).
Assembly order: `assembly.key_access: [{group, before: [items], why}]` says those items are fitted after the group's
screws are driven (e.g. the second motor of a coax pair covers the first motor's screw heads), so they don't block it.
"""
from __future__ import annotations

import math

import numpy as np
from build123d import Plane, Pos, Solid, Vector

from . import assembly as A, catalog, geom
from .iface import screw_spec

HEAD_ON_SURFACE = {"clearance", "counterbore"}   # site origin = under the head; countersink heads sit flush


def key_spec(screw: str, kind: str) -> dict:
    hk = catalog.get("tools.hex_key")
    table = hk["socket_s_countersunk"] if kind == "countersink" and screw in hk["socket_s_countersunk"] else hk["socket_s_shcs"]
    if screw not in table:
        raise ValueError(f"no hex key size for {screw} in catalog tools.hex_key")
    s = float(table[screw])
    reach = float(hk["long_arm_mm"][f"{s:g}"])
    return {"s": s, "r": s / math.cos(math.radians(30)) / 2, "reach": reach, "ball_deg": float(hk["ball_end_max_deg"])}


def _rod(o, d, r, L):
    return Solid.make_cylinder(r, L, Plane(origin=Vector(*o), z_dir=Vector(*d)))


def _blocked(rod, shapes):
    return [i for i, s in shapes if geom.overlap(s, rod) > geom.OVERLAP_TOL_MM3]


def _rigid_part(sh):
    """The shape a tool can't push aside: without its `kerf_flex` solids (loose servo leads, item frame)."""
    flex = getattr(sh, "kerf_flex", None)
    if not flex:
        return sh
    out = sh
    for f in flex:
        out = out - f.moved(sh.location)
    return out


def _ball_end_dir(start, z, k, present, n_azimuth=12):
    """A ball-end key direction (tilted k['ball_deg'] off the screw axis) that clears `present`, else None."""
    a = math.radians(k["ball_deg"])
    ex = np.cross(z, [1.0, 0, 0] if abs(z[0]) < 0.9 else [0, 1.0, 0])
    ex /= np.linalg.norm(ex)
    ey = np.cross(z, ex)
    for t in np.linspace(0, 2 * math.pi, n_azimuth, endpoint=False):
        d = math.cos(a) * z + math.sin(a) * (math.cos(t) * ex + math.sin(t) * ey)
        # the ball end sits in the socket, so the tilted shank starts one key radius up the axis
        if not _blocked(_rod(start + z * k["r"], d, k["r"], k["reach"]), present):
            return d
    return None


def _install_steps(asm) -> dict:
    """assembly.order: the build sequence, a list of item ids (or lists of ids installed in the same step). Items not
    listed count as present from the start (step 0), the conservative choice."""
    steps = {}
    for k, entry in enumerate(asm.proj.data["assembly"].get("order") or [], start=1):
        for i in ([entry] if isinstance(entry, str) else entry):
            if i not in asm.proj.items:
                raise ValueError(f"assembly.order names unknown item '{i}'")
            steps[i] = k
    return steps


def hex_key_reach(asm, n_azimuth: int = 12) -> tuple[list, list, list]:
    """Returns (per-screw results, problems, warnings) at the current pose. With `assembly.order`, a screw is driven
    when the later of the parts it joins is installed, so only items installed by then can block the key."""
    items = asm.proj.items
    step = _install_steps(asm)
    female_items: dict = {}
    for i, it in items.items():
        for fs in getattr(it.shape, "kerf_sites", []) if it.shape is not None else []:
            if fs.role == "female":
                female_items.setdefault(fs.group, set()).add(i)
    all_shapes = [(i, _rigid_part(it.shape)) for i, it in items.items() if it.shape is not None and it.role != "keepout"]
    # sub-assemblies a linear order can't express: {group, before: [items], why} = those items go on after this
    # group's screws are driven (e.g. each motor of a coax pair is screwed to its own plate before the plates join)
    later = {}
    for k in asm.proj.data["assembly"].get("key_access") or []:
        if not k.get("why"):
            raise ValueError(f"assembly.key_access for group '{k.get('group')}' needs a 'why' (the assembly order)")
        later.setdefault(k["group"], set()).update(k["before"])
    results, problems, warnings = [], [], []
    for iid, it in items.items():
        if it.shape is None:
            continue
        for s in getattr(it.shape, "kerf_sites", []):
            if s.role != "male":
                continue
            when = max([step.get(iid, 0)] + [step.get(f, 0) for f in female_items.get(s.group, ())])
            present = [(i, sh) for i, sh in all_shapes if step.get(i, 0) <= when and i not in later.get(s.group, ())]
            w = it.shape.location * s.loc
            o = geom.world_point(w, (0, 0, 0))
            z = geom.world_dir(w, (0, 0, 1))
            k = key_spec(s.screw, s.kind)
            top = o + z * (screw_spec(s.screw)["head_h"] if s.kind in HEAD_ON_SURFACE else 0.0)
            start = top + z * 0.05           # the key tip sits in the socket; start just above the head
            hits = _blocked(_rod(start, z, k["r"], k["reach"]), present)
            res = {"item": iid, "group": s.group, "screw": s.screw, "key_mm": k["s"], "at": np.round(top, 2).tolist(),
                   "straight": not hits, "blocked_by": hits}
            if hits:
                ok_dir = _ball_end_dir(start, z, k, present, n_azimuth)
                res["ball_end"] = ok_dir is not None
                where = f"{s.screw} screw in {iid} (group '{s.group}') at {res['at']}"
                if ok_dir is not None:
                    warnings.append(f"{where}: a straight {k['s']:g} mm hex key hits {hits}; it needs a ball-end key "
                                    f"(up to {k['ball_deg']:g} deg off axis)")
                else:
                    problems.append(f"{where}: no {k['s']:g} mm hex key can reach the head (straight hits {hits}, "
                                    f"ball-end at {k['ball_deg']:g} deg also blocked)")
            results.append(res)
    _horn_centre_screws(asm, items, all_shapes, step, results, problems, warnings)
    return results, problems, warnings


def _horn_centre_screws(asm, items, all_shapes, step, results, problems, warnings):
    """Every servo horn is held on its spline by a centre screw, driven when the horn goes on (assembly.order) through
    whatever is already there (the link bolted to the horn on the bench: iface.horn_mount cuts its access hole). Checked
    like any screw: the head sits on the horn face, a hex key of its size along the servo axis (else a ball-end key)
    must reach it past everything installed by then except the horn and its servo."""
    from .iface import horn_dims
    for iid, it in items.items():
        if it.shape is None or it.role == "keepout" or it.spec.get("proxy") != "horn":
            continue
        h = horn_dims(it.spec["catalog"])
        cs = h["center_screw"]
        top_z = -h["engage"] + max(h["hub_total"] or h["t"], h["t"])           # horn face, proxy frame
        w = it.shape.location
        o = geom.world_point(w, (0, 0, top_z))
        z = geom.world_dir(w, (0, 0, 1))
        k = key_spec(cs, "clearance")
        start = o + z * (screw_spec(cs)["head_h"] + 0.05)
        e = asm.by_child.get(iid)
        servo = e.parent if e is not None else None                      # the screw threads into its spline
        present = [(i, sh) for i, sh in all_shapes if i not in (iid, servo) and step.get(i, 0) <= step.get(iid, 0)]
        hits = _blocked(_rod(start, z, k["r"], k["reach"]), present)
        res = {"item": iid, "group": f"{iid} centre screw", "screw": cs, "key_mm": k["s"],
               "at": np.round(start, 2).tolist(), "straight": not hits, "blocked_by": hits}
        if hits:
            ok = _ball_end_dir(start, z, k, present)
            res["ball_end"] = ok is not None
            where = f"{cs} horn centre screw of {iid} at {res['at']}"
            if ok is not None:
                warnings.append(f"{where}: a straight {k['s']:g} mm key hits {hits}; it needs a ball-end key")
            else:
                problems.append(f"{where}: no {k['s']:g} mm key can reach it along the servo axis (hits {hits}, "
                                f"ball-end also blocked): cut an access hole (iface.horn_mount) or fit those parts "
                                f"after the horn (assembly.order)")
        results.append(res)


def insertion_paths(asm, step_mm: float = 1.0) -> tuple[list, list]:
    """Slide every item with an `insert:` spec into its seat; returns (results, problems)."""
    items = asm.proj.items
    allow = A._allowed(asm)
    step = _install_steps(asm)
    results, problems = [], []
    for iid, it in items.items():
        spec = it.spec.get("insert")
        if not spec or it.shape is None:
            continue
        d_loc = np.asarray(spec["direction"], float)
        d_loc /= np.linalg.norm(d_loc)
        dist = float(spec["distance"])
        # with assembly.order, only what is already installed matters: subtree items fitted later (a horn and arm on a
        # servo that goes in first) neither ride along nor block, and nothing installed later blocks. Subtree items
        # installed in the SAME step ride along (a bench sub-assembly); ones installed EARLIER are already in place,
        # so they stay put and are obstacles (a servo slid in last onto a horn + link that are already mounted)
        now = step.get(iid, 0)
        moving = sorted(m for m in asm.subtree(iid) if m == iid or step.get(m, 0) == now)
        homes = {m: items[m].shape.location for m in moving}
        d = geom.world_dir(items[iid].shape.location, d_loc)
        others = [i for i, o in items.items() if o.shape is not None and o.role != "keepout" and i not in moving
                  and step.get(i, 0) <= now]
        n = max(8, math.ceil(dist / step_mm))
        hits = []
        try:
            for back in np.linspace(dist, 0, n, endpoint=False):
                off = Pos(*(-d * back))
                for m in moving:
                    items[m].shape.location = off * homes[m]
                for m in moving:
                    if items[m].role == "keepout":
                        continue
                    for o in others:
                        lim = allow.get(frozenset((m, o)), (0.0, ""))[0]
                        v = geom.overlap(items[m].shape, items[o].shape)
                        if v > max(lim, geom.OVERLAP_TOL_MM3):
                            hits.append({"a": m, "b": o, "volume_mm3": round(v, 3), "mm_from_seat": round(float(back), 2)})
        finally:
            for m in moving:
                items[m].shape.location = homes[m]
        results.append({"item": iid, "direction": d.round(4).tolist(), "distance_mm": dist, "clear": not hits,
                        "collisions": hits[:12]})
        if hits:
            h = max(hits, key=lambda h: h["mm_from_seat"])
            problems.append(f"{iid} cannot be inserted along {np.round(d, 3).tolist()}: {h['a']} hits {h['b']} "
                            f"({h['volume_mm3']} mm3) {h['mm_from_seat']} mm before it is seated")
    return results, problems
