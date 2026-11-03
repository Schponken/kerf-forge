# Portable folding bungee rail launcher — design

## What it is
A no-power launcher for hand-launch-sized fixed-wing drones (foam, 0.3-2.0 kg, pusher or tractor, high or low wing).
A 3 m aluminium V-slot rail in four 750 mm sections folds into one bundle; on the field it unfolds, stands on a
two-leg front bipod and a staked rear foot at ~11°, and throws the drone off its nose at a set, repeatable speed.

How it works, in order of use:
1. **Unfold**: each section joint has a quick-release (QR) pin on both sides. Pull one pin and the joint swings open
   on the other one, like a door hinge; to stand it up, swing it straight and push the pin back in. Which pin you
   pull decides the fold direction, so the four sections zig-zag into a flat stack.
2. **Stand**: push the two aluminium legs into the bipod mounts and clamp them; drive two tent stakes through the
   rear foot plate (the rail pivots on that plate, so leg length sets the rail angle, 8-14°).
3. **Set the power**: hook 1-4 latex strands (sled tow hooks → over the top of the rail → round the nose pulley →
   back under the rail → anchor hooks) and drop the anchor's QR pin into notch 1-10. The two numbers (strands ×
   notch) are printed on each drone's cradle: the same numbers give the same launch every time.
4. **Cock**: a line from the rear block runs round the steel pin at the sled's tail and back to your hand (2:1), so
   you pull half the strand force while walking the sled back until the trigger hook snaps over the pin. Fit the
   red-flag safety pin through the trigger.
5. **Load + arm**: clip the drone's cradle onto the sled (two pins + latch), put the drone in, arm it, step back to
   the foot pedal (on its lanyard, staked behind the rail), radio in both hands.
6. **Launch**: pull the red flag (safety pin out), throttle up, step on the pedal. The pedal line pulls the trigger
   hook off the sled pin; the strands throw the sled up the rail; at the nose the sled runs into a shock-cord brake,
   stops, and the drone flies on out of its open-front cradle.

## Use story → requirements
Who: Spencer and other hobby pilots. Where: outdoors, mown grass or a field, sun and wind, light rain; carried in a car
or on a backpack. How often: a few sessions a month, 5-20 launches each. What goes wrong:
- **Sun / hot car**: PETG HDT 70 °C (catalog) vs a 60 °C car-boot / sun-on-black-plastic case → `heat_limit`.
- **Dropped bundle / knocked over rail**: printed parts may crack; `survive: false` with the consequence (cheap
  printed parts reprinted from the field spares list) because the stress simulations are paused — no drop strength claim.
- **Cocked launcher / fingers**: a cocked rail stores up to ~190 J. Safety pin through the trigger until the pilot is
  behind the rail; the release is a foot pedal on a lanyard, so no hand is near the sled.
- **Gloves**: the QR pin rings and the trigger safety pin are pulled with a gloved finger (38 mm ring/opening).
- **Repeated hard stops**: the brake absorbs the sled's energy every launch → brake stop distance + peak force checked
  (`launch_top`), sled bumper and brake posts sized for the peak (`cantilever_stress`).

