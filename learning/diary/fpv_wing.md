# Diary: fpv_wing

48 problems recorded (0 open). Found at: before parts 0, rough 0, detail 0, final review 48.
Estimated active fix time 1037 min; parts redrawn: elevon, hatch, horn, layout, motor_mount, nose, pod, splice, wing. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| 8a14d0b0 | 2026-11-01 | FAIL | 20 |
| e74072cf | 2026-11-02 | FAIL | 15 |
| 1463c30b | 2026-11-02 | FAIL | 10 |
| e273907f | 2026-11-02 | PASS | 9 |
| 40ade74f | 2026-11-02 | FAIL | 4 |
| 3e0923de | 2026-11-02 | PASS | 3 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | blocker | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | The pod is a closed box with one way in: the front opening (y +-30, z -62.6 to +6). Above  |
| 2 | major | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | The moment-carrying V sleeves are checked as solid PLA: the DESIGN.md hand check uses I =  |
| 3 | major | motor | final review | resolved | 36 | 7: elevon, hatch, horn... | Prop strike on every belly landing. The motor axis is at z = tail_z = -6 and the Gemfan 70 |
| 4 | major | motor | final review | resolved | 36 | 7: elevon, hatch, horn... | The twr requirement passes on thrust from a different prop. The catalog motor note gives 2 |
| 5 | major | elevon_l | final review | resolved | 36 | 7: elevon, hatch, horn... | Printability: each elevon stands 314 mm tall on a 102 mm2 foot (the build warns about it). |
| 6 | major | elevon_l | final review | resolved | 36 | 7: elevon, hatch, horn... | Control linkage (both elevons): (1) The horn hole is only about 9.7 mm from the hinge (3.5 |
| 7 | major | wing_l2 | final review | resolved | 36 | 7: elevon, hatch, horn... | The brief asks for 'bolted sections I can replace after a crash', and DESIGN.md says 'a cr |
| 8 | major | wing_l1 | final review | resolved | 36 | 7: elevon, hatch, horn... | The root heat-set inserts (2 per side) and the servo pocket are cut into a 1-wall, 3 % inf |
| 9 | major | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | Battery retention: there are no strap slots and no stops, only 'a strip of anti-slip pad', |
| 10 | major | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | No cooling path. The 60 A ESC (73 x 30 x 12, 48 A peak) and an 800 mW TX800 VTX sit in a s |
| 11 | major | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | The print package puts every part on ONE plate (plate_1.3mf) in three materials: PLA, PETG |
| 12 | minor | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | Pod print: 310 mm tall, about 300 g, on a 48 x 50 mm foot (5 mm brim). The wing centre sec |
| 13 | minor | wing_l2 | final review | resolved | 36 | 7: elevon, hatch, horn... | Outboard of the elevon (y 460-500), the TE stub is a ceiling about 30 mm deep over the ele |
| 14 | minor | fin_l | final review | resolved | 36 | 7: elevon, hatch, horn... | The TPU fin (2 walls, 15 %, E about 26 MPa) is about 130x softer than PLA. A rough estimat |
| 15 | minor | wing_l1 | final review | resolved | 36 | 7: elevon, hatch, horn... | Brief: 'TPU where it lands'. A flying wing lands on its belly, and the belly here is the 2 |
| 16 | minor | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | Wiring: the 12 AWG main lead (49.5 A peak) is routed 'over the GPS'. The QMC5883 compass i |
| 17 | minor | motor_mount | final review | resolved | 36 | 7: elevon, hatch, horn... | The mount_strength load case pulls the motor aft (+x) and says 'a nose-in crash throws the |
| 18 | minor | pod | final review | resolved | 36 | 7: elevon, hatch, horn... | Balance: req_balance puts each printed part's mass at its solid centroid. For 1-wall, 3 %  |
| 19 | minor | nose | final review | resolved | 36 | 7: elevon, hatch, horn... | The 15 mm lens hole is in a 2.4 mm wall in front of a 155 deg lens, so the window edge lim |
| 20 | minor | elevon_r | final review | resolved | 36 | 7: elevon, hatch, horn... | The TE is 1.01 mm (2 perimeters), which is fragile on a hinged surface that gets handled.  |
| 21 | major | hatch | final review | resolved | 8 | 4: elevon, hatch, pod... | The hatch (x -5 to 205, 72 mm wide, 1.7 mm PLA) is held only at its ends: 2 x M3 at x 4 an |
| 22 | major | hatch | final review | resolved | 8 | 4: elevon, hatch, pod... | The hatch's rear tongue covers the VTX antenna's exit hole. The tongue spans x 204-213 and |
| 23 | major | wing_l1 | final review | resolved | 3 | 2: elevon, wing | At one end of the elevon throw the pushrod hits the servo pocket's aft edge. The servo poc |
| 24 | major | elevon_lo | final review | resolved | 3 | 2: elevon, wing | The outer elevon halves (60 % of the surface, the outboard and most flutter-prone part) ar |
| 25 | major | pod | final review | resolved | 8 | 4: elevon, hatch, pod... | Plates are now one material each (fixed), but plate_2.3mf puts every PLA part in one job:  |
| 26 | minor | pod | final review | resolved | 8 | 4: elevon, hatch, pod... | The ESC (73 mm long) cannot drop in from above. Between the sleeves the gap is only about  |
| 27 | minor | pod | final review | resolved | 8 | 4: elevon, hatch, pod... | Battery swap: the pack is reached only with the nose off (4 x M3 x 16 into inserts, every  |
| 28 | minor | pod | final review | resolved | 8 | 4: elevon, hatch, pod... | Mass margin is thin: TWR 1.54 against 1.5 allows only about 33 g of growth (1389 g). The 1 |
| 29 | minor | pod | final review | resolved | 8 | 4: elevon, hatch, pod... | 26 inside corners are still sharp: 16 are declared (fillet would face down), 10 are not (v |
| 30 | minor | hatch | final review | resolved | 8 | 4: elevon, hatch, pod... | The hatch prints standing on its 1.7 mm edge (363 mm2 contact, flagged by the build), 218  |
| 31 | minor | splice_l | final review | resolved | 104 | 6: elevon, hatch, motor_mount... | The splice plate is a 30 x 50 mm block standing about 3.5-5 mm proud of the lower skin, wi |
| 32 | minor | pod | final review | resolved | 8 | 4: elevon, hatch, pod... | Still open from the last review: there is no TPU belly skid (brief: 'TPU where it lands';  |
| 33 | minor | motor_mount | final review | resolved | 3 | 2: elevon, wing | Stale or inconsistent documents. The mount_strength 'why' in project.yaml still describes  |
| 34 | minor | wing_l1 | final review | resolved | 3 | 2: elevon, wing | The 100 % modifiers are now in project.yaml and PRINT_SETTINGS.md (fixed in substance), bu |
| 35 | major | wing_l1 | final review | resolved | 11 | 2: elevon, motor_mount | The fixes depend on things the builder must do, and the build outputs never tell them. (a) |
| 36 | minor | elevon_lo | final review | accepted at PASS |  |  | The aft joiner bore leaves only about 0.80-0.85 mm of PLA each side. I sliced out/parts/el |
| 37 | minor | wing_l1 | final review | resolved | 11 | 2: elevon, motor_mount | Plate 3 still holds every tall, slender PLA part: 4 wing segments 220-230 mm tall on 1 wal |
| 38 | minor | hatch | final review | resolved | 11 | 2: elevon, motor_mount | Printed outer face down, only the flat centre band touches the bed. The rounded side edges |
| 39 | minor | wing_l1 | final review | resolved | 11 | 2: elevon, motor_mount | The pushrod is still not modelled. Its clearance through the new slot (about 0.5 mm at ful |
| 40 | minor | pod | final review | resolved | 11 | 2: elevon, motor_mount | DESIGN.md 'CG and balance' tells the builder to set the CG '10-13 % MAC ahead of the neutr |
| 41 | minor | motor_mount | final review | resolved | 11 | 2: elevon, motor_mount | The plate's outer edges still have no edge break, and report.maker_notes is still empty. T |
| 42 | minor | pod | final review | resolved | 5 | 2: elevon, splice | ASSEMBLY.md step order contradicts its own notes. Step 21 fits the battery 'held by the st |
| 43 | minor | wing_l1 | final review | resolved | 5 | 2: elevon, splice | Formatting slip in the new engine output. The item_notes writer splits assembly_note at it |
| 44 | minor | hatch | final review | resolved | 5 | 2: elevon, splice | Carried over: 8.3 % of the surface needs support (the tongue and the rounded edges lift of |
| 45 | blocker | splice_l | final review | resolved | 24 |  | splice_l and splice_r have no M3 clearance holes. Evidence: out/parts/splice_l.stl and spl |
| 46 | minor | wing_l1 | final review | resolved | 24 |  | The new epoxy step (wing_l1/r1 assembly_note) says to butter the tube, slide the segment b |
| 47 | minor | pod | final review | accepted at PASS |  |  | Still open (tracked as its own PLAN item, not new): no TPU belly skid; consumables missing |
| 48 | minor | wing_l1 | final review | accepted at PASS |  |  | The new note (wing_l1/r1 assembly_note, ASSEMBLY.md lines 66-74) has the right idea: the p |
