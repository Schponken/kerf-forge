# Diary: tvc_drone

38 problems recorded (0 open). Found at: before parts 0, rough 0, detail 0, final review 38.
Estimated active fix time 1353 min; parts redrawn: gimbal_outer, leg, motor_hub, motor_plate, ring_low, ring_mid, ring_top. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| 27f7bfff | 2026-10-31 | FAIL | 10 |
| 4e8d44f7 | 2026-10-31 | PASS | 7 |
| e19a384a | 2026-10-31 | PASS | 7 |
| cef68c23 | 2026-10-31 | FAIL | 7 |
| 394d78d8 | 2026-10-31 | PASS | 4 |
| a237a77a | 2026-10-31 | PASS | 2 |
| 1106a30f | 2026-10-31 | FAIL | 5 |
| 6de303b4 | 2026-10-31 | FAIL | 4 |
| 3d0ef07e | 2026-10-31 | PASS | 4 |
| 123d4b1e | 2026-10-31 | PASS | 6 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | blocker | wiring (project.yaml) / ring_low / motor_hub / gimbal_outer | final review | resolved | 21 |  | The routes for ph_top, ph_bottom, servo_pitch_pwr/sig (and servo_roll at gimbal tilt) cann |
| 2 | major | stack (drone.stacks.fc_20) / electrical | final review | resolved | 21 |  | The design says the SpeedyBee F405 Mini drives both gimbal servos from 'FC servo output S1 |
| 3 | major | ring_low / gimbal_outer / motor_hub (assembly order) | final review | resolved | 21 |  | DESIGN.md step 2 presses both dowels in first, then step 3 fits horn_roll on the roll serv |
| 4 | major | ring_top (xt60 mount) | final review | resolved | 21 |  | The XT60 is held by one cable tie plus a stop block that only resists pushing in. XT60 mat |
| 5 | minor | wiring bat_lead | final review | resolved | 21 |  | WIRING.md step 1 says to 'cut 2 x 100 mm AWG 12 and solder battery -> xt60', and the BOM b |
| 6 | minor | bom | final review | resolved | 122 | 5: gimbal_outer, leg, motor_hub... | The brief asks for a buy link on every wire, connector and electrical part. The wire rows  |
| 7 | minor | bom (dowels) | final review | resolved | 21 |  | The pin check sizes the dowels at 3 x 20 mm and the BOM lists them that way (twice), but b |
| 8 | minor | ring_mid / motor_hub | final review | resolved | 21 |  | ring_mid is printed top-up with its tube bosses hanging below, so the whole plate undersid |
| 9 | minor | ring_low / ring_mid / ring_top (tube locks) | final review | resolved | 21 |  | Radial M3 set screws bear directly on a pultruded 5x3 CF tube with a 1 mm wall. Overtighte |
| 10 | minor | horn_roll / horn_pitch | final review | resolved | 21 |  | Both horn mounts and the servo face positions depend on the 21T micro disc horn geometry,  |
| 11 | minor | stack (drone.stacks.fc_20) / REFERENCES.md | final review | resolved | 101 | 5: gimbal_outer, leg, motor_hub... | The ArduPilot facts the flight depends on are only cited in DESIGN.md prose. They are not  |
| 12 | minor | out/ASSEMBLY.md | final review | resolved | 101 | 5: gimbal_outer, leg, motor_hub... | The generated steps still say 'press the 3 x 20 mm dowel into ring_low / gimbal_outer' at  |
| 13 | minor | wiring (roll and pitch pivot crossings) | final review | resolved | 101 | 5: gimbal_outer, leg, motor_hub... | All the gimbal-bound conductors cross the roll pivot as a single short span of about 23 mm |
| 14 | minor | wiring bat_lead / ring_top | final review | resolved | 101 | 5: gimbal_outer, leg, motor_hub... | The pack's own XT60 lead must be at least 110 mm long, but CNHL does not publish its lengt |
| 15 | minor | motor_hub / ring_low / legs | final review | resolved | 101 | 5: gimbal_outer, leg, motor_hub... | The support warnings are unchanged: motor_hub 24 %, ring_low 17 %, gimbal_outer 18 %, legs |
| 16 | minor | horn_roll / horn_pitch / servos | final review | resolved | 101 | 5: gimbal_outer, leg, motor_hub... | The micro 21T disc horn geometry is still an estimate, and the MG90S tab height has a 2.5  |
| 17 | major | rod_1..3 / xt60 / mass | final review | resolved | 23 | 7: gimbal_outer, leg, motor_hub... | report.json purchased mass_g is 0.0 for rod_1, rod_2, rod_3 and xt60. kerf/checks.py item_ |
| 18 | minor | ring_low | final review | resolved | 23 | 7: gimbal_outer, leg, motor_hub... | DESIGN.md, STATUS.md and the ring_low docstring say the bosses, webs and lug ribs touch th |
| 19 | minor | ring_mid, ring_top, leg_1..3 | final review | resolved | 23 | 7: gimbal_outer, leg, motor_hub... | A-5 is only partly done. The radial M3 lock taps in ring_mid and ring_top are plain cylind |
| 20 | minor | motor_hub, gimbal_outer, ring_low, all | final review | resolved | 23 | 7: gimbal_outer, leg, motor_hub... | A-11 is only partly done. The leg root fillet is there. The hub fork/arm-to-disc roots, gi |
| 21 | minor | ring_low (lug_fea) | final review | resolved | 23 | 7: gimbal_outer, leg, motor_hub... | lug_fea passes on p99.9 8.08 vs 13 MPa, but its volume peak is 21.70 MPa (1.7x the limit;  |
| 22 | minor | ring_low, ring_mid, ring_top / rods | final review | resolved | 23 | 7: gimbal_outer, leg, motor_hub... | The 5x3 pultruded CF tubes (1 mm wall) are held only by 9 cup-point set screws on filed fl |
| 23 | minor | DESIGN.md | final review | resolved | 23 | 7: gimbal_outer, leg, motor_hub... | Stale numbers remain. The XT60 row says 'hover 11.8 A, peak 36.6 A' (report: 12.2 / 43.8 A |
| 24 | minor | motor_hub, gimbal_outer, all | final review | resolved | 1 |  | Remaining s5 detail. ENGINEERING.md s5 says inside corners on any load path get r >= 1 mm  |
| 25 | minor | DESIGN.md (ring_low row) | final review | resolved | 1 |  | The Parts table (DESIGN.md:95) still says 'bosses, webs and ribs on the bed'. The STL show |
| 26 | minor | leg_1..3 | final review | resolved | 95 |  | leg_fea deflection is 2.948 mm against its 3.0 mm limit (98 %) at the 790 g budget. Stress |
| 27 | minor | lug_fea / leg_fea | final review | resolved | 1 |  | Both peaks are at load or fixture patches, not geometry. lug_fea peaks at 10.97 MPa at [-4 |
| 28 | minor | gimbal_outer | final review | resolved | 94 |  | 14 of 38 first-layer edges could not be chamfered (build warning). They are at the -Y pin  |
| 29 | major | plates (engine kerf/export.py) | final review | resolved | 21 | 3: ring_low, ring_mid, ring_top | Metadata/model_settings.config is missing objects. plate_1 has gimbal_outer but not leg_1  |
| 30 | minor | DESIGN.md (edge distance) | final review | resolved | 21 | 3: ring_low, ring_mid, ring_top | The new holewall check warns that the MG90S tab taps (79 % material at 1.5 d, groups yoke_ |
| 31 | minor | ring_low (lug_fea) | final review | resolved | 21 | 3: ring_low, ring_mid, ring_top | FEA is run on a solid model, but ring_low now prints at 20 % infill (was 40 %). The 8 mm l |
| 32 | minor | gimbal_outer | final review | accepted at PASS |  |  | Carried over: 14 first-layer edges cannot be chamfered (deburr warning). |
| 33 | minor | leg_1..3 | final review | accepted at PASS |  |  | Carried over: leg_fea deflection is 2.966 vs 3.0 mm (99 %); accepted. |
| 34 | blocker | all (out/ stale) | final review | resolved | 20 |  | `kerf review-status tvc_drone` reports geometry 721479e716c80d8c, but out/report.json is 0 |
| 35 | minor | ring_low (lug_fea) | final review | accepted at PASS |  |  | The FEA uses a solid model and the print is 30 % infill with 4 perimeters. lug_fea is 7.88 |
| 36 | minor | ring_low, gimbal_outer (M2 servo-tab taps) | final review | accepted at PASS |  |  | The teardropped servo-tab taps now use the horizontal pilot tap_h = 2.10 mm, which is larg |
| 37 | minor | gimbal_outer, ring_low (pitch_pin, roll_pin) | final review | accepted at PASS |  |  | First recorded here (the warning comes from the ENG-7..20 engine and was already in the 12 |
| 38 | minor | motor_hub (pitch_horn) | final review | accepted at PASS |  |  | Carried over and documented in DESIGN.md assembly step 6: a straight 1.5 mm key cannot rea |
