# Servo test rig — design record

## Brief
A bench rig: an MG996R servo on a printed bracket swings a 100 mm arm through ±90° under gravity, with a 50 g test
weight at the tip. Everything bolts together with M3 hardware. It is the seed project that exercises every Kerf
Forge mechanism (catalog-backed mounts on both sides, joint tree, sweep, fasteners, torque, FEA, exports).

## Requirements (numbers)
| Requirement | Value | Check |
|---|---|---|
| Arm swing | ±90° from vertical, collision-free | sweep `swing` |
| Holding torque | arm + 50 g at 100 mm, <= 50% of MG996R stall (9.4 kg·cm at 4.8 V) | `arm_torque` |
| Bracket strength | full stall-torque reaction at the four tab screws, SF 3 on layer-direction strength, deflection <= 0.3 mm; held only at its 4 foot screw heads (the foot may lift: conservative) | `bracket_fea` (0.64 of 13 MPa) |
| Stays put | screwed to the bench through the base's 4 counterbored M4 holes (stall reaction 0.92 N m vs 0.12 N m from its own weight); free-standing it must survive a 10 deg knock with the 50 g weight at either end of the swing | `stand` (37.1 deg), BOM: 4 x M4 wood screws |
| Arm strength | stall torque driving the arm into an obstacle (9.2 N at the tip), SF 2 in-plane, tip deflection <= 1 mm | `arm_fea` |
| Mass | <= 250 g assembled | `rig_mass` |
| Printability | every part fits the A2L, no supports needed | print checks |

## Architecture
Options: (a) servo upright, arm swinging horizontally — no gravity load, tests nothing; (b) servo on its side in an
upright wall, arm swinging in a vertical plane — real gravity torque, real bracket moment. **Picked (b).**

