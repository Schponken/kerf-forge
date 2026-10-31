"""Horizontal holes (docs/ENGINEERING.md section 4, audit ENG-7): a round hole whose axis lies along the bed in the
print orientation sags at its roof (the top of the circle is an unsupported bridge), so a pin or screw meant to fit it
binds. iface cuts a teardrop (45-degree roof) when given `teardrop=` (iface.print_up_deg works out the angle); this
check finds the iface holes that were cut round although they print horizontal.

- A pin hole (free or press fit) cut round and horizontal is a PROBLEM: the fit is the pin's whole job.
- A fastener hole (clearance, tap, heat-set) cut round and horizontal is a WARNING: a screw clears a small sag, but
  the pilot / insert bore comes out undersize vertically.
Holes within HORIZONTAL_DEG of the bed plane count as horizontal. Holes not cut by iface (teardrop unknown) are skipped.
"""
from __future__ import annotations

import math

from build123d import Location

from . import geom

HORIZONTAL_DEG = 30.0
TEARDROP_KINDS = {"clearance", "tap", "heatset"}     # the kinds iface.hole can teardrop


def _up_component(rot, loc) -> float:
    """|cos| of the angle between the hole axis (loc +Z, part frame) and the printer's vertical."""
    d = geom.world_dir(rot * loc, (0, 0, 1))
    return abs(float(d[2]))


def check(item) -> tuple[list, list]:
    shape = item.shape
    rot = Location((0, 0, 0), tuple(float(a) for a in (item.spec.get("print_rot") or [0, 0, 0])))
    lim = math.sin(math.radians(HORIZONTAL_DEG))
    problems, warnings = [], []
    pins = {}
    for p in getattr(shape, "kerf_pins", []) or []:
        if p.teardrop is False and p.fit in ("free", "press") and _up_component(rot, p.loc) < lim:
            pins.setdefault(p.group, 0)
            pins[p.group] += 1
    for g, n in pins.items():
        problems.append(f"{item.id}: {n} pin hole(s) of group '{g}' print horizontal and are cut round; the roof sags "
                        f"and the pin binds. Pass teardrop=iface.print_up_deg(ctx, loc) to iface.pin_hole "
                        f"(docs/ENGINEERING.md s4)")
    fast = {}
    for s in getattr(shape, "kerf_sites", []) or []:
        if s.teardrop is False and s.kind in TEARDROP_KINDS and _up_component(rot, s.loc) < lim:
            fast.setdefault((s.group, s.kind), 0)
            fast[(s.group, s.kind)] += 1
    for (g, k), n in fast.items():
        warnings.append(f"{item.id}: {n} {k} hole(s) of group '{g}' print horizontal and are cut round (the top sags, a "
                        f"pilot or insert bore comes out undersize); pass teardrop=iface.print_up_deg(ctx, loc) "
                        f"(docs/ENGINEERING.md s4)")
    return problems, warnings
