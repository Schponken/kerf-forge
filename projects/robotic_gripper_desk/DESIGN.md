# Parallel gripper for the desk robot arm — design

Spencer's request (Kerf Studio, 2026-10-31): "robotic gripper for the desk robot arm". Nobody was available to ask, so
the assumptions are written here: the gripper replaces the arm's current single-finger gripper (projects/robot_arm
`gripper` + `finger`) on the same wrist, reuses the arm's grip servo and wiring, and must not push any of the arm's
servos past half their stall torque.

## Requirements
| Requirement | Number | Why / where it is proven |
|---|---|---|
| Fits the arm's wrist unchanged | wrist fork 35 mm wide (robot_arm `grip_w`), plate A on the wrist's aluminium 25T horn (4 × M3), plate B on the M3 pivot screw in a heat-set insert, coaxial | the bench stand reproduces the forearm's wrist end from the same catalog math; fastener + pin checks |
| Clears the arm over the wrist range | wrist −75…+75° | wrist sweep against the stand (= forearm end) and the wrist servo |
| Payload | hold 150 g (the arm's payload) by friction, slip factor ≥ 2 | grip-force math below (needs oiled rods); proven by the bench hold test, assembly step 9 |
| Opening | ≥ 40 mm (robot_arm brief), target ~54 mm; jaws stay parallel, object stays centred on the tool point | `grip_open`, `grip_closed` |
| Arm torque budget | no arm servo past half stall: gripper + grip servo + horn ≤ 166 g (≤ 194 g incl. rods and screws), wrist gravity torque with 150 g at the tool point ≤ 2.35 kg·cm (25 % of the wrist MG996R) | `gripper_mass`, `torque_wrist`; the shoulder hand check below |
| Strength | FEA on every structural part at the grip servo's stall, SF per ENGINEERING.md §3; teeth by Lewis at stall | `*_fea`, `pinion_teeth`, `rack_teeth` |
| Motion | no collision over the grip and wrist ranges; mechanical stop at full open | sweeps, `stop_open_*` |
| Electrics | the arm's own: grip servo on its 5 A-fused lead, PWM from the arm's PCA9685 | `power`, WIRING.md |

## Architecture
Options (REFERENCES.md):
- (a) keep the arm's single moving finger against a fixed jaw (today's gripper): simplest, but the contact point moves
  with object size, the jaws close at an angle, and the arm must re-aim for every object;
- (b) two gear-coupled pivoting fingers (MeArm / hobby "claw" style): symmetric, all pin joints, but the pads still
  rotate as they close (objects squeeze out) unless every finger gets a four-bar;
- (c) **rack-and-pinion parallel jaws** (OpenManipulator-X style linear jaws): one pinion on the servo drives two racks
  in opposite directions, so both jaws move the same distance and stay parallel; the object is centred on a fixed tool
  point and the grip force is the same at every opening. Picked (c).

Layout (parts/layout.py, gripper frame: X forward, Y up at home, Z across the wrist fork; the same frame as the arm's
gripper, so the files port to robot_arm by copying):
- The grip servo (MG996R, 55 g) lies **inline** between the two fork plates (20.0 mm wide body in the 21 mm gap),
  inserted top-first through a 6 mm bulkhead at x = 45 (`servo_mount(top_through)`, the same mounting as every arm
  joint), output shaft pointing forward on the wrist line (y = 0), so the tool point is on the wrist line too.
- A 20-tooth module-1.5 pinion (pitch Ø 30, face 12) is bolted to the servo's aluminium 25T horn. Two racks mesh
  with it, one above and one below; the top rack is part of jaw_r, the bottom one of jaw_l (the same printed part
  turned 180° about X). Servo +θ moves both jaws outward by 15 mm × θ (rad) each (kerf.drives.rack_pinion; the sweep
  couples them with ratio 0.2618 mm/deg).
