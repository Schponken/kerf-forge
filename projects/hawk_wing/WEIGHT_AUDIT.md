# Hawk mass and structural redesign audit

Baseline: installed source snapshot `5a98dc7`, geometry fingerprint `adf3ad47a8d22d2d`.
The installed engine's validated per-part cache was read on 2026-11-03 UTC; no installed source was changed.
The early-stopped report has no part table, so values below use the same `checks.item_mass_g` function.
They are model estimates, not weighed or sliced print masses. Wiring is absent from this baseline.

| Printed item | Estimated mass (g) | Geometry observation |
|---|---:|---|
| Glove | 360.98 | Solid CAD envelope, three perimeters and 10% infill; reinforcement modifiers are prose |
| Fuselage | 272.21 | Explicit 1.6 mm main shell, filled aft socket cone |
| Hub, each | 110.14 | Solid airfoil root, raised aft box, bearings and gear; 50% infill |
| Pod, each | 72.02 | Closed 3 mm ring, ribs, floor and servo skirt |
| Inner wing skin, each | 52.83 | Already one wall, 3% infill, carbon tube primary load paths |
| Outer wing skin, each | 34.77 | Already one wall, 3% infill |
| Tail mount | 33.56 | Boom sleeve, surface seats and servo pockets |

Reported assembled mass: **2155.1 g**, at least **355.1 g above the 1800 g limit** before adding wiring.
No part is a placeholder. Lowering catalog density, infill assumptions, or acceptance limits is not a fix.

## Investigation status

The weight worker owns `glove.py` and `hub.py`; the integration worker owns the fuselage, pods,
layout and packaging. Moving the pivot inward requires the hub's raised-box taper to follow
`pivot_y + 32`, preserving its original distance from the pivot instead of leaving a fixed 182 mm station.

Before removing structural material, verify the existing hub under a normal flight load case.
The project currently contains no `fea_static` requirements despite its design prose. Strength simulation
was explicitly resumed by Spencer for this task. No flight-strength or completed-weight claim is made here.

Candidate hub relief preserves the outer section, socket walls, bearing boss, raised aft box, gear and
wire channel, with ribs at its ends and mid-span. It remains a candidate until geometry mass and strength
are measured. Even this and an explicitly hollow glove may be insufficient for 1800 g once wiring is counted.
