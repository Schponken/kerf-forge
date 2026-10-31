# References — pan-tilt camera mount (pan_tilt)

No design-researcher subagent could be launched in this session (no agent-spawning tool), so this list reuses the
pan-tilt rows already studied in `references/INDEX.md` plus the catalog sources; nothing new was cloned or measured.

| Reference | License | Why |
|---|---|---|
| inertiarobotics Pan-Tilt-Camera-B — https://github.com/inertiarobotics/Pan-Tilt-Camera-B | MIT | 2x SG90; bearings on both axes because SG90 pan-tilts "rattle and wiggle" at the spline; base 50x75, tilt holder ~35x62x42 |
| Adafruit mini pan-tilt kit (Pimoroni listing) — https://shop.pimoroni.com/en-no/products/adafruit-mini-pan-tilt-kit-assembled-with-micro-servos | not stated | proven envelope: 67 mm tall at zero tilt, 37 g, ~180 pan / ~150 tilt; its camera mount does not fit Camera Module 3 |
| traxrobotics Pi face-tracking turret — https://github.com/traxrobotics/Raspberry-Pi-Face-Tracking-Turret-V1 | MIT | base -> arm on pan horn -> tilt servo -> camera on tilt horn; "servos are the weak point long before the plastic"; 1000 uF cap across servo power |
| Raspberry Pi Camera Module 3 product brief (catalog `boards.rpi_camera_module_3`) | — | board 25 x 23.862, M2 holes 21 x 12.5, lens 14.4 mm above the connector edge, ~3.2 mm of parts behind the PCB |
| Joy-IT RB-Camera-3 spec page — https://joy-it.net/en/products/RB-Camera-3 | — | standard lens FOV 66 x 41 deg (75 diagonal): sizes the `cam_view` keep-out |
| SG90 drawing (catalog `servos.SG90`, baud-dance PDF + TowerPro cross-checks) | — | body 22.6 x 12.2, tabs at 15.6, hole spacing 27.85, output 6.0 from the end, stall 1.8 kg·cm @ 4.8 V, ~14 mm round gear boss above the case |
| 21T aluminium micro disc horn (catalog `servo_horns.aluminum_micro_21T`) | — | 20 OD, 12 mm bolt circle, 4 x M2 — ESTIMATED geometry (catalog says buy and measure) |
| ASME B18.2.2 1/4 hex nut (catalog `tripod_nut_1_4_20`, amesweb table) | — | 11.13 AF max, 5.74 thick max: the captive tripod nut pocket |

## Decisions this supports
- Two SG90s, pan servo upright in the base, tilt servo on a side wall of the pan yoke (traxrobotics / Adafruit layout).
- Tilt carried on BOTH sides (servo horn + M3 screw pivot), following the inertiarobotics lesson that the SG90 spline
  should not carry the side load alone. The pan axis keeps the servo's own output bearing: the turning head is 34 g
  with its CG 15 mm off the axis (0.05 kg·cm overturning moment), far below the ENGINEERING.md section 8 thresholds
  (60 mm / 100 g) that call for a separate bearing.
- Screwed metal horns, not glued (INDEX lesson: glued horns are not serviceable).
- Captive purchased 1/4-20 nut, never a printed thread (INDEX cross-cutting lesson; ENGINEERING.md section 5: printed
  threads only >= M6 and this one carries the clamp).
- Camera lens centred on the tilt axis: tilting does not swing the image centre and the tilt servo carries ~0 torque.

## Open questions
- Horn bolt circle / thread / height are estimates: measure the horn you buy before printing the yoke and bracket.
- Camera rear-parts depth (3.2 mm) is an approximate reading of the drawing: check the standoffs clear the FPC
  connector before the final print.
- Tripod screw protrusion is not standardised in anything opened here (assumed <= 8 mm, see DESIGN.md).
