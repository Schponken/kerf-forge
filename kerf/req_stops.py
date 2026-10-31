"""Hard stops: prove that a revolute or linear joint cannot go past an end of its range.

The sweep checks only look inside [min, max], so a joint whose parts simply stop touching at its limit (e.g. a finger
that keeps bending backward past straight) passes them. `hard_stop` moves the joint `beyond` its range (e.g. 5 deg
past 0) and requires the parent and child to overlap there by at least `min_mm3`, i.e. a real shoulder meets them
before that point."""
from __future__ import annotations

from . import assembly as A, geom
from .requirements import check


@check("hard_stop")
def hard_stop(proj, asm, joint, beyond, min_mm3=1.0):
    """value = overlap (mm3) of the joint's parent and child with the joint at `beyond` (outside its range)."""
    e = next((x for x in asm.edges if x.name == joint), None)
    if e is None:
        raise ValueError(f"no joint '{joint}'")
    lo, hi = e.range
    if lo <= beyond <= hi:
        raise ValueError(f"beyond = {beyond} lies inside joint '{joint}' range {list(e.range)}; give a value past an end")
    pj = proj.items[e.parent].shape.joints[e.pjoint]
    attr = "angular_range" if e.kind == "revolute" else "linear_range"
    old = getattr(pj, attr)
    setattr(pj, attr, (min(old[0], beyond), max(old[1], beyond)))
    try:
        A.solve(asm, {joint: beyond})
        v = geom.overlap(proj.items[e.parent].shape, proj.items[e.child].shape)
    finally:
        setattr(pj, attr, old)
        A.solve(asm)
    unit = "deg" if e.kind == "revolute" else "mm"
    return {"ok": v >= min_mm3, "value": round(v, 2), "limit": float(min_mm3),
            "detail": f"{e.parent} and {e.child} overlap (mm3) with '{joint}' at {beyond:g} {unit}, past its range "
                      f"{list(e.range)}: a stop must meet them before that"}
