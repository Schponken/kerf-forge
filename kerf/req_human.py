"""The person using it (docs/VISION.md section 2): reach and access from the use story, and the carry / repair notes.

- `repair_access`: the parts the use story expects to replace in the field (`use_story.field_repair`, e.g. a drone's
  arms) come off the finished device with a hex key: every screw that holds them is reachable with everything else
  still fitted (straight key, or a ball-end key when `ball_end_ok`). A part whose screws hide under others needs a
  teardown, which is a workshop repair, not a field one.
- Things touched in use (`use_story.handles`) get an `access_opening` check (kerf/usestory.py): 32 mm bare-finger
  opening, 38 mm when the story has a gloves hazard.
- ASSEMBLY.md "Carrying and field repair" (`notes()`): mass and size, how to carry it (`use_story.carry_by`), props
  off for transport on a drone, the field-repair parts with their key sizes, and the spares to keep (accepted
  failures and the designed weak link).
"""
from __future__ import annotations

from .requirements import UNITS, check


@check("repair_access")
def repair_access(proj, asm, parts, ball_end_ok=True):
    from . import access, assembly as A
    A.solve(asm)
    rows = access.repair_reach(asm, parts)
    bad = [r for r in rows if not (r["straight"] or (ball_end_ok and r["ball_end"]))]
    keys = sorted({r["key_mm"] for r in rows})
    return {"ok": not bad and bool(rows), "value": len(bad), "limit": 0, "keys_mm": keys,
            "detail": (f"{len(rows)} screws hold {', '.join(parts)}; " + (f"all reachable on the finished device with a "
                       f"{' / '.join(f'{k:g}' for k in keys)} mm hex key" if not bad else
                       "blocked on the finished device: " + "; ".join(f"{r['screw']} in {r['item']} ({r['group']}) by "
                       f"{r['blocked_by']}" for r in bad[:4]))) if rows else f"no screws found holding {parts}"}


def notes(proj, rep: dict) -> list[str]:
    """ASSEMBLY.md 'Carrying and field repair'."""
    s = proj.data.get("use_story") or {}
    m = (rep.get("mass") or {}).get("device_g")
    L = []
    if m:
        L.append(f"- It weighs about {m:.0f} g as built" + (f"; carry it by {s['carry_by']}." if s.get("carry_by") else "."))
    if any(str(it.spec.get("catalog", "")).startswith("drone.props.") for it in proj.items.values()):
        L.append("- Take the props off (and the battery out) before it goes in a bag or a car: a bent prop or a "
                 "spun-up motor is the usual transport damage.")
    fr = s.get("field_repair") or []
    if fr:
        row = next((r for r in rep.get("requirements") or [] if r.get("check") == "repair_access"), None)
        keys = row.get("keys_mm") if row else None
        L.append(f"- Field repair: {', '.join(fr)} come off the finished device"
                 + (f" with a {' / '.join(f'{k:g}' for k in keys)} mm hex key" if keys else "") + ".")
    spares = [a["hazard"] + ": " + a["consequence"] for a in ((rep.get("use_story") or {}).get("accepted_failures") or [])]
    wl = [r for r in rep.get("requirements") or [] if r.get("check") == "weak_link" and r.get("ok")]
    if fr or spares or wl:
        keep = sorted(set(fr))
        L.append("- Spares worth keeping: " + (", ".join(keep) if keep else "the parts named below")
                 + (" (the designed weak link breaks first)" if wl else "") + ".")
    if not L:
        return []
    return ["## Carrying and field repair", ""] + L + [""]


UNITS.update({"repair_access": ("screws blocked", "max")})
