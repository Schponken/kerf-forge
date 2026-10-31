# Kerf Forge — final cross-project audit (2026-10-31)

Three independent design-reviewer subagents audited every eval project rule by rule against docs/ENGINEERING.md
(fingerprints as built at ~04:30 UTC). Their full reports are the appendices below, verbatim. This page is the
tracking index: every finding must end up **fixed** (with the commit) or **justified** (with the reason) here.

Finding IDs: `A-n` = appendix A (servo_link, tvc_drone), `B-Fn` = appendix B (fpv_5in, pan_tilt), `C-n` = appendix C
(bionic_finger, robot_arm). Engine findings from all three are merged into `ENG-n` below.

Totals: 1 blocker (A-1, tvc_drone ring_low leg inserts on the lug edge — passed both `kerf check` and its review),
about 20 project majors, 6 engine majors.

## Engine findings (merged, deduplicated)

| ID | Sev | Finding | From | Resolution |
|---|---|---|---|---|
| ENG-1 | major | No check of wall around inserts / hole edge distance (let A-1 through); wall check uses 2nd percentile so local thin walls pass | A-E1, B-E7, C-23 | open |
| ENG-2 | major | `fea_static` accepts any safety factor; nothing requires an FEA/strength proof on each structural part or resolves the across-layers warning | A-E2, C-21 | open |
| ENG-3 | major | `cg` leaves out declared wiring mass while mass / T/W include it | A-E3 | fixed: req_balance.wiring_masses at each run's route centroid per pose; also rod/tube mass from catalog density and a warning for massless purchased items (found in review) — tests test_req_balance, test_item_mass |
| ENG-4 | major | `thrust_to_weight` uses a hand-typed thrust, not derated from test voltage to nominal / sagged pack voltage | A-E4 | partly fixed: `test_v` / `pack_v` scale thrust by (V/test_V)^2 (test_twr); the thrust figure is still typed from the catalog table with its source in `why` |
| ENG-5 | major | `fea_static` bearing loads on single-shear pivots ignore the lever moment (pins.py knows which band is fixed) | C-22 | open |
| ENG-6 | major | Plate 3MFs carry no per-part infill / walls; FEA is solid vs 100%-infill strength and judged at the volume p99.9 | B-E1, B-E2 | open |
| ENG-7 | minor | Horizontal holes: no warning without teardrop; `iface.pin_hole` has no teardrop; pilot size ignores hole axis | A-E5, C-26, B-E6 | partly: `iface.print_up_deg(ctx, loc)` gives the teardrop angle from print_rot, `servo_mount(teardrop=)` added (pin_hole already had it); warning and pilot size still open |
| ENG-8 | minor | `load_axis` optional; FEA direction not cross-checked against it; warning persists after a direction-z proof | A-E8, B-E3, B-E4 | open |
| ENG-9 | minor | No check that the largest flat face is on the bed | A-E6 | open |
| ENG-10 | minor | Sweeps catch overlap only; 0.5 mm moving clearance unchecked unless opted in | A-E7 | open |
| ENG-11 | minor | FEA clamp region not tied to fastener sites; dowel bores loaded evenly instead of `bearing_n` | A-E9 | open |
| ENG-12 | minor | Wire colour optional; bundle fill not checked; no FPC (ribbon) wiring kind | A-E10, B-E8 | open |
| ENG-13 | minor | Pin span vs stocked length: doc and check disagree | A-E11 | open |
| ENG-14 | minor | Horn centre screws and pivot hardware not modelled (BOM, mass, collision, key access, tools list) | B-E5, C-24 | open |
| ENG-15 | minor | `bom_extra` unknown keys accepted silently; duplicates vs auto fasteners not flagged | B-E9, C-27 | open |
| ENG-16 | minor | Engine recommends threadlocker on screws tapped into printed plastic (pins.py, export.py, ship.py) | B-E10, C-17 | open |
| ENG-17 | minor | `electrical.limits` treats a throttle-cap estimate like a hard current limit | B-E11 | open |
| ENG-18 | minor | review-status / verify don't flag out/ docs older than the geometry or engine | B-E12, C-25 | open |
| ENG-19 | minor | ship.py "an insert left proud clamps it" is backwards for shoulder screws | C-25 | open |
| ENG-20 | minor | Missing checks: gear tooth bending at stall, tendon termination bearing stress, desk/ground plane in sweeps, servo pigtail length | C-27 | open |

## Project findings

Each project's findings are listed in its appendix section with severity and a concrete fix. Status per project:

| Project | Findings | Resolution |
|---|---|---|
| tvc_drone | A-1 (blocker), A-2..A-7 (major), A-9..A-14 (minor) | **all resolved** — design-reviewer round 3 PASS at 435d517f3a37c360 (review.json has the per-finding table); 2 minors kept: 14 gimbal_outer first-layer edges deburred by hand, leg deflection 2.97 / 3.0 mm |
| servo_link | A-8 (major), A-15..A-17 (minor) | open |
| fpv_5in | B-F1, F1b, F2, F3 (major), F4..F10 (minor) | open |
| pan_tilt | B-F11, F12 (major), F13..F18 (minor) | open |
| bionic_finger | C-1..C-3 (major), C-4..C-9 (minor) | open |
| robot_arm | C-10..C-12 (major), C-13..C-20 (minor) | fixed (see log); review round 5 PASS (5b285dd83259e4c0) |

## Resolution log
(append: `- <date> <session>: <IDs> fixed in <commit> / justified: <reason>`)
- 2026-10-31 18259c3d8c: robot_arm C-10 (base_fea, direction z, SF 3: 1.2 MPa p99.9), C-11 (SCHURTER DD11 fused +
  switched inlet in the new psu_hood, C13 cord, 5 A ATO fuse per servo, engine `fuse:` checks), C-12 (servo lead +
  extension via engine `lead:`, lead_length_mm checked; signal pins crimped into housings), C-13 (upper_arm/forearm
  stall FEA added), C-14 (free pivot holes teardrop: `iface.pin_hole` already had `teardrop`; horn clearance holes
  and insert holes stay round, a 3.4 mm hole sags < 0.2 mm), C-15 (front foot screws x = 7.5: 6.5 mm edge
  distance), C-16 (washers in BOM, M2 x 8 row removed), C-17 (threadlocker on the screw tip only, BOM note), C-18
  (software desk limit in DESIGN.md 'Use notes'; no engine desk plane — justified: the base may sit at a desk edge),
  C-19 (assembly.order + desk step), C-20 (DESIGN numbers from report) fixed in e5b8ec6..7b72d26. Engine side notes:
  ENG-20's servo pigtail length is now checked by `lead:`; ENG-7's "pin_hole has no teardrop" was already false.


---

# Appendix A

## Cross-project audit A: servo_link, tvc_drone vs docs/ENGINEERING.md (2026-10-31)

