# E1 servo_link (seed, built before handoff)

"A servo test rig: a base plate, a bracket that holds an MG996R servo, and a 100 mm arm on the servo horn that
can swing ±90° without hitting anything. Everything bolts together with M3 screws."

## Grading contract
- Purchased `servo` (servos.MG996R) and `horn` (aluminum 25T horn); printed `base`, `bracket`, `arm`.
- Joint `swing` (servo output) covers [-90, 90] and sweeps clear.
- Every connection is a real fastener joint: base↔bracket, bracket↔servo, horn↔arm (>= 12 screws total, all aligned).
- Requirement `arm_torque` (static_torque on `swing`, payload 50 g at the arm tip, max_fraction <= 0.5) passes.
