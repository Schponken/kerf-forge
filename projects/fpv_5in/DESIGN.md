# 5" freestyle FPV frame — design

## Requirements (evals/fpv_5in/brief.md)
- 2207 motors, 5.1" props, 30.5 mm FC/ESC stack, 19 mm camera with ≥ 0-30° tilt, XT60, 6S 1100-1300 battery on top.
- Motor-to-motor diagonal 200-240 mm; neighbouring prop discs ≥ 4 mm apart, every disc ≥ 3 mm from everything else.
- Thrust-to-weight ≥ 6; printed frame ≤ 250 g; arms survive 2 × one motor's max thrust with SF 3; fits the A2L.
- CG within 5 mm of the thrust centre (ENGINEERING.md section 9).

## Architecture
1. Unibody printed plate (Drone-v1): fewest parts, but a crash means reprinting the whole frame.
2. **Body plate + 4 bolt-on arms + top plate on posts (picked)**: like the carbon frames (OpenFrame-5F, Source One),
   arms are the replaceable crash part; the battery rides on a separate top plate above the prop plane.
3. Arms sandwiched between two plates (OpenFrame): stiffest root, but three-layer joints and more parts.

## Purchased parts and sizing
| Item | Catalog | Mass | Notes |
|---|---|---|---|
| 4 × motor | drone.motors.2207_1855kv_6s | 4 × 31.6 g | 1685 g max thrust each (iFlight test report) |
| stack | drone.stacks.fc_30_5 | 34 g | 45.6 mm ESC board, 22 mm tall |
| camera | drone.cameras.micro_19mm | 9 g | tilt about the side M2 screws |
| battery | drone.batteries.6S_1300 | 215 g | 82 × 40 × 36 mm |
| XT60 | drone.connectors.XT60 | (not catalogued) | |
- Thrust/weight: 4 × 1685 = 6740 g / ~498 g all-up (frame 125 g + parts above; props, screws and wires ~40 g more)
  → ~13 (requirement ≥ 6).
- Arm root bending (hand calc): crash load 2 × 1685 g = 33.1 N at r = 113 mm; outer arm screw at r = 52 mm → lever
  61 mm, M = 2017 N·mm; section 20 × 11 mm: Z = 403 mm³ → 5.0 MPa nominal. FEA (fixed at the two arm screws, load on
  the four motor-screw seats) gives a 10.4 MPa 99.9th-percentile peak at the screw holes vs CF-PETG 35 MPa / SF 3 =
  11.7 MPa, deflection 1.1 mm (crash case; ~0.2 mm at hover thrust).
- Mass: printed parts 125 g (limit 250).

## Parts (all CF-PETG, hardened nozzle, ≥ 4 walls)
| Part | Job | Print orientation | load_axis | Envelope |
|---|---|---|---|---|
| body | centre plate, stack, arm clamps, camera cheeks, post seats | flat, cheeks up | both diagonals | 98 × 86 × 23 |
| arm_1..4 | carry each motor to the body | flat, top face up | x (along the arm) | 107 × 32 × 11 |
| top_plate | battery deck, XT60 cradle, 4 posts | upside down (plate on bed) | – | 104 × 42 × 30 |

## Interfaces
| A | B | How | Group | Screws |
|---|---|---|---|---|
| arm_N | body | M3 counterbored from below into nut traps (pockets open on the body top) | arm_N | 2 × M3 × 12 per arm |
| motor_N | arm_N | M3 from below (counterbored, 7 mm grip) into the motor base | motor_N | 4 × M3 × 10 per motor |
| stack | body | M3 from the stack top through grommets into nut traps (pockets open underneath) | stack | 4 × M3 × 30 |
| top_plate | body | M3 counterbored from below into heat-set inserts in the post feet | posts | 4 × M3 × 6 + 4 inserts |
| camera | body | side M2 screws through the cheek teardrop holes into the camera (pivot, friction) | – | 2 × M2 × 5 |
| battery | top_plate | 20 mm strap through two slots | – | – |
| XT60 | top_plate | cradle under the rear tab + cable tie | – | – |

## Joint tree
body (root) → arm_1..4 (rigid, along the diagonals) → motor_N → prop_N keep-out; body → stack; body → top_plate →
battery, xt60; body → camera (`cam_tilt`, revolute about the side screws, 0-40°, lens up positive, home 25°).

## Geometry choices
- Prop plane: motor top + 40% of the shaft = 24.5 mm above the arm top; discs 7 mm thick (hub 6.8 mm). The top plate
  underside is at 32 mm and inside r ≈ 47 mm, so the battery sits above and inside the props (prop_gap 5.7 mm).
- Arm screws at r = 38 and 52 mm, outside the stack board (±22.8 mm) so screw tips never reach under the ESC; the
  stack nut pockets (r = 21.6 mm) open underneath inside the arm-free centre.
- Camera pivot 48 mm forward, 17 mm up: the cube's corners clear the body top (1.2 mm) and the front posts (3.5 mm)
  over the whole tilt range (swept).

## Assembly order
1. Press 4 M3 heat-set inserts into the top-plate post feet.
2. Put 8 M3 nuts into the arm nut pockets on the body top and 4 M3 nuts into the stack pockets underneath.
3. Bolt each arm under the body: 2 × M3 × 12 from below.
4. Bolt each motor onto its arm: 4 × M3 × 10 from below (check ~3 mm thread engagement, never longer: windings).
5. Stack on the grommets: 4 × M3 × 30 from the top into the stack nuts. Solder motors / XT60 lead.
6. Camera between the cheeks: 2 × M2 × 5 into its side holes; set the tilt, snug the screws.
7. Top plate: 4 × M3 × 6 up through the body into the post inserts; XT60 into the cradle with a cable tie.
8. Battery on top with the strap through both slots.

## Risks / measure first
- Camera side-hole position (catalog note: scaled from a drawing) and the 22 mm stack height (typical, not published).
- Motor thread depth is typical (catalog): M3 × 10 with 7 mm grip leaves 3 mm in the motor — check before tightening.
- Hover-test before freestyle and check gyro noise: a printed frame is far less stiff than carbon.
