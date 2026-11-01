# Robotic gripper claw (for the desk robot arm) — design

## What it is
A symmetric two-finger claw that replaces the desk robot arm's gripper (projects/robot_arm `gripper` + `finger`:
one finger swinging against a fixed jaw) on the arm's wrist. Both fingers move: each is one printed piece with its own
spur gear, the two gears mesh 1:1, so the grip servo drives one finger directly and the other through the gears.
The object is squeezed from both sides toward the claw's centre line instead of being pushed against a fixed jaw.

Nothing new to buy for the arm: it bolts onto the arm's wrist exactly where the old gripper did and uses the arm's
own grip servo (MG996R), its horn, wiring and driver channel. New hardware: two steel dowels, M3 screws/inserts and
two printed TPU pads.

## Requirements
| Requirement | Number | Where it is proven |
|---|---|---|
| Fits the arm's wrist | same interface as the old gripper: 25T aluminium horn (4 × M3 on a 14 mm circle) on plate A, M3 pivot screw into a heat-set insert in plate B, 35 mm across the fork (horn face to pivot face), clear of the forearm over the full wrist range ±75° | `wrist_stand` replicates the forearm's wrist end (layout `fa_*`, tests/test_claw_fits_arm.py); fastener + pin checks; wrist motion sweep |
| Opening | ≥ 60 mm between the pads (cups, cans); closes to ~1 mm (pens, wire) | `grip_open` at grip 40°, `grip_closed` at 0° |
| Hold | the arm's 150 g payload with friction safety factor ≥ 2, servo at ≤ 50 % of stall | hand calc below (grip force) |
| Wrist torque | wrist servo (MG996R) ≤ 50 % of stall with the claw + 150 g held level | `torque_wrist` |
| Arm budget | the rest of the arm stays inside its own limits (shoulder ≤ 50 % of stall, reach 230–300 mm) | hand calc below from the arm's report |
| Strength | FEA on every structural part at grip-servo stall (the worst case: the servo can always be commanded into a hard object) | `*_fea` |
| Gears | printed teeth survive the full stall torque through the mesh | `gear_bending` |
| Mass | claw on the arm (printed + grip servo + horn) ≤ 130 g (old gripper + finger + servo + horn ≈ 98 g) | `claw_mass` |

## Architecture
Options (references in REFERENCES.md):
- (a) the arm's current single finger against a fixed jaw: off-centre grip, the object is pushed sideways first.
- (b) **two fingers geared 1:1 on one servo** (MeArm / EEZYbotARM claw pattern): centred grip, twice the jaw travel per
  degree, one extra pivot. Fingers swing in arcs, so the pads tilt as they open.
- (c) geared parallelogram (aluminium MG996R claw kits): pads stay parallel, but 4 more links and pivots (play at
  every printed pivot) and a closed kinematic loop the engine cannot prove over the motion (every item has one parent;
  pin alignment is checked at home only) — a pass would not be evidence.
- (d) rack and pinion parallel jaws: parallel, but printed slides bind when the grip force acts 50 mm in front of the
  guide (jamming when guide length < 2 μ × offset ≈ 40 mm) and the palm gets ~90 mm wide.

**Picked (b)**, with two things that recover most of what (c) offers: the pad faces are angled so they are parallel
at a mid-size grip (`pad_par` = 21°, 35 mm objects), and the pads are TPU 95A, whose friction holds a tilted contact
(an object is squeezed out of a V only when tan(half-angle) > μ). Both fingers' pivots are supported on both sides
(ENGINEERING.md §8): the drive finger on the servo horn below and a dowel in the cover above, the idler finger on a
dowel pressed into the palm and running in the cover.

## Purchased parts and sizing
| Item | Catalog | Why |
|---|---|---|
| grip servo | servos.MG996R (9.4 kg·cm = 922 N·mm stall @ 4.8 V, 55 g) | the arm's own grip servo (`gr_servo`, PCA9685 ch 4); fits the same palm mount |
| grip horn | servo_horns.aluminum_25T | the arm's own; the drive finger bolts to it |
| wrist servo + horn (stand only) | servos.MG996R + servo_horns.aluminum_25T | on the arm these are the forearm's; on the bench stand they hold the claw exactly as the arm does |
| idler dowel | motion.pin_3mm, 3 × 25 | pressed into the palm's pedestal, the idler finger turns on it, top end runs in the cover |
| drive top dowel | motion.pin_3mm, 3 × 10 | pressed into the cover, runs in a blind bore in the drive finger's hub: the second support of the drive axis |

