# tvc_drone — design

A rocket-style thrust-vectoring drone after fd.iwth and Mistral (REFERENCES.md): a tall, light carbon mast with the
battery at the top, a counter-rotating motor pair at the bottom on a two-axis servo gimbal that steers the thrust,
three splayed legs. Numbers below are from `kerf build tvc_drone` (out/report.json) unless marked as a hand estimate.

## Requirements (numbers)
| What | Target | Result |
|---|---|---|
| Thrust / weight (`twr`) | >= 1.8 | 2.31 (1683 g at the 80 % motor output limit / 730 g incl. 66 g of wiring) |
| CG on thrust axis (`cg_axis`) | <= 3 mm lateral, above pivot | 0.45 mm worst over gimbal corners; 136 mm above the pivot |
| Stand on its own (`stand`) | >= 15 deg tip-over | 20.9 deg |
| Gimbal travel | +/-15 deg each axis + 4 corners, collision-free | clear (sweeps + `gimbal_corners`) |
| Prop clearance (`props`) | >= 3 mm to anything, >= 20 mm between discs | 5.3 mm (bottom prop to the roll ring at pitch 15 deg) |
| Gimbal hub strength (`gimbal_fea`) | 2 x max thrust = 66.1 N, SF 2 | 3.5 MPa vs 24 MPa allowable, 0.17 mm |
| Roll ring / yoke / leg FEA | SF 2 | 3.2 / 3.5 (Z-strength) / 2.7 MPa vs 24 / 19.5 / 24 |
| Mass | <= 750 g | 730 g (664 g of parts + 66 g of wire from the catalog g/m x cut lengths) |
| Power budget (`power`) | every rating at avg and peak | worst 0.61 of rating (battery 11.8 A hover, 36.6 A peak) |
| Hover time (`flight_time`) | >= 2 min | 4.5 min on 80 % of 1100 mAh (momentum theory, coax kappa 1.281) |
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
| SpeedyBee F405 mini 20 x 20 stack | drone.stacks.fc_20 | FC + 35 A 4-in-1 ESC (2 channels used); runs ArduPilot, PWM 3-4 drive the servos (see Electrical) |
| 2 x 3 x 20 mm steel dowel (length from the pin check) | motion.pin_3mm | pivots opposite each servo (press in one side, free in the other) |

| RadioMaster RP1 ELRS receiver | electronics.receivers.elrs_nano | 5 V from the FC pad, CRSF to a free UART; tied under ring_mid |
| Hobbywing UBEC 3 A (5 V) | electronics.becs.ubec_5v_3a | servos off the FC rail: 2 x 0.7 A stall = 1.4 A peak vs 3 A |
| Amass XT60 male on a 14 AWG pigtail | drone.connectors.XT60 | 30 A continuous / 60 A instantaneous; hover 11.8 A, peak 36.6 A |
| TBS anti-slip pad, cut 70 x 38 | electronics.pads.battery_pad | under the pack |
| 20 x 250 mm strap | electronics.straps.strap_20x250 | over the pack across its width, through two ring_top slots |

## Electrical (project.yaml `electrical:` / `wiring:`; out/WIRING.md + wiring.svg)
Power tree: 6S 1100 pack -> its own XT60 lead (`supplied`, must be >= 110 mm) -> XT60 on a 14 AWG pigtail hanging just
past the ring_top edge at 30 deg (held by hand to plug/unplug; the pigtail is tied through two plate slots, so no pull
reaches a solder joint) -> down the 90 deg tube -> ESC battery pads (ring_mid) with a >= 35 V low-ESR capacitor.
ESC channels 1-2 -> the two motors on 18 AWG 3-wire extensions; ESC pads -> UBEC (5 V jumper) -> both servos (24 AWG);
servo signals from FC pads M3/M4 (28 AWG). FC 5 V pad -> receiver; CRSF on a free UART.

**Firmware: ArduPilot Copter.** The SpeedyBee F405 Mini is an ArduPilot board with PWM 1-2 in timer group 1, PWM 3-4
in group 2 and PWM 5 (LED pad) in group 3 (ardupilot.org common-speedybeef405-mini); channels in a group share one
output rate, so motors go on 1-2 (DShot) and the servos on 3-4 (50 Hz), soldered to the FC's M3/M4 pads (the ESC's
channels 3-4 get the same signal but drive nothing). Frame: CoaxCopter (`FRAME_CLASS = 9`, two motors + flap
outputs, ardupilot.org singlecopter-and-coaxcopter) with `SERVOn_FUNCTION` remapping the two motor functions to
outputs 1-2 and two flap functions to outputs 3-4, which here drive the pitch and roll gimbal servos. That this flap
mixer steers a 2-axis gimbal well (sign, gain, clamp ~ +/-8.5 deg) is **not yet proven**: bench-check servo
directions and tune on a tether (Risks).
- **Motor output limit 80 % (ArduPilot `MOT_SPIN_MAX = 0.80`, default 0.95) is required**: two motors at full
  output draw 2 x 35.08 A = 70 A, above the XT60's 60 A instantaneous rating. Prop power goes as speed^3, so 80 %
  output = 0.512 x 35.08 = 18.0 A per motor and 64 % thrust: 1683 g, still T/W 2.31 >= 1.8.
- Hover: 730 g on one coaxial 5.1" pair -> electrical power from momentum theory (FM 0.5, motor eff. 0.75, coax
  1.281), 11.8 A at 22.2 V with FC, servos and receiver -> 4.5 min on 880 mAh usable.
