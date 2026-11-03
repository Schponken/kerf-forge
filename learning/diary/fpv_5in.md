# Diary: fpv_5in

57 problems recorded (0 open). Found at: before parts 0, rough 0, detail 0, final review 57.
Estimated active fix time 1603 min; parts redrawn: arm, body, top_plate. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| 37e54362 | 2026-10-31 | FAIL | 12 |
| 2baea6ca | 2026-10-31 | FAIL | 10 |
| fedf03cc | 2026-10-31 | FAIL | 10 |
| 7ea3894a | 2026-10-31 | FAIL | 8 |
| b18b8b6f | 2026-10-31 | PASS | 8 |
| c9589790 | 2026-10-31 | FAIL | 11 |
| 5f1fd4aa | 2026-10-31 | FAIL | 12 |
| da5b23aa | 2026-10-31 | PASS | 11 |
| f31da762 | 2026-10-31 | PASS | 7 |
| 123d4b1e | 2026-10-31 | PASS | 8 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | blocker | arm_1 | final review | resolved | 53 | 3: arm, body, top_plate | The stack holes (15.25, 15.25) sit at r = 21.57 mm on the arm diagonals, inside the arm's  |
| 2 | blocker | top_plate | final review | resolved | 6 | 1: top_plate | The XT60 cradle closes both ends of the connector. The front end wall (x = -40.35 to -38.4 |
| 3 | major | body | final review | resolved | 53 | 3: arm, body, top_plate | Each arm is held against yaw only by two M3 screws in a line along the arm, 14 mm apart, i |
| 4 | major | arm_1 | final review | resolved | 53 | 3: arm, body, top_plate | Motor screws are M3 x 10 with a 7.0 mm grip, so 3.0 mm goes into the motor. That is exactl |
| 5 | major | body | final review | resolved | 53 | 3: arm, body, top_plate | The camera is unprotected in a crash. The pivot is at x = 48 and the lens sits 13.9 mm ahe |
| 6 | major | body | final review | resolved | 53 | 3: arm, body, top_plate | The body has no fea_static requirement, although it carries all four arm moments and is th |
| 7 | major | top_plate | final review | resolved | 6 | 1: top_plate | There is no provision for a video transmitter, receiver or antenna mount. The brief's anal |
| 8 | minor | arm_1 | final review | resolved | 53 | 3: arm, body, top_plate | The FEA render is inconsistent with the report. The render title says peak 13.93 MPa, but  |
| 9 | minor | arm_1 | final review | resolved | 53 | 3: arm, body, top_plate | Each arm has only one motor-wire tie slot (the loop iterates over a single x), but the BOM |
| 10 | minor | body | final review | resolved | 53 | 3: arm, body, top_plate | The top-plate post counterbores (30, +/-12) sit right against the arm edges. The 5.5 mm sc |
| 11 | minor | body | final review | resolved | 53 | 3: arm, body, top_plate | Camera M2 x 5 pivot screws pass through 3 mm of cheek plus a 0.5 mm gap, leaving about 1.5 |
| 12 | minor | arm_1 | final review | resolved | 53 | 3: arm, body, top_plate | Flight stiffness and heat are not verified. A hand calc gives the first arm bending mode a |
| 13 | major | top_plate | final review | resolved | 17 | 1: top_plate | The XT60 has no working retention, so round-1 blocker 2 is only half fixed. The plug end i |
| 14 | major | top_plate | final review | resolved | 17 | 1: top_plate | The top plate has no strength verification, although it is a structural part (ENGINEERING. |
| 15 | minor | body | final review | resolved | 50 | 2: body, top_plate | Camera screw engagement was not actually improved. The cheeks were thickened from 3 to 4 m |
| 16 | minor | body | final review | resolved | 50 | 2: body, top_plate | The lens is protected front-on but not from above. The cheek tops slope from z = 25 (x <=  |
| 17 | minor | arm_1 | final review | resolved | 17 | 1: top_plate | The yaw-key ridges (3 x 1.5 mm, 22 mm long, printed on the arm top) take side loads by ben |
| 18 | minor | top_plate | final review | resolved | 17 | 1: top_plate | The VTX screw length does not match the hardware. The fastener check sizes M2 x 12 for an  |
| 19 | minor | top_plate | final review | resolved | 17 | 1: top_plate | Wire path: the rear post pair (x = -31.5, y = +/-5, 9 mm dia with a 1 mm gap, z 7-45) stan |
| 20 | minor | body | final review | resolved | 50 | 2: body, top_plate | Assembly convenience: the stack nut pockets open on the underside, so the 4 nuts fall out  |
| 21 | minor | top_plate | final review | resolved | 17 | 1: top_plate | Not graded on mechanics here, but missing for the brief's 'Complete electronics' section,  |
| 22 | blocker | top_plate | final review | resolved | 9 | 1: top_plate | The battery strap cannot be fitted. The strap slots are 3 x 22 mm at x = +/-18. So the 20  |
| 23 | major | xt60 | final review | resolved | 9 | 1: top_plate | Engine change kerf/electrical.py connector_burst_limit: I judge this a loosened check, not |
| 24 | major | top_plate | final review | resolved | 9 | 1: top_plate | Neither antenna can reach where it is modelled or described. VTX: the catalog Foxeer Lolli |
| 25 | major | top_plate | final review | resolved | 9 | 1: top_plate | The brief's graded line 'the BOM lists every wire, connector and electrical part with a bu |
| 26 | minor | top_plate | final review | resolved | 9 | 1: top_plate | XT60 retention against unplugging is friction only. The tie now wraps under the connector, |
| 27 | minor | body | final review | resolved | 37 | 3: arm, body, top_plate | Camera field of view (estimate, Phoenix 2 at 155 deg diagonal on 4:3, roughly 124 x 93 deg |
| 28 | minor | arm_1 | final review | resolved | 9 | 1: top_plate | Phase-wire model. The runs are 18 AWG, 175 mm, 'the motor's own leads extended where neede |
| 29 | minor | top_plate | final review | resolved | 9 | 1: top_plate | Flight time is reported as 13.08 min at hover, from momentum theory with FM 0.5 and eta 0. |
| 30 | minor | top_plate | final review | resolved | 9 | 1: top_plate | Small craft issues. (1) The XT60 cradle walls run to x = -63.55 but the rear tab ends at - |
| 31 | major | stack | final review | resolved | 4 | 2: arm, body | The `power` pass depends on a Betaflight setting that the build package never tells Spence |
| 32 | minor | stack | final review | resolved | 4 | 2: arm, body | The cap's current estimate is slightly optimistic, and the comment calls it conservative.  |
| 33 | minor | top_plate | final review | resolved | 4 | 2: arm, body | The XT60 pigtail has very little room to turn. The 12 AWG leads (3.6 mm OD, catalog wire.s |
| 34 | minor | top_plate | final review | resolved | 149 | 3: arm, body, top_plate | The single battery strap sits 14.5 mm ahead of the pack's centre (band x 4.5..24.5 on a pa |
| 35 | minor | vtx_ant | final review | resolved | 4 | 2: arm, body | The antenna head (x -83.5..-72.5, y -16..-5, z 48-68) and its tube bending up past the tab |
| 36 | minor | top_plate | final review | resolved | 4 | 2: arm, body | Stale and missing numbers in the documents. DESIGN.md line 30 still reads '-> 12.6 (requir |
| 37 | minor | top_plate | final review | resolved | 21 | 2: arm, body | The 8-10 mm heat-shrink note for the XT60 pigtail is in WIRING.md, ASSEMBLY.md and DESIGN. |
| 38 | minor | top_plate | final review | accepted at PASS |  |  | Nothing positively stops the XT60 from pulling out rearward. The front stops take the plug |
| 39 | minor | body | final review | accepted at PASS |  |  | The generated ASSEMBLY.md never says to drop the 12 M3 nuts into the arm and stack nut poc |
| 40 | minor | top_plate | final review | resolved | 21 | 2: arm, body | Some DESIGN.md numbers no longer match report.json. Printed mass is given as 145 g (report |
| 41 | minor | stack | final review | resolved | 21 | 2: arm, body | Carried, now handled in the documents: the 14.22 A per motor under the cap is a central pr |
| 42 | major | body | final review | resolved | 31 |  | The motor phase wires rest on the arm screw tips. Each arm's two M3 x 14 screws seat at z  |
| 43 | minor | arm_1 | final review | resolved | 31 |  | The build documents never call for a thread-locker. The motor screws are steel into the mo |
| 44 | minor | arm_1 | final review | resolved | 31 |  | The arm prints top-up, so the M3 counterbores (motor: 3.5 mm deep; arm root: 5 mm) open on |
| 45 | major | body | final review | resolved | 3 |  | The BOM buy links are for the wrong screw lengths. bom.md row 'M3 x 12 mm socket head scre |
| 46 | minor | body | final review | resolved | 93 | 3: arm, body, top_plate | Round-6 major, now resolved. The only remaining exposure: each arm nut now sits at the bot |
| 47 | minor | body | final review | accepted at PASS |  |  | Thread engagement in the sunk nut is near the minimum. The tip is only 0.3 mm past the nut |
| 48 | minor | stack | final review | resolved | 3 |  | WIRING.md shows the camera supply at 4.988-4.99 V against the catalog's 5.0 V minimum ('sa |
| 49 | minor | body | final review | resolved | 3 |  | DESIGN.md numbers are stale after this round. It says body FEA is 9.6 MPa, but report.json |
| 50 | minor | arm_1 | final review | resolved | 93 | 3: arm, body, top_plate | Carried. The counterbore ceilings in the arms and top plate open on the bed face and print |
| 51 | minor | stack | final review | resolved | 90 | 3: arm, body, top_plate | Carried. The XT60 has no weight_g (it counts as 0 g in the mass budget), and the XING2 mot |
| 52 | minor | top_plate | final review | resolved | 90 | 3: arm, body, top_plate | New, documentation only. The new screw:M2x12:socket price entry is a third-party Walmart l |
| 53 | minor | body | final review | accepted at PASS |  |  | FEA is judged on the engine's 99.9th-percentile stress. The body passes at 10.76 MPa again |
| 54 | minor | top_plate | final review | accepted at PASS |  |  | T/W is 6.02 against a 6.0 floor, on a 161 g printed-mass estimate and a 74 % output cap. D |
| 55 | minor | body | final review | accepted at PASS |  |  | The 14.22 A per motor at the 74 % limit is a propeller-law estimate, not a firmware limit. |
| 56 | minor | arm_1 | final review | accepted at PASS |  |  | The motor-screw edge-distance warnings (88 % of the ring is material on the arm pad, 46-50 |
| 57 | minor | top_plate | final review | accepted at PASS |  |  | New since round 9 (engine check added in d3677bb): report.json warns that the bom_extra ro |
