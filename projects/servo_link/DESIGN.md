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
| Bracket strength | full stall-torque reaction, SF 2 on layer-direction strength, deflection <= 0.3 mm | `bracket_fea` |
| Mass | <= 250 g assembled | `rig_mass` |
| Printability | every part fits the A2L, no supports needed | print checks |

## Architecture
Options: (a) servo upright, arm swinging horizontally — no gravity load, tests nothing; (b) servo on its side in an
upright wall, arm swinging in a vertical plane — real gravity torque, real bracket moment. **Picked (b).**

## Sizing
- Worst static torque at ±90°: 0.050 kg × 10.0 cm + arm 7.7 g × ~5 cm ≈ 0.54 kg·cm → 11% of the 4.7 kg·cm allowed.
- Wall: 8 mm PETG holds M3 heat-set inserts (6.7 mm deep holes + 0.8 mm floor; CNC Kitchen M3 × 5.7).
- Stall reaction 9.4 kg·cm = 922 N·mm, carried as a ±18.6 N couple across the 49.5 mm tab-hole spacing.

## Parts
| Part | Job | Material | Print orientation |
|---|---|---|---|
| base | bench plate, 4× M3 inserts for the bracket, 4× M4 counterbored bench holes | PETG | flat |
| bracket | upright wall with servo window + 4 M3 inserts, foot, two gussets, 4 mm fillet at the wall/foot corner | PETG | on its back face: the window needs no bridge, inserts face up for installation |
| arm | flat link bolted to the aluminium 25T horn; access hole for the horn's centre screw | PETG | flat |

## Interfaces
| A | B | Type | Group | Hardware |
|---|---|---|---|---|
| bracket foot | base | clearance → heat-set | base_bracket | 4× M3 (auto-sized 10 mm) + 4 inserts |
| servo tabs | bracket wall | clearance → heat-set | bracket_servo | 4× M3 (8 mm) + 4 inserts |
| arm | horn | clearance → threaded horn | horn_arm | 4× M3 (8 mm) |
| horn | servo | 25T spline + centre screw | — | supplied with the horn |

Foot screws sit outside the servo tab span so a hex key reaches them from above with the arm at home.

## Joint tree
base → bracket (rigid) → servo (rigid, tabs on the wall face) → horn (`swing`, revolute ±90°) → arm (rigid).

## Assembly order
1. Melt 4 inserts into the base and 4 into the bracket wall (print orientation leaves them facing up).
2. Screw the bracket foot to the base (4× M3×10).
3. Drop the servo body through the window from the front, tabs on the wall; 4× M3×8 into the inserts.
4. Centre the servo electrically, press the horn on the spline pointing up, fit its centre screw.
5. Bolt the arm to the horn through the access hole layout (4× M3×8).
