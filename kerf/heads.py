"""Screw heads as solids. Purchased screws are not items, so a socket head standing proud of a moving part (e.g. horn
screws on a gear face under a turning platform) was invisible to the interference and sweep checks. After
`assembly.fasteners` pairs and sizes the screws, every socket head (clearance or counterbore seat; countersunk heads
sit flush and are skipped) becomes a cylinder (catalog head_d x head_h, from the seat outward) fixed to the part it
seats on, so it moves with that part through every pose. `assembly.interference` then checks each head against
every item except the two parts it clamps (and the pair's allow_overlap), so sweeps catch it too."""
from __future__ import annotations

import numpy as np
from build123d import Plane, Solid, Vector

from . import geom

SHRINK = 0.05      # mm off the head radius and the seat, so a head touching a counterbore wall or its seat is not a hit


def build(asm, joints) -> list:
    """Head solids in the male part's own frame (call with all joints at home, right after fasteners())."""
    from .iface import screw_spec

    items = asm.proj.items
    heads = []
    for j in joints:
        if j.get("length_mm") is None or "at" not in j or j.get("head") == "countersink":
            continue
        sp = screw_spec(j["screw"])
        if not sp.get("head_d") or not sp.get("head_h"):
            continue
        up = -np.array(j["dir"], dtype=float)                      # from the seat out of the part, away from the tip
        o = np.array(j["at"], dtype=float) + up * SHRINK
        world = Solid.make_cylinder(sp["head_d"] / 2 - SHRINK, sp["head_h"] - SHRINK, Plane(origin=Vector(*o), z_dir=Vector(*up)))
        male = items[j["male"]].shape
        heads.append({"male": j["male"], "female": j["female"], "group": j["group"], "screw": j["screw"],
                      "local": male.location.inverse() * world})
    return heads


def interference(asm, pairs=None, allow=None) -> list:
    """Overlaps of screw heads with other items at the current pose. pairs: only (male, other) pairs in this set
    count (the sweep passes the pairs that move relative to each other); None = every item."""
    heads = getattr(asm, "heads", None) or []
    if not heads:
        return []
    items = asm.proj.items
    allow = allow or {}
    pairset = None if pairs is None else {frozenset(p) for p in pairs}
    hits = []
    for h in heads:
        male = items[h["male"]].shape
        solid = None
        for iid, it in items.items():
            if it.shape is None or iid in (h["male"], h["female"]):
                continue
            if pairset is not None and frozenset((h["male"], iid)) not in pairset:
                continue
            if solid is None:
                solid = male.location * h["local"]
            v = geom.overlap(it.shape, solid)
            lim = allow.get(frozenset((h["male"], iid)), (geom.OVERLAP_TOL_MM3, ""))[0]
            if v > max(lim, geom.OVERLAP_TOL_MM3):
                hits.append({"a": f"{h['male']} ({h['screw']} screw head, group '{h['group']}')", "b": iid,
                             "volume_mm3": round(v, 3)})
    return hits
