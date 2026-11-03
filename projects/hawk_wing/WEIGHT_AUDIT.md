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

## Bounded deeper-box candidate — not accepted

After the first diagnostic, the coordinator authorized one deeper hub and matching cap while retaining
all bearing, pin, gear and stop interfaces. Commit `ea82e3c` preserves that **experimental WIP** only;
do not install it or cherry-pick its geometry into the ready design. It raises the hollow box to 26 mm
depth, adds explicit 1.7 mm walls, relieves the forward airfoil and raises the cap fairing.

Both parts build as valid single solids: hub **103.32 g**, cap **21.31 g**. Together they are approximately
the original pair's mass, so this does not solve the aircraft's 331 g-plus-wiring deficit. The taller pair
also adds about 1512 mm² frontal projected area before the cap lobes; no drag coefficient or aerodynamic
improvement is claimed.

The corrected baseline load case applies pure vector forces to two bands of each **epoxied** spar socket
plus local hub lift, without an extra torque. At 1800 g / 6 g it gives 33.0472 N, with the resultant moment
within 0.7% of the elliptical lift calculation. Mesh sizes 6.0 and 5.6 mm give **10.269 / 10.225 mm** maximum
displacement (0.43% difference) and **20.65 / 20.14 MPa** p99.9 stress, with no coarsening note.
See `validation/hub_normal_flight.json` for the exact regions and both results.

The new 135 mm pivot candidate uses its corresponding 34.9866 N and 5311.7 N mm target. The applied moment
is 5300.4 N mm (0.21% difference). It returns **4.053 mm** maximum displacement and **16.92 MPa** p99.9 stress;
the solver coarsened after an iterative stall. Full evidence and limitations: `validation/hub_candidate.json`.

**Interpretation matters:** these displacements are at the leading-edge corner, not measured socket rotation.
The 1 mm value is a diagnostic stiffness target, not an existing project acceptance threshold. The result
does not prove the aircraft cannot fly. It does leave structural adequacy unverified, and the candidate
provides no meaningful mass saving. Source review also found that its cylindrical socket-relief exclusion
does not establish the claimed 2.4 mm wall over a teardrop roof. No sweep/contact approval was performed
on this rejected candidate. The ready integration should retain the original hub/cap plus the safe taper fix.

Revisit only with an integrated root load path, explicit glove reinforcement, measured socket rotation,
credible print-material behavior and folded-wing aerodynamic/recovery validation. The bounded trial does
not establish that all possible architectures are infeasible; it establishes that this trial is not ready.
