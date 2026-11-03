# Hawk candidate validation — FAIL, not ready to print or fly

Frozen implementation: `7911eea`. Final source fingerprint: `8614ff72b99bbbb3` (including the dependency manifest recorded by the check).

`PYTHONPATH=. KERF_PROGRESS=1 .venv/bin/kerf check hawk_wing --all` completed in **507.2 s**, with **63 reported problems**. The complete unchanged report, including every collision pair and sampled pose, is [validation/final_check_report.json](validation/final_check_report.json). The integrated wiring and recovery fixtures passed **17 tests in 2.54 s**. No full build, independent design review, print, installation or flight was performed. PR81 remains a draft and the original project task remains unchecked.

| Measurement | Preserved baseline | Final isolated candidate |
|---|---:|---:|
| Body case envelope | 517.8 × 355.6 × 98 mm | **496.8 × 325.6 × 98 mm — PASS** against 500 × 330 × 220 |
| Spread static margin | 0.0736 MAC | **0.0799 — FAIL**, minimum 0.08 |
| Estimated mass | 2155.1 g, wiring omitted | **2215.4 g — FAIL**, includes 109.7 g declared wiring; maximum 1800 |
| Wing loading | 107.8 g/dm² | **110.8 — FAIL**, maximum 95 |
| Stall speed | 46.2 km/h | **46.8 — FAIL**, maximum 45 |
| Cruise endurance | Missing electrical graph | **15.6 min — FAIL**, minimum 20 |
| Power | Missing electrical graph | **FAIL**: stock 18 AWG phase leads predict 227 K rise versus 60 K allowed over 10 s |

These are model estimates, not weighed or flight-measured results. The mass columns are not directly comparable because the baseline omitted wiring. The supported fuselage orientation fits the printer envelope, but the part still fails watertightness and insert-wall checks; support removal, print stability and layer strength are unproven.

Remaining candidate findings (no attribution to the baseline versus these changes without a separate baseline comparison):

- Both pinion screw heads hit the glove from 5° through 45° sweep, worst 5.87 mm³ per side.
- Elevator hits the tail mount at −22°, −14.67° and −7.33°, worst 1133.926 mm³; the boom also hits the elevator at −22° and −14.67°.
- Fuselage mesh is not watertight; two glove insert walls are insufficient. The boom-clamp screw intersects the boom; four motor screws lack assembled tool access.
- Multiple declared wire routes intersect physical parts. Exact run, part, volume and pose records are retained in the full report. XT60 access is blocked by the hatch in the assembled access check.
- Fuselage and motor-mount layer-direction strength remain unproven; explicit root/glove structural proof is incomplete.
- Mass, loading, stall, endurance, stock phase-lead heating and spread margin still fail. Recovery remains explicitly UNPROVEN despite adequate modeled lift for the proposed gentler recovery.

The user selected a lower-speed direction; the coordinating agent chose **100 km/h EAS as a provisional target**, not a verified safe speed. No aerodynamic improvement, safe recovery altitude, deployment reliability or flutter clearance is established. Original pilot-speed instructions were withdrawn. See [DIVE_RECOVERY.md](DIVE_RECOVERY.md) and [ELECTRICAL.md](ELECTRICAL.md).

The deeper hub/cap experiment was rejected and its geometry was **not integrated**. [WEIGHT_AUDIT.md](WEIGHT_AUDIT.md) and the saved diagnostic JSON explain exact loads, solver limitations, the diagnostic-only displacement target and the absence of meaningful mass savings. Those diagnostics do not establish that the aircraft is categorically unflyable or that every architecture is infeasible.

The installed Hawk source was preserved and remains unchanged by this work. Continue only from this isolated candidate after addressing the recorded load paths, mechanical clearances, electrical routing and endurance architecture; no acceptance limits were relaxed, apart from applying the requested lower dive-speed direction.
