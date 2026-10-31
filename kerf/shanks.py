"""Screw shanks: after `assembly.fasteners` picks each screw's length, the screw body (head seat to tip) must not run
into anything but the part it threads into. Catches a stack screw whose tip pokes out of its nut into an arm, or a
screw tip that reaches a prop disc or a board. Modelled as a cylinder of 0.8 x the nominal diameter (just under the
ISO 261 minor diameter, so threads cut in a pilot hole of the receiving part are not counted)."""
from __future__ import annotations

import numpy as np
from build123d import Plane, Solid, Vector

from . import geom

SHANK_FRAC = 0.8


def check(asm, joints) -> list:
    items = asm.proj.items
    problems = []
    for j in joints:
        if j.get("length_mm") is None or "at" not in j:
            continue
        d = float(j["screw"].lstrip("M"))
        o, z = np.array(j["at"]), np.array(j["dir"])
        rod = Solid.make_cylinder(SHANK_FRAC * d / 2, float(j["length_mm"]), Plane(origin=Vector(*o), z_dir=Vector(*z)))
        for iid, it in items.items():
            if it.shape is None or iid in (j["male"], j["female"]):
                continue
            v = geom.overlap(it.shape, rod)
            if v > geom.OVERLAP_TOL_MM3:
                tip = np.round(o + z * j["length_mm"], 2).tolist()
                problems.append(f"fastener group '{j['group']}': the {j['screw']} x {j['length_mm']:g} screw from {j['male']} "
                                f"into {j['female']} runs into {iid} ({v:.1f} mm3; tip at {tip})")
    return problems


def build(asm, joints) -> list:
    """Each sized screw as one solid (shank cylinder from the seat to the tip, 0.8 d, plus the head where it has one),
    in the male part's own frame so it moves with that part; electrical.route_check keeps wires off them (a phase
    lead lying on a thread end that stands proud of a nut wears through)."""
    from .iface import screw_spec

    items = asm.proj.items
    out = []
    for j in joints:
        if j.get("length_mm") is None or "at" not in j:
            continue
        d = float(j["screw"].lstrip("M"))
        o, z = np.array(j["at"], dtype=float), np.array(j["dir"], dtype=float)
        world = Solid.make_cylinder(SHANK_FRAC * d / 2, float(j["length_mm"]), Plane(origin=Vector(*o), z_dir=Vector(*z)))
        sp = screw_spec(j["screw"])
        if j.get("head") != "countersink" and sp.get("head_d") and sp.get("head_h"):
            world = world + Solid.make_cylinder(sp["head_d"] / 2, sp["head_h"], Plane(origin=Vector(*o), z_dir=Vector(*(-z))))
        out.append({"male": j["male"], "female": j["female"], "group": j["group"], "screw": j["screw"],
                    "local": items[j["male"]].shape.location.inverse() * world})
    return out
