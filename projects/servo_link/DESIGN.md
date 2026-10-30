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
| Bracket strength | full stall-torque reaction at the four tab screws, SF 3 on layer-direction strength, deflection <= 0.3 mm | `bracket_fea` |
| Arm strength | stall torque driving the arm into an obstacle (9.2 N at the tip), SF 2 in-plane, tip deflection <= 1 mm | `arm_fea` |
| Mass | <= 250 g assembled | `rig_mass` |
| Printability | every part fits the A2L, no supports needed | print checks |

## Architecture
Options: (a) servo upright, arm swinging horizontally — no gravity load, tests nothing; (b) servo on its side in an
upright wall, arm swinging in a vertical plane — real gravity torque, real bracket moment. **Picked (b).**

## Sizing
- Worst static torque at ±90°: 0.050 kg × 10.0 cm + arm 7.7 g × ~5 cm ≈ 0.54 kg·cm → 11% of the 4.7 kg·cm allowed.
- Servo tabs: thread-forming M3 screws into 2.72 mm pilot holes (7.2 mm deep in the 8 mm wall). Heat-set inserts
  were rejected: their 4.0 mm holes would leave only 2.1 mm of wall to the servo window (rule: >= 2.4 mm) and melting
  them could bulge the wall into a window that has 0.3 mm clearance per side. Window corners get 1 mm dog-bone reliefs.
- Test mass: a 50 g calibration weight or fishing sinker on a wire loop / S-hook through the 3.5 mm tip hole
  (a washer stack on an M3 screw is too long to reach 50 g).
- Servo mounting direction: the MG996R has a cable strain-relief boss low on its output-end face (~6.6 mm proud,
  3-7 mm above the case bottom; catalog note), so it cannot be pushed through a tight window bottom-first. The servo
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

## Parts
| Part | Job | Material | Print orientation |
|---|---|---|---|
| base | bench plate, 4× M3 inserts for the bracket, 4× M4 counterbored bench holes | PETG | flat |
| bracket | upright wall; the servo mounts from behind (window + 4 M3 pilot holes from the back face), foot with teardrop screw holes, two gussets with 1.5 mm root fillets, 4 mm fillet at the wall/foot corner, cable-tie slots under the window | PETG | on its back face: the window needs no bridge; the foot's horizontal holes are teardrops |
| arm | flat link bolted to the aluminium 25T horn; access hole for the horn's centre screw; M3 hole at the tip for the test mass | PETG | flat |

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

## Assembly order
1. Melt the 4 M3 inserts into the base.
2. Screw the bracket foot to the base (4× M3 × 10).
3. Remove the servo's rubber grommets (the screws are sized for bare tabs). From BEHIND the wall, push the servo in
   top-first so its output pokes through the window and the tab tops sit flat on the back face; drive 4× M3 × 8 with
   washers from behind through the tabs into the pilot holes (they form their own threads; don't over-tighten).
   Use a 2.5 mm ball-end hex driver for the two screws next to the cable boss: a straight key grazes the boss.
4. The servo lead leaves the cable boss behind the wall: run it down and tie it through the two slots under the window.
5. Centre the servo electrically, press the horn on the spline pointing up, fit its centre screw.
6. Bolt the arm to the horn (4× M3 × 8). The horn disc is only 2 mm thick: snug them (about 0.5 N·m) with medium
   threadlocker rather than torquing them down.
7. Hang the 50 g test mass (calibration weight or sinker on a wire loop / S-hook) from the tip hole.

## Use
- Screw the base to the bench (4× M4 counterbored holes) or clamp it. Unclamped it only resists ~0.12 N·m of tipping
  against up to 0.92 N·m of servo stall torque, so fast moves would make it hop.
- Before printing the final bracket, check the MG996R with calipers: the tab-hole pattern (catalog: 49.5 × 10 mm,
  4.2 mm holes) and the cable boss (catalog: ~6.6 mm proud, 4 mm tall, 3-7 mm above the case bottom) are partly
  unverified for this exact servo. If it differs, correct `catalog/hardware.json` with the
  measured value and a note, and rebuild — every dependent hole moves with it.
