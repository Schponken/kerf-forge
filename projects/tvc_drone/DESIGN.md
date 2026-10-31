# tvc_drone — design

A rocket-style thrust-vectoring drone after fd.iwth and Mistral (REFERENCES.md): a tall, light carbon mast with the
battery at the top, a counter-rotating motor pair at the bottom on a two-axis servo gimbal that steers the thrust,
three splayed legs. Numbers below are from `kerf build tvc_drone` (out/report.json) unless marked as a hand estimate.

## Requirements (numbers)
| What | Target | Result |
|---|---|---|
| Thrust / weight (`twr`) | >= 1.8 | 4.1 (2629 g / 641 g) |
| CG on thrust axis (`cg_axis`) | <= 3 mm lateral, above pivot | 0.45 mm worst over gimbal corners; 136 mm above the pivot |
| Stand on its own (`stand`) | >= 15 deg tip-over | 20.9 deg |
| Gimbal travel | +/-15 deg each axis + 4 corners, collision-free | clear (sweeps + `gimbal_corners`) |
| Prop clearance (`props`) | >= 3 mm to anything, >= 20 mm between discs | 5.3 mm (bottom prop to the roll ring at pitch 15 deg) |
| Gimbal hub strength (`gimbal_fea`) | 2 x max thrust = 66.1 N, SF 2 | 3.5 MPa vs 24 MPa allowable, 0.17 mm |
| Roll ring / yoke / leg FEA | SF 2 | 3.2 / 3.5 (Z-strength) / 2.7 MPa vs 24 / 19.5 / 24 |
| Mass | <= 750 g | 641 g |

## Architecture
Options: (a) coax pair on a 2-axis gimbal (fd.iwth, Mistral — flown); (b) single rotor + 4 vanes (Goose, Starkit) —
needs +/-15 deg vanes and more servos; (c) quad with tilt — not a TVC rocket. Picked (a): it is what the brief asks for
and has flown. Differences from fd.iwth, and why:
- **Direct-drive servos** (servo horn bolted to the ring/hub) instead of 3:1 / 4:1 printed gears: fewer parts and no
  gear backlash tuning. Cost: less angular resolution (1 deg servo step = 1 deg thrust step) and the servo's own gear
  backlash goes straight into the thrust direction. Mitigation: metal-gear MG90S, steel dowel pin on the opposite
  side of each axis carries the side load so the spline only carries torque. Flight software should clamp at
  ~+/-8.5 deg (fd.iwth 0.149 rad, Mistral 0.15 rad); the geometry is proven clear to +/-15 deg.
- **Props in the gimbal plane**: the motors sit back-to-back inside the roll ring; both props are outside the ring's
  height band and inside its radius (65.9 mm props, ring inner radius 72), so neither ring nor hub arms cross a prop
  disc at any angle. The pitch axis runs along the hub arms (Y) and the roll axis along X, both through the thrust
  line, so thrust makes no static moment on either servo.
- **Battery high, motors low** (fd.iwth): slows tip-over dynamics; CG trimmed onto the axis by sliding the battery
  (`batt_dx` -14, `batt_dy` -4.2 mm) to cancel the two servos on +X / +Y.

## Purchased parts and sizing
| Item | Catalog | Why / math |
|---|---|---|
| 2 x iFlight XING2 2207 1855 KV | drone.motors.2207_1855kv_6s | 1685 g max each with 51466 props at 24 V; coax factor 0.78 (MDPI Aerospace 3(4):32) -> 2 x 1685 x 0.78 = 2629 g |
| 2 x 5.1" props | drone.props.5_1in (keep-outs) | 131.8 mm discs, planes 65 mm apart (> 0.25 D = 33 mm, no extra coax loss) |
| 2 x MG90S | servos.MG90S | gravity torque on each axis <= 0.1 kg cm (`roll_torque`, `pitch_torque`) vs 1.8 stall; real load is aerodynamic + inertial — the reason for metal gears |
| 2 x micro 21T disc horn | servo_horns.aluminum_micro_21T | UNVERIFIED geometry (estimate) — measure before printing |
| 3 x 5 x 3 mm carbon tube, 228 mm | rods.cf_tube_5x3 | Starkit: 3 mm rods flex at 0.5 m; 5 mm tubes in 5.5 mm bores + radial M3 lock |
| 6S 1100 mAh | drone.batteries.6S_1100 | motors are 6S-rated; 197.5 g on top |
| SpeedyBee F405 mini 20 x 20 stack | drone.stacks.fc_20 | FC + 35 A 4-in-1 ESC (2 channels used), drives the servos |
| 2 x 3 x 16 mm steel dowel | motion.pin_3mm | pivots opposite each servo (press in one side, free in the other) |

