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
| XT60 | drone.connectors.XT60 | (not catalogued) | battery plug end open to the rear |
| VTX | drone.vtx.tx800 | 5.6 g | 28 × 28 mm, 20 × 20 M2, hangs under the rear half of the top plate (centre x −13.5) |
| VTX antenna | electronics.antennas.lollipop4p_mmcx_95 | 4.8 g | 95 mm tube, MMCX 90°, head above the rear tab end |
- Thrust/weight: 4 × 1685 = 6740 g at full output, but the XT60 is rated 60 A burst (Holybro: 1 minute) and four
  motors at full output draw 4 × 35.08 = 140 A. Betaflight `set motor_output_limit = 73` caps each motor: by the
  propeller law (thrust ~ rpm², power ~ rpm³) 1685 × 0.73² = 898 g and 35.08 × 0.73³ = 13.65 A per motor →
  3592 g / 558.5 g all-up = **6.43**, peak 55.1 A (the `power` requirement). Raise the limit only with a bigger
  connector; the 73 % figure is an estimate — check the Blackbox current peak on the first flights.
  → 12.6 (requirement ≥ 6).
- Arm root bending (hand calc): crash load 2 × 1685 g = 33.1 N at r = 113 mm; outer arm screw at r = 52 mm → lever
  61 mm, M = 2017 N·mm; section 20 × 11 mm: Z = 403 mm³ → 5.0 MPa nominal. FEA (fixed at the two arm screws, load on
  the four motor-screw seats) gives 9.8 MPa (99.9th percentile) at the screw holes vs CF-PETG 35 MPa / SF 3 =
  11.7 MPa, deflection ~1 mm (crash case; ~0.2 mm at hover thrust).
