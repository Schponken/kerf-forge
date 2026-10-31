# E2 fpv_5in

"Design me a 5-inch freestyle FPV quad frame I can print on my A2L. 2207 motors, 5.1-inch props, a 30.5 mm
flight controller / ESC stack, a 19 mm micro FPV camera with adjustable tilt, an XT60 mount, and a 6S 1100–1300 mAh
battery strapped on top. It should survive normal crashes and be as light as a printed frame can sensibly be."

## Grading contract (names the grader looks for; the design itself is up to you)
- Purchased motors `motor_1`..`motor_4` (catalog drone motor entry for 2207), keep-outs `prop_1`..`prop_4` (prop disc
  at the prop plane, diameter from the catalog 5.1" prop, `owner: motor_N`), purchased `stack` (30.5 mm FC/ESC
  stack proxy), `camera` (19 mm micro camera proxy), `battery` (6S pack proxy), `xt60`.
- Each motor is held by 4 aligned M3 screws; the stack by 4 aligned M3 screws.
- Motor-to-motor diagonal between 200 and 240 mm.
- Neighbouring prop discs at least 4 mm apart; prop discs touch nothing but their own motor (interference with keep-outs).
- Camera tilt joint named `cam_tilt` covering at least [0, 30] degrees, sweep clear.
- Requirements (ids exactly): `prop_gap` (prop_clearance: >= 4 mm between neighbouring discs, >= 3 mm from each
  disc to every non-owner item, at home and over the cam_tilt sweep), `twr` (thrust_to_weight >= 6 using catalog thrust x 4), `arm_strength`
  (fea_static on the arm under 2x one motor's max thrust at the motor mount, fixed at its frame bolts, safety factor
  per docs/ENGINEERING.md),
  `frame_mass` (mass_max on the printed parts only, <= 250 g).
- Every printed part fits the A2L.

## Complete electronics (added 2026-10-30; graded)
- Every electrical part needed to actually fly is in the project as a catalog-backed purchased item, not just the
  ones named above: flight controller, ESC(s), receiver + antenna, BEC/regulator for any servos, battery strap, power
  connector, video TX + antenna + camera.
- project.yaml has a `wiring:` section covering every connection, with wire gauge and routed length per run.
- Requirements (ids exactly): `power` (power_budget: battery C-rating, BEC, connector and every wire within rating
  at peak current), `flight_time` (estimate reported; must be >= 3 min at hover).
- out/WIRING.md and out/wiring.svg exist; the BOM lists every wire, connector and electrical part with a buy link.
