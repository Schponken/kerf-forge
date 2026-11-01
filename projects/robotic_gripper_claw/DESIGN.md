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
| idler dowel | motion.pin_3mm, 3 × 30 | pressed 8 mm into the palm's pedestal, the idler finger turns on it, top end runs in 9 mm of cover (span 8 + 0.5 + 12 + 0.5 + 9 = 30) |
| drive top dowel | motion.pin_3mm, 3 × 16 | pressed through the cover's 9 mm (plate + boss), runs in a 7 mm blind bore in the drive finger's hub: the second support of the drive axis (span 9 + 0.5 + 7 = 16.5) |

**Gears** (`kerf.drives.spur_pair`): module 1.5, 16 : 16 teeth (pitch Ø 24, tip Ø 27, centre distance 24 mm), 12 mm
wide, 0.3 mm backlash. Axes at z = 5.5 (drive) and 29.5 (idler), symmetric about the fork mid-plane z = 17.5.
Lewis check at the WORST case — the whole stall torque going through the mesh (an object touching only the idler
finger): Wt = 922 / 12 = 76.8 N, Y(16) = 0.296, σ = Wt / (b m Y) = 76.8 / (12 × 1.5 × 0.296) = 14.4 MPa < 48 / 3 = 16 MPa
(teeth printed flat, stress along the layers, SF 3) → `gear_bending`.
Each finger keeps teeth only on the arc that ever meshes (the 0…40° of travel plus ~1.5 teeth each side, edges in tooth
gaps); the rest of the hub is a smooth r 11.5 disc (the other gear's tips only reach r 10.5 at the mesh line). That keeps
the claw narrow and gives the arm a smooth root to leave from.
**Horn screws on the gear face, not counterbored.** The drive finger bolts to the 25T horn with 4 × M3 on a 14 mm circle.
A counterbore for an M3 socket head (Ø 5.5 + 0.6) at r 7 reaches r 10.05, and the 16 T tooth roots are at r 10.125: it
would leave 0.08 mm of plastic under the teeth. So the heads stand on the gear's top face, the four holes sit centred
under teeth (the horn's `hole_start_deg` 0 matches the gear phase: finger.py derives it from the gear), and the cover is
raised to 0.5 mm over the heads (layout `y_c0`), with bosses reaching down to 0.5 mm over each gear so the dowels stay
short-levered.

**Grip force.** The pad's tip end sits `finger_len` = 45 mm in front of its gear axis (see 'Jaw angle': the 20 mm pad runs
back from there toward the palm, so an object touches it 26.6–46.4 mm from the axis; the tip end is the worst case for
holding, the root end for the force on the jaw). The pad's normal force acts at that lever. Both fingers squeeze, so at servo torque T each pad pushes F = T / (2 × 45 mm):
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

**Opening.** Each pad's tip end is L = √(45² + 11.5²) = 46.4 mm from its axis at α = 14.3° inward (closed gap
`pad_gap` = 1 mm at the centre line). Opening at finger angle θ: gap = 35 − 2 × 5.5 − 2 L sin(α − θ):
θ = 10° → 17 mm, 21° → 35 mm, 30° → 49 mm, 37° → 60 mm, **40° → 64 mm** (`grip_open` ≥ 60). Joint range grip 0…40°:
inside the MG996R's ±60° at 1000–2000 µs. The commercial aluminium MG996R claw opens 50 mm (P11).

**Jaw angle.** An object is squeezed out of a V when each face leans more than the friction angle tan⁻¹ μ = 16.7°
(μ 0.30, Modern Robotics §12.2.1, P5). The pad faces are made parallel at θ = `pad_par` = 21° (a 35 mm object): from
10 mm (θ 6.5°, faces 14.5° the safe way: the V opens toward the palm and pulls the object in) to 60 mm (θ 37°, 16° open
toward the tips) every object is held inside the friction cone. Above 60 mm the faces lean more than the friction
angle: 60 mm is the rated opening (64 mm is the travel). How it is built: each pad face passes through its tip-end point
and is turned `pad_par` inward toward the tip, so the pad ENDS at that point (closed, the two tip ends are 1 mm apart and
the faces open toward the palm) and runs 20 mm back; no hook can sit past it without the two fingers colliding closed.
The pad stands on the gear's bed face (20 mm tall, gear 12): pad centre 10 mm over the horn face, tcp y = 23.9.

**Wrist (MG996R, 922 N·mm stall).** `torque_wrist` computes it from the assembled masses (claw ~124 g at its CG ≈ 50 mm
from the wrist axis, payload at the tcp 83 mm out): `torque_wrist` reports the value (≈ 1.8 kg·cm ≈ 20 % of stall).