## Sizing
- Worst static torque at ±90°: 0.050 kg × 10.0 cm + arm 10.6 g × ~5 cm ≈ 0.55 kg·cm → 12% of the 4.7 kg·cm allowed.
- Servo tabs: thread-forming M3 screws into 2.60 mm pilot holes (the catalog's PETG size; 7.2 mm deep in the 8 mm wall). Heat-set inserts
  were rejected: their 4.0 mm holes would leave only 2.0 mm of wall to the servo window (rule: >= 2.4 mm) and melting
  them could bulge the wall into a window that has 0.3 mm clearance per side. Window corners get 1 mm dog-bone reliefs.
- Servo window: 45° lead-in chamfer on its entry face (the back face, which prints on the bed), so the case slides in
  square and elephant's foot on that face can't pinch it; the window itself keeps 0.3 mm clearance per side. Asked
  for 0.5 mm; `iface.servo_lead_in` limits it to 0.30 mm (window 41.48 x 20.56 for the 40.9 x 20 body) so the wall to the pilot holes stays 2.4 mm at that face.
- Test mass: a 50 g calibration weight or fishing sinker on a wire loop / S-hook through the 3.5 mm tip hole
  (a washer stack on an M3 screw is too long to reach 50 g).
- Servo mounting direction: the MG996R has a cable strain-relief boss low on its output-end face (catalog keep-out: 7.0 mm proud,
  2.5-10.5 mm above the case bottom, 8 mm wide), so it cannot be pushed through a tight window bottom-first. The servo
  goes in TOP-first from behind the wall: only the 10 mm case top passes the window, the tab tops bear on the back
  face, and the body + cable boss stay behind the wall.
- Thread-forming tab screws vs ENGINEERING §7 (inserts for parts assembled repeatedly): PETG pilot holes take
  roughly 5-10 re-insertions before the threads wear; a test rig's servo is rarely swapped, and inserts were ruled
  out by the wall-to-window distance above. If the threads wear, re-drill to a 4.0 mm insert after moving to a
  wider window margin.
- Arm width 18 mm: at 14 mm the stall-load tip deflection was 1.44 mm (FEA), over the 1 mm (1% of length) limit.
- Servo travel: the MG996R gives ~120° (±60°) at standard 1000-2000 µs pulses; the ±90° swing needs ~500-2500 µs
  pulses from the controller. The mechanics are cleared for the full ±90°.
- Single-sided support: the rule asks for a second pivot on links over ~60 mm or ~100 g. Here the arm + mass load the
  servo output with about 0.6 N radially at ~10 mm from the bearing, far inside what the MG996R's own two output
  bearings carry, so the extra pivot (and the friction it adds) is not worth it for a test rig.
- Stall reaction 9.4 kg·cm = 922 N·mm, carried as a ±18.6 N couple across the 49.5 mm tab-hole spacing.

## Mass budget (report.json)
| Item | g |
|---|---|
| base (2 perimeters, 30 % infill) | 60.3 |
| bracket (4 perimeters, strength-checked, 40 %) | 69.3 |
| arm (4 perimeters, 30 %) | 10.6 |
| MG996R servo | 55.0 |
| aluminium 25T horn | 3.0 |
| **rig total (`rig_mass`)** | **198.3** of 250 |
| beside it on the desk: adapter 310, Nano 7, jack (weight not published) | — |

## Edge distance
The four servo tab pilot holes sit 4.0 mm from the window edge, under ENGINEERING.md s7's 1.5 d = 4.5 mm (`kerf
check` warns). The MG996R's tab hole pattern fixes both the window and the holes, so it cannot move; the wall round
each pilot is still 2.4 mm at the lead-in (`iface.servo_lead_in`) and the bracket FEA (stall couple at those holes)
is at 0.64 of 13 MPa. The horn bolt circle on the arm is likewise set by the horn.

## Parts
| Part | Job | Material | Print orientation |
|---|---|---|---|
| base | bench plate, 4× M3 inserts for the bracket, 4× M4 counterbored bench holes | PETG | flat |
| bracket | upright wall; the servo mounts from behind (window + 4 M3 pilot holes from the back face), foot with teardrop screw holes, two gussets with 1.5 mm root fillets, 4 mm fillet at the wall/foot corner, cable-tie slots under the window | PETG | on its back face: the window needs no bridge; the foot's horizontal holes are teardrops |
| arm | flat link bolted to the aluminium 25T horn; access hole for the horn's centre screw; 3.5 mm hole at the tip for the test-mass hanger | PETG | flat |

## Interfaces
| A | B | Type | Group | Hardware |
|---|---|---|---|---|
| bracket foot | base | clearance → heat-set | base_bracket | 4× M3 (auto-sized 10 mm) + 4 inserts |
| servo tabs | bracket wall | clearance → pilot hole (thread-forming) | bracket_servo | 4× M3 × 8 + 4 washers |
| arm | horn | clearance → threaded horn | horn_arm | 4× M3 (8 mm) |
| horn | servo | 25T spline + centre screw | — | supplied with the horn |

Foot screws sit outside the servo tab span so a hex key reaches them from above with the arm at home.

## Joint tree
base → bracket (rigid) → servo (rigid, tabs on the wall face) → horn (`swing`, revolute ±90°) → arm (rigid).

## Electrics
- Power: MEAN WELL GST60A05 5 V 6 A desk adapter (catalog) -> SparkFun PRT-10288 barrel-jack screw-terminal adapter
  (10 A) -> 22 AWG red/black to the servo's red/brown pins. 5 V is inside the MG996R's 4.8-7.2 V; its 2.5 A stall
  (datasheet) is 42 % of the adapter's 6 A (`power` check, worst element). A USB port could not feed a stall.
- The servo's own female plug pushes onto a 3-pin 2.54 mm male header: jack + / - to its red / brown pins, Nano D9
  to orange. The adapter needs a separate IEC C13 mains cord; the Nano a USB Mini-B cable (both in the BOM).
- Voltage drop (`power` check): at the 2.5 A stall the servo input sags to 4.57 V, under the MG996R's 4.8 V minimum,
  for the moment it stalls; at the 0.9 A running current it stays above. Harmless here (the arm needs 12 % of stall
  torque).
- Signal: Arduino Nano on USB, D9 -> servo signal (orange), Nano GND -> jack minus (common ground). Sweep sketch with
  `servo.attach(9, 500, 2500)` so the pulse range reaches the full ±90° (a cheap servo tester stops at about ±60°).
- The adapter sits behind the rig, the jack and Nano beside it on the desk (base `desk_*` spots), plugs facing away:
  `plug_access` / `usb_access` prove 30 mm free in front of both. `kerf build` writes out/WIRING.md and wiring.svg.

## Assembly order
0. Screw the base to the bench through its 4 counterbored M4 holes (4 x M4 x 20 wood screws, or bolts through).
1. Melt the 4 M3 inserts into the base.
2. Screw the bracket foot to the base (4× M3 × 10).
3. Remove the servo's rubber grommets (the screws are sized for bare tabs; with grommets in, use M3 × 12).
   The tab holes are 4.5 mm keyhole slots open to the tab end, so the washers are required, not optional: without
   them a screw head bears on only ~0.5 mm each side of the slot. With the 0.5 mm washer each screw gets 5.0 mm of
   thread in the pilot hole (minimum 4.5). From BEHIND the wall, push the servo in
   top-first so its output pokes through the window and the tab tops sit flat on the back face; drive 4× M3 × 8 with
   washers from behind through the tabs into the pilot holes (they form their own threads; don't over-tighten).
   Use a 2.5 mm ball-end hex driver for the two screws next to the cable boss: a straight key grazes the boss.
4. The servo lead leaves the cable boss behind the wall: run it down and tie it through the two slots under the window.
5. Centre the servo electrically, press the horn on the spline pointing up, fit its centre screw.
6. Bolt the arm to the horn (4× M3 × 8). The horn disc is only 2 mm thick: snug them (about 0.5 N·m) with medium
   threadlocker rather than torquing them down.
7. Wire it (out/WIRING.md): solder the 3-pin header (red/black from the jack, orange from Nano D9), Nano GND into
   the jack's minus terminal; push the servo plug onto the header (brown to black); plug in the adapter (with its
   mains cord) and the Nano's USB cable.
8. Hang the 50 g test mass (calibration weight or sinker on a wire loop / S-hook) from the tip hole.

## Use
- Screw the base to the bench (4× M4 counterbored holes) or clamp it. Unclamped it only resists ~0.12 N·m of tipping
  against up to 0.92 N·m of servo stall torque, so fast moves would make it hop.
- The MG996R numbers are re-sourced from 2 TowerPro drawings, 7 independent CAD models and 4 published mounts
  (catalog `sources`): hole pattern 49.5 × 10 mm, 4.5 mm keyhole slots, tab 2.5 mm and shaft offset 10 mm are confirmed.
  The tab height above the case bottom is not (TowerPro 26.6-26.8, models 26.5-30.2); the review rebuilt the rig at
  26.5 and 30.2 and it still fits, sweeps and keeps key access. The cable boss is a keep-out envelope covering every
  source (7.0 proud, 2.5-10.5 up, 8 wide). Measure the tab height on a real servo before printing: at the 30.2 mm extreme the 20 mm horn disc sits 0.5 mm
  inside the 20.6 mm window with ~0.3 mm to its edges (still clear, small margin). If it differs, correct `catalog/hardware.json` with the
  measured value and a note, and rebuild — every dependent hole moves with it.
