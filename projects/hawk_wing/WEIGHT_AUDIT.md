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

## Baseline structural diagnostic — failed

`validation/hub_baseline.json` records the reproducible boundary regions, loads, solver settings and result.
The original hub was fixed at the two 625 bearing seats and loaded at its two spar sockets with 35 N total
(73/27% split) plus 5300 N mm torque. This deliberately conservative test adds the socket-force lever
moment to the 5.3 N m panel moment; the total about the original pivot is approximately 6.19 N m.
It is an overtest, not an exact distribution of the new layout's 6 g lift.

Result: **24.04 MPa p99.9 stress versus 24 MPa at SF 2**, **11.925 mm maximum deflection** versus a
1 mm diagnostic stiffness target. The peak stress was 63.8 MPa near the bearing/raised-box transition.
The solver used a coarser exact solve after its iterative solver stalled (22,606 elements in the final solve).
This is not a converged proof, and the solid CAD model does not prove the 50% infill print. It demonstrates
no established stiffness margin for weight reduction; simply correcting the conservative load does not
explain away an order-of-magnitude displacement shortfall.

**Decision: defer hub hollowing.** An unbuilt cavity candidate was removed before any change to load-bearing
geometry was committed. Preserve the current hub while the torque path is redesigned and verified.
The glove also needs explicit reinforcement geometry: current text-only modifiers are ignored by both
mass accounting and local-infill analysis. Its current mass is not a complete reinforced print estimate.

A source review found no credible local 331 g-plus-wiring saving after the packaging change: the fuselage
main shell is already 1.6 mm, wing and tail skins already use one wall, and hollowing must retain the hub
boss, gear and aft torque path. A smaller battery would trade away the endurance requirement.
No all-up-mass PASS or flight-readiness claim is justified. Revisit after a deeper/shorter hub torque path
and a center-wing structure with explicit load-bearing ribs or spars have been validated.