- Each jaw is a carriage on **two shared Ø4 mm stainless guide rods** across the head (in front of the pinion), plus a
  finger forward to the grip pad. The rods (Ø4 stainless) are pressed into the gripper body's two end cheeks and kept from walking
  out by a small printed keeper (1 × M3).
- The two racks push the pinion in opposite directions, so when both jaws grip, the pinion's tooth forces form a pure
  couple and the servo spline carries torque only (ENGINEERING.md §8). Only when one jaw is blocked alone does the
  spline see a side load (61 N at stall, the same as an ordinary servo arm at stall).

Bench stand (`stand`): the arm's forearm wrist end (plate A carrying the wrist MG996R top-through, plate B with the
free pivot hole, 57.4 mm apart, as robot_arm/parts/forearm.py) on a base you clamp to the bench edge. It is there so
the checks prove the gripper fits and clears the real wrist, and so you can test and calibrate the gripper on the
bench before it goes on the arm.

## Bench electrics (testing on the stand)
On the arm the gripper needs nothing new: its servo stays on the arm's 5 A-fused lead (robot_arm `pwr_gr`) and PCA9685
channel 4 (`sig_gr`), proven by the arm's own `power` check. For the bench stand the project carries a small set of its
own, the one servo_link already proves for one MG996R: MEAN WELL GST60A05 5 V 6 A adapter -> SparkFun barrel-jack
screw-terminal adapter -> the grip servo through a 300 mm Pololu extension (male end cut off, red/brown into the jack's
screw terminals, orange crimped onto Nano D9); Nano GND to the jack minus (common ground); the Nano runs from the PC's
USB and `out/firmware/` has its bring-up sketch.
Only the grip servo is powered on the bench. With both servos on the adapter the 1 m DC cord (gauge unpublished, so
checked as 22 AWG) drops the servos to 4.72 V at their running current, under the MG996R's 4.8 V minimum (`power`
fails), and the only fixes were an unsourced cord gauge or a second regulator stage. The stand's wrist servo stands in
for the arm's wrist servo mechanically (it carries the horn and pivot the gripper bolts onto); on the bench it stays
unplugged and you set the wrist angle by turning the gripper slowly by hand.
The stand is not free-standing with the gripper on it (the head and payload sit ~110 mm ahead of the base's front
edge): screw it to the bench through the two M4 holes in its bars, or clamp the back bar at a bench corner, BEFORE
powering the grip servo. One servo at 0.9 A: 5.0 V minus 0.10 V in
the cord, 0.06 V in the 600 mm lead = 4.83 V >= 4.8 V; stalled 2.5 A of the adapter's 6 A.