**Gears** (`kerf.drives.spur_pair`): module 1.5, 16 : 16 teeth (pitch Ø 24, tip Ø 27, centre distance 24 mm), 12 mm
wide, 0.3 mm backlash. Axes at z = 5.5 (drive) and 29.5 (idler), symmetric about the fork mid-plane z = 17.5.
Lewis check at the WORST case — the whole stall torque going through the mesh (an object touching only the idler
finger): Wt = 922 / 12 = 76.8 N, Y(16) = 0.296, σ = Wt / (b m Y) = 76.8 / (12 × 1.5 × 0.296) = 14.4 MPa < 48 / 3 = 16 MPa
(teeth printed flat, stress along the layers, SF 3) → `gear_bending`.

**Grip force.** The pad's contact point sits `finger_len` = 45 mm in front of its gear axis; the pad's normal force
acts at that lever. Both fingers squeeze, so at servo torque T each pad pushes F = T / (2 × 45 mm):
at stall F = 922 / 90 = 10.2 N per pad; at half of stall 5.1 N (the old fixed-jaw gripper gave 18.4 N at stall from one
finger: two moving fingers halve it).
Friction (REFERENCES.md P1-P4): measured against steel, printed PETG 0.24-0.29 (Stoimenov 2024), TPU 30D 0.46-0.61
smooth / 0.69-0.79 knurled, TPE 88A 0.25-0.51 (Suder 2021); harder polyurethane grips less (Gallagher), and no figure
for TPU 95A is published, so **μ = 0.30 is assumed for the ribbed TPU 95A pads** (the open risk below).
Hold the 150 g payload (1.47 N) with friction SF 2 (ENGINEERING.md has no friction factor; SF 2 = its static-load row):
2 μ F ≥ 2 × 1.47 N → F ≥ 4.9 N → T = 2 × 4.9 × 45 = 441 N·mm = **48 % of stall** ✓ (≤ 50 %); at exactly half stall
the friction SF is 2.09. This is why the contact sits at 45 mm (at 50 mm it would need 53 %) and why the pads are TPU:
bare PETG (μ 0.24) at half stall gives SF 1.67 only. With μ 0.46+ (softer TPU, measured smooth 30D) the servo needs
under a third of stall.
Command the servo just past contact: holding far past it holds the MG996R at stall (≈ 2.5 A; a gripper servo held at
stall gets "very hot in 2 or 3 minutes", REFERENCES.md P10).

**Opening.** Each pad's contact point is L = √(45² + 11.5²) = 46.4 mm from its axis at α = 14.3° inward (closed gap
`pad_gap` = 1 mm at the centre line). Opening at finger angle θ: gap = 35 − 2 × 5.5 − 2 L sin(α − θ):
θ = 10° → 17 mm, 21° → 35 mm, 30° → 49 mm, 37° → 60 mm, **40° → 64 mm** (`grip_open` ≥ 60). Joint range grip 0…40°:
inside the MG996R's ±60° at 1000–2000 µs. The commercial aluminium MG996R claw opens 50 mm (P11).

**Jaw angle.** An object is squeezed out of a V when each face leans more than the friction angle tan⁻¹ μ = 16.7°
(μ 0.30, Modern Robotics §12.2.1, P5). The pad faces are made parallel at θ = `pad_par` = 21° (a 35 mm object): from
10 mm (θ 6.5°, faces 14.5° the safe way: the V opens toward the palm and pulls the object in) to 60 mm (θ 37°, 16° open
toward the tips) every object is held inside the friction cone. Above 60 mm only the hooked tips hold it.

**Wrist (MG996R, 922 N·mm stall).** `torque_wrist` computes it from the assembled masses (claw ~124 g at its CG ≈ 50 mm
from the wrist axis, payload at the tcp 83 mm out): `torque_wrist` reports the value (≈ 1.8 kg·cm ≈ 20 % of stall).

**Effect on the rest of the arm** (from projects/robot_arm/DESIGN.md: shoulder needs 8.21 kg·cm of 21.0, elbow 4.46 of
19.0, reach 266 mm with the old tcp 100 mm past the wrist axis):
- the tcp moves 17 mm closer to the wrist (x_tcp 83 vs 100): reach 266 − 17 = 249 mm (spec 230–300 ✓); the 150 g
  payload's lever on the shoulder drops by 1.7 cm: −0.26 kg·cm;
- the claw is ~26 g heavier than gripper + finger + servo + horn (~124 vs ~98 g), at ≈ L1 + L2 + 5 cm ≈ 21.5 cm from the
  shoulder: +0.56 kg·cm. Shoulder 8.21 − 0.26 + 0.56 = 8.5 kg·cm = 40 % of stall ✓; elbow 4.46 − 0.26 + 0.026 × 13 =
  4.5 kg·cm = 24 % ✓. (Re-run robot_arm's torque checks with the claw if it is ever made the arm's default gripper.)