**Effect on the rest of the arm** (from projects/robot_arm/DESIGN.md: shoulder needs 8.21 kg·cm of 21.0, elbow 4.46 of
19.0, reach 266 mm with the old tcp 100 mm past the wrist axis):
- the tcp moves 17 mm closer to the wrist (x_tcp 83 vs 100): reach 266 − 17 = 249 mm (spec 230–300 ✓); the 150 g
  payload's lever on the shoulder drops by 1.7 cm: −0.26 kg·cm;
- the claw is ~29 g heavier than gripper + finger + servo + horn (~127 vs ~98 g, `claw_mass`), at ≈ L1 + L2 + 5 cm ≈
  21.5 cm from the shoulder: +0.62 kg·cm. Shoulder 8.21 − 0.26 + 0.62 = 8.6 kg·cm = 41 % of stall ✓; elbow 4.46 − 0.26 +
  0.029 × 13 = 4.6 kg·cm = 24 % ✓. (Re-run robot_arm's torque checks with the claw if it is ever made the arm's default gripper.)
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
| cover | triangulated frame over the two gears: top support of both gear axes (drive dowel pressed in, idler dowel running in it), 2 screws into the palm posts | PETG 50 % | flat, top face down (print_rot [-90, 0, 0]): bosses and deep members grow up from it | 6 g |
| finger_l | drive finger: gear + hub bolted to the grip horn + tapered finger + jaw with the pad slot | PETG 50 % | flat on its gear face (layers in the grip plane: the finger bends along the layers) | 11 g |
| finger_r | idler finger: mirror of finger_l, turns on the idler dowel | PETG 50 % | flat | 11 g |
| pad_l / pad_r | TPU 95A grip pads, slid into a dovetail in each jaw | TPU 95A 100 % | standing on its top end (print_rot [180, 0, 0]): the dovetail is in the layers and the tongue grows from the bed | 2 g each |
| wrist_stand | bench stand that replicates the forearm's wrist end (plate A with the wrist servo, plate B with the pivot hole, the rear web) on a foot | PETG 30 % | on its back | 60 g |

## Load → section
Loads at grip-servo stall (the servo can always be driven into a hard object), per pad F = 10.2 N toward the claw's
outside; the idler's torque F × 45 = 461 N·mm comes through the mesh: tangential Wt = 461 / 12 = 38.4 N along X at the
pitch point, separating Wr = Wt tan 20° = 14.0 N along Z; each gear axis carries 38.4 N along X and 24.2 N across.

| Part | Loads in → out | Moment / torque, where it peaks | Section chosen, and how it changes |
|---|---|---|---|
| finger_l / finger_r | half the stall torque, 461 N·mm, reaches each pad: along the pad's normal at the pad centre (lever 36.2 mm) 12.7 N (17.3 N at the root end, 10.2 N at the tip end) → jaw → arm → hub (finger_l: 4 horn screws + top dowel; finger_r: dowel + teeth) | bending in the grip plane, 0 at the pad → 461 N·mm at the hub (the same for any contact point) | arm 6 mm deep (in the bending plane) × 12 mm tall, layers in the grip plane so bending runs along them (8 mm ran at 15 % of allowable: overbuilt); r 2 root fillets into the hub; the jaw is a 6.5 mm plate behind the pad (dovetail groove 3.9 deep + 2.6 wall), 20 mm tall, its top ramping up from the arm; r 3 round nose; toothed sector only where it meshes |
| palm | servo stall 922 N·mm (couple on 4 tab pilots) + the drive axis side load (≈ 45 N: 38.4 along X, 24.2 across) on the servo tabs; the idler dowel's 45 N on the pedestal plus its single-shear moment (engine: 749 N·mm); all of it back to the wrist horn screws and pivot | in-plane torque in the palm plate; out-of-plane bending and twist of the whole palm about the root between the wrist fork and the gear axes (that is where the first FEA showed the compliance: everything forward of x ≈ 30 rotated rigidly) | a channel: 7 mm palm plate (servo pilots need 7 mm) with the servo window; plate B runs on as a 7 mm keel below and rises as a wall to 0.5 mm under the idler gear (30 mm deep web carrying the pedestal); a 3 mm far web from x 25.5 (forearm plate A reaches only 24.1 mm from the wrist axis) also rising to 0.5 mm under the drive finger; a root beam across the claw on top of the palm plate from the posts' rear faces to 1.5 mm before the servo window (x 14.7–26.25, y 7–13.4) tying both cheeks, both posts and the keel wall; a pedestal wall from the beam to the pedestal's front (keel wall thickened inboard to z 24) where the idler moment enters; wrist discs as the old gripper (7 mm, r 17); pedestal Ø 10 boss; r 1 on the inside corners. Tried and dropped (FEA): a 6 mm far web (no gain), an end wall closing the channel (−0.05 mm for 2.6 g, over the mass budget), a 4 mm keel (+0.08 mm) |
| cover | each dowel's full side load (45 N, in the cover's plane) plus its single-shear moment out of the plane (engine: drive 295, idler 715 N·mm) → the two post screws and the post tops they clamp | in-plane: the two separating forces are equal and opposite (the front member between the dowels is a tie holding the centre distance); out of plane: the idler node turns about the posts | triangulated frame: members post–post, post–idler, post–idler diagonal (passes 14.5 mm from the drive axis), post–drive, drive–idler, two triangular windows; 6 mm plate (cover_t) on the bed; the idler-side members run 9 mm deep down to 0.5 mm over the gears, the drive side stays plate-deep (the horn-screw heads turn under it); dowel bosses down to 0.5 mm over each finger |
| wrist_stand | wrist-servo stall 922 N·mm on plate A's tab pilots + the claw's weight (≈ 1.2 N) | in-plane torque on plate A, carried by the web and back column to the foot | plates and web exactly the forearm's (they ARE the fit gauge); column + foot sized by FEA; this part is a fixture, keep it light |