## Purchased parts and sizing
| Item | Catalog | Notes |
|---|---|---|
| grip servo | servos.MG996R | the arm already has it (old gripper): 9.4 kg·cm stall @ 4.8 V, 55 g, 0.17 s/60° |
| grip horn | servo_horns.aluminum_25T | the arm's; pinion bolts to its 4 × M3 holes on Ø 14 |
| guide rods | rods.ss_rod_4 | 2 × Ø 4 × 100 mm stainless precision shafting (ServoCity 2100-0004-0100, $2.79 each), 9.9 g each; Ø4 is 3.2× stiffer than Ø3 (REFERENCES.md decision 8). Pressed into blind/through seats in the two end cheeks, kept in by the rod keeper |
| stand wrist servo + horn | servos.MG996R, servo_horns.aluminum_25T | only for the bench stand (on the arm it is the arm's wrist servo) |

**Grip force.** MG996R stall T = 9.4 kg·cm = 922 N·mm (catalog, 4.8 V). The pinion pitch radius is r = 15 mm.
With both jaws on the object the torque splits over two meshes: F = T / (2 r) = 922 / 30 = **30.7 N per jaw at stall**,
15.4 N at half stall. Holding the 150 g payload by friction with both jaws: 2 μ N ≥ S · m g. With μ = 0.24 (bare
PETG, the low end of Stoimenov 2024's printed-polymer-on-steel values; REFERENCES.md decision 6) and a slip factor
S = 2 (covers ~1 g of arm acceleration): N ≥ 2 × 1.47 / (2 × 0.24) = 6.1 N per jaw.
*Guide friction (the carriage cocks on its rods; corrected in review round 3).* Three things load the 14 mm bores
while the rack drives the jaw with force D and the object pushes back with P at the pad:
(1) in the plane of the finger, the rack line (x ≈ −6.6, jaw frame) and the pad centre (x ≈ 30) sit 11.6 and 25 mm
either side of the bores (x = 5): a couple 11.6 D + 25 P that each bore takes as two edge loads 14 mm apart;
(2) across it, jaw_r's rack pitch line is at y = +15 (jaw.py) while the pad and the rod pair's centre are at y = 0:
a second couple 15 D, the servo's own reaction, which the free object cannot take;
(3) the tooth separating force, D tan 20° = 0.36 D, pressing the carriage sideways on its rods.
Each adds bore friction μ × normal load. Adding them arithmetically, with (2) carried as opposite side loads on the
two rods 42 mm apart, gives D = P + μ (2 (11.6 D + 25 P) / 14 + 2 × 15 D / 42 + 0.36 D), so
**P = D (1 − 2.74 μ) / (1 + 3.57 μ)** (conservative); the reviewer's vector sum of the edge loads gives a little more.
Over the two models:

| Rods | μ in the bores | P / D | pad force per jaw at stall (D = 30.7 N) | at half stall (D = 15.4 N) | slip factor at half stall (6.1 N needed) |
|---|---|---|---|---|---|
| dry | 0.24 (Stoimenov 2024, printed PETG on steel) | 0.19–0.27 | 5.7–8.3 N | 2.9–4.2 N | 0.5–0.7 |
| dry | 0.29 (upper value) | 0.10–0.2 | 3–6 N | under 3 N | under 0.5 |
| oiled | 0.10–0.15 (assumed for lubricated plastic on steel; not measured here: the hold test checks the result) | 0.38–0.57 | 11.8–17.5 N | 5.9–8.8 N | 1.9–2.9 |

So dry rods do not meet the payload requirement even at full stall at the upper μ, and the carriage self-locks near
μ 0.37 (dry margin 1.3–1.5×): **lubricated rods are what make the gripper work**, not an extra. Oiled, it holds 150 g
at slip factor 2 with the servo squeezing at about half stall or a little more; the bench hold test (step 9) finds
that squeeze, and it is the payload requirement's proof. A longer carriage does not fix the dry case: 18 mm reaches
only about 0.33 D dry (half stall needs 0.40), and it would need the 150 mm rods (also stocked), so the 14 mm
carriage stays. All of this is printed in the generated ASSEMBLY.md (assembly notes on the jaws, the gripper and
the horn).
The ridged pad face does not raise μ on hard smooth objects, it
bites into soft ones (card, wood, foam); a separately printed TPU 95A pad (2–3.5 mm, μ ≈ 0.5 class) is the documented
upgrade for slippery objects (REFERENCES.md decision 7), not needed for the requirement.
Hold by position, not by stalling (every reference gripper limits force in software; a stalled MG996R draws ~2.5 A
and heats): command the jaws to the object's width minus a few mm (servo degrees past contact), so the servo's
proportional band squeezes with a fraction of stall; how far past contact is the bench-measured value of step 9.

**Opening.** Closed gap 2 mm (servo 0°), each jaw travels 15 × 100° × π/180 = 26.2 mm → open 2 + 52.4 = **54.4 mm**
at 100° of servo travel, inside the MG996R's standard 1000–2000 µs (~120°) range, so no extended pulses are needed.
Full open to closed takes about 0.28 s (0.17 s/60°).

**Teeth (Lewis, kerf `gear_bending`).** Worst case: one jaw blocked alone at stall, the whole torque on one mesh:
Ft = 922 / 15 = 61.5 N. Pinion (printed flat, in-plane): σ = Ft / (b m Y) = 61.5 / (12 × 1.5 × 0.322) = 10.6 MPa ≤
48 / 3 = 16 MPa. Rack teeth (the jaw prints on its side, so the teeth bend across layers): checked with the same
smaller pinion form factor (conservative) against 39 / 3 = 13 MPa: 10.6 MPa ✓.

**Arm torque budget** (projects/robot_arm/out/report.json): today the old gripper + finger + grip servo + horn weigh
94 g and the wrist sees 1.91 kg·cm with 150 g at the tool point; the shoulder uses 8.23 of its 10.5 kg·cm half-stall
limit (DS3225, 21 kg·cm), the elbow 4.47 of 9.5. The shoulder axis is 16.5 cm behind the wrist, the elbow 8.0 cm, at
full reach. A gripper of mass m (everything on the wrist) with wrist torque τ changes the shoulder torque by
(m − 94 g) × 16.5 cm + (τ − 1.91 kg·cm).
The first plan capped the items at 130 g (wrist torque ≤ 2.82). The parts as engineered (FEA-sized walls, 4 perimeters,
two steel rods) weigh more: items 163 g, wrist torque 2.29 kg·cm. The cap was a budget, not the requirement; the
requirement is "no arm servo past half stall". So both limits are re-derived together from it, the wrist-torque cap
tightened to what this gripper actually needs: items ≤ 166 g (+ 19.8 g rods + ~8 g screws/inserts = 194 g) and
τ ≤ 2.35 kg·cm (25 % of the wrist MG996R) give shoulder ≤ 8.23 + (194 − 94) × 0.165 / 10 + (2.35 − 1.91) =
**10.32 kg·cm = 49 % of stall** ✓; elbow ≤ 4.47 + 1.00 × 0.80 + 0.44 = 5.71 of 9.5 ✓; wrist ≤ 2.35 of 4.7 ✓.
As built (163 g, 2.29 kg·cm) the shoulder is at 10.21 kg·cm (48.6 %). The margin is thin: the arm should not take
anything heavier on its wrist. The arm's own `torque_*` checks are not re-run with the new gripper (separate project);
this hand check is the proof, the two limits make every build re-check it.
The tool point moves from 100.5 to ~101.5 mm ahead of the wrist axis (reach +1 mm). The arm's own mass cap
(robot_arm `arm_mass` ≤ 900 g, today 792 g) would see about 888 g with this gripper: inside, by 12 g.

## Part list
| Part | Job | Material | Print orientation | Approx. |
|---|---|---|---|---|
| gripper | wrist fork (2 × 7 mm plates), bulkhead holding the grip servo, wings + two end cheeks holding the guide rods | PETG | on its top face (print_rot [-90, 0, 0]: Y down); rod seats and tab pilots horizontal (teardrops) | 60 g |
| pinion | 20 T m1.5 pinion on the grip horn, 4 counterbored M3 | PETG 60 % infill, 4 walls | flat on its front (tooth-chamfered) face, registration rim up: print_rot [180, 0, 0] (teeth in the layer plane) | 9 g |
| jaw_r / jaw_l | carriage on the two rods + rack + finger with grip pad (one STL, printed twice) | PETG | on its rack side (rack teeth up, pad face vertical) | 17 g each |
| rod_keeper | covers both rod ends on the −Z cheek | PETG | flat | ~2 g |
| stand | bench stand = the forearm's wrist end on a clamp base | PETG | on its base | 44 g |

## Load → section
| Part | Loads in → out | Moment / torque along it (peak) | Section and why | How it changes |
|---|---|---|---|---|
| gripper fork plates | wrist horn (4 × M3) + pivot ← bulkhead | payload + gripper weight: 2 × (1.47 + 1.4) N at ~100 mm ≈ 0.6 N·m about Z at the wrist; jaw grip couples are internal | two 7 mm plates 21 mm apart (a fork: the arm's interface), deeper toward the bulkhead where the servo bay needs the height | Ø 34 disc at the wrist (arm interface) growing to the bulkhead height; pockets where FEA shows idle material |
| gripper bulkhead + wings | servo tabs (stall torque 922 N·mm about X) → wings → cheeks → rods → jaws → racks → pinion (closed internal loop) | 922 N·mm couple across the 49.5 × 10 tab pattern; wing bending from the rod reactions | 6 mm plate (tab pilots), ribbed / gusseted to the fork plates and to the cheeks | full height at the tabs, tapering wings to the cheeks |
| gripper cheeks | rod ends (jaw carriage couples) → wings | rod reactions at x_rod, ~30 mm ahead of the bulkhead | plates in their own plane (in-plane bending: strong), 8 mm thick for the rod seats | gussets back to the bulkhead |
| jaw finger | pad grip force (≤ 61.5 N, one jaw blocked at stall) → carriage | F × ~25 mm ≈ 1.5 N·m at the root | rectangular, deep in Y, thick in Z at the root | tapers toward the tip (moment falls to zero at the pad end); root fillet |
| jaw rack bar | rack tooth force (≤ 61.5 N along, 22 N separating) → carriage | separating force × up to 27 mm reach | deep backbone (8 mm behind the tooth roots) so the rack does not spring away from the pinion | constant (the mesh point moves along it) |
| jaw carriage | rods ← finger + rack moments | grip couple over the 14 mm bore length | solid block around two 3 mm bores | — |
| pinion | horn screws ↔ teeth | 922 N·mm | solid gear body, 12 mm face | — |
| stand | wrist servo tabs (stall 922 N·mm) + gripper/payload weight → base | ≤ 1 N·m at the upright root | two plates (forearm copy) on an upright, gussets to the base | deeper toward the base |

Style: radii 1.0 / 2.0 / 4.0 mm (inside load-path corners ≥ 1), 0.6 mm edge break on outside edges.

## Strength and detail (kerf check results)
| Check | Load case | Result | Limit |
|---|---|---|---|
| `gripper_stall_fea` | grip servo stalled, one jaw blocked: 922 N·mm on the tab screws, held at the four rod seats | 1.7 MPa (p99.9), 0.07 mm | 13 MPa (PETG across layers / SF 3), 0.3 mm |
| `gripper_wrist_fea` | crash: wrist servo stalled against the closed head, 922 N·mm through the horn screws | 3.9 MPa, 0.57 mm | 13 MPa, 1.0 mm |
| `jaw_fea` | one jaw blocked at stall: 61.5 N at the pad, held by the rack teeth (fully open) and both rod bores | 5.2 MPa, 0.47 mm | 24 MPa (in-plane / SF 2), 0.5 mm |
| `finger_root` | same, beam theory at the finger root | 3.1 MPa | 24 MPa |
| `pinion_fea` / `pinion_teeth` / `rack_teeth` | stall torque through the horn screws / Lewis, one mesh | 1.4 / 10.6 / 10.6 MPa | 16 / 16 / 13 MPa |
| `stand_fea` | wrist servo stalled + 2 × (gripper + payload) weight, base on the bench | 4.6 MPa, 0.66 mm | 13 MPa, 1.0 mm |
Stiffness, not strength, sets the gripper body and the jaws: the jaw's 0.47 mm (rack bar springing away from the
pinion under the separating force is what costs tooth contact) and the fork's 0.57 mm in the crash case are near their
limits, so neither is thinned further although the stresses are low. The pinion's body works at 7 % (the stress map
calls it overbuilt): its size is set by 20 teeth of module 1.5 (Lewis 66 % of allowable) and the horn's Ø14 bolt circle
inside the Ø26 root circle, so there is nothing to pocket between them.

Detail pass:
- Inside corners: the gripper body is ~20 unioned slabs; OCC's fillet operator crashes the process on it (segfault,
  not an exception), so its load-path junctions get R2 (else R1) fillets as boolean coves (kerf/coves.py). The earlier
  coves left a 0.02 mm sliver at each tangent point, which showed as a 217 MPa spike in `gripper_stall_fea`; with
  exact tangent points the same case reads 1.7 MPa. Rack tooth roots get the ISO 53 basic-rack root fillet 0.38 m.