- The tcp now sits on the fork mid-plane (z = 17.5 in the old gripper frame, the old tcp was ~23): 5.5 mm less side
  offset in the arm's inverse kinematics.

**Electrics.** Unchanged from the arm (robot_arm DESIGN.md 'Electrics'): the same MG996R on its `pwr_gr` / `sig_gr` runs
(5 A fuse, its 300 mm lead + the 600 mm extension, PCA9685 channel 4). The claw adds no load and no wire; it keeps the
old gripper's two lead tie points (`lead_1`, `lead_2`) so the arm's route is unchanged. This project declares no
`electrical:` section because the power tree, ratings and run lengths live in robot_arm and do not change. Bench test
on the stand: plug both servos into the arm's driver (wrist into channel 3, grip into channel 4) with the arm's supply.

## Part list
| Part | Job | Material | Print orientation | Approx. |
|---|---|---|---|---|
| palm | wrist fork (horn plate A + pivot plate B, as the old gripper), palm plate the grip servo hangs under, idler pedestal, two posts the cover screws to, lead tie points | PETG 40 % | on plate A's outer face (z = 0 on the bed: horn holes vertical, the palm plate and posts stand up, `print_rot` [0, 0, 0] in the claw frame turned so z is up) | 30 g |
| cover | plate over the two gears: top support of both gear axes (drive dowel pressed in, idler dowel running in it), 2 screws into the palm posts | PETG 50 % | flat, top face down | 8 g |
| finger_l | drive finger: gear + hub bolted to the grip horn + tapered finger + jaw with the pad slot | PETG 50 % | flat on its gear face (layers in the grip plane: the finger bends along the layers) | 11 g |
| finger_r | idler finger: mirror of finger_l, turns on the idler dowel | PETG 50 % | flat | 11 g |
| pad_l / pad_r | TPU 95A grip pads, slid into a dovetail in each jaw | TPU 95A 100 % | flat on the back | 2 g each |
| wrist_stand | bench stand that replicates the forearm's wrist end (plate A with the wrist servo, plate B with the pivot hole, the rear web) on a foot | PETG 30 % | on its back | 60 g |

## Load → section
Loads at grip-servo stall (the servo can always be driven into a hard object), per pad F = 10.2 N toward the claw's
outside; the idler's torque F × 45 = 461 N·mm comes through the mesh: tangential Wt = 461 / 12 = 38.4 N along X at the
pitch point, separating Wr = Wt tan 20° = 14.0 N along Z; each gear axis carries 38.4 N along X and 24.2 N across.

| Part | Loads in → out | Moment / torque, where it peaks | Section chosen, and how it changes |
|---|---|---|---|
| finger_l / finger_r | pad force 10.2 N at 45 mm → hub (finger_l: 4 horn screws + top dowel; finger_r: dowel) | bending in the grip plane, 0 at the pad → 461 N·mm at the hub | solid rectangular beam deep in the bending direction (z) and tall (y) for the pad: ~9 (z) × 12 (y) at the root tapering to ~6 at the jaw; layers in the grip plane so bending runs along them; r ≥ 2 root fillet into the hub; the jaw is a T at the tip carrying the pad's dovetail |
| palm | servo stall 922 N·mm (couple on 4 tab pilots) + the drive axis side load (≈ 45 N: 38.4 along X, 24.2 across) shared by the horn/servo case and the top dowel; idler dowel ≈ 45 N shared pedestal / cover; all of it back to the wrist horn screws and pivot | torque about the drive axis in the palm plate; bending of the palm plate between the servo tabs and the wrist fork; the pedestal root (≈ 22 N at ~8 mm: 180 N·mm) | 7 mm palm plate (servo pilots need 7 mm) with the window; wrist discs as the old gripper (7 mm, r = 17) blending into the palm along a 45° rise; pedestal Ø 12 boss with a 2 mm root fillet; two 7 × 7 posts with r ≥ 1.5 root fillets; material out of the palm plate where the stress map says it idles |
| cover | the two dowel tops (≈ 22 N each at stall) → the 2 post screws | cantilever from the posts, ≈ 900 N·mm at the posts | 4 mm plate with a rib along X between the dowel bosses and the post bosses (T section), tapering toward the front |
| wrist_stand | wrist-servo stall 922 N·mm on plate A's tab pilots + the claw's weight (≈ 1.2 N) | in-plane torque on plate A, carried by the web and back column to the foot | plates and web exactly the forearm's (they ARE the fit gauge); column + foot sized by FEA; this part is a fixture, keep it light |