- Routes (every one is checked at home, at both ends of each gimbal axis and at the 4 gimbal corners: a tube of the
  wire's diameter must not enter any part or prop disc, and the cut length covers the worst pose + 15 %): down
  through the ring_mid wire pass at 30 deg, over the +Y edge of ring_low to the +X yoke, down beside the yoke plate
  (two tie slots), across the roll pivot close to its axis onto the gimbal ring (cable tie round the ring section),
  along the ring top to the pitch servo, across the pitch pivot onto the hub fork bar (tie round the bar), then to
  the top motor over the hub, or down beside the fork and under the motor plate to the bottom motor. Motor
  extensions 550 / 580 mm, servo leads 350-500 mm. Leave the loops at the two pivots loose.
- Wire heating at peak for 5 s: 18 AWG motor leads at 18 A < 60 K rise; 14 AWG pigtail at 36.6 A ~10 K.
- Fit the FC with its USB-C port facing -X (`usb_access`); +Y faces a tube.
- The UBEC's input max is 26 V against 25.2 V at full charge: only 0.8 V headroom, hence the capacitor at the pads.

## Parts (all PETG)
| Part | Job | print_rot | load_axis |
|---|---|---|---|
| ring_low | root: mast base, 3 tube bosses, 3 leg lugs, +X yoke with roll servo window, -X yoke with roll dowel, top webs | [180,0,0] upside down | z (FEA in Z strength) |
| gimbal_outer | roll ring: roll horn lug (+X), roll dowel pad (-X), pitch servo pad (+Y), pitch dowel pad (-Y) | flat | x, y |
| motor_hub | pitch frame: top motor (counterbored M3 x 6), +Y fork to the pitch horn, -Y arm to the dowel, 3 M3 inserts | flat | y |
| motor_plate | bottom motor (M3 x 6, counterbored), bolts under the hub | flat | — |
| ring_mid | tubes through, radial locks, flight stack on 4 thread-formed M2; UBEC + receiver tied underneath | flat | — |
| ring_top | tube caps, battery tray with strap slots beside the pack, two tie slots for the XT60 pigtail | upside down | — |
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
| ring_top | xt60 pigtail | cable tie round the 14 AWG pair through two slots; the XT60 hangs past the plate edge | — |
| battery | strap | strap over the pack through two ring_top slots | — |

## Joint tree
ring_low (root) -> rods, ring_mid -> stack, ring_top -> battery, legs, servo_roll -> horn_roll (**gimbal_roll**,
+/-15) -> gimbal_outer -> servo_pitch -> horn_pitch (**gimbal_pitch**, +/-15) -> motor_hub -> motor_top -> prop_top,
motor_plate -> motor_bottom -> prop_bottom. Coupled sweep `gimbal_corners` = the four (+/-15, +/-15) corners.

## Assembly order (also `assembly.order` / `key_access` in project.yaml, so the hex-key check follows it)
1. Melt the heat-set inserts (ring_low leg lugs, motor_hub). Glue nothing.
2. Roll servo into the +X yoke window, 4 x M2 thread-forming screws; centre it (1500 us), fit horn_roll.
3. Hang gimbal_outer: bolt its +X lug to horn_roll (4 x M2 from inside), then press the roll dowel in from outside
   through ring_low's -X plate into gimbal_outer's -X pad (the holes go through, so the pin goes in last).
4. Pitch servo into the +Y pad, fit horn_pitch.
5. motor_hub: top motor on with 4 x M3 x 6 from below. Bench: bottom motor onto motor_plate (4 x M3 x 6 from the top).
6. motor_hub onto horn_pitch (4 x M2; the two upper screws need a **ball-end 1.5 mm key**), then press the pitch
   dowel in from outside through gimbal_outer's -Y pad into the hub's -Y arm.
7. motor_plate under the hub, 3 x M3 from below. Props on (top CCW, bottom CW per the ArduPilot CoaxCopter layout).
8. Tubes into ring_low, ring_mid, ring_top; tighten the radial lock screws gently on filed flats (the tube wall is
   1 mm: use nylon-tipped set screws or stop at first contact + 1/8 turn). Stack (USB-C facing -X), pad, battery,
   strap, legs.
9. Wiring (out/WIRING.md has every run, gauge and cut length): XT60 pigtail tied through the ring_top slots; UBEC and receiver tied under
   ring_mid; solder the pigtail, capacitor, motor extensions, UBEC input, servo and receiver leads, and tie them at the
   points listed under Electrical with loose loops at both pivots. In ArduPilot set `MOT_SPIN_MAX = 0.80` before the
   first flight.

## Risks / measure first
- Micro 21T horn geometry is an estimate (catalog note): measure OD, bolt circle and hub height; re-run `kerf check`.
- MG90S tab height (18.5 vs 21 mm spread) — measure; it moves the horn faces.
- Direct-drive gimbal is untested in flight (the flown designs use 3:1/4:1 gears). Tune on a tether.
- 1685 g thrust is at full-charge 24 V; the 0.78 coax factor comes from a different rotor size.
- Flight control: ArduPilot's CoaxCopter mixer is written for flaps; driving a 2-axis gimbal through its two flap
  outputs is plausible (both deflect the thrust) but unproven here. Check each servo's direction against a hand tilt
  on the bench, clamp the gimbal to about +/-8.5 deg (REFERENCES.md), and make the first hovers on a tether.
- Wire runs to the gimbal are long (550-580 mm motor extensions): keep them twisted, tie them at the listed points
  and leave loose loops at both pivots; recheck the gimbal moves freely through all four corners after wiring.
- Reviewer round 2 (PASS) follow-ups for the builder: make the roll-pivot crossing a 30-40 mm U-loop (not a straight
  23 mm span) and check the gimbal still moves freely at all four corners with the servo current low; measure the
  pack's XT60 lead on arrival (it must reach 110 mm; CNHL does not publish it) and tie the mated XT60 pair under the
  strap; in ASSEMBLY.md the two dowel steps must be done LAST and from outside (step order here, steps 3 and 6).
