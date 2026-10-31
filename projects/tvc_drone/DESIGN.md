# tvc_drone — design

A rocket-style thrust-vectoring drone after fd.iwth and Mistral (REFERENCES.md): a tall, light carbon mast with the
battery at the top, a counter-rotating motor pair at the bottom on a two-axis servo gimbal that steers the thrust,
three splayed legs. Numbers below are from `kerf build tvc_drone` (out/report.json) unless marked as a hand estimate.

## Requirements (numbers)
| What | Target | Result |
|---|---|---|
| Thrust / weight (`twr`) | >= 1.8 | 2.54 (1683 g at the 80 % motor output limit / 664 g) |
| CG on thrust axis (`cg_axis`) | <= 3 mm lateral, above pivot | 0.45 mm worst over gimbal corners; 136 mm above the pivot |
| Stand on its own (`stand`) | >= 15 deg tip-over | 20.9 deg |
| Gimbal travel | +/-15 deg each axis + 4 corners, collision-free | clear (sweeps + `gimbal_corners`) |
| Prop clearance (`props`) | >= 3 mm to anything, >= 20 mm between discs | 5.3 mm (bottom prop to the roll ring at pitch 15 deg) |
| Gimbal hub strength (`gimbal_fea`) | 2 x max thrust = 66.1 N, SF 2 | 3.5 MPa vs 24 MPa allowable, 0.17 mm |
| Roll ring / yoke / leg FEA | SF 2 | 3.2 / 3.5 (Z-strength) / 2.7 MPa vs 24 / 19.5 / 24 |
| Mass | <= 750 g | 664 g (wires not modelled: ~25-35 g more, hand estimate) |
| Power budget (`power`) | every rating at avg and peak | worst 0.61 of rating (battery 10.3 A hover, 36.6 A peak) |
| Hover time (`flight_time`) | >= 2 min | 5.1 min on 80 % of 1100 mAh (momentum theory, coax kappa 1.281) |
| Battery plug / USB (`plug_access`, `usb_access`) | reachable assembled | both clear |

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

| RadioMaster RP1 ELRS receiver | electronics.receivers.elrs_nano | 5 V from the FC pad, CRSF to a free UART; tied under ring_mid |
| Hobbywing UBEC 3 A (5 V) | electronics.becs.ubec_5v_3a | servos off the FC rail: 2 x 0.7 A stall = 1.4 A peak vs 3 A |
| Amass XT60 male | drone.connectors.XT60 | 30 A continuous / 60 A instantaneous; hover 10.3 A, peak 36.6 A |
| 20 x 250 mm strap | electronics.straps.strap_20x250 | over the pack across its width, through two ring_top slots |

## Electrical (project.yaml `electrical:` / `wiring:`; out/WIRING.md + wiring.svg)
Power tree: 6S 1100 pack -> its own 12 AWG lead -> XT60 (under ring_top, pointing out at 30 deg) -> 14 AWG down the
90 deg tube -> ESC battery pads (ring_mid). ESC channels 1-2 -> motors on 18 AWG 3-wire extensions through the
30 deg wire pass and down a tube to the gimbal, with a service loop. ESC pads -> UBEC (5 V jumper) -> both servos
(24 AWG); servo PWM from FC outputs S1/S2 (28 AWG). FC 5 V pad -> receiver; CRSF on a free UART.
- **Motor output limit 80 % (Betaflight `motor_output_limit = 80`) is required**, not optional: two motors at full
  throttle draw 2 x 35.08 A = 70 A, above the XT60's 60 A instantaneous rating. Prop power goes as speed^3, so 80 %
  output = 0.512 x 35.08 = 18.0 A per motor and 64 % thrust: 1683 g, still T/W 2.54 >= 1.8. Without the limit the
  `power` check fails on the XT60.
- Hover: 664 g on one coaxial 5.1" pair -> 219 W electrical (FM 0.5, motor eff. 0.75, coax 1.281) = 10.3 A at
  22.2 V; with FC 0.3 A + servos/receiver = 10.3 A -> 5.1 min on 880 mAh usable.
- Wire heating at peak for 5 s: 18 AWG motor leads at 18 A stay < 60 K rise; 14 AWG main at 36.6 A ~10 K.
- Fit the FC with its USB-C port facing -X (`usb_access`); +Y faces a tube.

## Parts (all PETG)
| Part | Job | print_rot | load_axis |
|---|---|---|---|
| ring_low | root: mast base, 3 tube bosses, 3 leg lugs, +X yoke with roll servo window, -X yoke with roll dowel, top webs | [180,0,0] upside down | z (FEA in Z strength) |
| gimbal_outer | roll ring: roll horn lug (+X), roll dowel pad (-X), pitch servo pad (+Y), pitch dowel pad (-Y) | flat | x, y |
| motor_hub | pitch frame: top motor (counterbored M3 x 6), +Y fork to the pitch horn, -Y arm to the dowel, 3 M3 inserts | flat | y |
| motor_plate | bottom motor (M3 x 6, counterbored), bolts under the hub | flat | — |
| ring_mid | tubes through, radial locks, flight stack on 4 thread-formed M2; UBEC + receiver tied underneath | flat | — |
| ring_top | tube caps, battery tray with strap slots beside the pack, XT60 tie slots + stop block underneath | upside down | — |
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
| ring_mid | bec, receiver | one 2.5 mm cable tie each through two slots, under the ring | — |
| ring_top | xt60 | cable tie through two slots + printed stop block behind it | — |
| battery | strap | strap over the pack through two ring_top slots | — |

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
9. Tubes into ring_low, ring_mid, ring_top; tighten the radial lock screws on filed flats. Stack (USB-C facing -X),
   battery, legs.
10. Wiring (out/WIRING.md has every run, gauge and cut length): XT60 tied under ring_top; UBEC and receiver tied under
   ring_mid; solder main lead, motor extensions (service loop at the gimbal), UBEC input, servo and receiver leads.
   In Betaflight set `motor_output_limit = 80` before the first flight.

## Risks / measure first
- Micro 21T horn geometry is an estimate (catalog note): measure OD, bolt circle and hub height; re-run `kerf check`.
- MG90S tab height (18.5 vs 21 mm spread) — measure; it moves the horn faces.
- Direct-drive gimbal is untested in flight (the flown designs use 3:1/4:1 gears). Tune on a tether.
- 1685 g thrust is at full-charge 24 V; the 0.78 coax factor comes from a different rotor size.