## Requirements
| Requirement | Number | Proven by |
|---|---|---|
| Launch Spencer's drone_foldable_wings (1590 g, stall 11.5 m/s) | >= 1.2 x stall = 13.8 m/s at its setting 5 strands x notch 5, <= 8 g | `launch_spencer` (commodity latex, the soft end) |
| Heaviest drone in the brief (2.0 kg foam, stall ~12 m/s) | >= 14.4 m/s at 6 x 10, <= 8 g | `launch_top` |
| Lightest drone in the brief (0.3 kg foam, stall ~6 m/s) | >= 1.15 x stall (Novakovic 2014) = 6.9 m/s at 1 x 1, <= 8 g | `launch_light` |
| Peak acceleration on the drone | <= 8 g (research: under 10 g for foam; BRIN LSU-02 7.6 g) | `max_g` in the three launch checks |
| Brake stops the sled + cradle | <= 300 mm into the brake (then the nose block) at the top setting, soft AND stiff latex | `launch_top`, `launch_peak` |
| Strength (worst force: stiff latex at 6 x 10) | trigger / anchor hold 474 N; nose pulley 948 N; sled bumper and brake posts the brake peak (~860 N) | `launch_peak` gives the loads; `cantilever_stress` per part (FEA paused) |
| Prop clears the strands and the nose | >= 10 mm from the tractor prop disc to the strands, sled, cradle; and to the nose block / pulley / brake posts as the drone flies off | `prop_clear` |
| Return strands run free | 9 mm channel under the rail from the pulley to the anchor, centre and outer strand | `strands_under_mid`, `strands_under_out` |
| Fold joints | fold to a flat zig-zag stack without collisions; cannot over-fold past straight | sweeps `fold_a/b/c`, pose `folded`, `fold_*_stop` |
| Stands | does not tip sideways before 20 deg with the drone loaded | `stands` |
| Carry | launcher <= 6 kg (no drone, stakes and pins outside the model) | `carry_mass` (advisory) |
| Heat | PETG HDT 70 C vs 60 C (car boot / sun) | `heat_limit` (use story) |

## Launch sizing (kerf/req_launch.py `bungee_launch`)
Latex: catalog `motion.latex_tubing` (3/16 in ID x 1/16 in wall surgical / hi-start tubing, 31.7 mm2). Per strand,
commodity curve 16.9 / 29.4 / 38.2 / 46.9 N at 100 / 200 / 300 / 400 % stretch; the premium (slingshot) curve is 2.1x
stiffer. **The setting table is sized on the commodity curve (the speed is then a lower bound) and every structural
load on the premium curve (the force is then an upper bound).** Efficiency 0.7 (Novakovic 2014, assumed).

Geometry (parts/layout.py): rail 4 x 750 mm, pulley pitch radius 48 mm at x = 3066, strands over the rail at
z = 68 and under it at z = -28. Tow hooks at x = 185 when cocked, 2685 when the sled meets the brake cord: a 2500 mm
power stroke. Anchor notch 1 at x = 1400 (nearest the nose), 55 mm pitch to notch 10 at x = 905. Strand centre-line
length at the end of the stroke 2198 (notch 1) .. 2693 mm (notch 10), +2500 cocked. Strand rest length 1299 mm (loop
to loop): stretch 69-108 % at the end of the stroke, 262-300 % cocked, so notch 10 sits at the 300 % long-life limit
and the strands never go slack (the sled always rests against the brake after a launch: decock = pull it back off the
brake by hand, or unhook the strands).

Speeds (m/s, commodity latex, 0.40 kg sled + wheels + cradle, 11 deg, rolling mu 0.05 assumed; notch 1 / 5 / 10):

| Drone | 1 strand | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 0.3 kg | 10.4/10.9/11.5 | 14.9/15.6/16.4 | | | | |
| 0.6 kg | 8.5/9.0/9.5 | 12.4/13.0/13.7 | 15.3/16.0/16.8 | | | |
| 1.0 kg | 7.0/7.4/7.8 | 10.4/10.9/11.5 | 12.9/13.5/14.2 | 14.9/15.6/16.4 | | |
| 1.6 kg | 5.6/5.9/6.3 | 8.5/9.0/9.5 | 10.7/11.2/11.8 | 12.4/13.0/13.7 | 13.9/14.6/15.3 | 15.3/16.0/16.8 |
| 2.0 kg | | 7.7/8.1/8.5 | 9.7/10.1/10.7 | 11.3/11.8/12.4 | 12.7/13.3/14.0 | 13.9/14.6/15.3 |

(The check's `table` in out/report.json repeats this for each launch case's payload with the real part masses.)
Notches move ~5 % of speed either way around notch 5; strands are the coarse step. A 0.3 kg foamie launches at
>= 10.4 m/s on one strand: fast but under 4 g; a gentler "light strand" (thinner tubing) is the remedy if a very
slow glider ever needs it (not in this build).
**Calibrate before printing the cradle cards**: hang one strand at 100 / 200 / 300 % on a luggage scale and replace
`force_curve` in the catalog with the measurement; `kerf build` recomputes every table. Latex pulls ~7 % less per
20 C colder (research) and loses force with age and UV: replace the set together.

