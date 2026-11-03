# Diary: servo_link

51 problems recorded (0 open). Found at: before parts 0, rough 33, detail 0, final review 18.
Estimated active fix time 2396 min; parts redrawn: arm, base, bracket, layout. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| 48b367ea | 2026-10-30 | FAIL | 11 |
| 1b846f6e | 2026-10-30 | FAIL | 8 |
| 23a30b61 | 2026-10-30 | PASS | 5 |
| 4cbe662b | 2026-10-30 | PASS | 3 |
| bc24372d | 2026-10-30 | PASS | 3 |
| 0450e8b5 | 2026-10-30 | PASS | 6 |
| b99dc7b9 | 2026-10-31 | PASS | 5 |
| 35c8a101 | 2026-10-31 | PASS | 4 |
| d2573c9f | 2026-10-31 | PASS | 4 |
| 21ae8dc0 | 2026-10-31 | PASS | 4 |
| e519768e | 2026-11-01 | PASS | 10 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | major | arm | rough | resolved | 26 | 3: base, bracket, layout | No way to attach the payload at the tip. DESIGN.md and requirement arm_torque are built ar |
| 2 | minor | bracket | rough | resolved | 26 | 3: base, bracket, layout | The servo tab hole pattern (49.5 x 10 mm, 4.2 mm holes) is marked UNVERIFIED in the catalo |
| 3 | minor | bracket | rough | resolved | 26 | 3: base, bracket, layout | The tab screws are sized for bare tabs: tab_t 2.5 mm plus M3x8 gives 5.5 mm of thread in t |
| 4 | minor | bracket | rough | resolved | 26 | 3: base, bracket, layout | Only 2.1 mm of plastic separates each tab-screw insert hole from the servo window: the hol |
| 5 | minor | bracket | rough | resolved | 26 | 3: base, bracket, layout | When printed on its back, the foot stands vertical, so the 4 M3 clearance holes in the foo |
| 6 | minor | bracket | rough | resolved | 26 | 3: base, bracket, layout | Inside corners on the load path have no fillets, contrary to ENGINEERING section 5: where  |
| 7 | minor | bracket | rough | resolved | 26 | 3: base, bracket, layout | The bracket_fea load case understates the load and uses a lower safety factor than the rul |
| 8 | minor | arm | rough | resolved | 26 | 3: base, bracket, layout | ENGINEERING section 8 calls for a second support for the servo output when the link is lon |
| 9 | minor | horn | rough | resolved | 26 | 3: base, bracket, layout | The arm screws (M3x8 through the 6 mm arm) engage only the 2 mm aluminium horn disc, about |
| 10 | minor | base | rough | resolved | 26 | 3: base, bracket, layout | The rig must be screwed down. Unclamped, it resists tipping about a base edge with only ab |
| 11 | minor | bracket | rough | resolved | 26 | 3: base, bracket, layout | Nothing is provided for the servo cable. Its exit position on the case is not in the catal |
| 12 | blocker | bracket | rough | resolved | 9 |  | The servo cannot be fitted. bracket.py puts the tabs on the wall's front face, so the 26.6 |
| 13 | minor | arm | rough | resolved | 9 |  | The tip hole fixes the earlier major finding: a 3.5 mm hole at (0, -arm_len) with 5.25 mm  |
| 14 | minor | bracket | rough | resolved | 9 |  | The tab hole pattern (49.5 x 10 mm, 4.2 mm) is still marked UNVERIFIED in the catalog. The |
| 15 | minor | bracket | rough | resolved | 9 |  | The tab screws are now thread-forming M3 screws in 2.72 mm pilot holes, confirmed 7.2 mm d |
| 16 | minor | arm | rough | resolved | 9 |  | The arm carries the payload but has no fea_static requirement, which ENGINEERING section 3 |
| 17 | minor | bracket | rough | resolved | 9 |  | bracket.py wraps the gusset-root fillet in try/except and appends to ctx.notes, with the c |
| 18 | minor | bracket | rough | resolved | 9 |  | The docs are stale after the switch to pilot holes. The bracket.py module docstring still  |
| 19 | minor | servo | rough | resolved | 9 |  | The catalog source datasheet says the MG996R rotates 'approximately 120 degrees (60 in eac |
| 20 | minor | bracket | rough | resolved | 44 | 1: arm | Hex-key access to the two tab screws on the cable end (x = +24.75, z = 78 and 88). These s |
| 21 | minor | bracket | rough | resolved | 44 | 1: arm | The servo window has only 0.3 mm clearance per side, and the servo enters it from the back |
| 22 | minor | engine | rough | resolved | 44 | 1: arm | Three engine changes from this round have no test in tests/, which CLAUDE.md requires: (1) |
| 23 | minor | bracket | rough | resolved | 44 | 1: arm | Carried over: the tab hole pattern (49.5 x 10 mm, 4.2 mm) is still marked UNVERIFIED in th |
| 24 | minor | arm | rough | resolved | 44 | 1: arm | The comment in arm.py still says 'an M3 screw carries the 50 g weight', but DESIGN.md and  |
| 25 | minor | engine | rough | resolved | 96 |  | Still open from the last review (engine half): nothing in the engine checks assembly acces |
| 26 | minor | bracket | rough | resolved | 6 |  | New: the lead-in chamfer thins the wall between the window and the tab pilot holes at the  |
| 27 | minor | bracket | rough | resolved | 90 |  | New: DESIGN.md describes the old numbers. Sizing says '2.72 mm pilot holes', but the built |
| 28 | minor | bracket | rough | resolved | 48 | 2: base, bracket | DESIGN.md and project.yaml still quote the replaced catalog values. DESIGN.md line 29 says |
| 29 | minor | servo | rough | resolved | 48 | 2: base, bracket | The keyhole slots make the washers load-bearing, not optional. A DIN 125 M3 washer (7 mm O |
| 30 | minor | engine | rough | resolved | 48 | 2: base, bracket | The servo's insertion path can't be proven by kerf check. access.insertion_paths moves the |
| 31 | minor | horn | rough | resolved | 48 | 2: base, bracket | The horn proxy seats the hub bottom on top of the 6.3 mm spline, but a real 25T horn slide |
| 32 | minor | catalog | rough | resolved | 48 | 2: base, bracket | The servos.MG996R note is dated '2026-10-31', a day after this review. tab_z is still mark |
| 33 | minor | engine | rough | resolved | 48 | 2: base, bracket | The FEA pictures show a different peak from report.json. fea_bracket_fea.png says 0.65 MPa |
| 34 | minor | engine | final review | resolved | 31 |  | The generated packages still give the wrong action words. WIRING.md and the Electrical sec |
| 35 | minor | engine | final review | resolved | 31 |  | Nothing checks voltage drop. Checked as AWG 24, the adapter cord drops about 0.42 V at the |
| 36 | minor | bracket | final review | accepted at PASS |  |  | tab_z is still unconfirmed (26.5-30.2). At 30.2 the 20 mm horn disc sits 0.5 mm inside the |
| 37 | minor | servo | final review | resolved | 189 |  | The two tab screws next to the cable boss need a ball-end driver. It is documented and now |
| 38 | minor | project | final review | resolved | 31 |  | Some BOM rows have no buy link or price: the mains cord, the Mini-B cable, the header, the |
| 39 | minor | project | final review | resolved | 4 |  | The generated ASSEMBLY.md fits the electrics last (step 6, after the horn at step 4). The  |
| 40 | minor | catalog | final review | resolved | 528 | 1: bracket | The adapter's DC cord gauge is still assumed (now AWG 22, the thinnest gauge whose chassis |
| 41 | minor | project | final review | resolved | 153 |  | out/report.json (written 03:09:43) is newer than the build outputs (bom.md 03:09:00, rende |
| 42 | minor | jack | final review | resolved | 371 | 1: bracket | The catalog entry electronics.connectors.dc_jack_5521_screw has no weight_g (kerf warning) |
| 43 | minor | bracket / arm | final review | accepted at PASS |  |  | The servo tab pilot holes and the arm's horn holes are under the 1.5 d edge distance (88 % |
| 44 | minor | bracket | final review | accepted at PASS |  |  | DESIGN.md 'Load -> section' says the bracket's moment peaks at 'wall bending at its root o |
| 45 | minor | bracket | final review | accepted at PASS |  |  | The overbuilt justification has the right conclusion but wrong support. (a) It says 'the 8 |
| 46 | minor | bracket | final review | accepted at PASS |  |  | Outside edges are broken only in places, so the edge language claimed in DESIGN.md ('0.6-1 |
| 47 | minor | bracket | final review | accepted at PASS |  |  | Gusset toe kept sharp (sharp_kept at [+/-40, 42.6, 6.0]). The stated reason is true: the h |
| 48 | minor | arm | final review | accepted at PASS |  |  | Constant 18 x 6 mm section from hub to tip, although the DESIGN table itself says the mome |
| 49 | minor | base | final review | accepted at PASS |  |  | A flat slab with holes. Every feature has a purpose (blind M3 inserts with a floor, which  |
| 50 | minor | bracket | final review | accepted at PASS |  |  | out/plates/PRINT_SETTINGS.md labels the bracket orientation 'on its front (-Y) face', whil |
| 51 | minor | jack / catalog | final review | accepted at PASS |  |  | Carried over: dc_jack_5521_screw has no weight_g (it sits on the desk, so no effect on rig |