- Corners left sharp on purpose (the `sharp inside corner` warning lists them): the rack bar's end under the bridge
  (jaw [-0.6, 16.8, z]): it is inside the 0.6 mm slot between the rack bar and the carriage that the pinion's front
  face runs past, too narrow for any fillet (0.3 mm does not fit); FEA puts the jaw's peak there at 7.5 MPa, 0.3 of the
  allowable; the step where each cheek's 4 mm frame arms meet its 9 mm rod bar ([72, ±, -28.7 / 63.7], [52, …, -24.7 /
  59.7]): the frame window runs right up to the bar, so a cove has no face to land on; the gripper's stall FEA reads
  1.7 MPa there; the 2 mm triangle ends where a cove
  runs out at an open edge (a fillet run-out, no load crosses it); the servo window's 1.1 mm relief into the fork plates
  (iface `servo_mount` top-through: the MG996R case is wider than the 21 mm gap with its clearance) and the tab-seat
  corners on the bulkhead's back face, where the servo tabs must sit flat; the apex lines of teardrop bores (rod seats
  and jaw rod bores, pivot hole, hex-key holes: they print round only with the apex); rack roots where the root land is
  shorter than the fillet (the rack's two ends).
- Grip pad: round-bottom grooves (r 0.5, 1.5 pitch) instead of V grooves: same texture, no crack-starting roots.
- Edge distance warnings (horn screws Ø14, servo tabs 49.5 × 10): the purchased parts' hole patterns fix them; the
  plates and bulkhead are as large around them as the wrist fork and the servo bay allow.

- Rod keeper: each rod is bottomed in the +Z cheek's blind seat and sits 0.86 mm inside the −Z cheek's outer face, so
  the 3 mm keeper is a lid that only stops a pressed rod backing out (axial load ≈ 0).

## Interfaces
| A | B | Call | Group | Hardware |
|---|---|---|---|---|
| wr_horn (stand / arm wrist) | gripper plate A | `horn_mount` | wr_horn | 4 × M3 |
| stand plate B (arm: forearm plate B) | gripper plate B | `pin_hole` free / heatset | wr_pivot | M3 pivot screw + insert |
| stand plate A (arm: forearm) | wrist MG996R | `servo_mount` top_through, tap | wr_servo | 4 × M3 |
| gripper bulkhead | grip MG996R | `servo_mount` top_through, tap | gr_servo | 4 × M3 |
| gr_horn | pinion | `horn_mount` (counterbored) | gr_horn | 4 × M3 |
| gripper cheeks | guide rods | `pin_hole` press (blind on +Z, through on −Z) | rod_top, rod_bot | 2 × Ø4 × 100 rod |
| jaw carriages | guide rods | `pin_hole` free (linear joint along the rod) | rod_top, rod_bot | — |
| gripper −Z cheek | rod_keeper | `bolt_pattern` heatset / clearance | keeper | M3 + insert |

## Joint tree
stand → wr_servo → **wrist** (−75…75°) → wr_horn → gripper → (gr_servo → **grip** (0…100°, home 0 = closed) → gr_horn →
pinion; jaw_r / jaw_l on linear slides along ±Z (0…26.18 mm) that follow grip × 0.2618 mm/deg; rod_keeper).

## Assembly order
0. First article: print the gripper body and ONE jaw (jaw_l is jaw_r printed a second time: one STL, the other turned
   180° about X at assembly) and test-fit: the grip servo in its bay and a rod in a cheek seat and a jaw bore (the
   rod's diameter tolerance is not published: `kerf calibrate --material PETG` and `kerf feedback`, then rebuild, if
   the seats are loose or the bores tight). Fit the pinion on the horn and slide the jaw on a rod with its rack in
   mesh: it must run with a little backlash (≈ 0.3 mm at the pad) and not touch the wing rail ends 0.5 mm away. The
   centre distance is set by two printed interfaces with no adjustment, so check this before printing the rest.
1. Heat-set inserts: the M3 pivot insert in plate B's boss and the two keeper inserts in the −Z cheek.
2. Grip servo: lower it into the bay from above (between the fork plates), slide it forward until its case top passes
   the bulkhead window, 4 × M3 thread-forming screws from behind through the tabs (the two by the cable boss need a
   ball-end key). Lead up out of the bay.
3. Power the servo and send the centre pulse (1500 µs = grip 50°, jaws half open); press the aluminium horn on the
   spline and fit its centre screw.
4. Pinion onto the horn (its rim centres it on the horn's disc), 4 × M3 counterbored screws.
5. Jaws: with the servo still at centre, slide both jaws in from the front, racks meshing (jaw_r's rack above the
   pinion, jaw_l's below), with the pads 28 mm apart (a 28 mm block between them sets it: 2 + 2 × 13.1 mm).
6. Rods: push each rod through the −Z cheek, through both carriages, into the +Z cheek's blind seat (a drop of light
   oil on the rod where the carriages run); then the rod keeper (2 × M3) over the rod ends. Lubricating the rods
   is NOT optional (dry PTFE spray or light machine oil where the carriages run, renewed when the jaws feel rough):
   the carriages cock on their 14 mm bores and dry friction costs two thirds of the pad force ('Grip force').
7. Mount on the wrist (the arm's forearm, or the bench stand): wrist servo at centre, horn on, the gripper's plate A
   onto the horn (4 × M3 from inside the fork, hex key through the access holes in plate B), M3 pivot screw through the
   forearm/stand plate B into the insert with washers to take up the side gap, then back it off 1/8 turn (a drop of
   medium threadlocker on the screw TIP only).
8. Lead: a 2.5 mm cable tie through the slot pair in plate A (x 9 / 15, 20 mm above the wrist axis) cinches the grip
   servo lead to the plate's inner face, so the wrist swing pulls on the tie, not on the servo's cable boss; then over
   the fork top and across the wrist outside plate A, and on along the arm's existing route (on the arm nothing is
   rewired: same channel, extension, fuse) or down the stand's leg through its slot pair.
9. Calibrate: find the pulse where the pads just touch (grip 0°) and where they reach full open (grip 100°). Set
   the touching pulse as the software floor: there is no mechanical stop at the closed end (past it the servo
   stalls against the pads). Hold test: grip a 25 mm block hanging 300 g (150 g × slip factor 2) and raise the
   command past contact one degree at a time until it holds without slipping; use that overdrive (never a stall)
   for every hold. If it slips even at full stall, re-lubricate the rods. Weigh the finished gripper (items +
   rods + screws) before it goes on the arm: ≤ 194 g ('Arm torque budget'), nothing else may go on the wrist.
   First article (step 0) adds the sliding check: the jaw must slide on an oiled rod while you press the pad.

## Risks / measure first
- MG996R stall torque and tab height are catalog figures (UNVERIFIED tab height, see the arm's DESIGN.md); print the
  gripper body first and test-fit the servo.
- Horn hub height varies 4.5–5.5 mm by vendor: it moves the pinion along the servo axis; the racks are as wide as the
  pinion, so up to 1 mm of shift only shortens the tooth contact.