Peak g (commodity): 5.0 g for Spencer's drone at 5 x 5, 6.4 g for 2 kg at 6 x 10. Stiff latex at 6 x 10 with 2 kg:
474 N pull, 22.4 m/s, 13.4 g: the misuse case the structure must survive, not a setting anyone should use.

**Brake.** The quote's shock cord has no published force-elongation data (research), so the brake uses the same
sourced latex: 6 cords, each 300 mm at rest, tied in at 600 mm (100 % pre-stretch) between an anchor 258 mm behind
the cord crossing on each brake post, round a post 42 mm either side of the rail, across the rail at z = 47. The sled's
bumper pushes the crossing forward into a V. Commodity, top setting: the 0.40 kg sled at 15.3 m/s stops in 272 mm,
peak 406 N; stiff latex misuse: 285 mm, peak 856 N. 300 mm are available before the nose block. The launch strands
keep pulling 107 N (commodity) / 249 N (stiff) at the end of the stroke; the brake holds the sled against that at rest.

**Ground reaction.** While the sled accelerates the rail is pulled back by the full strand tension (research): up to
229 N (commodity 6 x 10), 474 N stiff. One 9 in steel stake holds roughly 60-100 N (research, low confidence):
the rear foot takes **four stakes driven at ~45 deg leaning back**, plus a foot on the plate for the top settings.

## Architecture
See REFERENCES.md and the quote that Spencer picked (option 0, "Folding bungee rail launcher").
- (a) **Bungee rail launcher** (picked by Spencer): no battery, few moving parts, energy set by strand count and anchor
  position; proven at this size (BRIN LSU-02: 2.7 m rail, 15.2 m/s).
- (b) Electric winch rail: dial speed, but a LiPo, motor and controller to carry and charge.
- (c) Ground hi-start: cheapest, but needs 50+ m of field and gives no repeatable speed.

Joint design picked here: **two QR pins per fold joint, one on each side** (vertical axes, 26 mm out from the rail
centre). Either pin is the hinge for the other side's opening, so both joint blocks are the same two designs (a
"two-lug" and a "one-lug" block) at all three joints, and the zig-zag fold is chosen by which pin is pulled. The pins
sit 16 mm out from the rail faces so the sled's wheels clear the neighbouring section in the folded stack.
Rail standing 40 mm tall (strong axis vertical: the sag under the sled and drone is ~3x less than flat). The sled
rides on four Delrin V-wheels in the two upper side slots (vertical axles), the lower side slots and the bottom slot
carry the joint blocks, the bipod and the brake posts.

## Parts
| Part | Job | Material | Print | Load axis |
|---|---|---|---|---|
| rear_foot | staked ground plate, hinge for the rail angle | PETG | flat | x |
| rear_block | caps section 1's rear: foot hinge, trigger pivot, safety pin, cocking-line cleat, pedal-line guide | PETG | on its side | x |
| trigger | latch hook on the sled's tail pin; pedal line pulls it off | PETG | flat | x |
| anchor_rack | 10 numbered notch holes under section 1, butted against the rear block | PETG | flat | x |
| anchor | slides on the rack, carries the strands' rear ends, QR pin into a notch | PETG | flat | x |
| hinge_2 (x3) | two-lug fold block on the front end of sections 1-3 | PETG | flat (lugs horizontal) | x |
| hinge_1 (x3) | one-lug fold block on the rear end of sections 2-4 | PETG | flat | x |
| bipod_mount (x2) | leg socket clamped to section 3's lower side slot, M5 clamp screw | PETG | on its side | z |
| leg_foot (x2) | foot pad + short spike on each leg's lower end | PETG | upright | z |
| nose_block | caps section 4's front: pulley axle, strand guides | PETG | on its side | x |
| pulley | 4-groove strand pulley on two 608 bearings | PETG | flat | radial |
| brake_post (x2) | shock-cord posts beside section 4, 280 mm from the nose | PETG | on its side | x |
| sled | wheel carriage: 4 V-wheels, tow hooks, tail pin, bumper, cradle seat | PETG | upside down | x |
| cradle | per-drone seat from the template (example: drone_foldable_wings) | PETG | upright | x |
| pedal_base | staked base of the release pedal | PETG | flat | x |
| pedal | treadle on a pin, pulls the release line | PETG | flat | x |

