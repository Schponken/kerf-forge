# Hawk: lower-speed dive and re-extension design screen

Status: **UNPROVEN; not a flight procedure or approved flight envelope.** The user chose a lower-speed direction on
2026-11-02; the coordinating agent selected **100 km/h equivalent airspeed (EAS)** as a provisional target, replacing the old 150 km/h design aspiration. No CFD,
wind-tunnel, flutter, deployment-time or flight result establishes an aerodynamic improvement yet.

## Pressure, geometry and deployment contract

Aerodynamic loading scales with dynamic pressure, q = ½ρV². The provisional 100 km/h EAS target is **472.6 Pa**,
44.4% of the old 150 km/h point (**1063.4 Pa**). Full re-extension's existing 80 km/h reference corresponds to
**302.5 Pa**. These are pressure limits for analysis, not GPS speed limits: EAS uses sea-level reference density;
true airspeed increases at altitude for the same q. Source: [NASA dynamic pressure](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/dynamic-pressure/).

Proposed recovery-control improvement, pending physical verification:

1. Gate requested sweep changes on measured/calibrated airspeed or q, actual wing positions and remaining recovery
   height. A GPS speed or altitude alone cannot establish the aerodynamic load.
2. Use staged symmetric re-extension while unloaded, within a separately proven deployment q/load limit. The
   present low-CL hinge-torque cases establish neither loaded opening nor deployment time. An airspeed gate
   alone does not unload the wing.
3. Confirm **both** wings reached the commanded configuration before commanding the pullout. A commanded servo
   angle is not position evidence. No new flight-controller commands or automatic flight actions are delivered.
4. Limit subsequent recovery by both available lift and the verified complete structural load path. The new
   screen considers a gentler **2 g** spread-wing recovery; existing 4 g actuator sizing and 6 g spar cases remain.
   Those cases do not prove the hub, cap, pod, glue joints or full assembly can carry 6 g.

Folded pitch stability is necessary but does not prove low drag or flutter resistance. The cap's existing round
extruded fairing has no validated drag coefficient. Raising two 42 mm-wide cap roofs by 18 mm adds roughly
1512 mm² of frontal projection before lobes: at the new target its force scale is **0.715 N per unit Cd**.
This is an area sensitivity, not predicted drag. A deeper structural root must keep a smooth, tapered external
transition and pass folded clearances before any aerodynamic benefit is claimed. No fairing geometry is adopted
by this change.

## Lift and recovery-height calculation

`dive_recovery_screen` uses the actual assembled mass, including modeled wiring, and the same MH45 CLmax model
as `stall_speed` (Re 200,000). It explicitly leaves `structural_limit_g: null`; its status therefore remains
**unproven/FAIL**, even when the estimated lift can supply 2 g. Deployment and flutter evidence remain unproven.

For context, the following calculation uses **2240.92 g**, the 2131.2 g packaging snapshot plus 109.72 g wiring,
not a newly measured final build mass. At 80 km/h EAS it estimates **2.889 g** maximum lift. A 4 g pullout would need
at least **94.13 km/h EAS**, so the old 4 g / 84 km/h example cannot be reused as a recovery guarantee. At the
1800 g mass target the same 80 km/h point supplies 3.597 g, still below 4 g. The 2 g proposal keeps lift headroom
in this model; it does not establish structural or control headroom.

For a constant-speed circular pullout, bottom-of-arc force balance gives R = V_TAS²/[g(n−1)]. A vertical-to-level
quarter circle loses R of height. At 2 g and 80 km/h EAS:

| Illustrative altitude | True airspeed | Conditional radius / arc height loss |
|---|---:|---:|
| 0 m | 80.00 km/h | 50.36 m |
| 1500 m | 86.07 km/h | 58.29 m |
| 3000 m | 92.84 km/h | 67.82 m |

These are conditional kinematics, **not safe recovery heights**. They exclude deceleration from the dive,
deployment distance/time, response delay, gusts, terrain, uncertainty and reserve. Each second before recovery
at the 3000 m example adds up to 25.8 m descent at that recovery speed. Actual speed can increase before control
is established. No minimum starting height or high-altitude operation is approved here.

Density uses the [NASA troposphere fit](https://www.grc.nasa.gov/www/k-12/airplane/atmosmet.html), normalized to the
engine's 1.225 kg/m³ sea-level reference, within 0–11 km only. The altitude examples hold the reference CLmax
constant; Reynolds-number changes, separated flow and aeroelasticity are not resolved. Further physical evidence
must establish the complete root load path, loaded deployment envelope, measured wing-position feedback and
flutter/control behavior before replacing any unproven state.