## Interfaces
| A | B | Call | Group | Hardware |
|---|---|---|---|---|
| wrist horn | palm plate A | `horn_mount` (clearance, holes vertical in print) — the old gripper's call | wr_horn | 4 × M3 (length from the check) |
| wrist_stand plate B | palm plate B | `pin_hole` M3 free (stand) / heatset (palm boss, t + 3 deep) — the arm's wrist pivot | wr_pivot | M3 × 14 screw + washers for the 1.5 mm side gap |
| wrist_stand plate A | wrist servo | `servo_mount` top_through, tap (the forearm's) | wr_servo | 4 × M3 × 8 thread-forming |
| palm (underside) | grip servo | `servo_mount` top_through from below, tap (the old gripper's) | gr_servo | 4 × M3 × 8 thread-forming, from below |
| grip horn | finger_l hub | `horn_mount` clearance, heads on the gear's top face (a counterbore would undercut the tooth roots), holes under teeth (`hole_start_deg` 0) | gr_horn | 4 × M3 |
| palm pedestal / finger_r / cover | idler dowel | `pin_hole` press (pedestal, 8 deep) / free (finger_r, cover 9) | gr_idler | 3 × 30 dowel |
| cover / finger_l | drive top dowel | `pin_hole` press (cover, 9) / free (finger_l blind bore 7) | gr_top | 3 × 16 dowel |
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
2. Press the 3 × 30 idler dowel into the palm pedestal from above until it bottoms (8 mm; the Ø 2 hole below it lets
   you push it out later). Press the 3 × 16 drive dowel into the cover's drive boss from its top face until flush
   (7 mm stands out below the boss).
3. Grip servo into the palm from below, case top first through the window, tab tops against the palm underside;
   4 × M3 × 8 thread-forming from below. Its lead leaves at the rear (output end), toward the wrist.
4. Centre the servo (1500 µs), press the grip horn on the spline, fit the horn's centre screw.
5. Close the servo to its "closed" end (decide its pulse in the bring-up; the claw is assembled closed): drive finger
   onto the horn pointing along the claw, 4 × M3 through the hub into the horn (heads on the gear's top face).
6. Idler finger onto its dowel, meshing so the two pads meet at the centre line.
7. Cover on: its dowel into the drive finger's top bore, the idler dowel's top into the cover; 2 × M3 into the posts.
8. Pads: slide each TPU pad down into its jaw's dovetail (from the top, lead-in end first) until it sits on the floor.
9. On the arm: take off the old gripper (4 horn screws, pivot screw), fit the claw: 4 × M3 through plate A into the
   wrist horn (hex key through the access holes in the claw's plate B and the forearm's plate B), then the M3 × 14 pivot
   through the forearm's plate B into the claw's insert with washers for the 1.5 mm side gap (threadlocker on the tip
   only, back off 1/8 turn). Tie the grip lead at `lead_1` / `lead_2` as before. On the bench stand: the same steps
   with the stand in place of the forearm.

## Checks and margins (kerf build, full check with motion sweeps)
| Check | Result | Limit | Margin |
|---|---|---|---|
| grip_open (tip ends at 40°) | 64.2 mm | ≥ 60 | rated 60 (friction cone, 'Jaw angle') |
| grip_closed | 1.0 mm | ≤ 2 | — |
| torque_wrist (claw + 150 g, worst pose) | 1.76 kg·cm | ≤ 4.7 (50 % of stall) | 19 % of stall |
| gears (Lewis, whole stall torque through the mesh) | 14.42 MPa | 16.0 (48 / SF 3) | SF 3.3 |
| claw_mass | ~127 g | 130 | ~3 g |
| finger_l_fea / finger_r_fea (12.7 N on the pad normal) | 5.0 / 4.5 MPa | 24 (SF 2, along layers), 1 mm | SF ~10 on stress; sized by printability (6 mm arm, 2.6 mm behind the groove) and the jaw's pad, not by stress |
| palm_fea (stall, conservative single-shear idler) | 5.7 MPa, 0.20 mm | 16 (SF 3), 0.3 mm | stiffness governs: 33 % on deflection |
| cover_fea (both axes' full loads + lever moments; held at the screws and the post tops they clamp) | 7.9 MPa, ~0.14 mm | 24, 0.2 mm | ~30 % on deflection |
| stand_fea | 3.2 MPa | 16 | fixture |
| sweeps | wrist ±75° and grip 0…40° (idler following −1) collision-free | | the far web from x 25.5 clears the forearm copy |

## Warnings kept, and why
- **Edge distance** of the wr_horn / gr_horn holes (25T horn's 14 mm circle) and the wr_servo / gr_servo tab pilots
  (MG996R tab pattern): the purchased parts' hole patterns force them (ENGINEERING.md s7 allows it); the walls are the old
  gripper's and the arm forearm's, which are proven on the arm.
- **Sharp inside corners kept, and why:** the pad's tongue-to-plate corner (the jaw floor's edge sits in it; TPU, no
  crack risk); the apex of the teardrop roof of the palm's wrist-pivot insert hole (an interface print feature; the
  engine exempts screw features, not pin features); two short corners where the palm's root beam top meets cover post A
  (measured in palm_fea: 0.5 and 0.65 MPa within 2.5 mm, 3-4 % of allowable); one 10 mm corner where the cover's
  diagonal member runs into the idler boss beside a window's round end (4.6 MPa locally, 19 % of allowable). Two short
  cover corners at the members' lower ends take r 0.5 only. The engine's "highly stressed zone" tag is per 16 mm cell;
  the local values above are from the FEA field at the corner itself.
- **How corners are rounded:** OCC fillets after the interface cuts (kerf's own corner detector picks them,
  parts/detail.py). Near the servo window and the idler pedestal, and along the cover's post B - idler member, a fillet
  either fails or leaves surfaces the FEA mesher cannot close; there the r 1 radii are built in as quarter-round strips
  (the same geometry a fillet gives). The palm's root beam stops 1.5 mm before the servo window to leave room for its
  radius, and the cover's deep members stop 1.2 mm short of the palm posts so their root radii clear the posts' edges.
- **palm needs support (~9 %):** the palm plate's underside inside the servo bay (between the keel and the far web).
  Printed with claw +Y up (plates and webs vertical, posts, walls and pedestal growing up) every other face is
  self-supporting; any other orientation puts the wrist discs, posts or pedestal on overhangs. Use tree supports from
  the bed only (Bambu Studio "support on build plate only"); the servo window and tab pilots are vertical and stay clean.
- **wrist_stand** (overbuilt, ~5 % support, fixed box not at a fastener): its plates and web are the arm forearm's wrist
  end verbatim (they ARE the fit gauge, tests/test_claw_fits_arm.py); it rests on the bench, so the bench face is its
  support in stand_fea.
- **Ball-end key** for the servo tab screws (driven from below; the servo body blocks a straight key) and the M3 screw
  pivot note: as on the arm.
- **No electrical section**: see 'Electrics' (the arm's power tree, unchanged).

## Known limits
- The pads' tip ends are 4.5 mm ahead of the palm's front edge (the grip servo sits under the fingers, as on the arm's
  old gripper). Objects are taken from the side or from above; something lying flat on the desk (< ~8 mm tall) is picked
  with the claw pointing down, by the pad tips.
- 60 mm is the largest object held inside the friction cone; 60-64 mm objects are held by squeeze only.

## Risks / measure first
- MG996R tab height and hub depth vary by vendor (robot_arm DESIGN.md): print the palm first and test-fit the servo.
- Gear centre distance depends on where the servo's output really is relative to its tab holes (catalog
  shaft_offset, keyhole slots ±0.5 mm): check the mesh turns freely by hand before fitting the cover; shim nothing,
  the 0.3 mm backlash takes ±0.4 mm of centre-distance error.
- **TPU 95A friction is assumed (μ 0.30), not measured.** Before trusting a 150 g lift, tilt-test a printed pad against
  the real objects (raise a board with the object on a pad until it slides: μ = tan of that angle). If μ < 0.30, print
  the pads in a softer TPU (85A-90A) or lower the payload.
- TPU pad fit: print one pad first; a pad that slides out too easily gets a drop of CA glue in the slot.