## Load cases (worst = stiff latex at 6 x 10, `launch_peak`; FEA is paused, so `cantilever_stress` hand checks carry the proof)
| Load | Value | Where it goes |
|---|---|---|
| Strand pull, cocked | P = 474 N (6 x 79 N at 300 %; commodity 229 N) | sled tow hooks (79 N each) -> sled -> tail rollers -> trigger hook -> trigger pin -> rear block -> rail end face; anchor hooks -> anchor -> QR notch pin -> rack -> rack_a's front end butts hinge_aft_b (T-nut friction is the backup) |
| Nose pulley | 2P = 948 N rearward on the 8 mm axle | axle -> two axle cheeks in compression -> nose block cap -> rail end face |
| Brake peak on the sled | 860 N (commodity 406 N) | bumper face -> sled body; cradle pins carry the cradle's own inertia (~0.15 kg x 210 g = 310 N) |
| Brake cord on each post | 340 N resultant at rest (pre-stretch, stiff latex), 430 N along the rail on the rear anchor at the end of a stop | steel post (8 mm rod, both ends held) -> post block -> 3 T-nuts; rear cord anchor -> post block |
| Launch recoil on the ground | up to P along the rail, then the brake pushes it forward | rail -> rear block pivot (centre line, no bending) -> 5 mm pin -> rear foot -> 4 stakes |
| Fold joint bending | +-20 N m static (sled + drone over a joint, the 0.7 m nose overhang), x2 dynamic = 40 N m | butt of the rail ends on one face, 2 QR pins at the other (40 mm lever) -> 500 N per pin side through the lugs |
| Bipod | ~30 N per leg static, A-frame takes side loads axially | tube -> socket -> 2 T-nuts |

## Part contracts (frames and names from parts/layout.py; every value below is a layout or param name, not a copy)
Common: PETG, M5 tee-nut screws (catalog motion.tnut_m5_vslot) through **6 mm** of printed wall (TNUT_GRIP, counterbore deeper walls) so the
fastener check picks a 12 mm screw; T-nut screw rows on the lower side slots at z = 10 (|y| = 10 faces) and the bottom slot (y = 0, z = 0),
`iface.bolt_pattern(..., "clearance", 6)` with the same group as the section's sites (project.yaml `sec*` sites). Nothing printed may enter
the sled's swept envelope: |y| <= 36 for z >= 41 (plate, bumper, cradle), |y| <= 33 for 23.5 <= z <= 36.5 (wheels). Strands run over the
rail at z = Z_TOP (68) and under it at z = Z_BOT (-28) for |y| <= 31 (STRAND_Y +- 4.5): keep that clear from the pulley to the anchor.

- **rear_foot** (root, world: ground z = 0, X forward): plate >= 8 mm, ~170 x 130, flat boot pad; 4 stake holes dia 7 at 45 deg (heads
  leaning toward the nose so a backward pull drives them in); two knuckles either side of the rear block holding a rods.ss_rod_5 pin
  (press here, free in the rear block, pin group `rail_pivot`, span = a stocked length 50) on the axis (0, y, pivot_h) along Y; revolute
  `rail_pivot` Axis((0, 0, pivot_h), (0, -1, 0)) range (8, 14); rigid `pedal_spot` (-350, 160, 0). Clear the rear block over 8-14 deg.
