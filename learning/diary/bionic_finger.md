# Diary: bionic_finger

34 problems recorded (8 open). Found at: before parts 0, rough 0, detail 0, final review 34.
Estimated active fix time 2950 min; parts redrawn: base, distal, fingerlib, middle, proximal. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| 51c543e1 | 2026-10-31 | FAIL | 9 |
| 6168b97d | 2026-10-31 | PASS | 7 |
| ae90d5a5 | 2026-10-31 | PASS | 5 |
| 46b8032a | 2026-10-31 | PASS | 5 |
| 487e740c | 2026-10-31 | PASS | 8 |
| 259a710a | 2026-11-02 | FAIL | 8 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | blocker | base/proximal/middle/distal (fingerlib.child_end, parent_end) | final review | resolved | 37 | 1: fingerlib | No hyperextension (straight) hard stop at any joint. Child positioned at negative flexion  |
| 2 | major | fingerlib.pin_holes / all joints | final review | resolved | 37 | 1: fingerlib | The pivots are ISO 4762 M3 x 14 SHCS, which are fully threaded at that length (b = 18 mm). |
| 3 | minor | base/proximal/middle (parent knuckle band) | final review | resolved | 37 | 1: fingerlib | Over the top ~1 mm of the heat-set bore (the gap face), the swept extensor groove comes to |
| 4 | minor | fingerlib.crossing_cuts | final review | resolved | 37 | 1: fingerlib | The knuckle-face tendon grooves are a union of straight tubes at 10 deg steps. The part re |
| 5 | minor | distal | final review | resolved | 37 | 1: fingerlib | Line termination: 3 mm knot pockets behind a 2.2 mm channel. A single stopper knot in 0.5  |
| 6 | minor | all (tendon geometry) | final review | resolved | 37 | 1: fingerlib | The flexor moment arm is only 4 mm (inside the 7.5 mm knuckle disc), so tendon tension is  |
| 7 | minor | all (pin screws) | final review | resolved | 37 | 1: fingerlib | The screw heads (5.5 dia x 3 mm, on alternating sides) are not modelled as proxies, so the |
| 8 | minor | middle, distal | final review | resolved | 37 | 1: fingerlib | Wall check warns of 1.14-1.15 mm walls (below the 1.2 mm reliable minimum), at the tendon  |
| 9 | minor | proximal (FEA) | final review | resolved | 37 | 1: fingerlib | The FEA follows the brief's load case: hot spots at the pip load bore and the mcp fixed bo |
| 10 | minor | all joints (fingerlib W/GAP, shoulder length) | final review | resolved | 9 |  | Axial play per joint is now 0.45 mm: the 0.3 lap gap plus 0.15 from the 8 mm shoulder over |
| 11 | minor | base/proximal/middle (insert mouth) | final review | resolved | 9 |  | The shoulder bottoms on the insert face and the joint only has 0.15 mm of head play. An in |
| 12 | minor | DESIGN.md | final review | resolved | 9 |  | Section 2 'Side play' is stale. It still says the 7.85 mm lap faces and that the 0.3 mm ga |
| 13 | minor | bom (motion.shoulder_4_m3) | final review | resolved | 9 |  | In report.json the shoulder-screw BOM rows have an empty buy link and no price. It is the  |
| 14 | minor | proximal/middle/distal (child stop lug, fingerlib.child_end) | final review | resolved | 9 |  | In the child's top band the lug is cut by the r = RH circle. Where that circle meets the l |
| 15 | minor | out/ASSEMBLY.md, bom (generated) | final review | resolved | 18 |  | The owner-facing build sheet still has 'Tools: none', no insert heat-set step, no flush-to |
| 16 | minor | all joints | final review | resolved | 108 | 5: base, distal, fingerlib... | Side play is unchanged in geometry: 0.45 mm axial, ~1.7 deg tilt per joint, a few mm of fi |
| 17 | minor | proximal/middle/distal (child stop lug) | final review | resolved | 108 | 5: base, distal, fingerlib... | Cosmetic cusp where the pocket circle cuts the child's top-band lug (documented in DESIGN) |
| 18 | minor | out/ASSEMBLY.md step 4 (distal assembly_note) | final review | resolved | 90 | 5: base, distal, fingerlib... | Order and practicality of the tendon step. The note is nested under 'Fit distal' and says  |
| 19 | minor | base | final review | resolved | 281 | 4: base, distal, middle... | base_fea_line has a volume peak of 194 MPa and a surface peak of 61.8 MPa at [-4.3, -0.2,  |
| 20 | minor | proximal | final review | resolved | 281 | 4: base, distal, middle... | Under the 222 N line case plus the pin moment, proximal_fea_line shows 1.33 mm of deflecti |
| 21 | minor | base | final review | resolved | 281 | 4: base, distal, middle... | DESIGN s9 step 1 says an insert left proud of the boss 'eats the 0.2 mm play and clamps th |
| 22 | minor | base | final review | resolved | 281 | 4: base, distal, middle... | Tightening the shoulder screw until the shoulder bottoms preloads the screw, and that prel |
| 23 | minor | middle | final review | resolved | 281 | 4: base, distal, middle... | The p2 wall is 1.27 mm, below the 1.6 mm structural-part guideline in ENGINEERING.md s5. I |
| 24 | minor | distal | final review | resolved | 281 | 4: base, distal, middle... | Tendon threading. The swept fan grooves at each knuckle open out to the disc rim, as the p |
| 25 | minor | distal | final review | resolved | 281 | 4: base, distal, middle... | DESIGN s7 says the two stop slots are '1.6 mm apart with >= 1.6 mm skin'. From the code (r |
| 26 | minor | base | final review | resolved | 281 | 4: base, distal, middle... | BOM and ASSEMBLY ordering. The shoulder screw and the M3 insert each still appear as three |
| 27 | major | base | final review | open |  |  | All three pivots (mcp in base, pip in proximal, dip in middle; fingerlib.PIN = motion.shou |
| 28 | major | distal | final review | open |  |  | Washer line stops. The last FEA run before the pause gave distal_fea_extensor = 25.01 MPa  |
| 29 | minor | middle | final review | open |  |  | The report's '4 sharp inside corners' on middle and '2' on distal come from an engine fram |
| 30 | minor | proximal | final review | open |  |  | Stale and broken evidence in the review pack. Every out/renders/fea_*.png is from Oct 31 2 |
| 31 | minor | distal | final review | open |  |  | DESIGN.md is stale in several places since the detail pass and dd32cf9. s7 says the clear  |
| 32 | minor | base | final review | open |  |  | Tendon exits. Both lines leave the base's back face through plain 2.2 mm holes with a shar |
| 33 | minor | proximal | final review | open |  |  | Concept lever left unused. The flexor runs 4.7 mm palmar of the axes while the extensor us |
| 34 | minor | distal | final review | open |  |  | Proportions and craft. All four parts are the same 15.6 x 18 mm box section with full-roun |
