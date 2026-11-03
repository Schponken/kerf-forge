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