- **rear_block** (rail frame, section 1 rear end face at x = 0): cap over the end face (x < 0), cheeks + bottom with group `s1_rear`
  (side screws x = 15, 45; bottom x = 30); knuckle on the pivot axis (pivot_x, 0, pivot_z) = the rail's centre line, rigid `pivot`
  Location((pivot_x, 0, pivot_z), (90, 0, -90)); rigid `section` (0, 0, 0); linear `sled_travel` Axis((X_S0, 0, H), (1, 0, 0)) range
  (0, TRAVEL_MAX). A tower behind/over the rail end (x <= 18, the cocked sled's rear is at x = 20) carries the trigger pivot: revolute
  `trigger` Axis((x_tr, 0, z_tr), (0, 1, 0)) range (-25, 0) with a rods.ss_rod_5 pivot pin (press in the tower, free in the trigger,
  group `trigger_pin`), z_tr 3-4 mm BELOW the strand pull line through the tail-roller centre (rail z 50) so the pull closes the hook;
  a hard stop for the latched angle; the safety pin: motion.qr_pin_6mm, fit "lock", group `safety`, through both tower cheeks and the
  trigger (grip 25 or 30), locking `trigger`; an eye for the cocking line on the tower top; a guide hole that turns the pedal line from
  the trigger's lower arm down to ground level. Load: P through the trigger pin; cocking line ~P/2.
- **trigger** (frame: pivot at origin, Y = pivot axis; rigid `pivot` Location((0, 0, 0), (-90, 0, -90))): hook 9 mm wide (fits
  between the sled's tail lugs) closing in front of the two tail rollers (rail centre (26, 50), OD 16) with 0.3 mm gap at home
  (`hook_seat`); release = rotate to -25 deg (hook front goes up, clears the rollers); lower arm with a line hole for the pedal line
  (~60 mm from the pivot); hole for the safety pin; P = 474 N on the hook; infill 100 %.
- **hinge_aft** (on a section's FRONT end, block frame body x < 0, items hinge_aft_a/b/c, params jt, sec) and **hinge_fwd** (on the next
  section's REAR end, body x > 0, items hinge_fwd_a/b/c): cheeks |y| 10-16 on the lower side faces z -9..20 and a bottom plate z -9..0,
  T-nut groups `s{sec}_front` (aft: x = -15, -45 sides, -30 bottom) / `s{sec}_rear` (fwd: 15, 45, 30); outboard webs at |y| >= 34 up to
  the top lugs; lugs r 8 round the pin axes (0, +-pin_off): hinge_aft at z LUGS_AFT, hinge_fwd at LUGS_FWD (stack -9..41 = the 50 mm QR
  grip); every lug `iface.pin_hole(ctx, "motion.qr_pin_6mm", Location((0, +-pin_off, z_top_of_lug)), f"fold{jt}_pos"/"_neg", LUG_T,
  fit="lock")`; 0.5 mm radial clearance round the other block's lugs through 180 deg of fold; end faces flush with the rail end (x = 0)
  so the joint cannot over-fold (`fold_*_stop`). hinge_aft: rigid `section` (0, 0, 0), revolutes `fold_neg` Axis((0, -pin_off, 0),
  (0, 0, 1)) range (-180, 0) and `fold_pos` Axis((0, pin_off, 0), (0, 0, 1)) range (0, 180). hinge_fwd: rigid `section` (0, 0, 0),
  `pin_neg` (0, -pin_off, 0), `pin_pos` (0, pin_off, 0). Folded, the sections stack 2 pin_off = 88 mm apart side by side.
- **anchor_rack** (x2, under section 2's bottom face, frame = its first notch on the rail bottom centre line, z = 0 = rail bottom;
  param first_notch 1 / 6): bar z -10..0, 5 vertical dia-6 QR holes (fit "lock") at x = 0, -notch_pitch, ... -4 notch_pitch, numbers
  embossed on both sides; T-nuts in the bottom slot, heads counterbored flush (the anchor slides under): rack_a x = -175, -25 group
  `s2_rack_a`, rack_b x = -200, -50 group `s2_rack_b`; rack_a's front end reaches rail x = 1440 (butts hinge_aft_b), rack_b butts
  rack_a. Only the rack holding `notch` registers its hole as group `anchor_notch` (lock). rack_a has linear `slide`
  Axis((0, 0, 0), (-1, 0, 0)) range (0, 9 notch_pitch); rigid `section` (0, 0, 0) on both.
- **anchor** (frame: on its QR pin axis at the rail bottom centre line; rigid `rack` (0, 0, 0)): slides along the rack, QR pin
  (lock, group `anchor_notch`) through it and the rack; 6 open hooks at x = +30, y = STRAND_Y, z = Z_BOT (strand loops drop on from
  above, pull +X, 79 N each); rigid `hook_mid` (30, STRAND_Y[3], Z_BOT), `hook_out` (30, STRAND_Y[5], Z_BOT); stays within the S2
  bottom between x 880 and 1440 over its travel.
- **bipod_mount** (bipod_l side +1, bipod_r side -1; frame: rail bottom centre at bipod_x on section 3): cheek on the lower side face,
  group `s3_bipod` at x = +-15; blind socket for the 20 mm tube (bore 20.4) whose closed end is the joint `leg`
  Location((0, side SOCK_Y, sock_z), (180 + side leg_splay, 0, 0)) and whose open end is 60 mm down the leg axis; split clamp with an M5
  screw + nut trap (the leg slides +-25 mm for levelling); rigid `section` (0, 0, 0). Keep |y| >= 31.5 below z = -20 (outer strand).
- **leg_foot** (foot_l side +1, foot_r side -1; frame: tube end centre, +Z along the leg toward the ground; rigid `leg` (0, 0, 0)):
  sleeve over the tube end (bore 20.4, 30 deep) and a pad whose ground face is level at home: plane through (0, 0, foot_t) with outward
  normal (-sin rail_deg, side cos rail_deg sin leg_splay, cos rail_deg cos leg_splay) (= world down in the foot frame); pad ~60 x 45,
  a 15 mm spike in the middle for grass.
- **nose_block** (block frame on section 4's FRONT end, body x < 0, pulley ahead): cheeks + bottom, group `s4_front` (x = -15, -45
  sides, -30 bottom); cap over the rail end face (x 0..8) taking 948 N in compression; two axle cheeks |y| 35.5-50 reaching forward to
  hold motion.rod_8mm_smooth (100 mm, press) on the axis (pulley_dx, y, Z_MID) along Y — the cheeks are struts in line with the 948 N;
  rigid `section` (0, 0, 0), `axle` and `pulley` Location((pulley_dx, 0, Z_MID), (-90, 0, 0)), `strand_exit`
  (pulley_dx - 35, STRAND_Y[3], Z_BOT), `strand_exit_out` (pulley_dx - 35, STRAND_Y[5], Z_BOT) in clear space; top <= z 80 so a
  tractor prop clears it.
- **pulley** (frame: centre, +Z = axle axis; rigid `hub` (0, 0, 0), `brg_1`, `brg_2` = the two 608 faces, each bearing 7 mm along +Z):
  width <= 69 (|z| <= 34.5), 6 grooves at z = STRAND_Y for the 7.94 mm tubing (strand centre at r = R_P = 48), flanges r <= 54; two 608
  seats (press) at both ends, a shoulder between; 948 N radial.
- **brake_post** (brake_l side +1, brake_r side -1; frame: rail bottom centre at brake_x on section 4): bar on the lower side face
  x -265..10, group `s4_brake` at x = -250, -125, -20 (6 mm grip); the post: rod post_l / post_r (motion.rod_8mm_smooth, 40 long,
  `post` rigid joint = its lower end, axis +Z) pressed into a lower boss and a top cap with the cord gap between at rail z 41-53 around
  z = 47, axis at (0, side brake_w); a cord anchor at x ~ -258 at z 47 (cleat or tie slot) for the 6 brake cords' tied ends; 430 N on
  the anchor along +X, 340 N on the post. Everything |y| >= 37 above z = 41.
- **sled** (frame: rail top centre line under the sled's middle, rail z = 40 -> sled z = 0): |x| <= SLED_HALF (85), plate z >= 2
  (spacer seats at z 1.115 over each wheel), wheels at (+-50, +-WHEEL_Y) wheel bottom face z = WHEEL_Z - WHEEL_W/2 - H (rigid
  `wheel_1` (50, 20), `wheel_2` (-50, 20), `wheel_3` (50, -20), `wheel_4` (-50, -20), identity), M5 axle holes from the top (wheels 3, 4:
  eccentric spacer seat dia 7.12); tow bar with 6 open hooks at x = TOW_DX, y = STRAND_Y, z = Z_TOP - H (79 N each), rigid `strands`
  (TOW_DX, 0, Z_TOP - H); bumper face at x = +85, |y| <= 36, z 2..16 (860 N; meets the brake cord at sled z 7); tail lugs at |y| >= 6
  holding rods.ss_rod_5 (50 long, press) at (-79, 0, 10): rigid `tail_pin` Location((-79, 0, 10), (-90, 0, 0)), `tail_roller_1`
  Location((-79, -5, 10), (-90, 0, 0)), `tail_roller_2` Location((-79, 0, 10), (-90, 0, 0)); cradle seat on the top (z = 12): rigid
  `cradle` (0, 0, 12), two rods.ss_rod_4 holes (free, group `cradle_pins`) at (+-60, 0) 10 deep, a 2 mm catch lip for the cradle's
  snap hook; rigid `carriage` (0, 0, 0). Mass <= 170 g (the launch speed depends on it).
- **cradle** (TEMPLATE, frame: sled top at the sled middle; rigid `base` (0, 0, 0)): base plate with the 2 rods.ss_rod_4 pins pressed
  (group `cradle_pins`, 25 mm pins: 15 here + 10 in the sled), a snap hook on the sled's lip (`flex_strain`), saddle pads for a
  cr_fuse_w x cr_fuse_h fuselage, rear push face (notch cr_boom_d for a tail boom), open front. Seat height from the template:
  tractor (cr_tractor = 1): prop axis (fuselage mid-height) >= Z_TOP + 4 + 10 + cr_prop_r (rail z); pusher: the prop disc behind the
  push face clears the sled, the rail and the strands by 10 mm. Linear `fly_off` Axis((x_d, 0, seat), (1, 0, 0)) range (0, 700), x_d
  so the drone box (frame = its bottom-face centre) touches the push face. Label "S{strands} N{notch}" + drone name embossed. Mass
  <= 150 g. Loads: drone 1.6 kg x 8 g = 125 N on the push face; its own inertia at the brake (310 N) into the pins.
- **pedal_base / pedal**: base staked (one dia-7 hole at 45 deg), hinge with a rods.ss_rod_4 pin (press base, free pedal, group
  `pedal_pin`), revolute `treadle` on the base about +Y range (0, 15); pedal rigid `pivot` Location((0, 0, 0), (-90, 0, -90)); a line
  guide low at the base front; stepping 15 deg pulls ~25 mm of line; the pedal bottoms on the base (someone standing on it).

## Joint tree
rear_foot -(rail_angle 8..14, home 11)- rear_block - sec1 - hinge_aft_a -(fold_a -180..0)- hinge_fwd_a - sec2 - hinge_aft_b
-(fold_b 0..180)- hinge_fwd_b - sec3 - hinge_aft_c -(fold_c -180..0)- hinge_fwd_c - sec4 - nose_block (axle, pulley + 2 x 608),
brake_l/r (+ posts). sec3 - bipod_l/r - leg_l/r - foot_l/r. sec2 - anchor_rack_a/b; rack_a -(notch_slide 0..495, home 220 = notch 5)-
anchor. rear_block -(trigger -25..0)- trigger; rear_block -(sled_travel 0..2800)- sled (4 wheels, tail pin + 2 rollers, strands_top)
- cradle -(fly_off 0..700)- drone (+ wing, prop keep-out). rear_foot - pedal_base -(pedal 0..15)- pedal.
Coupled poses: `folded` (fold_a -180, fold_b 180, fold_c -180 and halfway), `drone_leaves` (sled in the brake, drone 0..600 mm out).

## Interface table
| Part A | Part B | Interface | Group | Hardware |
|---|---|---|---|---|
| rear_block / hinge_aft_x / hinge_fwd_x / nose_block | rail sections | M5 tee-nut screws, 6 mm printed grip (12 mm screws) | s1_rear, s{n}_front, s{n}_rear, s4_front | 5 per block |
| hinge_aft_x | hinge_fwd_x | QR ball-lock pins, slip holes (`fit="lock"`), either one is the hinge | fold{j}_pos / fold{j}_neg | 2 x 6 mm QR, 50 mm grip, per joint |
| anchor_rack_a/b | section 2 | M5 tee-nut screws, heads flush underneath | s2_rack_a / s2_rack_b | 2 per rack |
| anchor | anchor_rack | QR pin in the set notch | anchor_notch | 1 x 6 mm QR |
| bipod_l/r | section 3 | M5 tee-nut screws | s3_bipod | 2 per side |
| brake_l/r | section 4 | M5 tee-nut screws | s4_brake | 3 per side |
| rear_foot | rear_block | 5 mm steel pin, press in the foot, free in the block | rail_pivot | rods.ss_rod_5 x 50 |
| rear_block | trigger | 5 mm steel pivot pin + QR safety pin | trigger_pin, safety | rods.ss_rod_5, 6 mm QR |
| sled | wheels | M5 x 25 axle from the top, 6 mm spacer (eccentric on wheels 3, 4), nyloc under the wheel | held_by | 4 kits |
| sled | tail pin + rollers | 5 mm pin pressed in the tail lugs, 2 x 625 on it | held_by | rods.ss_rod_5 x 50, 2 x 625 |
| sled | cradle | 2 x 4 mm pins (press in the cradle) + snap hook on the sled's lip | cradle_pins | rods.ss_rod_4 x 25 |
| nose_block | pulley | 8 mm axle pressed through both cheeks, 2 x 608 in the pulley | held_by | motion.rod_8mm_smooth x 100 |
| brake_l/r | posts | 8 mm steel post pressed top and bottom | held_by | motion.rod_8mm_smooth x 40 |
| pedal_base | pedal | 4 mm pin | pedal_pin | rods.ss_rod_4 |

## Risks and numbers to measure on the real hardware first
- **Latex force** (dominant): the sourced curves differ 2.1x. Measure one strand at 100 / 200 / 300 % before cutting the
  set; put the numbers in the catalog `force_curve` and rebuild: the setting table and every cradle card follow.
- **Stakes**: no steel-stake pull-out test exists (research); 4 stakes at 45 deg + a boot on the plate for settings
  above 4 strands.
- **QR pins**: industrial 6 mm ball-lock pins cost ~$35 each (Kipp); hobby pins are $3-6 with unverified balls. Six fold
  pins + safety + notch = 8 pins. Check the balls hold the pin under a firm pull before trusting a hobby set.
- **Joint play**: a 0.35 mm slip on a 6 mm pin over the 40 mm lever is ~0.5 deg of kink when a joint's bending reverses;
  the sled's Delrin wheels ride over it, but measure the step at each joint (< 0.3 mm) after assembly.
- **Tee nuts, V-slot slot geometry, wheel centre-to-face (10.0 mm)**: from bd_warehouse / a forum quote, UNVERIFIED;
  check one wheel on the rail before printing the sled (the eccentric spacers give +-0.75 mm).
- **Dry fire** (no drone on the sled; commodity latex, 0.40 kg sled): 1 strand stops in 187-212 mm, 2 strands notch 1 in
  299 mm (the limit), 2 x 10 in 342 mm and 3 strands in 390-450 mm: the sled then hits the nose block. Test-fire empty
  on ONE strand only (ASSEMBLY.md, use story).
- **Brake cords wear** (latex, UV): replace with the launch strands.
