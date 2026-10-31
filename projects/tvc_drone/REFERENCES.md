# References — TVC coax drone (eval E4)

These designs were already studied for `references/INDEX.md` (research date 2026-10-30). This file takes the decisions
they support and applies them to this build. The parts it uses are catalog entries: rods.cf_tube_5x3,
drone.batteries.6S_1100, drone.motors.2207_1855kv_6s, drone.props.5_1in, servos.MG90S,
servo_horns.aluminum_micro_21T and drone.stacks.fc_20.

| Reference | Link | License | Why relevant |
|---|---|---|---|
| fd.iwth TVC coax drone (minu920/tvc-drone) | https://github.com/minu920/tvc-drone | GPL-3.0 (reference only, no geometry copied) | The design the brief names: carbon-rod mast through printed rings, battery high, coax pair on a 2-axis MG90S gimbal at the bottom, gimbal clamp 0.149 rad, rods locked by screws into notches |
| Mistral / Zephyr v2 (prabavac) | https://github.com/prabavac/Mistral | MIT | Flown fd.iwth derivative: clamp 0.15 rad, 0.370 kg, thrust-to-pivot arm 0.200 m, servo µs per degree, servo-sign check |
| Starkit (mikuel210) | https://github.com/mikuel210/starkit | not stated (ideas only) | Coax 2807 TVC rocket on 5 mm carbon rods: rod size, rod fit/lock, PETG over PLA, model the real prop |
| Goose (Eryk-Mozdzen) | https://github.com/Eryk-Mozdzen/uav-tvc-goose | not stated (ideas only) | ±15° fin travel (the brief's ±15° sweep), fallback architecture |
| Low-cost printed TVC servo gimbal (arXiv 2509.00061) | https://arxiv.org/html/2509.00061v1 | CC BY 4.0 | Round gimbal rings, printed pivot pins vs metal screws, 30 N FEA load, fillets at pivots/servo slots |
| inertiarobotics Pan-Tilt-Camera-B | https://github.com/inertiarobotics/Pan-Tilt-Camera-B | MIT | The servo spline must not carry the overturning load: put a bearing or pin on the axis opposite the servo |
| Overlapping/coaxial rotor interference study, Aerospace 3(4):32 (2016) | https://www2.mdpi.com/2226-4310/3/4/32 (also https://eprints.soton.ac.uk/401416/1/aerospace-03-00032.pdf) | CC BY 4.0 | Published coax efficiency loss and the axial spacing beyond which it stops mattering |
| iFlight XING2 2207 1855KV test report | https://shop.iflight.com/image/catalog/TEST%20REPORT/XING2-2207-1855KV.png (via catalog) | vendor data | 1685 g max thrust per motor with Gemfan 51466 at 24.0 V |
| TowerPro MG90S | https://www.towerpro.com.tw/product/mg90s-3/ (via catalog) | vendor data | 1.8 kg·cm @4.8 V, 0.10 s/60°, 13.4 g, ships with arms only (no disc horn listed) |
| 21T CNC aluminium micro horn (eBay TL2366) | https://www.ebay.de/itm/125626159464 | vendor listing | 21T aluminium horn for 12-18 g metal-gear servos, 2 g; disc geometry not published (see Open questions) |

## Decisions this supports

1. **Gimbal travel.** The geometry must sweep clear over ±15° on each axis and at the four (±15, ±15) corners (brief).
   Flight firmware should clamp to about ±8.5° (0.149 rad fd.iwth firmware, 0.15 rad Mistral `mistral_config.h`).
   ±15° matches the Goose fin limit, so the extra mechanical travel is margin, not flight authority.
2. **Coax thrust and T/W.** Published loss: a torque-balanced coax pair is **22% less efficient** than two isolated
   rotors, and spacing beyond **z/D = 0.25** has no further effect (Aerospace 3(4):32 conclusions, CC BY 4.0). We use
   a thrust factor of **0.78**: 2 × 1685 g (catalog `thrust_g_max`, iFlight report, 24.0 V, 100 %) × 0.78 =
   **~2630 g**. The purchased parts alone are about 317 g (battery 197.5 + motors 2×31.6 + props 2×4.2 + servos 2×13.4 +
   stack 16.8 + horns 2×2). With about 200 g of printed parts and rods the all-up weight is about 520 g, which gives
   T/W ≈ 5 against the required 1.8. Flown builds hover at T/W ~1.3 (fd.iwth: 0.430 kgf hover vs ~280 g × 2), so this
   drone has a large margin and will hover at low throttle. Note that 0.78 is an efficiency (thrust per power) figure
   applied as a thrust factor, which is a conservative reading.
3. **Prop-plane spacing.** Keep the two prop planes at least 0.25 D = 0.25 × 131.8 mm = **33 mm** apart (Aerospace
   3(4):32). Closer spacing costs up to 26% (z/D = 0.05). Model both prop discs from the catalog prop (131.8 mm), not a
   nominal 5" disc: Starkit bought larger props than it planned for and was left with no clearance.
4. **Prop clearance at full tilt.** At 15° tilt a 65.9 mm prop tip moves 65.9 × sin 15° = **17.1 mm** axially. The
   legs, the lowest ring and the mast rods must stay outside the tilted prop discs at all four gimbal corners. This
   is the reason for the `gimbal_corners` sweep.
5. **Mass layout.** Put the battery at the top and the motors at the bottom, and the pivot well below the CG.
   fd.iwth puts mass at the ends so the drone tips over slowly enough for 50 Hz servos to keep up. Mistral flies with
   a 0.200 m thrust-to-pivot arm at 0.370 kg, which is a reasonable target for the pivot-to-CG distance.
