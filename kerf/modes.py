"""Selectable modes (docs/VISION.md section 1): one pipeline, different depths. A mode switches pipeline stages on or
off; a deeper mode run later reuses what a shallower one finished (kerf/partcache.py keeps every built part and its
print checks, the FEA cache keeps every solved load case), so upgrading never starts over.

| Mode     | Gives                                                        | Skips                              |
| sketch   | the parts, fit check, assembly.glb + viewer.html to look at  | motion, wiring, engineering checks, print files, BOM |
| print    | STL / 3MF per part, A2L plates + print settings, fit + motion| FEA, wiring, BOM, renders          |
| check    | every check: fit, motion, wiring, requirements incl. FEA     | files                              |
| simulate | check + the viewer, FEA plots and joint poses                | print files, BOM, assembly guide   |
| kit      | everything: files, priced BOM, wiring, assembly guide, firmware, renders, review pack | nothing |
| ship     | kit, then (only with explicit confirmation) the printer handoff, once a design review is current | - |

`ship` is opt-in only: never a default, refused without `--ship` (Studio asks for its own click), because it sends
plates to the user's printer.
"""
from __future__ import annotations

# stage -> what it does (kerf/pipeline.py checks these names)
STAGES = {
    "build": "build every part",
    "print": "per-part print checks (overhang, walls, bed size)",
    "fit": "assembly: interference, fasteners, pins, hex-key reach, insertion",
    "motion": "joint sweeps and wire routes over every joint extreme",
    "electrical": "electrical model: loads, wire gauges, lengths",
    "requirements": "requirement checks (torque, mass, clearance, ...)",
    "fea": "FEA load cases inside the requirements",
    "files": "STEP, STL / 3MF per part, A2L plates, print settings, drawings, URDF",
    "docs": "priced BOM, WIRING.md, ASSEMBLY.md, firmware",
    "viewer": "assembly.glb + viewer.html",
    "renders": "renders: sheets, FEA plots, poses, assembly steps, review pack",
}

MODES = {
    "sketch": {"build", "print", "fit", "viewer"},
    "print": {"build", "print", "fit", "motion", "requirements", "files", "viewer"},
    "check": {"build", "print", "fit", "motion", "electrical", "requirements", "fea"},
    "simulate": {"build", "print", "fit", "motion", "electrical", "requirements", "fea", "viewer", "renders"},
    "kit": set(STAGES),
    "ship": set(STAGES),
}
ORDER = ["sketch", "print", "check", "simulate", "kit", "ship"]
GIVES = {
    "sketch": "a 3D model to look at (viewer.html), fit checked",
    "print": "printable STL / 3MF and A2L plates with print settings, fit and motion checked",
    "check": "the full engineering report: fit, motion, wiring, requirements, FEA",
    "simulate": "the full report plus the viewer, FEA plots and joint poses",
    "kit": "everything: files, priced BOM, wiring guide, assembly guide, firmware, renders",
    "ship": "the kit, then plates sent to your printer (needs a current design review and your confirmation)",
}


class ShipNotConfirmed(ValueError):
    pass


def stages(mode: str) -> set:
    if mode not in MODES:
        raise ValueError(f"unknown mode '{mode}' (use {', '.join(ORDER)})")
    return set(MODES[mode])


def legacy(sweeps: bool, do_export: bool, do_render: bool) -> set:
    """The stage set the old `kerf check [--quick]` / `kerf build` flags mean."""
    if do_export or do_render:
        s = set(STAGES)
        return s if do_render else s - {"renders"}
    return MODES["check"] if sweeps else MODES["check"] - {"motion", "fea"}


def confirm_ship(mode: str, confirmed: bool):
    """Ship it prints on the user's printer: refuse unless they confirmed it explicitly."""
    if mode == "ship" and not confirmed:
        raise ShipNotConfirmed("Ship it sends plates to your printer, so it only runs with your explicit go-ahead: "
                               "add --ship (Studio: the Ship it button's own confirmation). Nothing was run.")