- Body (the part that must outlive the arms): the same crash reaches it as a lever couple on the arm screws — arm as
  a beam on supports at r 38 / 52 with 33.06 N at r 113 → inner nut pulls the body down 144.0 N, the arm presses up
  on the underside round the outer screw with 177.1 N. FEA held at the four post feet: 9.8 MPa vs 11.7 MPa
  (needed a 7 mm plate plus 3 × 5 mm ribs either side of each arm's screws; 5 mm plain plate gave 22 MPa).
- Mass: printed parts 145 g (limit 250).

## Parts (all CF-PETG, hardened nozzle, ≥ 4 walls)
| Part | Job | Print orientation | load_axis | Envelope |
|---|---|---|---|---|
| body | 7 mm centre plate + ribs, stack, arm clamps with key grooves, camera cage, post seats | flat, cheeks and ribs up | both diagonals | 114 × 92 × 25 |
| arm_1..4 | carry each motor to the body; key ridges on top | flat, top face up | x (along the arm) | 102 × 32 × 12.5 |
| top_plate | battery deck, camera roof, VTX bosses, XT60 cradle, receiver/antenna tie slots, 2 post pillars (9 × 25 mm) | upside down (plate on bed) | – | 122 × 42 × 41 |

## Interfaces
| A | B | How | Group | Screws |
|---|---|---|---|---|
| arm_N | body | M3 counterbored from below into nut traps (pockets open on the body top); 2 ridges in 2 grooves take side loads | arm_N | 2 × M3 × 14 per arm |
| motor_N | arm_N | M3 from below (counterbored, 7.5 mm grip: 2.5 mm into the 3 mm motor thread) | motor_N | 4 × M3 × 10 per motor |
| stack | body | M3 from the stack top through grommets into nut traps (pockets open underneath) | stack | 4 × M3 × 30 |
| top_plate | body | M3 counterbored from below into heat-set inserts in the post feet | posts | 4 × M3 × 8 + 4 inserts |
| vtx | top_plate | M2 through the VTX (washers: its holes take M3) and 6 mm nylon spacers into pilot holes in 3 mm bosses | vtx | 4 × M2 × 12 |
| camera | body | side M2 screws through the cheek teardrop holes (heads in 1 mm recesses) into the camera, 2.5 mm thread (pivot, friction) | – | 2 × M2 × 6 |
| battery | top_plate | one 20 mm strap around the pack's width at x 4.5–24.5 (past 1 mm plate-edge notches, under the plate clear of the VTX) | – | – |
| XT60 | top_plate | cradle under the rear tab: rear end open for the battery plug, 1 mm stops at the front; a cable tie through two vertical slots beside the cradle wraps under the connector (its lower 4 mm hangs below the walls) | – | – |
| receiver | top_plate | under the camera roof, cable tie through two slots | – | – |
| VTX antenna | top_plate | tube runs from the VTX rear corner outside the rear pillar, under the tab (tie through the y −10.5 slot pair), up behind the tab end | – | – |
| receiver antenna | top_plate | T legs tied up and out in a V through the two slots at the roof front (behind the lens) | – | – |

## Joint tree
body (root) → arm_1..4 (rigid, along the diagonals) → motor_N → prop_N keep-out; body → stack; body → top_plate →
battery, xt60, vtx; body → camera (`cam_tilt`, revolute about the side screws, 0-40°, lens up positive, home 25°).

## Geometry choices
- Prop plane: motor top + 40% of the shaft = 24.5 mm above the arm top; discs 7 mm thick (hub 6.8 mm). The top plate
  underside is at 45 mm (raised to fit the VTX above the stack screw heads), so the battery sits well above the props.
  Tightest prop gap 3.45 mm (prop_1 to the body).
- Arm screws at r = 38 and 52 mm, outside the stack board (±22.8 mm) so screw tips never reach under the ESC; the
  arms start at r = 26 (rounded root about r = 36) so the M3 × 30 stack screw tips (1 mm out of the body, r = 21.6)
  touch nothing — `kerf check` now models every screw shank to prove it.
- Camera pivot 48 mm forward, 19 mm up: the cube's corners clear the body top and the front posts over the whole
  tilt range (swept). The 4 mm cheeks run to x = 68, 3 mm past the lens front at its furthest (x 64.8 at 34°),
  gusseted to the nose; their tops slope down at the front to keep 3 mm from the front prop discs.

- Top plate (review round 2): each post pair is filled into one 9 × 25 mm pillar (posts at x ±33, y ±8) so a 50 g battery
  hit (112.8 N + its 2369 N·mm tipping couple, posts bent across the layers) stays inside CF-PETG z strength / 3:
  FEA 7.7 (front/back) and 8.7 (side) vs 9.67 MPa. A 24 mm roof tongue reaches over the camera to x 58 (lens front
  61.9-64.8), 9.8 mm above the camera top at full tilt, so a hit from above lands on the roof.
- Arm key ridges are 4.5 × 1.5 mm: a 33 N side hit bends the ridge root across one layer line at about 3 MPa.

## Assembly order
1. Press 4 M3 heat-set inserts into the top-plate post feet; screw the VTX under the top plate (4 × M2 × 12 with
   washers and 6 mm nylon spacers) — on the bench, before the plate goes on.
2. Put 8 M3 nuts into the arm nut pockets on the body top and 4 M3 nuts into the stack pockets underneath (those
   open downward: hold each with a strip of tape or a dab of CA until its screw has started).
3. Bolt each arm under the body, ridges in the grooves: 2 × M3 × 14 from below.
4. Bolt each motor onto its arm: 4 × M3 × 10 from below (2.5 mm into the motor; never longer: windings).
5. Stack on the grommets: 4 × M3 × 30 from the top into the stack nuts. Solder motors / XT60 lead.
6. Camera between the cheeks: 2 × M2 × 6 into its side holes; set the tilt, snug the screws.
7. Top plate: 4 × M3 × 8 up through the body into the post inserts; XT60 into the cradle (solder cups forward)
   with a cable tie wrapped under it through the two slots beside the cradle; receiver tied under the camera roof;
   VTX antenna tube tied under the tab and bent up behind it; receiver antenna legs tied in a V at the roof front. XT60 leads run outside the post pillars (|y| > 12.5 mm).
8. Battery on the pad; strap around the pack's width in the plate-edge notches, under the plate (between the VTX
   and the front pillar).
9. Betaflight: `set motor_output_limit = 73`, `save` (keeps the XT60 inside its 60 A rating; see sizing).

## Risks / measure first
- Camera side-hole position (catalog note: scaled from a drawing) and the 22 mm stack height (typical, not published).
- Motor thread depth is typical (catalog): M3 × 10 with 7.5 mm grip leaves 2.5 mm in the motor, 0.5 mm short of the
  3 mm thread bottom (> the ±0.29 mm screw-length tolerance) — check one before tightening all.
- VTX height (8 mm incl. heatsink) is typical, not published: 2 mm stays above the stack screw heads.
- Arm first bending mode is roughly in the gyro noise band (reviewer hand calc ~165 Hz) and PETG-CF softens near a
  hot motor: hover-test and check Blackbox gyro noise before freestyle.
- Flight time 13 min is the ideal-hover estimate (momentum theory, figure of merit 0.5); real hover draws more and
  freestyle flying gives about 3–5 min on a 1300 mAh 6S pack.
- Motor phase runs are modelled as 18 AWG extensions; the motors' own lead gauge/length is not in the catalog (with
  the 73 % output limit a 20 AWG lead also stays inside the 60 K / 5 s burst rule: 13.65 A).