6. **Mast rods.** Use 5 mm carbon tubes (catalog rods.cf_tube_5x3, 18.8 g per metre, calculated from OD 5 / ID 3 at
   1.5 g/cm³). Starkit: 3 mm rods are "really bad" for flex at 500 mm, so it moved to 5 mm. fd.iwth uses 3 mm, but on
   a smaller drone. For the ring bores use **~0.5 mm total diametral clearance (Ø5.5 bore)** plus a mechanical lock
   (an M2/M3 screw into a notch or flat on the rod, as fd.iwth does, or a clamp bolt), not a press fit. Starkit found
   that rod fit changes with print orientation and moisture.
7. **Gimbal drive and pivots.** Each axis is driven directly by an MG90S through a metal disc horn bolted to the
   gimbal ring with 4 screws (horn screws, not a printed spline). The opposite side of each axis is a free pin
   pivot, and that pin carries the radial/overturning load (inertiarobotics: an unsupported micro-servo spline
   rattles). arXiv 2509.00061 found that printed pins rubbed less and had less backlash than metal-screw pivots. A
   steel dowel in a printed bushing with ~0.2-0.35 mm clearance (`iface.FIT` snug/free) is an acceptable alternative.
   Use round gimbal rings so they don't hit the motor body (same paper), with fillets and ribs at the pivots and
   servo slots.
8. **Gimbal FEA load.** The ring that carries both motors' thrust into the pivots must take 2 × max thrust =
   2 × 2 × 1685 g × 9.81 = **~66 N** (brief: 2× max thrust; no coax derating, to be conservative). This is about 2.2×
   the 30 N design load used in arXiv 2509.00061.
9. **Coax torque cancels at the gimbal.** With counter-rotating props the yaw reaction torques and gyroscopic
   moments largely cancel. fd.iwth steers yaw by differential motor speed, so the servos mostly see inertia and
   thrust-line offset. Put the pivot axes through the thrust line so that full thrust puts no static moment on a
   1.8 kg·cm (0.18 N·m) MG90S.
10. **Standing stability.** With 3 feet at radius r, the shortest distance from the centre to a tipping edge is
    r·cos 60° = r/2. A static tip-over angle of ≥15° then needs r/2 ≥ h_cg·tan 15°, i.e. **r ≥ 0.536 × h_cg**
    (geometry). Because the battery sits high, h_cg is large, so the legs must splay wide. They must also stay outside
    the 15°-tilted prop discs (decision 4).
11. **Materials.** Use PETG or better, not PLA, near the motors. Starkit's PLA bolts broke where PETG held, and
    arXiv 2509.00061 saw PLA deform from heat. INDEX cross-cutting lessons: PETG-CF or PA-CF is preferred for crash
    loads.

## Open questions / unverified numbers

- **Micro disc horn geometry is UNVERIFIED.** `servo_horns.aluminum_micro_21T` has confidence `estimate`. Only the
  21T spline, aluminium and 2 g are published (eBay TL2366 listing, M5Stack SG90 "Spline: 21T"). OD 20, disc 2.0,
  total height 4.0, hub Ø7, bolt circle 12, 4× M2 are scaled from the sourced 25T 20 mm disc. No vendor drawing of a
  21T micro metal disc was found: Pololu and Botland/Feetech pages were blocked, and Adafruit, DFRobot, TowerPro and
  M5Stack publish no horn dimensions. Buy the horn and measure OD, bolt circle, thread and height before printing the
  gimbal ring.
- The MG90S spline itself (21T, Ø4.8) is UNVERIFIED for this specific servo (copied from the SG90 data in the
  catalog). Some sources call it 20T / 4.9 mm, and some call micro splines "25T". Check that the horn fits the
  actual servo.
- MG90S tab height is uncertain (catalog: 18.5 vs 21 mm spread). Leave adjustment room in the servo pocket.
- The coax factor 0.78 comes from a rotor study of a different size. It is quoted as efficiency at equal combined
  solidity, not measured thrust at full throttle for this motor/prop pair. A thrust-stand test of the real pair would
  settle it.
- Direct drive (no 3:1/4:1 gears as in fd.iwth/Mistral) gives up angular resolution and adds servo-gear backlash
  straight into thrust direction. Mistral measured 12.8 µs per servo degree after its gearing. Untested for this
  build.
- The 1685 g thrust is at 24.0 V (full 6S), 100 % throttle, 35 A per motor. A 1100 mAh 130C pack can supply it
  briefly. It will sag in flight.

## Flight control and power references (added 2026-10-31, electronics round)
| Reference | Link | Used for |
|---|---|---|
| ArduPilot: SpeedyBee F405 Mini | https://ardupilot.org/copter/docs/common-speedybeef405-mini.html | board supported; PWM 1-2 timer group 1, PWM 3-4 group 2, PWM 5 (LED pad) group 3; channels in a group share one rate -> motors on 1-2 (DShot), servos on 3-4 (50 Hz); 5 V 2 A and 9 V 3 A BECs |
| ArduPilot: SingleCopter and CoaxCopter | https://ardupilot.org/copter/docs/singlecopter-and-coaxcopter.html | FRAME_CLASS 9 = CoaxCopter; motors on outputs 5/6 (upper CCW, lower CW) and flaps on 1-4 by default -> remap with SERVOn_FUNCTION to this board's 5 outputs |
| ArduPilot: Motor Thrust Scaling | https://ardupilot.org/copter/docs/motor-thrust-scaling.html | MOT_SPIN_MAX: the output at which thrust saturates, default 0.95; set 0.80 here as the current cap |
| letronic UL 3672 silicone wire data sheet | https://www.letronic.de/de/produkte/kabel/pdf/970/silicone-ul-3672.pdf | wire OD and g/m per AWG (catalog wire.silicone) |