Method: read ENGINEERING.md, project.yaml, parts/*.py, DESIGN.md, out/report.json, bom.md, ASSEMBLY.md, WIRING.md and the
renders (assembly sheets, all FEA PNGs, leg and ring_low part renders). I also ran three probes (scripts in the scratchpad):
- `clr.py`: the smallest gap between moving pairs over every sweep and pose.
- `edge.py`: how much material surrounds every fastener hole at a radius of 1.5 x screw diameter, over the engagement depth.
- `lug.py` plus a wiring-CG estimate: the leg insert holes, and where the declared wire mass sits.

### servo_link: compliance

| Rule | Status | Evidence |
|---|---|---|
| 1 Requirements first | ok | DESIGN.md:8-16 table; every number is a `requirements:` entry (project.yaml:72-101) |
| 2 Materials | ok | PETG everywhere; Z strength used for the bracket (`direction: z`) |
| 3 SF table | ok | bracket SF 3 in Z (yaml:79-80); arm SF 2 in XY, not crash-exposed (yaml:90-91); torque 0.54/4.7 kg cm (report arm_torque) |
| 3b FEA | finding (minor) | Load cases are right: stall couple ±18.6 N at the tabs gives applied_moment -920 N mm about Y, and stall into an obstacle gives 9.22 N at the tip. Hot spots sit at the window corners and the hub root (fea_bracket_fea.png, fea_arm_fea.png). The bracket is clamped over its whole underside `box [[-200,-1,-1],[200,200,0.01]]` (yaml:82), not at the `base_bracket` screw sites, so uplift and prying at the foot are not modelled. Margin is about 23x, so the result stands. |
| 4 Orientation / load_axis | finding (minor) | The bracket is on its back with `load_axis: Z` in-plane, and the foot holes are teardrops (bracket.py:41). `arm` and `base` have no `load_axis` (yaml:20,22). |
| 4 Overhang / horizontal holes | ok | overhang 0 / 0.07 / 0 %; the only horizontal holes are teardrops |
| 5 Walls / fillets / chamfers | ok | wall_p02 6.4/5.0/3.4 mm; 4 mm wall-foot fillet, 1.5 mm gusset fillets, 0.6-1 mm edge chamfers |
| 6 Fits, 0.5 mm moving clearance | ok | Measured arm-to-servo 0.78 mm at swing 90 (probe). Nothing else moving comes within 1.5 mm. |
| 7 Fasteners: inserts / pilot | ok (documented deviation) | Thread-forming pilots for the servo tabs, with the reason given in DESIGN.md:24-39 |
| 7 Edge distance >= 1.5 d | finding (minor) | Servo pilot hole centres are 4.0 mm from the window edge (24.75 - 41.48/2), below 4.5 mm. The probe found 19/24 material at 1.5 d. DESIGN.md only argues the 2.4 mm wall. |
| 7 Hex-key access | ok | 2 ball-end warnings; ball-end driver in bom_extra (yaml:42) and in ASSEMBLY step 3 |
| 8 Joint range / sweep | ok | swing ±90, 13 samples, clear |
| 8 Servo side load (> 60 mm link) | ok (documented deviation) | DESIGN.md:43-45 |
| 10 Torque <= 50 % stall | ok | 0.54 vs 4.7 kg cm |
| 10 tip_over or bolt-down | **finding (major)** | No `tip_over` requirement. DESIGN.md:102-103 says the base must be screwed or clamped down because unclamped it resists only 0.12 N m against 0.92 N m of stall. The 4 x M4 bench screws are not in bom.md and ASSEMBLY.md has no bolt-down step. |
| 10b Electrical system | ok | psu, jack, Nano, header, mains cord and USB cable are all in the BOM. power_budget worst is 0.417. Voltage drop is 4.872 V average against 4.8 V; the peak sag to 4.568 V is reported. |
| 10b Wiring cut >= routed + 15 % | ok | 250 ≥ 238.7, 240 ≥ 234.8, 110 ≥ 102.1 |
| 10b connector_access | ok | plug_access and usb_access both clear |
| 10b DESIGN consistency | finding (minor) | DESIGN.md:74-76 says "Not checked by Kerf yet: voltage drop". power_budget now checks it (WIRING.md ratings rows). |
| 11 Assembly order | ok | DESIGN.md:82-99 matches `assembly.order` |
| 11 Mass budget within 10 % | finding (minor) | DESIGN.md has only the 250 g limit, no budget table. Its sizing uses arm 7.7 g; the report gives 9.2 g (19 % off). |
| BOM completeness | finding (major, same as rule 10 row) | Missing 4 x M4 bench screws (or clamps). Otherwise complete: 4 x M3x10, 8 x M3x8, 4 inserts, 4 washers, wires, heat-shrink, header. |

### tvc_drone: compliance

| Rule | Status | Evidence |
|---|---|---|
| 1 Requirements first | ok | DESIGN.md:7-20; all present as requirements |
| 2 Materials | ok | PETG. Z strength is used for ring_low (catalog z = 39 MPa). |
| 3 SF, static across layers = 3.0 | **finding (major)** | `yoke_fea` uses `direction: z` with `sf: 2.0` (yaml:195-196); the table requires 3.0. It still passes at SF 3 (3.43 vs 13.0 MPa). |
| 3 SF, crash-exposed (legs, "arms") = 3.0 | **finding (major)** | `leg_fea` uses sf 2.0 (yaml:209) on a landing case. The case is computed for **600 g**, but the report gives a **729 g** all-up mass (yaml:207). The correct case is 729 x 3 x 9.81 / 2 = 10.7 N up and 5.4 N sideways. Scaled, that is about 3.25 MPa vs 16 MPa and about 2.5 mm deflection vs the 3 mm limit, so it still passes. `gimbal_fea` and `outer_fea` (the drone's "arm" thrust path, §9) also use sf 2 (pass at 3: 3.66 and 3.16 vs 16). |
| 3 T/W >= 2.0 multirotor | **finding (major)** | `twr` limit is 1.8 (yaml:155) and the value is 2.31. That value uses 1685 g measured at **24.0 V** (catalog note). Thrust goes with V², so at 22.2 V nominal it is 0.856 x 1683 = 1440 g, T/W 1.98 (below the §3 2.0). At about 21 V under a 36 A load it is 0.766, about 1290 g, T/W 1.77 (below even the 1.8 requirement). |
| 3b FEA load placement | finding (minor) | Hot spots match the load paths: hub arm roots, ring at the servo pad, yoke bridges and webs, leg root (all four FEA PNGs). Departures from the rule: (a) the pin bores in outer_fea and yoke_fea are loaded with `force_n` on a full `cylinder` (yaml:190, 203), not `bearing_n` as §3b requires; (b) leg_fea clamps the whole pad top (yaml:211), not the 2 `leg` screw sites, so pad prying and insert pull-out are not modelled; (c) the landing reaction into ring_low's leg lugs is not analysed at all (yoke_fea has only thrust loads). |
| 3b CG | **finding (major)** | cg_axis reports 0.48 mm lateral on **667 g**, which leaves out the 62 g of declared wiring. mass and twr do count the wiring (729 g). The wire runs are mostly on +X/+Y (ESC leads and servo leads down the +X yoke). Weighting each run by its routed centroid moves the home CG to (3.46, 1.72), **3.86 mm lateral, over the 3 mm limit**. |
| 4 load_axis declared | finding (minor) | Missing on motor_plate, ring_mid, ring_top (yaml:29-31). ring_low (z, 90°) is acknowledged and proven with FEA in Z. |
| 4 Largest flat face on the bed | **finding (major)** | Several parts float above the bed because a protrusion is lower than the main face, so the main face prints on supports: |
| | | - **leg**: the pad is 34 mm wide, the strut only 14 mm (leg.py:13-16). Printed on its side, the whole strut and foot are 10 mm above the bed; 19.7 % of the surface needs support (part_leg_1_sheet.png). |
| | | - **motor_hub**: the fork, lug and arms reach z -7/-9 but the disc bottom is at z 0 (motor_hub.py:25-28). The plate mating face, motor counterbores and insert holes all print on supports (23.9 %). |
| | | - **gimbal_outer**: the pads are ±10 high but the ring is ±8 (gimbal_outer.py:16-24), so the annulus is 2 mm up (18.4 %). Its docstring says "ring plane on the bed". |
| | | - **ring_low**: 16.7 % support. |
| 4 Horizontal holes | **finding (major)** | No teardrop anywhere in tvc_drone. All 4 dowel pin holes are horizontal in print (ring_low -X plate press fit, gimbal_outer ±X/−Y, motor_hub −Y free fit). So are the M2 servo tap holes in the yoke and ring pad, the horn screw holes, the leg clearance holes and 9 radial lock taps. The ±0.05 / +0.35 pin fits will print oval, which risks a tight or sloppy gimbal pivot. |
| 5 Wall >= 2.4 around inserts | **BLOCKER** | ring_low leg lugs are `Box(leg_r0+12, 22, t)`, edges at ±11 (ring_low.py:22). The leg heat-set holes are at tangential ±11 (ring_low.py:68). **All 6 insert centres sit on the lug edge**: the probe found 19/36 points of a 2.3-5 mm ring inside material, i.e. half-holes. The notches are visible in part_ring_low_top.png. The inserts cannot be seated or loaded. kerf check and the per-project review both missed this. |
| 5 Inside-corner fillets / edge chamfers | finding (minor) | The leg pad-to-strut root has no fillet, and that is the FEA hot spot (fea_leg_fea.png). The hub arm and fork roots, gimbal_outer pads and ring_low gussets also have no fillets. No outside-edge chamfers on any tvc part. |
| 6 Moving clearance >= 0.5 mm | ok | Measured over every sweep and corner: gimbal_outer–servo_roll 0.84, motor_hub–servo_pitch 0.84, outer–hub 0.98, outer–ring_low 1.0 mm. |
| 7 Edge distance / boss | finding (blocker above) | Leg inserts as above. The MG90S tab taps see the window inside 1.5 d (19/24); everything else is ok. |
| 7 Inserts vs thread-forming | finding (major, see 9) | The stack is thread-formed M2 into ring_mid. The ring_mid docstring says "heat-set inserts" (ring_mid.py:2-3); the code uses `kind="tap"` (ring_mid.py:37). |
| 7 Hex-key access | ok, minor BOM gap | pitch_horn needs a 1.5 mm ball-end key (warning; DESIGN step 6). There is no ball-end tool row in the BOM (servo_link has one). |
| 8 Pins | ok / minor | Pin 20 mm in spans of 21.5 and 21 mm. The engine accepts this; §8 says "make the knuckle span equal one". |
| 8 Servo carries torque only | finding (minor) | DESIGN.md:28-29 says the dowel makes "the spline only carry torque". With a dowel on one side and the servo on the other, the servo output still carries half the thrust radially. outer_fea loads 33 N at the ring_servo sites, which is that same path. That is 8.3 N per MG90S at the 80 % cap. Correct the claim. |
| 9 Prop clearance | ok | 5.34 mm ≥ 3; discs 65 mm apart |
| 9 Motor screw depth | ok, doc minor | M3x5 with 3 mm grip gives 2.0 mm engagement (catalog min 2.0, max 3.0). DESIGN.md:92,127 still says "M3 x 6". |
| 9 Stack soft-mount | **finding (major)** | The catalog drone.stacks.fc_20 note says "3.5 mm holes accept ... silicone grommets; M2 with grommets is the usual choice". The stack is hard-mounted with M2 x 18 thread-formed into ring_mid; there are no grommets in the BOM. |
| 9 Battery strap / pad | ok | ring_top strap slots, 70 x 38 pad |
| 10 tip_over | ok | 20.4° (DESIGN says 20.9, and "136 mm" for CG height vs report 142: stale, minor) |
| 10b Electrical system | ok / minor | FC, ESC, receiver with antenna, UBEC, XT60, strap and pad are catalog items. power_budget worst is 0.61 and burst temperature rises are ≤ 15.7 K. The capacitor is a bom_extra without catalog entry or source, which §10b does not allow. |
| 10b Wiring declaration | finding (minor) | `ph_top`, `ph_bottom`, `bat_lead` have no colour (WIRING.md rows); §10b asks for one. Cut lengths are all ≥ routed + 15 %. |
| 10b connector_access | ok | XT60 and USB-C clear |
| 10b flight_time | ok | 4.46 min |
| 11 channel_clear | n.a. / minor | No enclosed channels declared. The ring_mid 6 x 12 wire pass carries about 11 conductors, a fill of about 35 %. Bundle fill is not checked. |
| 11 Assembly order | ok | DESIGN.md:121-137 with `assembly.order` and `key_access` |
| 11 Mass budget | ok | 730 vs 729.2 g |
| BOM completeness | finding (major) | Missing stack grommets / nylon standoffs, and a 1.5 mm ball-end driver. The capacitor has no source. The "M3 x 6 mm set screw / short screw" line is ambiguous. Screws, inserts, pins, wires and heat-shrink counts match the fastener report. |
| Misc docs | minor | DESIGN step 2 says "4 x M2" for one MG90S; it has 2 tab holes (4 total). The mass req `why` says "keep T/W well above 3" but the actual is 2.31. |

### Findings

| # | Sev | Project | Part | Issue | Fix |
|---|---|---|---|---|---|
| 1 | blocker | tvc_drone | ring_low | All 6 leg heat-set insert holes are centred on the 22 mm lug's edge (lug ±11, holes at ±11; ring_low.py:22,68). They are half-holes with no wall (§5 needs ≥ 2.4 mm around inserts; §7 edge distance). | Widen the lug to ≥ 34 mm (match the leg pad), i.e. `Box(p.leg_r0 + 12, 34, t)`, giving ≥ 6 mm to each insert centre. Re-run the leg/lug FEA. |
| 2 | major | tvc_drone | battery / wiring (cg_axis) | With the 62 g of declared wiring included, the CG is about 3.9 mm off axis (limit 3). The check runs on 667 g; mass and twr use 729 g. | Re-trim `batt_dx`/`batt_dy`: about -13 mm more in X and -6 mm in Y (`batt_dx` is already at its -15 limit), or move part of the ESC lead run to -X. Re-check once the engine counts wire mass (E3). |
| 3 | major | tvc_drone | twr | T/W uses the 24.0 V test thrust. At 22.2 V nominal it is about 1.98 (below §3's 2.0); with load sag to about 21 V it is about 1.77 (below the 1.8 requirement). | Derate thrust by (V/24)² at nominal and loaded voltage. Raise the limit to the §3 2.0, or recover thrust: lift MOT_SPIN_MAX with an XT60-safe current split, use higher-pitch props, or cut mass (legs and hub on supports, see 6). |
| 4 | major | tvc_drone | ring_low, leg_1..3, motor_hub, gimbal_outer | Safety factors are below the §3 table: yoke_fea is Z-direction at sf 2 (needs 3); leg_fea is crash at sf 2 (needs 3) and uses 600 g instead of 729 g; gimbal_fea and outer_fea (2 x thrust, "arms") use sf 2 (needs 3). All would still pass at the correct values. | Set sf 3.0 on all four, set leg loads to [0, 5.4, 10.7] N, re-run. |
| 5 | major | tvc_drone | ring_low, gimbal_outer, motor_hub | Horizontal pivot pin holes (press and free fits) and other horizontal holes have no teardrop or +0.2 mm (§4). Pivot fits will print oval, so the gimbal may bind or be sloppy. | Pass `teardrop=` to `pin_hole`, `servo_mount`, `horn_mount` and `bolt_pattern`, with the print-up direction, on every horizontal hole. Print a pin fit coupon (`kerf calibrate`). |
| 6 | major | tvc_drone | leg_1..3, motor_hub, gimbal_outer | The largest flat face is not on the bed (§4): small protrusions lift the main face 10 / 9 / 2 mm, so the strut, the hub mating face with its counterbores and insert holes, and the ring underside all print on supports. | leg: make the strut as deep as the pad (34 mm in Y, or taper it from 34 to 14 toward the foot), or make one strut side face coplanar with a pad side face, so the whole profile lies on the bed. motor_hub: flush the fork, lug and arms to the disc bottom or top and print with that face down. gimbal_outer: make the pads the same height as the ring (ring_h 20) or trim the pads to ±8. |
| 7 | major | tvc_drone | ring_mid / stack | The FC/ESC stack is hard-mounted with thread-formed M2 although the catalog lists grommets (§9). No grommets in the BOM. | Use the stack's silicone grommets (M2 through 3.5 mm holes). Put M2 heat-set inserts or a nut trap in ring_mid. Add the grommets to bom_extra / the catalog, and recheck stack height and screw length. |
| 8 | major | servo_link | base | No `tip_over` requirement. DESIGN relies on screwing the base to the bench (stall 0.92 N m vs 0.12 N m resisting), but the 4 M4 bench screws are not in the BOM and there is no bolt-down step in ASSEMBLY.md (§10). | Add 4 x M4 wood or machine screws (or 2 bench clamps) to bom_extra, with an assembly_note on base, or add a `tip_over` requirement at the stall case. |
| 9 | minor | tvc_drone | ring_low | The landing load path (leg → 2 inserts in the 8 mm lug, pulled across layers) has no FEA. leg_fea clamps the whole pad face instead of the screw sites. | Add a landing load case on ring_low (fixed at the tube bores, `sites: leg` loads), and fix leg_fea at `{sites: leg}`. |
| 10 | minor | tvc_drone | gimbal_outer, ring_low | Pin bores in outer_fea and yoke_fea are loaded with `force_n` on a full cylinder; §3b requires `bearing_n`. | Use `bearing_n: [0, 0, 33.05]` on those cylinders. |
| 11 | minor | tvc_drone | leg, motor_hub, gimbal_outer, ring_low | No fillet at load-path inside corners (the leg root is the FEA hot spot); no outside-edge chamfers (§5). | Add 2 mm fillets at the leg root and hub arm and fork roots, 1.5 mm at the pad roots, and 0.6 mm edge chamfers. |
| 12 | minor | tvc_drone | DESIGN.md | Stale or incorrect text: M3x6 vs the M3x5 that was picked; "4 x M2" per MG90S (2 holes); tip_over 20.9 vs 20.4; CG 136 vs 142 mm; the "spline only carries torque" claim (the servo carries half the thrust radially); the ring_mid docstring says inserts; the gimbal_outer docstring says "ring plane on the bed"; the mass why says "T/W well above 3". | Update to match report.json and the code. |
| 13 | minor | tvc_drone | wiring / BOM | ph_top, ph_bottom, bat_lead have no colour (§10b). The capacitor is not a catalog item with a source. There is no 1.5 mm ball-end driver in the BOM. The set screw line is ambiguous. | Add colours, add a catalog entry for the capacitor with its source, add a tool row, and specify "M3 x 6 cup-point set screw ISO 4029" (or nylon-tip). |
| 14 | minor | tvc_drone | motor_plate, ring_mid, ring_top | No `load_axis` (§4). | Declare one (z for the plates). |
| 15 | minor | servo_link | bracket | Servo pilot hole centres are 4.0 mm from the window edge, under the §7 1.5 d = 4.5 mm (set by the MG996R hole pattern). bracket_fea is clamped over the whole underside, not the base_bracket sites. | Record the edge-distance deviation in DESIGN.md. Change `fixed` to `{sites: base_bracket, radius: 3}` plus the foot contact. |
| 16 | minor | servo_link | arm, base | No `load_axis` (§4). | arm: `load_axis: y`; base: `z` or a list. |
| 17 | minor | servo_link | DESIGN.md | "Not checked by Kerf yet: voltage drop" is stale (power_budget now reports a 4.568 V peak sag). There is no mass budget table, and arm 7.7 g vs 9.2 g in the report (§11). | Update the Electrics bullet and add a mass table from report.json. |

### ENGINE findings (would recur in the next project)

| # | Sev | Issue | Fix |
|---|---|---|---|
| E1 | major | Nothing checks material around a hole: insert wall (§5 ≥ 2.4 / catalog fdm_holes) or edge distance (§7 1.5 d). tvc ring_low's half-hole inserts passed check, build and review. | In `assembly.fasteners()` (or a new `kerf/holewall.py`), sample the receiving and clearance parts on a ring of r = hole_r + min_wall over the engaged depth. Fail below about 95 % solid; warn below 1.5 d coverage. Allow a per-group `edge_ok: why`. Add a test with a hole on a plate edge. |
| E2 | major | `fea_static` takes any `sf` (requirements.py:244). There is no floor of 3.0 for `direction: z` and no crash or landing case, so §3 can be undercut silently (tvc has 4 such cases). | Enforce sf ≥ 3 when direction is z, and add `case: crash` (sf ≥ 3). Fail otherwise, or require a `why_sf` override. |
| E3 | major | `cg` (req_balance) leaves out declared wiring mass; `mass_max` and `thrust_to_weight` include it (requirements.py:129). | Add each run's mass at its routed polyline centroid per pose (the {item, at} points move with the gimbal). |
| E4 | major | `thrust_to_weight` uses a hand-typed `thrust_g_total`. There is no link to catalog thrust, test voltage, motor_output limit or pack voltage, so a full-charge 24 V number passes. | Compute it from catalog `thrust_g_max` at its test voltage, scaled by (V_nominal/V_test)² and by the configured output limit, with an optional coax factor. Report full, nominal and sagged values. |
| E5 | minor | No warning for horizontal holes without a teardrop (§4). iface knows each hole axis and print_rot is known. | Record each iface hole axis. When it is within 30° of the bed plane and no teardrop was given, warn, and fail for pin holes or press fits. |
| E6 | minor | First-layer check is missing. The generic "x % needs support" warning does not say the main face is lifted off the bed (tvc legs 10 mm, hub 9 mm, ring 2 mm). | Warn when the bed-contact area is much smaller than the part's largest planar face, or when the lowest face is not its largest. |
| E7 | minor | Sweeps only test overlap > 0.05 mm³, so the §6 0.5 mm moving clearance is not checked unless a project adds `clearance_min`. | Inside `sweeps()`, report the minimum distance for moving pairs (screened by bounding box) and warn below 0.5 mm. |
| E8 | minor | `load_axis` is optional with no warning, even on parts with `fea_static`. FEA `direction` is not cross-checked against print_rot and load_axis. | Warn when a part with fea_static or cantilever_stress has no load_axis. Warn when `direction: xy` is used and the load_axis is more than 30° out of the bed. |
| E9 | minor | The FEA `fixed` region is not tied to fastener groups, and pin bores loaded with `force_n` are not flagged (§3b). | Warn when `fixed` is a box not containing any fastener site of the part, or when a cylinder load matches a pin_hole or bearing seat but uses force_n. |
| E10 | minor | `wiring` colour is optional (§10b says required), and bundle fill through wire passes is not checked. | Require `color` unless `supplied`. Optionally sum the conductor areas per `channel_clear`. |
| E11 | minor | Pin length check accepts L ≤ span (pins.py:149); §8 says the span should equal a stocked length. | Align the doc, or warn when span - L > 1 mm. |


---

# Appendix B

## Cross-project audit B: fpv_5in and pan_tilt vs docs/ENGINEERING.md

Date 2026-10-31. Read-only audit. Sources: project.yaml, parts/*.py, DESIGN.md, out/report.json, out/bom.md,
out/ASSEMBLY.md, out/WIRING.md, the plate 3MF, assembly sheets and every fea_*.png, catalog/hardware.json, kerf/*.py.

**Correction to the brief:** fpv_5in/out is **not** current. report.json has fingerprint 8f3a9a18a3cb4af6. The
geometry and review are at c0d6880d38b83a40, because project.yaml changed at 04:12 (commit 5f1fd4a, camera moved to the
9 V pad) and the last build ran at 03:45. `kerf status` shows "build PASS (stale)" and **eval FAIL** (run_evals:
"report.json is stale"). pan_tilt/out is current (1dc98e4ae7048aca).

---

### fpv_5in: compliance

| Rule | Status | Evidence |
|---|---|---|
| 1 Requirements first | ok | DESIGN.md sec. Requirements and sizing (TWR, arm hand calc, XT60 current); every pass/fail number has a requirement (project.yaml:142-202) |
| 2 Materials | ok (see F3) | CF-PETG xy 35 / z 29 MPa from the Bambu TDS (catalog materials.CF-PETG). These are measured Z values, so the 50 % default does not apply. The TDS values are for 100 % infill specimens, but the parts are infill 0.3-0.5 and FEA uses a solid model |
| 3 Safety factors | ok | arm 2 x 1685 g = 33.06 N, SF 3 (yaml:151-159). The body uses the same crash load (SF 3). top_plate SF 3 on z. TWR 6.18 >= 6 |
| 3 Wrong load case? | finding (F5) | arm: correct (2x full, unlimited thrust: conservative). Body: fixed only at the 4 post feet (yaml:167), so the load path from arm_1 to the opposite arm's screws across the stack-hole region is never loaded. top_plate: "50 g" battery hit has no source |
| 3b FEA, applied loads | ok | applied_force/moment match the asked loads: arm 33.06 N, M_y -3736 = 33.06 x 113; top_plate_x M_y 6994 = 112.8 x 41 + 2369 |
| 3b hot spot location | ok | fea_arm_strength.png: hot at the root screw holes. fea_body_strength.png: at the arm_1 screw/rib zone. fea_top_plate_*.png: pillar feet and pillar-to-plate junction |
| 3b margins | finding (F3) | p99.9 arm 9.50/11.67, body 10.15/11.67, top_plate_y 8.86/9.67 (92 %). Surface peak exceeds the limit: arm 12.12, body 14.23. Solid-model FEA on 30-50 % infill parts |
| 3b arm deflection < 1 % of length | ok, limit not encoded | 0.766 mm vs 0.87 mm (1 % of the 87 mm arm), but max_disp_mm is 1.5 (yaml:157), so the rule is not enforced |
| 4 print_rot / load_axis | finding (F4) | body and arms ok (yaml:24-28). **top_plate has no load_axis** (yaml:29), although its posts bend across layers. The z FEA covers strength, but the orientation guard never runs |
| 4 overhang | minor | body 3.67 % > 3 % warning (report warnings); counterbore seat ceilings on the bed face (DESIGN.md:120) |
| 5 walls | ok | wall_p02: body 3.0, arm 3.2, top_plate 1.6. Post insert wall (9 - 4.0)/2 = 2.5 >= 2.4 |
| 5 fillets on load path | **finding (F2)** | top_plate pillars are joined to the plate with no fillet (top_plate.py:56-58). That joint is the governing section (top_plate_y at 92 %). Arm ridge roots and body rib roots are sharp too (arm.py:30-32, body.py rib loop) |
| 6 fits | finding (F7) | arm-ridge grooves have 0.2 mm all round (body.py:57) and sit **on the bed face** with no elephant's-foot chamfer (body.py has no bed-edge chamfer) |
| 7 fastener engagement | minor (F9) | arm M3 x 12, grip 6, into a nut sunk 1 mm: the tip ends exactly flush with the nut top (report fasteners: grip 6.0, length 12, nut 2.4 at z 3.6-6.0), so the -0.35 length tolerance loses up to 15 % of the thread. Motor 2.5 mm >= catalog min 2.0, <= max 3.0 ok |
| 7 edge distance / boss | ok | arm holes 10 mm from the arm edge (>= 6.1). Outer body hole 9.2 mm from the plate edge. Post insert centre 4.5 mm from the pillar edge is below 1.5d + wall (6.1), but the pillar is a 9 mm boss (>= 2.2d) with 2.5 mm insert wall, so the boss rule governs (doc ambiguity, E7) |
| 7 hex-key access | ok | report hex_keys: all straight, blocked_by [] |
| 8 moving joints | ok | cam_tilt 0-40 swept, friction pivot on M2 into the camera |
| 9 drones | ok | prop gap 3.45 >= 3. Motor screw 2.5 <= 3.0. Grommets in BOM. Strap notches 21 mm. Pad. CG lateral 0.9 <= 5 |
| 10b system complete | ok | FC/ESC stack, rx + antenna, VTX + antenna, camera, XT60, strap, pad, all catalog-backed |
| 10b power_budget | finding (F6) | XT60 57.44 / 60 A passes only through `electrical.limits` peak_a 14.22 (yaml:56-60). That is a **throttle cap converted to current by the cube law**, not a current limit. The BLHeli_S BLS 55A ESC has none. DESIGN.md:29-30 itself says the real peak "may reach ~60 A" |
| 10b connector_access, FC USB | **finding (F1b)** | only xt60_plug (yaml:201). The FC USB port is not checked or specified, although the build **requires** a Betaflight CLI change (DESIGN.md:104). The pillars at x ±28.5..37.5 and the hanging VTX may block a USB-C plug depending on the stack's yaw |
| 10b wiring routes | minor (F10) | vtx_5v and vtx_video have no route (yaml:83, 91), so the routed length and 15 % slack are unchecked |
| 10b out/ docs | **finding (F1)** | stale: WIRING.md:24 and ASSEMBLY.md:111 tell the builder to solder the camera to **stack.5v** (`cam_5v`). project.yaml:84 says the 9 V pad. report.json still shows the soft voltage fail "camera input 4.99 V < 5.0 V" |
| 11 assembly order | ok | DESIGN.md:90-104, key_access for the VTX bench step |
| 11 mass vs DESIGN | ok | 149.4 g vs 149.5 g; all-up 598 vs 597 |
| BOM completeness | ok (stale) | 16 M3x10, 8 M3x12, 4 M3x30, 4 M3x8, 4 inserts, 12 nuts, 4 M2x12, 2 M2x6 button, washers, spacers, ties, threadlocker, grommets, wire and heat-shrink. Some links point at other lengths (M3x12 links to an M3x8 SKU). Rebuild before judging |

### pan_tilt: compliance

| Rule | Status | Evidence |
|---|---|---|
| 1 Requirements first | ok, minor | DESIGN.md sec. 1 R1-R10. Pan holding torque is a hand number only (DESIGN.md:56, 3 % of stall) with no static_torque requirement. bracket_arm has no `why` (report "why": "") |
| 2 Materials | ok | PETG xy 48 / z 39 MPa, measured TDS values (catalog). Allowable 39/3 = 13 MPa |
| 3/3b across-layer proof (the build warnings) | **ok: proven** | All three warnings ("load axis Z across layers") are answered by fea_static with `direction: z`, SF 3: base_fea 1.14/13, yoke_fea 2.59/13, bracket_fea 2.20/13, plus cantilever bracket_arm 0.2/13 (direction z). The engine still prints the warnings after they are satisfied (E4) |
| 3 load cases | minor (F15) | Stall-torque cases are physically bounded (176.5 N·mm = 1.8 kg·cm): good. The handling loads are unsourced: 10 N knock applied **at the tab screws** (yaml:147), not at the head ~45 mm higher, so the overturning couple into the deck is left out. 5 N on the pivot. Pan-stall reaction through the yoke (head blocked) is not modelled. Margins of 5-11x make this documentation, not strength |
| 3b hot spots | ok | yoke: servo-window corners and wall roots. bracket: horn face and standoffs. base: at one tab site (load-application spot). Applied moments: yoke M_y 176.47, bracket 176.52; base M_z 169.7 = 176.5 - 10 N x 0.68 mm site offset (fine) |
| 4 print_rot / load_axis | ok | all declared (yaml:26-30). Teardrops on the pivot hole, standoffs and knuckle. 12.8 mm bridge on the servo window |
| 4 horizontal holes | finding (F14) | yoke tilt-servo pilots and bracket camera pilots are horizontal as printed but cut at the vertical self-tap pilot size. The catalog fdm_holes.M2 note gives 2.10 for horizontal vs 1.84 vertical. iface ignores orientation (E6) |
| 5 walls | **finding (F12)** | base lead slot leaves **1.3 mm** between the slot and the -X pan-servo tab pilot over the whole 3.6 mm engagement (base.py:48; slot y 2.2..6.6, pilot at y 0, x -13.9 inside slot x -22.1..-10.8). Rule: >= 2.4 mm around screw bosses (catalog M2 min 1.3 is the heat-set value, not a self-tapper beside a free edge). Bracket standoff wall 2.4 - 0.92 = 1.48 mm (= wall_p02 1.48): at the catalog M2 min, below 1.6 structural |
| 5 fillets | ok | yoke wall roots r 1.5 (yoke.py), bracket plate/arm r 1.5, gussets |
| 6 fits / clearance | ok | cam_clear 0.9 >= 0.8, cam_clear_base 3.32, pivot free + teardrop, nut pocket +0.2 AF |
| 7 edge distance | finding (F12, F13) | base pilot: 2.2 mm centre-to-slot-edge vs 1.5 x 2 + 1.2 = 4.2. Yoke upper tilt-tab pilot: 4.0 mm to the wall top (yoke.py:36: wall top = hole_top + 4.0) vs 4.2-4.6 |
| 7 inserts vs load | **finding (F11)** | the tilt pivot (a load-carrying revolute) is an M3 SHCS tapped straight into the PETG knuckle (bracket.py:86 `fit="tap"`), with **Loctite 243-class threadlocker** (DESIGN.md:132, BOM, engine warning). Henkel's 243 TDS advises against thermoplastics (stress cracking). An M3 x 12 SHCS is fully threaded, so the yoke wall bears on threads, not a shank |
| 7 hex-key access | ok, gap | all modelled screws straight/clear. Both **horn centre screws** are not fastener groups: not access-checked, not in the BOM (E5). The tilt one needs a 1.5 mm key ~41 mm through the wall, knuckle and arm gap |
| 8 moving joints | ok | ranges swept + 4 corner poses. Dual-support tilt. Pan on the SG90 spline alone: 34 g at 13.5 mm, below the sec. 8 thresholds, argued in DESIGN.md:45-47 |
| 10 tip_over | n.a. | tripod/clamp mounted |
| 10b system | ok, minor | PSU, jack, Pi Zero 2 W, Pi USB supply and capacitor. The Pi Zero 2 W ships **without a GPIO header** (catalog note) and WIRING says "solder to pi": acceptable, but say it. The pan_pwr note says "300 mm servo extension", but the BOM/WIRING give bare 22 AWG spliced wire (inconsistent) |
| 10b power_budget | ok | 0.143 of rating; mains, no run_time |
| 10b wiring | minor (F16) | the camera FPC (>= 300 mm, through the yoke notch, 60 mm slack loop over pan ±90 / tilt -35..65) is not a `wiring:` run, so the sweep never checks its path (E8) |
| 11 assembly | ok | DESIGN.md sec. 8 order; nut drops down the pocket (AF 11.3 < 13.2 pocket width) |
| 11 mass | ok | 59.3 g = report |
| BOM | finding (F17) | bom_extra[0] is **mangled**: unquoted comma in a YAML flow map (yaml:55) gives item "1/4-20 UNC hex nut (ASME B18.2.2" plus a junk key "7/16 in AF)". Servo, Pi and camera "Buy" links are datasheet PDFs, unpriced. M2x5/M2x8 link to the M2x6 SKU, M3x12 pivot to the M3x8 SKU. 2 horn centre screws missing |

---

### Findings

| # | Sev | Project | Part | Issue | Fix |
|---|---|---|---|---|---|
| F1 | major | fpv_5in | (all) | out/ is stale (report 8f3a9a18 vs geometry c0d6880d) and the fpv eval FAILS on it. The shipped WIRING.md:24 and ASSEMBLY.md:111 tell the builder to solder the camera to the **5 V** pad, which project.yaml:84 has now moved to the 9 V pad. | `kerf build fpv_5in`, check the eval passes and WIRING/ASSEMBLY show `cam_9v` |
| F1b | major | fpv_5in | stack / top_plate | ENGINEERING 10b requires `connector_access` for the FC USB port. None exists, though the build needs a Betaflight CLI session (`motor_output_limit = 74`). The catalog fc_30_5 has no USB position, and the pillars plus the hanging VTX can block a USB-C plug depending on stack yaw. | Add the USB-C position and side from the SpeedyBee F405 V4 drawing to catalog fc_30_5. State the stack yaw. Add `{check: connector_access, item: stack, direction, at, size: [12, 7], length_mm: 45}` as tvc_drone does |
| F2 | major | fpv_5in | top_plate | The pillar-to-plate junction, the governing section of the battery-crash cases (top_plate_y 8.86/9.67 = 92 %), has no fillet (top_plate.py:56-58). That breaks sec. 5 (r >= 1 on load-path inside corners), and a sharp re-entrant corner makes the p99.9 value mesh-dependent. | Fillet the pillar/plate and pillar/web junctions with r >= 2 (prints fine: plate on the bed). Re-run top_plate_x/y |
| F3 | major | fpv_5in | arm, body, top_plate | Strength margins are thin (arm 81 %, body 87 %, top_plate 92 % of allowable). They come from solid-model FEA against 100 %-infill TDS strengths, but the parts print at 0.5/0.4/0.3 infill. The plate 3MF carries **no** infill or wall settings at all (only 3D/3dmodel.model), so the slicer default (~15 %, 2 walls) applies, not the ">= 4 walls" in DESIGN.md:41. The surface peak already exceeds the limit on arm (12.1) and body (14.2). | Short term: tell the builder (DESIGN + ASSEMBLY) to slice the top_plate pillars and arm roots at 100 % infill (modifier) and >= 4 walls, then re-check mass/TWR. Proper fix in E1/E2 |
| F4 | minor | fpv_5in | top_plate | No `load_axis` (yaml:29) on a structural part whose posts bend across layers. Strength is covered by the z FEA, but the sec. 4 guard is skipped. | Add `load_axis: [x, y]` (post bending) |
| F5 | minor | fpv_5in | body | body_strength is fixed only at the 4 post feet (yaml:167). The diagonal path from the loaded arm to the opposite arm (inertia of motor/arm 3), across the stack-hole region, is never loaded. | Add a second case fixed at `arm_3` sites with the same arm_1 couple |
| F6 | minor | fpv_5in | stack / xt60 | The XT60 pass (57.44/60 A, ratio 0.957) relies on `electrical.limits` peak_a 14.22. That value is a cube-law estimate of a throttle cap, not a configured current limit (sec. 10b allows "a real, configured ESC/firmware current limit"). BLHeli_S has none, and the punch-out transient exceeds the steady-state propeller law. DESIGN admits ~60 A. | Treat it as an estimate: either switch to an ESC with a firmware current limit (AM32/BLHeli_32) and set it, or a connector with headroom (XT60 is the bottleneck; lowering the cap breaks TWR 6). Keep the Blackbox gate |
| F7 | minor | fpv_5in | body | The arm key grooves (0.2 mm per side, body.py:57) are on the bed face with no bed-edge chamfer, so elephant's foot eats the clearance and the arm may not seat. | 0.4 mm x 45° chamfer on the groove mouths and the plate's bed edge, or 0.3 mm per side |
| F8 | minor | fpv_5in | arm | The arm deflection rule (1 % of length = 0.87 mm) is met (0.766), but the requirement encodes 1.5 mm (yaml:157). | Set max_disp_mm: 0.87 |
| F9 | minor | fpv_5in | arm/body | The arm M3 x 12 tip ends exactly at the sunk nut's top face (grip 6, nut z 3.6-6.0). Under length tolerance (±0.35) the nut is not fully engaged and the threadlocker sits at the plastic pocket. | Sink the nut 0.5 mm instead of 1.0 (the tip still stays 0.5 below the top face), or use a 2.0 mm thin nut |
| F10 | minor | fpv_5in | vtx | vtx_5v and vtx_video have no `route` (yaml:83, 91), so the cut length >= routed + 15 % is unchecked. | Add routes (the VTX hangs under the top plate: route from the stack along a pillar) |
| F11 | major | pan_tilt | bracket / yoke | The tilt pivot is an M3 SHCS tapped directly into the PETG knuckle (bracket.py:86) with medium threadlocker (DESIGN.md:132, BOM). Anaerobic threadlocker on PETG risks stress cracking (Henkel 243 TDS: not recommended on thermoplastics), right at the bracket's only opposite-side support. A fully threaded M3 x 12 also turns its threads in the yoke wall. Sec. 7 calls for an insert on a load-carrying thread. | M3 heat-set insert (hole 4.0, fits the 8.8 mm knuckle with 2.4 mm wall) and an ISO 7379 shoulder screw or a partially threaded screw. Lock it with a nylon-patch screw or a plastic-safe locker (e.g. Vibra-TITE VC-3). Drop "medium threadlocker" from DESIGN and BOM |
| F12 | major | pan_tilt | base | The servo-lead slot leaves 1.3 mm of plastic between the slot and the -X pan-servo tab pilot over the full screw engagement (base.py:47-51). Edge distance is 2.2 vs 4.2 mm (sec. 7) and the wall is 1.3 vs 2.4 mm (sec. 5). A self-tapping M2 here is likely to split the wall, and it carries the pan stall reaction. | The lead is a flat 3-wire ribbon that drops in from the open top, so narrow the slot to ~2.0 mm (ribbon on edge) at y 4.5..6.6, or move it to the +X end / the -Y side, away from the pilot |
| F13 | minor | pan_tilt | yoke | The upper tilt-servo tab pilot is 4.0 mm from the wall top (yoke.py:36). The rule asks 1.5d + wall = 4.2-4.6. | Raise the wall top to hole_top + 5.0 |
| F14 | minor | pan_tilt | yoke, bracket | Horizontal M2 pilots (yoke tilt tabs, camera standoffs with 1.48 mm wall) are cut at the vertical pilot size 1.84. The catalog note gives 2.10 for horizontal holes. Undersize oval pilots plus thin standoff walls risk splitting. | Use the horizontal pilot value for horizontal holes (E6). Standoff r 2.4 -> 2.8 |
| F15 | minor | pan_tilt | base, yoke | Handling loads (10 N, 5 N) are unsourced, and the base knock is applied at the tab screws instead of at the head. Pan-stall reaction through a blocked head is not a yoke case. Margins are large, so no strength risk. | Apply the knock at the camera (moment ~10 N x 45 mm) and state the source of the magnitude. Add a pan-stall yoke case |
| F16 | minor | pan_tilt | camera | The camera FPC (a real run over pan ±90 / tilt -35..65, through the yoke notch next to the pan-horn screw heads) is not in `wiring:` and not swept. | Model it as a wiring run with route points (E8) |
| F17 | minor | pan_tilt | BOM | bom_extra[0] is broken by an unquoted comma (yaml:55): item "1/4-20 UNC hex nut (ASME B18.2.2" plus a junk key. The 2 horn centre screws are missing. Servo/Pi/camera links are datasheets. M2x5/x8 and M3x12 rows link to M2x6/M3x8 SKUs. | Quote the item string. Add 2 x M2 horn centre screws (or "ships with horn"). Add shop links/prices. Fix price keys per length |
| F18 | minor | pan_tilt | requirements | Pan holding torque is a hand number only (DESIGN.md:56). bracket_arm has no `why`. | Add static_torque on `pan` (tripod-on-its-side pose) and a why |

#### ENGINE findings (will recur in every project)

| # | Sev | Issue | Fix |
|---|---|---|---|
| E1 | major | Plate 3MFs carry no per-object process settings (verified: plate_1.3mf holds only 3D/3dmodel.model; no `infill`/`wall_loops` anywhere in kerf/). The `infill` in project.yaml feeds only the mass estimate, and DESIGN-level wall counts never reach the printer, so every FEA/mass claim assumes settings the slicer doesn't get. | Write Bambu `Metadata/model_settings.config` per object: sparse_infill_density from `infill`, wall_loops (default 4 for structural parts), filament/material. Add a test |
| E2 | major | fea_static uses a solid mesh against TDS (100 %-infill) strength for parts printed at 30-50 % infill. Separately, pass/fail is the **volume** p99.9, so the ignored volume scales with part size (67 mm³ on the fpv body, enough to hide the whole nut-seat hot spot), and surface peaks above the limit (fpv arm 12.1, body 14.2 vs 11.7) don't fail. | Knock strength (or stiffness) down by an infill/shell model, or require 100 % infill in the stressed region (E1 modifier). Judge on stress excluding only elements touching load/fixture patches, and report surface peak vs limit |
| E3 | minor | `fea_static.direction` is free-form and never cross-checked with the part's `load_axis` + `print_rot`. `load_axis` is optional even on parts that have an fea_static (fpv top_plate), so the sec. 4 orientation guard silently skips. | Require load_axis on every part named in an fea_static/cantilever_stress. Warn when direction xy is used while load_axis runs > 30° out of the bed plane |
| E4 | minor | The "load axis across layers ... prove it with direction z" warning keeps firing after the proof exists (pan_tilt base/yoke/bracket), so real warnings get lost in noise. | Suppress the warning when a passing direction-z fea_static/cantilever_stress exists for the part; otherwise make it a failure |
| E5 | minor | Servo-horn centre screws are not modelled: not in the BOM, no key-access check. The pan_tilt tilt centre screw needs a ~41 mm key path through three parts. | Have iface.horn_mount register the centre screw as a fastener (catalog center_screw), with access path and BOM row |
| E6 | minor | iface uses the vertical `self_tap_pilot` for every hole. The catalog notes horizontal (2.10) and PETG (1.70) values but has no keys for them. | Add `self_tap_pilot_horizontal` (and PETG) keys and choose by hole axis vs print_rot |
| E7 | minor | Edge distance (sec. 7) and wall-around-pilot (sec. 5) are not checked, and the wall check uses the p02 percentile, so local 1.3 mm walls (pan_tilt base) pass. Doc ambiguity: "1.5 x d + wall" vs the boss rule for inserts in bosses. | Per-fastener check: distance from the hole axis to the nearest free surface over the engagement depth >= 1.5d + 1.2 (or catalog min wall + hole radius for bosses). Clarify the rule text |
| E8 | minor | Flat-flex cables (camera FPC) can't be declared as `wiring:` runs, so they escape route/sweep checks. | Allow `kind: fpc` with width/min bend radius in wiring |
| E9 | minor | `bom_extra` accepts unknown keys silently (a YAML comma split the pan_tilt nut row). | Validate bom_extra keys and fail on unknowns |
| E10 | minor | The engine itself recommends "medium threadlocker" for screw pivots tapped into plastic (kerf/pins.py:145, export.py:152, ship.py:314). | Recommend a heat-set insert + shoulder screw / nylon-patch screw. Never anaerobic threadlocker on printed threads |
| E11 | minor | `electrical.limits` accepts any peak_a with a why. A throttle-cap estimate is treated like a hard current limit. | Add `kind: current_limit | throttle_estimate`. For estimates, require margin (e.g. 15 %) against connector/wire ratings |
| E12 | minor | `kerf verify` relies on the eval to catch stale out/ (it did for fpv). review-status still reports "current PASS" while out/ is stale. | Have review-status/verify also flag report fingerprint != current fingerprint |


---

# Appendix C

## Audit C: robot_arm and bionic_finger against docs/ENGINEERING.md

Audited outputs: robot_arm/out (report fingerprint 4f10b53919af2951, built 03:57 UTC), bionic_finger/out (fff481bce3957f7e, built 04:04 UTC).
Read: DESIGN.md, project.yaml, parts/*.py, report.json, bom.md, ASSEMBLY.md, WIRING.md, assembly sheets, and every FEA png for both projects.
I did not edit any project or review file.

---

### 1. bionic_finger: compliance table

| Rule | Status | Evidence |
|---|---|---|
| s1 Requirements in DESIGN + yaml | ok | DESIGN.md s1; yaml requirements: len_*, channel_clear x2, fea x2, hard_stop x3, mass |
| s1 Purchased parts sized with math | ok | DESIGN s7: tension T = 22.5 F, 100 lb braid |
| s2 Material / allowable | ok | PETG 48 MPa XY / SF 2 = 24 (report limit 24.0) |
| s3 SF, right load case | **finding** | proximal_fea_line puts 222 N on the insert bore. report applied_moment_nmm z = 769.5, so the load centroid is at y = +3.47, inside the parent band. In the real joint the load enters through the child's band at y ~ -3.9 (single-shear lap). The ~870 N·mm moment that tilts the insert is not modelled. |
| s3b FEA on every structural part | **finding** | Only `proximal` has FEA. base, middle (pip free hole and dip insert, p02 wall 1.28) and distal (line anchors) have none. |
| s3b Hot spot where load enters | ok (for the load case as modelled) | fea_proximal_fea_line.png: hot spot at the pip insert bore |
| s3b Deflection < 1 % | ok | 0.258 mm vs 0.44 |
| s4 print_rot / load_axis | ok | All four parts print on their side with load_axis X in the bed plane. No load-axis warning. |
| s4 Overhang / supports: avoid | ok | overhang_pct 0.0 on all four parts |
| s4 Horizontal holes | ok | Pivot holes and knot pockets are vertical on the printer |
| s5 Wall >= 1.2 | **finding** | distal p02 1.12. The extensor knot pocket (distal.py:29-33: x 12, z 4.981, Ø3) leaves 7.5 - 4.981 - 1.5 = 1.02 mm to the dorsal face. Base: I measured 0.91 mm between the M3 mount hole and the flexor channel; the p02 wall statistic does not see it. DESIGN does not justify either. |
| s5 >= 2.4 mm around inserts (catalog min 1.6) | **finding** | DESIGN s10: the extensor groove passes ~0.5 mm from the insert hole (~0.2 mm from the knurls) in the top 0.95 mm. DESIGN also says the insert "seats below that", but step 1 presses it flush with the face, so the two statements contradict each other. |
| s5 Inside fillets / outside chamfers | finding (minor) | Sharp box edges everywhere (assembly_sheet.png). No chamfers on a part people touch. |
| s5 Text, snap-fits, printed threads | n.a. | |
| s6 Fits | **finding (minor)** | Pin free +0.35 ok. Lap gap is 0.3 mm total (fingerlib.py:27), i.e. 0.15 per face: below the s6 printed-on-printed figure (0.3-0.4 per side) and s8 (0.5 mm). 7.55 / 0.3 are not multiples of a 0.2 mm layer, so the printed gap could come out anywhere from 0.1 to 0.5 mm. |
| s7 Catalog metric fasteners | ok | motion.shoulder_4_m3, fdm_holes.M3 |
| s7 Inserts for loaded threads | ok | Heat-set M3 in each parent band |
| s7 Edge distance 1.5d + wall | ok / marginal | Mount hole x=-24 to back face x=-30: 6.0 mm (need 5.7-6.1). Insert at the disc centre: 7.5 mm. |
| s7 Key access | **finding (engine)** | report hex_keys = [] because screw pivots are skipped. The catalog head is slotted (head 7 x 1.8), so a screwdriver is needed, but ASSEMBLY.md says "Tools: none". |
| s7 Same group both sides | ok | pin_mcp/pip/dip, coaxial proven (report pins) |
| s8 Ranges swept | ok | mcp/pip/dip and curl all clear, worst 0 mm3 |
| s8 Metal pin on loaded revolute | ok | 4 mm ground shoulder turning in the 4.35 hole |
| s8 0.5 mm axial clearance | finding | 0.3 mm lap gap (see s6) |
| s9, s10, s10b | n.a. | No electrics. Actuator out of scope. |
| s11 channel_clear at tendon + fit clearance | ok | 2.2 mm open vs 1.5 required, 7 poses. The real channel is 2.69 mm wide at mid-plane (teardrop bug, see B5). |
| s11 Assembly order in DESIGN | ok in DESIGN, **finding in out/** | DESIGN s9 is complete. out/ASSEMBLY.md has: no heat-set insert step, no tendon step (the distal `assembly_note` is missing), no frame-mount step, "Tools: none". |
| s11 Fits A2L / plate packs | ok | plate_1.3mf holds all four parts |
| s11 Mass budget in DESIGN within 10 % | finding (minor) | DESIGN has no mass budget, only a 40 g cap (report 20.5 g) |
| BOM completeness | ok with nits | Present: 3 shoulder screws, 3 inserts, line, 2 line stops, CA, 2 M3 mount screws+nuts. Shoulder screws and inserts are not proxies (report `purchased: {}`), so they are missing from mass and interference. The buy link is 97505A139 while the order number is 97505A106. There are 3 duplicate rows. |

### 2. robot_arm: compliance table

| Rule | Status | Evidence |
|---|---|---|
| s1 Requirements / sizing math | ok | DESIGN torque table and hand check (7.8 kg·cm); yaml torque_*, reach 266, grip_open 62.9 |
| s2 Material | ok | PETG. z = 39 MPa used where loads cross layers. |
| s3 Servo <= 50 % stall | ok | 7.77/10.5, 4.30/9.5, 1.87/4.7 |
| s3 SF on the right load case | **finding (minor)** | yoke_r and gripper use stall. upper_arm/forearm use 2x static elbow/wrist torque (841 / 367 N·mm), but elbow stall is 1863 N·mm and DESIGN admits a desk crash at shoulder < ~-22 deg. My hand estimate still passes (deep fork), so this is consistency, not failure. |
| s3b FEA on every structural part | **finding (major)** | No `base` FEA. The base tower carries the whole tipping moment (DESIGN: 0.85 N·m static) through both bearing seats, across layers, and the build warns about it ("prove it with fea_static ... direction z"). DESIGN.md:116 claims "base and turntable ... their FEA uses the z strength with SF 3", but base has no FEA. yaw_gear has no tooth check (my Lewis estimate at MG996R stall is ~8.4 MPa, ok). |
| s3b Applied loads / hot spots | ok | Resultants in the report match DESIGN (e.g. yoke_r My 2143 = stall 2060 + weight). PNGs: yoke_r hot at the cheek/foot step, gripper at the jaw root, upper_arm at the plate-B window and webs. |
| s3b Deflection 1 % | ok | 0.42/0.85, 0.16/0.8 |
| s4 Orientation vs load_axis | ok, justified | base and turntable are across layers (warned) with z SF 3; the turntable has FEA, the base does not (above). Links print on edge, bending along X. |
| s4 Overhang | ok, justified | supports allowed. gripper 16 %, forearm 3.6 % (DESIGN Risks). |
| s4 Horizontal holes teardrop / +0.2 | **finding (minor)** | upper_arm/forearm/gripper print [90,0,0], so the pin_hole free (3.35) and heat-set (4.0) pivot holes and the horn holes lie parallel to the bed (upper_arm.py:45-52, forearm.py:45-52, gripper.py:64-67). No teardrop or +0.2 is applied, and iface.pin_hole has no teardrop option. The yoke feet do use teardrop=90. |
| s5 Walls / inserts | ok | p02 >= 1.52. Pivot inserts sit in 7 mm plates with a +3 mm boss. |
| s5 Fillets | ok | DESIGN Strength: 1.5-4 mm on load corners (yoke_l.py:24-34, upper_arm.py:38-43) |
| s6 Fits | ok | Bearing seat press +0.05; free pin +0.35 |
| s7 Edge distance >= 1.5d + wall (6.1 for M3) | **finding (minor)** | Front yoke-foot screw at x=10 with the foot end at x=14 (yoke_l.py:8,20): 4.0 mm, at the FEA hot spot. Turntable front inserts at x=10 with the platform edge at x1=15 (turntable.py:24): 5.0 mm. |
| s7 Key access | ok | 1 yoke_r_foot, 4 el_horn, 2 wr_servo and 2 gr_servo screws need a ball-end key. This is listed in ASSEMBLY.md. |
| s7 Engagement | ok | Horn screws: grip 7 + horn 2.0 (M3x10 into 2 mm aluminium, normal for horns). Tab screws: 5+ mm in PETG. gr_horn M3x8 with a 6 mm grip leaves exactly the horn thickness, ok. |
| s8 Range sweeps | ok | All sweeps clear. yaw_drive is coupled at -0.6667. |
| s8 Revolute on bearing / metal | ok | 2 x 6001. M3 SHCS pivots in heat-set inserts. |
| s8 Dual support | ok | Every joint is a fork with an opposite pivot |
| s8 0.5 mm axial clearance / washers | **finding (minor)** | side_gap 1.5 mm. DESIGN says "take up the play with M3 washers", but there are no washers in the BOM. |
| s8 Printed gears | ok | m 1.5, 24/36 T, 0.3 backlash, coupled sweep |
| s10 Torque, yaw bearing, cable path, gripper numbers | ok | cable_loop 7.03 >= 5. Grip 18.4 N and opening 62.9 stated. |
| s10 tip_over | n.a. | The base is bolted or clamped to the desk (allowed by the rule) |
| s10 Reach vs desk | finding (minor) | The TCP goes below the desk top at shoulder < ~-22 deg (asin(100/266)). DESIGN step 0 says to work at the desk edge or use a software limit. No sweep checks it. |
| s10b Derived electrical system | **finding (major)** | No overcurrent protection between an 18 A supply (LRS overload trips at ~105-135 %) and 22 AWG servo leads that cross 4 moving joints. No mains cord/plug or switch in the BOM, even though the PSU has mains screw terminals. |
| s10b power_budget | ok | Worst element 72 %. Peak sag 4.68-4.75 V is reported (assumes 5.0 V; DESIGN trims to 5.3 V). |
| s10b run_time | n.a. | Mains supply |
| s10b connector_access | ok | usb_access clear |
| s10b Every run with gauge/colour/cut >= +15 % | ok | WIRING.md; pwr_yaw 210 >= 1.15 x 175.6 |
| s10b Wire ends / leads in BOM | **finding (major)** | BOM buys 5 x 300 mm extensions plus 5.0 m red/brown and 2.3 m orange 22 AWG plus 21 splice heat-shrinks, so it is unclear whether the leads are extensions or raw wire. The gr run needs a 710 mm cut, while an MG996R pigtail (typically ~300 mm; there is no lead length in the catalog) plus a 300 mm extension is ~600 mm. The single orange wire into the PCA9685 3-pin header needs a 1-pin housing/crimp, which is not in the BOM. |
| s11 Assembly order | finding (minor) | There is no `assembly.order` in project.yaml. The generated ASSEMBLY.md order differs from DESIGN s"Assembly order": no desk-bolting step 0 (DESIGN says the front M4 holes are blocked once the arm is on), no pivot washers, yoke_l is bolted (step 14) before the upper arm (step 19), while DESIGN step 7 has the arm between the yokes. |
| s11 Fits A2L | ok | report fits |
| s11 Mass budget within 10 % | **finding (minor)** | DESIGN part list says base 88 g; report says 130.5 g (+48 %). |
| BOM completeness | finding | Missing: washers, fuse, mains lead, signal housings. Conflicting rows: auto "M2 x 5" x4 and bom_extra "M2 x 8" x4 (DESIGN says M2x8). |
| DESIGN vs report drift | minor | Gripper FEA in DESIGN is 5.1 (peak 14.6); report is 7.22 (peak 20.42). Pivots: DESIGN "M3x12" vs report M3x14. project.yaml:6 and layout.py:5 say "M3 shoulder-screw pivot", but the pivot is a plain SHCS. grip_open 63.8 vs 62.9. |

---

### 3. Findings

#### bionic_finger

1. **major / bionic_finger / distal: the tendon line stop is not designed for the line load.**
   - **Issue.** The design case is 222 N (DESIGN s8). It ends on a 2.5-2.9 mm bead or sleeve in a Ø3 pocket, pulling against the mouth of the 2.2 mm channel. That channel is really 2.69 mm wide at mid-plane and 3.0 mm tall at the roof (B5). The bearing annulus is < ~1.5-2 mm², i.e. >100 MPa on PETG, so the bead crushes in and pulls through. A 2.5-2.9 mm OD crimp sleeve has a ~1.5+ mm bore, which does not crimp onto 0.5-0.8 mm line, and it is longer than the Ø3 pocket allows. No requirement checks any of this.
   - **Fix.** Seat an ISO 7089 M2 washer (OD 5) on a flat step: Ø5.4 pocket, with a 1.2 mm line hole for the last 1.5 mm before the pocket. Put the bead or knot on top of the washer. Bearing area then grows to ~18 mm², ~12 MPa at 222 N. Add a cantilever/bearing hand check or FEA on the distal for that case.

2. **major / bionic_finger / proximal (and base, middle): the FEA load case omits the single-shear tilting moment at each insert.**
   - **Issue.** In the report, applied_moment z 769.5 / 222 N puts the load centroid at y = +3.47, inside the insert's own band. The real load comes in through the shoulder from the child band at y ~ -3.9. That is ~870 N·mm of tilting moment on an insert 5.7 mm long and 4.6 mm OD. A rigid-insert / elastic-foundation estimate gives a peak of order 60+ MPa at the insert mouth vs 24 allowable. The mouth is also where the extensor groove leaves 0.5 mm of wall.
   - **Fix.** Add the moment to fea_static: either a torque_nmm about z on the insert bore, or apply the bearing load on a short cylinder at the child band's mid-plane. If it fails, use a longer or wider insert (M3 x 5.7 is already used; go to an M3 Voron 5 mm OD with a 4.4 hole, or a double-lap knuckle) and move the extensor wrap so the insert boss keeps >= 1.6 mm of wall.

3. **major / bionic_finger / base, middle, distal: no fea_static at all (rule 3b, every structural part).**
   - **Issue.** The middle has the same pip free hole and dip insert under 222 N, with less material (p02 1.28). The distal carries the line anchors.
   - **Fix.** Add middle_fea (fixed at pip bore, 222 N + moment at dip insert), distal_fea (fixed at dip bore, line tension at the two pockets), and base_fea (fixed at the two mount holes, 222 N at the mcp insert).

4. **minor / bionic_finger / distal: the 1.12 mm wall warning is not justified.**
   - **Issue.** It is the extensor knot pocket at z = 4.981, Ø3, leaving 1.02 mm to the dorsal face (distal.py:29-33, fingerlib H = 7.5). That skin sits beside the anchor that takes full line tension. DESIGN never mentions it.
   - **Fix.** Bring the extensor run down to z ~ 3.5 between ext_wc and the anchor (>= 2.5 mm skin), or move the pocket aft under the lug.

5. **minor / bionic_finger / all (fingerlib.py:94): `_tube` is not a true teardrop.**
   - **Issue.** The triangle base is the full chord at the circle centre, so the cutter is 2.69 mm wide at y = 0 (measured: Z ±1.343), not 2.2. This leaves 0.24 mm notches along every channel and thins every wall next to one. Measured: the base M3 mount hole to the flexor channel is 0.91 mm (< 1.2 rule).
   - **Fix.** Make the triangle base the tangent chord, i.e. vertices at (r·sinβ, ±r·cosβ) with β = 90 - ROOF. Or reuse kerf.features.teardrop_hole. Then re-check channel_clear.

6. **minor / bionic_finger / base, proximal, middle: insert boss wall violates rule 5.**
   - **Issue.** The wall is 0.5 mm to the swept extensor groove, against >= 2.4 (catalog heatset_min_wall 1.6). DESIGN s10 says the insert "seats below" the groove, but step 1 presses it flush, so that is self-contradictory. Expect a bulge into the groove when heat-setting.
   - **Fix.** Raise the extensor wrap radius (EXT 5.0 -> 5.6) or shrink the wrap angle so the swept groove stays >= 1.6 mm from the Ø4 bore. Otherwise use the M3 short insert (L 3.0) set below the groove depth.

7. **minor / bionic_finger / fingerlib (W, GAP): lap gap is too tight and not on the layer grid.**
   - **Issue.** The gap is 0.3 mm total (0.15 per face), against s6 (0.3-0.4 per side) and s8 (0.5 mm). The 7.55 band and 0.3 gap are not 0.2 mm layer multiples, so the printed gap will land anywhere from 0.1 to 0.5 mm.
   - **Fix.** Band 7.4 (37 layers) and gap 0.4: shoulder 8 - 7.8 = 0.2 play, width 15.2. Re-run the sweeps and hard_stop.

8. **minor / bionic_finger / out/ASSEMBLY.md: the build guide is stale and incomplete.**
   - **Issue.** It says "Tools: none". It has no heat-set insert step, no tendon step (the distal assembly_note never appears) and no frame-mount step. Current kerf/ship.py would emit inserts and a screwdriver line, so out/ predates the engine change.
   - **Fix.** `kerf build bionic_finger` and confirm that all three items appear.

9. **minor / bionic_finger / BOM + DESIGN: drift between catalog, BOM and DESIGN.**
   - **Issue.** The shoulder-screw buy link is 97505A139 while the order number is 97505A106. There are 3 unconsolidated shoulder-screw rows. DESIGN s5 says "picks the 14 mm length", but the report has 8 mm. The base.py docstring still says "mcp dowel (pressed)". DESIGN has no mass budget (s11). Outside edges have no 0.5-1 mm chamfer (s5).
   - **Fix.** Correct the text and the catalog link. Add the mass table. Chamfer the outer long edges by 0.5 mm.

#### robot_arm

10. **major / robot_arm / base: no fea_static for the base.**
    - **Issue.** The base tower carries the full arm tipping moment through two bearing seats, across layers, and the build warning asks for exactly this proof. DESIGN.md:116 says the base FEA exists, and it does not.
    - **Fix.** Add base_fea, direction z, SF 3. Fix the desk holes (or rear pad). Load bearing_n on both 6001 seats with the ±34 N x 2 couple, 12.8 N axial on the upper seat shoulder, and the yaw-servo shelf reaction at MG996R stall through the gear (34 N tangential at the 36 T pitch radius).

11. **major / robot_arm / electrics: no overcurrent protection and no mains lead or switch.**
    - **Issue.** An 18 A supply (overload ~105-135 %) feeds 22 AWG servo leads through 4 moving joints. A pinched lead can carry about 20 A. The BOM has no mains cord/plug and no power switch, but the LRS has bare mains screw terminals (rule 10b: power connector, switch/fuse where needed).
    - **Fix.** Add a blade-fuse holder with a 5 A fuse per arm-servo branch (or one 15 A fuse at the bus plus 3-4 A polyfuses per servo). Add a fused IEC inlet with switch, or a mains cord with a strain-relief clamp, as catalog items with sources. Add them to power_budget.

12. **major / robot_arm / wiring + BOM: lead source and wire ends are ambiguous.**
    - **Issue.** The BOM buys 5 x 300 mm extensions, plus 5.0 m red/brown and 2.3 m orange 22 AWG, plus 21 splice heat-shrinks. pwr_gr needs a 710 mm cut, more than a ~300 mm MG996R pigtail plus a 300 mm extension. No 1-pin JR/Dupont housings or crimps for the split orange signal wire going onto the PCA9685 3-pin header.
    - **Fix.** Pick one scheme: either 500 mm extensions for the wrist and grip and no raw wire, or raw wire with a crimp-housing kit. Add servo lead length to the catalog servos and let WIRING subtract it. List every end termination.

13. **minor / robot_arm / upper_arm, forearm: FEA uses 2x static servo torque, not stall.**
    - **Issue.** This is inconsistent with yoke_r and gripper, which use stall. Elbow stall is 1863 N·mm vs 841 modelled, and the arm can crash into the desk (finding 18). My estimate still passes.
    - **Fix.** Re-run at stall torque (sh/el/wr), or state in DESIGN why stall is excluded.

14. **minor / robot_arm / upper_arm, forearm, gripper: horizontal pivot, insert and horn holes are printed round.**
    - **Issue.** These parts print [90,0,0], which puts the holes parallel to the bed (rule 4). The free 3.35 pivot hole will print tight vertically.
    - **Fix.** Add a teardrop to pin_hole (engine), or +0.2 on these holes.

15. **minor / robot_arm / yoke_l, yoke_r, turntable: front fasteners below rule-7 edge distance (need 6.1).**
    - **Issue.** The front foot screw at x=10 is 4.0 mm from the foot end at x=14 (yoke_l.py:8,20), at the FEA hot spot. The turntable front inserts at x=10 are 5.0 mm from the platform edge at x1=15.
    - **Fix.** Extend the foot to x=16.5 and the platform x1 to 16.5, or move the front screws to x=8.

16. **minor / robot_arm / BOM: missing washers and conflicting M2 rows.**
    - **Issue.** No M3 washers, although DESIGN says to shim the 1.5 mm side_gap with them. The BOM lists both "M2 x 5" (auto) and "M2 x 8" (bom_extra).
    - **Fix.** Add 6-9 M3 x 0.5 washers (ISO 7089) to bom_extra. Drop the M2 x 8 row, or change the fastener group so M2x8 is picked.

17. **minor / robot_arm / pivots: anaerobic threadlocker near PETG.**
    - **Issue.** Medium threadlocker on screws threading into inserts can wick into the PETG free holes and cause stress cracking.
    - **Fix.** Apply it only to the screw tip in the brass insert (sparingly), or use nylon-patch screws. Say so in the BOM note.

18. **minor / robot_arm / reach vs desk: the tool point goes below the desk.**
    - **Issue.** The TCP is below the desk top at shoulder < ~-22 deg, so the brief's ±60 deg is only usable at a desk edge. Nothing checks this.
    - **Fix.** Keep the DESIGN note, add a software limit table to DESIGN, and add a desk-plane keep-out (engine).

19. **minor / robot_arm / ASSEMBLY.md + project.yaml: assembly order is not declared and the guide drifts from DESIGN.**
    - **Issue.** There is no assembly.order. The generated guide omits the desk-first step and the pivot washers, and orders the yokes before the upper arm, unlike DESIGN step 7.
    - **Fix.** Declare assembly.order and key_access/bench steps matching DESIGN, then rebuild.

20. **minor / robot_arm / DESIGN.md: numbers drift from the report.**
    - **Issue.** Base 88 g vs 130.5 g (>10 %, rule 11). Gripper FEA 5.1/14.6 vs 7.22/20.42. Pivot M3x12 vs M3x14. grip_open 63.8 vs 62.9. project.yaml:6 and layout.py:5 say "shoulder-screw pivot", but it is a plain SHCS.
    - **Fix.** Update the text from report.json.

#### ENGINE (would recur in future projects)

21. **major / ENGINE / requirements:** Nothing checks that every structural part has a fea_static. A load-axis "across layers" warning can be left standing with only DESIGN prose. **Fix:** in `kerf check`, warn/fail when a part with load_axis has no fea_static or cantilever_stress, and make the across-layer warning a failure unless a direction-z proof exists for that part.
22. **major / ENGINE / fea_static + pins.py:** bearing_n spreads the load over the bore of one part. Single-shear screw/shoulder pivots, where pins.py already knows the free and fixed bands, need the lever moment. **Fix:** derive the offset from the pin record and add it automatically, or warn when a bearing load sits on a single-shear fixed bore.
23. **minor / ENGINE / wall check:** The p02 wall statistic hides local thin spots: 0.91 mm in bionic base, 1.0 mm at the distal pocket, 0.5 mm insert walls. **Fix:** add a local check of minimum distance from each hole/insert/pin to other cuts and faces, against rule 5 (1.2 / 2.4 / catalog heatset_min_wall).
24. **minor / ENGINE / proxies:** Screw-pivot hardware (shoulder screws, pivot SHCS, inserts) is not modelled. It is missing from interference, mass and key/driver access (bionic hex_keys = []). The slotted head type is not reflected in Tools. **Fix:** proxy pins with their heads and run access with the right driver.
25. **minor / ENGINE / ship.py:** The shoulder-pivot line says "an insert left proud clamps it". That is backwards: the shoulder bottoms on the insert, so a proud insert only adds play. A recessed insert (by more than shoulder minus band) is what clamps. Out/ docs are not tied to the engine version, so a stale ASSEMBLY.md passes verify. **Fix:** correct the text and include an engine hash in the out/ fingerprint.
26. **minor / ENGINE / iface.pin_hole:** It has no teardrop option, and no check flags round holes whose axis is parallel to the bed in print orientation. **Fix:** add a `teardrop=` argument and a check-level warning.
27. **minor / ENGINE / missing checks:** (a) gear tooth bending (Lewis) for spur_pair at actuator stall; (b) tendon/line termination bearing stress; (c) desk/ground-plane keep-out in sweeps; (d) BOM dedupe between auto fasteners and bom_extra (M2x5 vs M2x8); (e) servo pigtail length in WIRING/BOM.
- 2026-10-31 session 262017a2: tvc_drone A-1..A-14 fixed (commits 66cc038, cef68c2, 394d78d), review round 3 PASS. ENG-3 fixed, ENG-4 and ENG-7 partly (see table). New engine helpers on the way: FEA reports peak and max-deflection locations; `features.bed_chamfer` (ENGINEERING s5 first-layer chamfer); heat-set `relief`.