## Interfaces
| A | B | Call | Group | Hardware |
|---|---|---|---|---|
| wrist horn | palm plate A | `horn_mount` (clearance, holes vertical in print) — the old gripper's call | wr_horn | 4 × M3 (length from the check) |
| wrist_stand plate B | palm plate B | `pin_hole` M3 free (stand) / heatset (palm boss, t + 3 deep) — the arm's wrist pivot | wr_pivot | M3 × 14 screw + washers for the 1.5 mm side gap |
| wrist_stand plate A | wrist servo | `servo_mount` top_through, tap (the forearm's) | wr_servo | 4 × M3 × 8 thread-forming |
| palm (underside) | grip servo | `servo_mount` top_through from below, tap (the old gripper's) | gr_servo | 4 × M3 × 8 thread-forming, from below |
| grip horn | finger_l hub | `horn_mount` counterbore (heads below the cover) | gr_horn | 4 × M3 |
| palm pedestal / finger_r / cover | idler dowel | `pin_hole` press (pedestal, 8 deep) / free (finger_r, cover) | gr_idler | 3 × 25 dowel |
| cover / finger_l | drive top dowel | `pin_hole` press (cover) / free (finger_l blind bore ≥ 5.5) | gr_top | 3 × 10 dowel |
| palm posts | cover | `bolt_pattern` heatset (palm) / clearance (cover) | cover | 2 × M3 + inserts |
| finger jaw | pad | dovetail slot open at the top, stop at the bottom (no fastener; `insert:` path checked) | — | — |

## Joint tree
wrist_stand (root) → wr_servo (tabs on the stand's servo seat) → **wrist** (±75°, the arm's range) → wr_horn → palm
→ gr_servo (tabs) → **grip** (0…40°, 0 = closed) → gr_horn → finger_l → pad_l;
palm → **grip_r** (idler, −40…0°, follows grip × −1) → finger_r → pad_r; palm → cover.
Coupled: `grip_r` follows `grip` with ratio −1 (`spur_pair` ratio_signed). Requirement poses list both joints.
tcp = rigid joint on the palm between the pads (x 83, y 19.9, z 17.5).

## Assembly order
1. Heat-set inserts: palm wrist-pivot boss (inside plate B), two cover posts.
2. Press the 3 × 25 idler dowel into the palm pedestal from above until it bottoms (the Ø 2 hole below it lets you
   push it out later). Press the 3 × 10 drive dowel into the cover from its top face until flush.
3. Grip servo into the palm from below, case top first through the window, tab tops against the palm underside;
   4 × M3 × 8 thread-forming from below. Its lead leaves at the rear (output end), toward the wrist.
4. Centre the servo (1500 µs), press the grip horn on the spline, fit the horn's centre screw.
5. Close the servo to its "closed" end (decide its pulse in the bring-up; the claw is assembled closed): drive finger
   onto the horn pointing along the claw, 4 × M3 through the counterbored hub into the horn.
6. Idler finger onto its dowel, meshing so the two pads meet at the centre line.
7. Cover on: its dowel into the drive finger's top bore, the idler dowel's top into the cover; 2 × M3 into the posts.
8. Pads: slide each TPU pad down into its jaw's dovetail until it sits on the stop.
9. On the arm: take off the old gripper (4 horn screws, pivot screw), fit the claw: 4 × M3 through plate A into the
   wrist horn (hex key through the access holes in the claw's plate B and the forearm's plate B), then the M3 × 14 pivot
   through the forearm's plate B into the claw's insert with washers for the 1.5 mm side gap (threadlocker on the tip
   only, back off 1/8 turn). Tie the grip lead at `lead_1` / `lead_2` as before. On the bench stand: the same steps
   with the stand in place of the forearm.

## Risks / measure first
- MG996R tab height and hub depth vary by vendor (robot_arm DESIGN.md): print the palm first and test-fit the servo.
- Gear centre distance depends on where the servo's output really is relative to its tab holes (catalog
  shaft_offset, keyhole slots ±0.5 mm): check the mesh turns freely by hand before fitting the cover; shim nothing,
  the 0.3 mm backlash takes ±0.4 mm of centre-distance error.
- **TPU 95A friction is assumed (μ 0.30), not measured.** Before trusting a 150 g lift, tilt-test a printed pad against
  the real objects (raise a board with the object on a pad until it slides: μ = tan of that angle). If μ < 0.30, print
  the pads in a softer TPU (85A-90A) or lower the payload.
- TPU pad fit: print one pad first; a pad that slides out too easily gets a drop of CA glue in the slot.