Electronics beyond these (receiver, BEC, XT60, strap, wiring, power budget, flight time) are part of the open PLAN
item "Complete electronics + wiring"; this project gets them when that engine feature lands.

## Parts (all PETG)
| Part | Job | print_rot | load_axis |
|---|---|---|---|
| ring_low | root: mast base, 3 tube bosses, 3 leg lugs, +X yoke with roll servo window, -X yoke with roll dowel, top webs | [180,0,0] upside down | z (FEA in Z strength) |
| gimbal_outer | roll ring: roll horn lug (+X), roll dowel pad (-X), pitch servo pad (+Y), pitch dowel pad (-Y) | flat | x, y |
| motor_hub | pitch frame: top motor (counterbored M3 x 6), +Y fork to the pitch horn, -Y arm to the dowel, 3 M3 inserts | flat | y |
| motor_plate | bottom motor (M3 x 6, counterbored), bolts under the hub | flat | — |
| ring_mid | tubes through, radial locks, flight stack on 4 thread-formed M2 | flat | — |
| ring_top | tube caps, battery tray with strap slots | upside down | — |
| leg_1..3 | splayed legs to r = 150 mm, ground 85 mm under the pivot | on its side | x, z |

## Interfaces
| A | B | How | Group |
|---|---|---|---|
| ring_low | servo_roll | `servo_mount` (tap M2) on the +X yoke plate | yoke_servo |
| horn_roll | gimbal_outer | `horn_mount`, 4 x M2 from inside the ring | roll_horn |
| ring_low | gimbal_outer | `pin_hole` press / free, 3 mm dowel on the X axis | roll_pin |
| gimbal_outer | servo_pitch | `servo_mount` (tap M2) on the +Y pad | ring_servo |
| horn_pitch | motor_hub | `horn_mount`, 4 x M2 from the fork side | pitch_horn |
| gimbal_outer | motor_hub | `pin_hole` press / free on the Y axis | pitch_pin |
| motor_hub | motor_top | `motor_mount` counterbore | hub_motor_top |
| motor_plate | motor_bottom | `motor_mount` counterbore | plate_motor_bottom |
| motor_plate | motor_hub | 3 x M3, heat-set inserts in the hub | hub_plate |
| ring_low | leg_i | 2 x M3 heat-set per leg | leg |
| ring_mid | stack | `stack_mount` thread-formed M2 | mid_stack |

## Joint tree
ring_low (root) -> rods, ring_mid -> stack, ring_top -> battery, legs, servo_roll -> horn_roll (**gimbal_roll**,
+/-15) -> gimbal_outer -> servo_pitch -> horn_pitch (**gimbal_pitch**, +/-15) -> motor_hub -> motor_top -> prop_top,
motor_plate -> motor_bottom -> prop_bottom. Coupled sweep `gimbal_corners` = the four (+/-15, +/-15) corners.

## Assembly order (also `assembly.order` / `key_access` in project.yaml, so the hex-key check follows it)
1. Melt the heat-set inserts (ring_low leg lugs, motor_hub). Glue nothing.
2. Press the 3 mm dowels into ring_low's -X plate and gimbal_outer's -Y pad.
3. Roll servo into the +X yoke window, 4 x M2 thread-forming screws; centre it (1500 us), fit horn_roll.
4. Hang gimbal_outer: slide its -X pad onto the roll dowel, bolt the +X lug to horn_roll (4 x M2 from inside).
5. Pitch servo into the +Y pad, fit horn_pitch.
6. motor_hub: top motor on with 4 x M3 x 6 from below. Bench: bottom motor onto motor_plate (4 x M3 x 6 from the top).
7. motor_hub onto the pitch dowel and horn_pitch (4 x M2; the two upper screws need a **ball-end 1.5 mm key**).
8. motor_plate under the hub, 3 x M3 from below. Props on (top CW, bottom CCW or per FC mixer).
9. Tubes into ring_low, ring_mid, ring_top; tighten the radial lock screws on filed flats. Stack, battery, legs.

## Risks / measure first
- Micro 21T horn geometry is an estimate (catalog note): measure OD, bolt circle and hub height; re-run `kerf check`.
- MG90S tab height (18.5 vs 21 mm spread) — measure; it moves the horn faces.
- Direct-drive gimbal is untested in flight (the flown designs use 3:1/4:1 gears). Tune on a tether.
- 1685 g thrust is at full-charge 24 V; the 0.78 coax factor comes from a different rotor size.
