# Diary: pan_tilt

45 problems recorded (10 open). Found at: before parts 0, rough 0, detail 0, final review 45.
Estimated active fix time 4988 min; parts redrawn: base, bracket, yoke. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| c0627290 | 2026-10-31 | FAIL | 6 |
| 7ba81224 | 2026-10-31 | PASS | 7 |
| d97ab0b2 | 2026-10-31 | FAIL | 7 |
| 6a808abf | 2026-10-31 | PASS | 7 |
| 10e312f6 | 2026-10-31 | PASS | 7 |
| f2445eeb | 2026-10-31 | FAIL | 6 |
| 852611aa | 2026-10-31 | PASS | 6 |
| 123d4b1e | 2026-10-31 | PASS | 10 |
| 43428835 | 2026-11-01 | FAIL | 10 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | blocker | yoke / bracket / base (layout.py via catalog servo_horns.aluminum_micro_21T) | final review | resolved | 14 |  | The horn does not engage the spline in the model. The catalog horn entry has hub_height 4. |
| 2 | minor | project.yaml bom_extra | final review | resolved | 14 |  | The BOM is inconsistent. bom_extra lists 'M3 x 10 SHCS + washer' for the pivot, while the  |
| 3 | minor | yoke / base | final review | resolved | 14 |  | No camera FPC or servo-lead routing. The camera FPC (~12-16 mm wide) hangs from the camera |
| 4 | minor | base | final review | resolved | 37 | 1: base | Servo pocket is only 0.3 mm per side (23.2 x 12.8 for a 22.6 x 12.2 case) and 15.6 mm deep |
| 5 | minor | yoke / bracket | final review | resolved | 14 |  | Moving clearance is thin: cam_clear min is 0.6 mm against a 0.5 mm limit and the pivot axi |
| 6 | minor | base | final review | resolved | 37 | 1: base | Tripod screw engagement depends on A2 (screw protrusion). The nut top sits 7.24 mm above t |
| 7 | minor | yoke | final review | resolved | 24 | 1: base | Pan-horn screws are M2 x 8 through the 6 mm plate, so they engage only 2.0 mm in a horn di |
| 8 | minor | bracket | final review | resolved | 24 | 1: base | Tilt horn screws are M2 x 6 through the 3.5 mm arm, giving 2.5 mm into the same estimated  |
| 9 | minor | yoke | final review | resolved | 24 | 1: base | The yoke needs support or bridging at the tilt-servo window, which has a 12.8 mm top bridg |
| 10 | minor | bracket | final review | resolved | 24 | 1: base | Slicer warning: 3.5% of the surface needs support. The cause is the teardrop and 45-degree |
| 11 | minor | pan_tilt | final review | resolved | 24 | 1: base | No electrical: block (kerf warning). Servo power and signal, the 5 V supply and bulk capac |
| 12 | major | pan_tilt | final review | resolved | 28 |  | No `electrical:` / `wiring:` block (kerf warns). ENGINEERING.md 10b says every project tha |
| 13 | minor | pan_tilt | final review | resolved | 28 |  | The cam_clear margin (bracket to yoke) is 0.9 mm against a 0.8 mm limit, which equals the  |
| 14 | minor | pan_servo/tilt_servo/horns | final review | resolved | 97 | 1: base | The 21T aluminium horn bolt circle (12 mm), M2 thread and 4 mm hub depth are catalog ESTIM |
| 15 | minor | bracket/yoke | final review | resolved | 97 | 1: base | The pivot axial gap is 0.9 mm against a 0.8 mm cam_clear requirement, so only 0.1 mm of ma |
| 16 | minor | wiring (project.yaml) | final review | resolved | 97 | 1: base | The WIRING steps say to cut and solder jack -> servo. An SG90 ships with its own 3-pin JR  |
| 17 | minor | electrics | final review | resolved | 97 | 1: base | The Pi's 3.3 V GPIO drives the SG90 signal pin directly. This usually works, but there is  |
| 18 | minor | bracket | final review | resolved | 116 | 3: base, bracket, yoke | 3.5% of the surface is flagged as needing support: the 45-degree and teardrop faces, plus  |
| 19 | minor | base/yoke | final review | resolved | 97 | 1: base | Load axis Z runs across layers on all three parts. FEA proves SF 3 against the Z strength  |
| 20 | minor | BOM | final review | resolved | 97 | 1: base | Several items are unpriced (servos, PSU, jack, Pi, camera, FPC, capacitor, USB supply). Th |
| 21 | major | base | final review | resolved | 19 |  | Zero vertical clearance for the slide-in pan servo. The servo bottom sits at servo_floor_z |
| 22 | minor | yoke | final review | resolved | 19 |  | The 30 N knock at the camera was added to base_fea (F15), but the yoke has only the 5 N pi |
| 23 | minor | DESIGN.md | final review | resolved | 19 |  | Numbers have gone stale after the rework. DESIGN.md says 59.3 g complete and printed masse |
| 24 | minor | base | final review | resolved | 19 |  | The two tab-screw pilots sit about 2 mm from the deck slot edge (ring 79% material, as the |
| 25 | minor | base/bracket | final review | resolved | 19 |  | Putting in the pan servo screws is fiddly. They go up from below through 4.8 mm holes in t |
| 26 | minor | horns/servos | final review | resolved | 19 |  | The 21T horn bolt circle, thread and hub height are catalog estimates. The SG90 tab-hole a |
| 27 | minor | bracket | final review | resolved | 460 | 3: base, bracket, yoke | The generated ASSEMBLY.md puts the shoulder-screw pivot (step 8) before the tilt servo goe |
| 28 | minor | base | final review | resolved | 460 | 3: base, bracket, yoke | The pan servo is held only by two M2 self-tap pilots with 3.6 mm engagement (6 mm screw mi |
| 29 | minor | yoke | final review | resolved | 460 | 3: base, bracket, yoke | The knock cases are judged on p99.9. The local volume peaks are 22.6 MPa (knock_in, pivot- |
| 30 | minor | base | final review | resolved | 460 | 3: base, bracket, yoke | The 1/4-20 nut pocket is cut from the floor right up into the open cavity, so the nut is n |
| 31 | minor | bracket | final review | resolved | 460 | 3: base, bracket, yoke | The M3 heat-set insert hole (4.0 mm) sits in a knuckle of r 4.4 mm, leaving about 2.4 mm o |
| 32 | minor | bracket | final review | resolved | 460 | 3: base, bracket, yoke | The horn bolt circle, thread and hub height (catalog A3 estimates), the SG90 tab hole and  |
| 33 | minor | bracket | final review | resolved | 370 | 3: base, bracket, yoke | The 4 M2 clearance holes of group 'bracket_tilt' (horn screws through the +Y arm) print ho |
| 34 | minor | base | final review | open |  |  | base_fea holds the whole bottom face fixed (engine warning: the fixed box holds no fastene |
| 35 | minor | bracket | final review | resolved | 370 | 3: base, bracket, yoke | The camera M2 pilots in group 'cam_mount' have only 22 % of a 1.5 x d ring of material at  |
| 36 | minor | bracket | final review | resolved | 370 | 3: base, bracket, yoke | Catalog bd486a2 changed motion.shoulder_4_m3.buy from 97505A139 to 97505A106, the correct  |
| 37 | major | yoke | final review | open |  |  | out/ASSEMBLY.md step 6 says: fit tilt_servo onto the yoke, drive its 2 x M2 x 6 tab screws |
| 38 | minor | bracket | final review | open |  |  | The camera-rear trim box starts 0.01 mm in front of the plate face (bracket.py: `Pos(0, 0, |
| 39 | minor | bracket | final review | open |  |  | Outside edges are not broken on the bracket or most of the yoke. ENGINEERING.md s5 asks fo |
| 40 | minor | base | final review | open |  |  | The 'servo cavity: the SG90's square case and tabs slide along it' reason is right for the |
| 41 | minor | base | final review | open |  |  | DESIGN.md section 4 calls the deck legs over the cavity 'short bridges'. They are not brid |
| 42 | minor | base | final review | open |  |  | Carried forward and still open: ASSEMBLY.md never mentions the 1/4-20 nut (step 1 just say |
| 43 | minor | bracket | final review | open |  |  | Tilt-horn centre screw: the BOM says 'M2 horn centre screw, comes with the servo ... a dro |
| 44 | minor | yoke | final review | open |  |  | Carried forward: the knock cases pass on p99.9 (9.71 / 9.15 of 13 MPa), but the volume pea |
| 45 | minor | bracket | final review | open |  |  | DESIGN.md has stale numbers after this pass. Section 5 says the camera standoffs are 'r 2. |
