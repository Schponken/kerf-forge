# E4 tvc_drone

"My thrust-vectoring rocket drone, like fd.iwth's build: a tall mast made of carbon rods and printed rings, the
battery mounted near the top, a coaxial counter-rotating motor pair (two motors, two props) on a two-axis servo
gimbal at the bottom that steers the thrust, and three landing legs. It has to stand on its own, the gimbal has to
move freely, and it needs enough thrust to climb."

## Grading contract
- Purchased `motor_top`, `motor_bottom` (catalog motors), keep-outs `prop_top`, `prop_bottom` (owners the motors),
  servos `servo_pitch`, `servo_roll` (catalog), `battery`, carbon rods named `rod_*` (catalog rods, >= 3).
- Printed landing legs named `leg_*` (>= 3).
- Gimbal joints `gimbal_pitch` and `gimbal_roll` each covering [-15, 15], swept clear, plus a coupled pose sweep
  named `gimbal_corners` containing the four corners (±15, ±15), clear.
- Requirements (ids exactly): `twr` (thrust_to_weight >= 1.8), `cg_axis` (cg: assembled CG within 3 mm of the
  thrust axis laterally and above the gimbal pivot), `stand` (tip_over: static tip-over angle >= 15°),
  `gimbal_fea` (fea_static on the part that carries the motors' thrust into the gimbal, 2x max thrust).

## Complete electronics (added 2026-10-30; graded)
- Every electrical part needed to actually fly is in the project as a catalog-backed purchased item, not just the
  ones named above: flight controller, ESC(s), receiver + antenna, BEC/regulator for any servos, battery strap, power
  connector, IMU-capable FC that can drive the gimbal servos.
- project.yaml has a `wiring:` section covering every connection, with wire gauge and routed length per run.
- Requirements (ids exactly): `power` (power_budget: battery C-rating, BEC, connector and every wire within rating
  at peak current), `flight_time` (estimate reported; must be >= 2 min at hover).
- out/WIRING.md and out/wiring.svg exist; the BOM lists every wire, connector and electrical part with a buy link.
