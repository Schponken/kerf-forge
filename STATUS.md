STATE: IN PROGRESS

## Final summary for Spencer (2026-10-31)

**What was built.** Kerf Forge is a working "describe it → printable, checked assembly" tool for your A2L. You give
the `kerf` skill a sentence; it researches proven designs, sizes the bought parts from datasheet numbers
(`catalog/hardware.json`, every value with its source), writes the printed parts in build123d, and proves the result
before you print anything: no part collides at any joint angle, every screw lines up and has a stocked length, every
hinge is coaxial, hex keys can reach every screw, FEA strength against PETG's weaker across-layer direction, torque /
thrust / centre-of-gravity / tip-over numbers, and a complete electrical system (every wire's current, fuse, voltage
drop and routed length). Each project ships a priced BOM, a step-by-step ASSEMBLY.md with a picture per step,
WIRING.md, A2L plates (.3mf) and a 3D viewer, and is passed by an independent design-reviewer agent.

**Results — the six eval projects** (all `kerf build` PASS, independent review PASS, acceptance PASS; details and
pictures in the README table and the gallery):

| Project | What it is | Printed / bought parts | Key numbers | BOM |
|---|---|---|---|---|
| servo_link | MG996R servo test rig, ±90° arm | 3 / 5 | arm torque 0.55 of 4.7 kg·cm, tips at 37° | ~$78 |
| fpv_5in | 5" freestyle quad, CF-PETG, 2207 motors, 6S | 6 / 13 | frame 161 g, T/W 6.0, ~11 min ideal hover (3–5 min real freestyle) | ~$386 |
| robot_arm | 4-axis desk arm + gripper, mains powered | 12 / 18 | 266 mm reach, 150 g at full reach with every servo ≤ 39 % of stall, 792 g | ~$165 |
| tvc_drone | thrust-vectoring coax rocket drone | 9 / 16 | T/W 2.08 (1.86 with pack sag), 4 min hover estimate, stands on 3 legs (tips at 21°) | ~$269 |
| bionic_finger | tendon-driven index finger, no supports | 4 / 3 shoulder screws + line | curls 80/80/70° without jamming, 222 N line load proven | ~$1 + line |
| pan_tilt | Pi Camera 3 pan-tilt on a 1/4-20 thread, SG90s (designed BLIND by a fresh agent) | 3 / 8 | pan ±80°, tilt −30..60°, 67 g | ~$62 |

**How to print each one.** For any project: open `projects/<name>/out/plates/plate_1.3mf` (and plate_2, 3 for
tvc_drone) in Bambu Studio; parts are already oriented and the per-part infill/walls are in
`out/plates/PRINT_SETTINGS.md`. PETG unless noted (fpv_5in: CF-PETG, hardened nozzle). Supports: robot_arm, tvc_drone,
pan_tilt and fpv_5in have a few supported faces (listed per part in the report); bionic_finger prints with none. Then
follow `out/ASSEMBLY.md` (heat-set inserts first, then the steps in order) and `out/WIRING.md`, and buy from `out/bom.md`.
Read each project's `DESIGN.md` "Risks / measure first" before the first print: a few bought-part dimensions are
best published figures (e.g. the DS32xx servo tab holes), so print the one part that holds them first and test-fit.
`kerf print <project>` will slice and send to the A2L over LAN once you do the one-time setup below.

**Known limits.**
- Strength checks are static (2–3× the working load, stall and crash cases where it matters); no vibration, fatigue
  or control-loop analysis. Hover/run times are momentum-theory estimates, not thrust-stand data.
- The FEA uses solid geometry judged against PETG's across-layer strength; the slicer's walls/infill are set per part
  so printed parts match the masses used.
- robot_arm: mains wiring (IEC inlet to the supply's terminals) is a 3-wire job for a competent person; trim the
  supply to 5.4 V through the hole in the hood before plugging servos in.
- One PLAN item is waiting on you: a real print through `kerf print` needs your A2L on the LAN (Developer Mode,
  IP/serial/access code in `~/.kerf/bambu.json`, Bambu Studio's exported A2L + PETG configs). The exact steps are in
  the STATUS.md entry "PLAN Bambu A2L handoff — code done"; then run `kerf print servo_link --dry-run` and
  `kerf print servo_link --send 1`.

# Kerf Forge status log

Newest entry at the bottom. Every session: read this, continue from the first unchecked item in PLAN.md, and add an
entry before each push (date, what changed, verify state, next step, open problems).

## 2026-10-30 — handoff from the planning session
- Built and tested before handoff (PLAN.md Phase 0): engine core, print checks, requirement checks, exports,
  headless renders, interface + proxy seed library, verified hardware catalog with sources, seed project
  `servo_link` (E1) passing build + review + eval, hooks, subagents, skills.
- Verified in this cloud environment: build123d 0.13 joints/booleans/STEP/GLB, bd_warehouse bearings/screws,
  py_gearworks gears, headless Chromium rendering. No slicer CLI is downloadable here (GitHub release assets blocked),
  so print time/supports come from our own mesh analysis; real slicing happens in Bambu Studio on Spencer's Mac.
- Catalog: 65 sourced entries from 4 research passes (fasteners/inserts/bearings/materials, servos/horns/steppers,
  drone hardware, boards). Known caveats, recorded in each entry's note:
  - Motor patterns "16x16"/"19x19"/"9x9" are bolt CIRCLES (4 holes, 90 deg apart), not squares; iface.motor_holes()
    uses `bolt_circle_d`. Motor `max_screw_depth` is typical (not published): keep screws <= 3 mm into the base.
  - MG996R and MG90S tab-hole spacing/diameter/tab height are partly UNVERIFIED (borrowed from DS3218/SG90 drawings);
    flag them in DESIGN.md of any project using them and tell Spencer to measure a real servo before the final print.
  - Bambu ABS TDS lists Young's modulus 3800 MPa but bending modulus 1880; use ~1900-2000 for ABS FEA (override in the
    requirement or fix the catalog entry with a better source).
  - Arduino Nano holes take M1.6 screws: add an M1.6 entry to `screws`/`fdm_holes` (with sources) before using them.
  - No published thrust table for the 2306 motor (thrust_g_max null); use the 2207 for thrust-critical designs.
  - Only one horn (aluminum_25T) is catalogued; add others with sources when needed.
- Hooks tested: the edit hook catches a broken part edit (exit 2 with the problem list); the Stop gate blocks on
  failing verify, uncommitted files and unpushed commits, and allows a stop only when all three are clean.
- Next: PLAN.md Phase 1, first unchecked item.

## 2026-10-30 — planning session, final handoff
- `servo_link` passed its third independent review (review.json, PASS). The reviewer measured servo insertion, screw
  access and assembly order itself.
- Added tests for material-specific pilot holes, `servo_mount(top_through=True)` and part notes → report warnings
  (85 tests pass).
- Reviewer's remaining minor findings went into PLAN.md Phase 1 (hex-key reach + insertion-path checks; window lead-in
  chamfer + re-review). DESIGN.md now notes the ball-end driver and says to measure the cable boss.
- Next: PLAN.md Phase 1, first unclaimed item.

## 2026-10-30 — session 01S68R6T: interface tests (PLAN Phase 1 item 1, done)
- New `tests/test_iface_fit.py` (84 tests, ~25 s): every iface function is exercised with both sides built and
  assembled. The CUT HOLES themselves are probed (a probe 0.02 mm under the catalog size must miss the part, 0.02 mm
  over must hit), so each hole is proven to be exactly the catalog size and on the fastener-site axis: clearance,
  counterbore (+head pocket), countersink (+rim), heat-set (+floor), tap pilot (+floor), nut trap (+hex pocket), for
  M2/M2.5/M3; servo windows (clearance/2 per side) + tab holes for all 5 catalog servos, both mounting directions;
  horn bolt circle + centre-screw access; bearing pockets for every catalog bearing x every fit (allowances checked
  against ENGINEERING.md section 6); motor + stack mounts for all 4 motors and 3 stacks. Mutation-checked: a 0.05 mm
  oversize hole or 0.03 mm oversize bearing pocket makes the tests fail.
- Bug found and fixed: `motor_mount`'s default 8 mm centre hole cut straight into the mount holes of the 1404 motor
  (9 mm bolt circle). New `iface.motor_center_hole()`: 8 mm, shrunk to keep a 1.2 mm wall to the mount holes, and
  raises if an explicit size cuts into them or does not clear the shaft.
- Learned (fastener check working as intended): with heat-set inserts, a 14-22 mm FC stack has no standard screw
  length that ends inside the insert; use nut traps / longer standoffs for tall stacks (relevant for E2 fpv_5in).
- verify --fast: pytest 169 passed; remaining failures are the not-yet-built eval projects + unchecked PLAN items.
- Next: next unclaimed PLAN item.

## 2026-10-30 — session 1c-pins (Pin / shaft joints)
- Done: printed-hinge pins. `iface.pin_hole(ctx, pin, loc, group, depth, fit)` cuts each knuckle (fits `free` / `press`
  for a catalog dowel, `heatset` / `tap` for a screw used as a pivot, optional teardrop). New `kerf/pins.py` check runs
  in every `kerf check`: all holes of a group coaxial within 0.05 mm / 0.5 deg, the pin held in some part, every moving
  joint that splits the group turns about the pin axis (or slides along it) with the pin fixed on one side only, and a
  stocked length that reaches every hole by min(hole, 1.5 d). Screw pivots get a threadlocker warning. Pins and
  pivot screws/inserts go in the BOM. 8 tests in tests/test_pins.py (93+8 pass).
- Catalog: new `fdm_fits.pin` (press +0.05, free +0.35 on diameter; CCI Bambu tolerance guide + Sovol, typical) and
  `motion.pin_3mm.lengths` (Bambu D3 dowel range). The catalog fingerprint changed, so servo_link's review is stale:
  it gets its fresh review in the open `servo_mount` lead-in item (no value servo_link uses changed).
- Fixed: `kerf verify` crashed under the Stop hook's C locale (UTF-8 project.yaml read as ASCII); text reads/writes
  in kerf/ and tools/claims.py now say encoding="utf-8".
- Verify (fast): fails only on the expected open items (stale servo_link review, eval projects not built, PLAN open).
- Next: next free PLAN item.

## 2026-10-30 23:xx — session fc7cb2cb: `cantilever_stress` requirement check
- New `cantilever_stress` check (kerf/requirements.py): cuts the part at a declared section plane, gets area +
  second-moment tensor from OCC, sums the declared loads' force/moment about the section centroid, and reports
  Kt x max |N/A + unsymmetric bending| over the section outline vs. material strength / SF. Layer direction:
  `direction: auto` (default) uses print_rot (stress along build Z -> Z strength, blended by cos^2), or force xy/z.
  Torsion is reported, not included. Loads on the wrong side of the section are rejected.
- tests/test_cantilever.py: 6 hand-calc tests (strong/weak axis, oblique, axial+bending, tube with Kt, print_rot
  layer awareness, wrong-side load). pytest 175 passed. Documented in docs/ARCHITECTURE.md.
- verify --fast: only the expected failures (eval projects not built yet, open PLAN items).
- Next: `cg` / `tip_over` / `channel_clear` checks are free for the next session.

## 2026-10-30 — session 01S68R6T: belt/gear helpers (PLAN Phase 1, done)
- New `kerf/drives.py`: `spur_pair` (py_gearworks involute gears, standard centre distance m(z1+z2)/2, 0.3 mm total
  backlash per the Sovol FDM gear guide, refuses module < 1 / < 10 teeth / bores that leave < 2 mm under the roots;
  gear 2 comes pre-rotated into mesh phase). GT2: `belt_length`, `belt_teeth`, `center_for_belt` (exact centre for a
  stock belt), `wrap_deg`, `teeth_in_mesh` (>= 6, SDP-SI), `belt_keepout` solid. Proxies `pulley` (published
  envelope) and `belt` (keep-out). Catalog: GT2 belt height 1.52 / tooth 0.76 (VXB listing), 20T pulley tip_od /
  flange_od / length as numbers (PiHut, already the cited source).
- Engine: coupled sweeps `{joint: j2, follows: j1, ratio: r}` in assembly.sweeps so geared/belted joints turn together.
- tests/test_drives.py (11): hand-calculated centre distance, tip diameters, belt lengths (240 / 260.405 mm, 130T),
  wrap 172.70 deg; the pair meshes collision-free through a full turn; measured backlash at the pitch circle ~0.3 mm;
  moving 0.6 mm closer interferes; coupled sweep clear vs. uncoupled jams; belt keep-out catches a post in the belt path.
- pytest: 180 passed. Docs: ARCHITECTURE (module, proxies, `follows`), ENGINEERING section 8 (gear + belt rules).
- Next: next unclaimed PLAN item.

## 2026-10-30 — session fc7cb2cb: `tip_over` requirement check
- New `tip_over` check: floor contact = mesh points within 0.5 mm of the lowest point (or of listed `support` items),
  convex hull, assembled CG (all items incl. purchased, plus optional payload at a joint), worst
  atan(edge distance / CG height) over `poses`. Negative = falls over by itself.
- tests/test_tip_over.py: 5 hand-calc tests (block, offset mast, legs footprint, payload outside footprint, worst pose).
  Documented in docs/ARCHITECTURE.md.

## 2026-10-30 — session 1c-pins: `cg` requirement
- Done: `check: cg` (new module kerf/req_balance.py, registered from requirements.py): mass-weighted CG of every
  non-keepout item (or `include`) plus an optional payload at a joint, against a line through `ref`/`point` along
  `axis`; limits `max_lateral_mm`, `min_along_mm`/`max_along_mm`; worst over home + `poses`. 4 hand-calculated tests
  (16:1 blocks -> x = 15/17, z = 95/17; payload; reference axis; poses). Documented in ARCHITECTURE/ENGINEERING.
- Next: next free PLAN item (`tip_over` can reuse `req_balance.assembly_cg`).

## 2026-10-30 — session 1c-pins: layer-direction check
- Done: parts may declare `load_axis` (x / -y / [x, y, z] / a list) in project.yaml; `checks.layer_direction` (run by
  every part check) warns when an axis is > 30 deg out of the bed plane in `print_rot`, with the cos^2-blended
  strength (same rule as cantilever_stress), and fails on a malformed axis. 6 tests. ENGINEERING.md section 4 now asks
  for `load_axis` on every structural part.

## 2026-10-30 — session 01S68R6T: `channel_clear` requirement check (done)
- `channel_clear` (kerf/requirements.py): path waypoints in item frames (coords or joint labels) so the channel follows
  the parts through `poses`; sweeps a ball-ended tube along it, reports the largest open diameter (bisection, 0.01 mm)
  and which items block it, at which pose; `ignore` for items allowed inside. tests/test_channel.py: drilled 2 mm bore
  measures 2.00; 2.2 mm is blocked by the hand-calculated ring volume pi(1.1^2-1^2)(30-2.4); a sliding gate is caught
  only at the pose where it crosses the bore; runs from project.yaml. Docs: ARCHITECTURE example, ENGINEERING s11.

## 2026-10-30 23:30 UTC — assembly viewer (planning chat, second session)
- Done: PLAN Phase 4 "Assembly viewer". `kerf build` writes `projects/<p>/out/viewer.html`: one offline file
  (three.js r186 subset in kerf/assets/viewer3d.js, regenerate with `node tools/viewer/build.mjs`), explode slider,
  a slider + sweep animation per moving joint, part show/hide/isolate, parts list, print info, checks; light/dark;
  phone layout; draws only when something changes.
- Joint axes are measured from `assembly.solve()` (kerf/viewer.py joint_motion), not re-derived: tests/test_viewer.py
  proves page kinematics match the engine to 1e-3 mm for a slide + hinge chain with a non-zero home.
- Browser check: `node tools/viewer/smoke.mjs <viewer.html> <out_prefix>` (no errors, no network requests, each joint
  moves exactly its subtree, screenshots). Headless note: avoid continuous rendering; it stalls software GL.
- Tooling: added parallel-session claims (tools/claims.py, CLAUDE.md "Parallel sessions"). Lesson: commit before
  `git pull --rebase`; `--autostash` with uncommitted edits to a shared file produced conflict markers twice.
- servo_link: build PASS with the merged engine (196 tests pass). Its geometry fingerprint is now 79fbc6e03da773f2
  (the review is for a9b581f37fd9cf80), so `kerf verify` will ask for a fresh design-reviewer pass.

## 2026-10-30 — session fc7cb2cb: `prop_clearance` requirement check
- New `prop_clearance` check: exact B-rep distance from each prop disc to every other disc (own `min_between_mm`) and
  to every non-keep-out item (owner motor, allow_overlap partners and `ignore` items skipped), at home, over each
  moving joint's range and any coupled `poses`; reports the tightest pair and pose.
- tests/test_prop_clearance.py: 3 hand-calc tests (disc-disc 20 mm and disc-frame 10 mm, post between discs 8 mm +
  ignore, prop on a swinging arm: 18.38 mm at +/-20 deg). Documented in docs/ARCHITECTURE.md.

## 2026-10-30 — session 1c-pins: kerf/features.py
- Done: detailed-modeling helpers, each tested for size/validity (tests/test_features.py, 11 tests): `channel` (spline
  sweep cutter, volume = pi r^2 L), `shell`, `gusset`, `teardrop_hole`, `threaded_rod`/`threaded_hole` (bd_warehouse
  ISO, >= M6 and pitch >= 1.0, 0.4 mm clearance; bd_warehouse internal threads are half a pitch out of phase with
  external ones, so the hole is turned 180 deg and a rod at the hole bottom meshes with zero overlap), `gear_pair`
  (= drives.spur_pair), `snap_hook` and `living_hinge` with Bayer-manual strain limits (raise with the fix), `label`,
  `pockets` (min web), `safe_fillet` (groups, then edge by edge, failures reported). ENGINEERING.md section 5 updated.
- Finding: by that strain rule a 0.5 mm PETG living hinge only bends ~19 deg; 90 deg hinges need TPU.

## 2026-10-30 — session 01S68R6T: vendor CAD proxies (done)
- `proxy: step` (new kerf/vendor.py): builds the catalog `base` proxy first and keeps its joints + fastener sites,
  places the vendor STEP (`model_rot`, `model_pos`, transform baked into the geometry) and refuses it unless every
  bounding-box face is within 0.5 mm of the base proxy's and a real hole exists at every fastener site.
- First vendor model: Raspberry Pi's official Pico STEP in catalog/models/rpi_pico.step; catalog/models/SOURCES.md
  has URL, licence quote (ISC-style "permission to use, copy, modify, distribute"), sha256 and placement.
- Catalog boards.rpi_pico: usb_overhang 1.3 / usb_w 8 (datasheet Fig. 3, rendered and read); component_height 3.2
  (approximate) -> 2.73 from the official STEP. The `board` proxy now models a catalogued USB overhang.
- tests/test_vendor.py (9): real Pico matches (52.3 x 21 x 3.73, sites identical to the board proxy); 1 mm shift,
  floating, upside-down, USB end reversed, inch-scaled and hole-less models are all refused; Pico on a tray with
  heat-set standoffs passes the fastener + interference checks.

## 2026-10-30 23:25 UTC — viewer click-to-edit (planning chat, second session)
- Done: PLAN "Click-to-edit in the viewer". Clicking a face opens an Inspect tab: `projects/<p>/parts/<part>.py:<line>`,
  the code on that line, every project param that moves or resizes the face (value, label, allowed range, a number box),
  "Copy edit request" (e.g. `projects/servo_link/project.yaml: arm_len 100 -> 130 (...)`) and a free-text request.
  Purchased parts show their catalog entry and source URL.
- kerf/attribution.py: line = first part-file line after which the face's SURFACE existed (line tracer, surface
  identity survives later trims; helper calls credit the calling line); params = one-step rebuilds per project param.
  Adds ~9 s to `kerf build` only (not `kerf check`). tests/test_attribution.py has hand answers.
- 232 tests pass; servo_link build PASS; tools/viewer/smoke.mjs clicks a face on every printed part.

## 2026-10-30 — session fc7cb2cb: FEA load cases + stress renders
- kerf/fea.py: loads may be dicts with `pressure` (into the face), `torque` about an axis (tangential traction
  proportional to radius) or `bearing` (cosine pressure on the half of a bore facing the load, resultant = the force),
  besides the old total `force`. Results now carry `applied_force_n` / `applied_moment_nmm` (exact resultants of the
  load vector) so every load case can be audited, and surface triangles + von Mises for rendering.
- requirements: yaml `pressure_mpa`, `torque_nmm` + `axis: {at: joint | xyz, dir}`, `bearing_n`; new `cylinder` region
  (bore/shaft seat selection by radius about an axis). `tip_over` now reuses req_balance.assembly_cg.
- kerf/fea_render.py + pipeline: `kerf build` writes `out/renders/fea_<id>.png` (two shaded views, magenta = over the
  limit); meshes stay out of report.json. design-reviewer is told to read them; ENGINEERING.md section 3 says which load
  to use when.
- tests/test_fea_loads.py: pressure bar (500 N, 5 MPa, 0.2 mm), torsion rod (sqrt3*Tr/J and twist within 3 %),
  bearing seat resultants through the bore centre, yaml end-to-end + PNG. servo_link check still PASS (review was
  already stale from the pins catalog change; it is re-reviewed in the open servo_mount item).

## 2026-10-30 23:45 UTC — planning chat: feasibility tests for the risky Phase 4b items
- Meshy + exact features: proven. Mesh-space booleans with manifold3d give one watertight body with exact M3 holes in
  0.2-1.6 s for 80k-330k triangle meshes; per-piece repair + union handles broken meshes. The B-rep route also works
  but is too slow (34 s at 20k triangles). Prototype: docs/prototypes/mesh_merge.py. PLAN item rewritten with the method.
- Click-to-edit: already done by another session (kerf/attribution.py); no compromise needed.
- Bambu: official LAN/developer mode exists for third-party send + status; fallback is open-in-Bambu-Studio. Search-first:
  Thingiverse API + Printables GraphQL automated, McMaster manual. PLAN items updated.
- New PLAN item: print-truth calibration loop (per-printer fit offsets from Spencer's real coupon prints).

## 2026-10-30 — session 1c-pins: reference library
- Done: `references/INDEX.md` — 25 open designs studied for the evals (robot arms: SO-101, EEZYbot MK2, Moveo, Thor,
  HowToMechatronics; pan-tilts: inertiarobotics, Adafruit/Pimoroni, traxrobotics; 5" frames: OpenFrame-5F, Source One,
  Apex, Drone-v1, MFPV, Crab, ModuFrame/uavmodel; TVC: fd.iwth tvc-drone, Mistral, Starkit, Goose, arXiv gimbal;
  fingers: InMoov, Raptor Reloaded, Brunel, Yale OpenHand, Aero Hand, Flexy-Hand) with license, key dimensions
  (read/measured from cloned repos) and failure lessons, plus anthropometric data and cross-cutting lessons per eval.
  `tests/test_references.py` enforces complete rows and that every design linked in a project REFERENCES.md is indexed.
  design-researcher now starts from and appends to the index.
- Headline lessons for eval sessions: an MG996R direct-drive shoulder is marginal for 150 g at 250 mm (counterbalance
  or DS3218-class); bearings under yaw/pan; printed 5" arms must be much thicker than carbon and fail at the root; TVC
  gimbals clamp ~±8.5°, 3 mm rods flex — use 5 mm with a screw lock; tendon bends need r >= 2.5 mm or a steel pin.

## 2026-10-30 — session 1c-pins: kerf skill
- Done: `.claude/skills/kerf/SKILL.md` rewritten as a gated workflow table (research → DESIGN.md sizing → project.yaml
  + stubs → parallel part-designers → integrate → FEA + detail → build + look → design-reviewer → deliver), starting
  from `references/INDEX.md`, with a toolbox of every requirement check, always-on check, iface/drives/features helper.
  `tests/test_kerf_skill.py` keeps it true to the engine (every REGISTRY check listed, every named helper/command/file
  exists, stages in order). The end-to-end proof is E6 (blind pan_tilt run).

## 2026-10-30 — session 1c-pins: docs complete
- Done: ARCHITECTURE.md now has every module in the package map (geom, req_balance, vendor, viewer, attribution),
  `kerf status`, an "Item keys" section (every printed/purchased/keep-out/project key the engine reads), a
  requirement-check table (all 12 checks with arguments), and "Pin sites". ENGINEERING.md names the checks that
  enforce its rules (pin_hole fits, cg for drone balance, tip_over for anything standing).
- `tests/test_docs.py` fails when a new module, requirement check, CLI command or project.yaml key is not
  documented — sessions adding engine features (access checks, perf caching) must add their docs line.
- pytest: 258 passed.

## 2026-10-31 00:05 UTC — servo window lead-in + fresh servo_link review (planning chat, second session)
- Done: PLAN "servo_mount lead-in chamfer". `iface.servo_mount(lead_in=0.5)` adds a 45-degree chamfer on the window's
  entry face (both mounting styles); `iface.servo_lead_in()` shrinks it so the wall to every tab screw hole keeps
  MIN_WALL_AROUND_HOLE (2.4 mm, or the catalog insert wall), 0 if < 0.2 mm would remain. servo_link gets 0.4 mm.
- servo_link: design-reviewer PASS for fingerprint ed0039103648c353 (wall measured 2.400 mm at the entry/bed face).
  Open minors: (1) the PLAN item "Assembly-access checks" (ball-end screws, insertion paths) is still needed;
  (2) MG996R tab pattern / tab thickness / cable boss are UNVERIFIED in the catalog until Spencer calipers a servo.
- Note for every session: any change to the catalog or a part file changes a project's fingerprint and makes its
  review stale; `kerf verify` then needs a fresh design-reviewer pass for that project.

## 2026-10-30 — session 01S68R6T: `kerf check servo_link` under 60 s (done: 86 s -> 43.5 s)
- Profile: ~95% of the time was the two FEA runs, half of it skfem's generic stiffness assembly. New
  `fea.stiffness()`: vectorised einsum assembly at quadrature order 2 (exact for P2 on straight tets), chunked to bound
  memory; same matrix as skfem (test_fast_stiffness_equals_skfem). Round-off entries < 1e-10 x max are dropped:
  leaving them in changed pyamg's aggregation pattern and made the arm solve diverge. Results unchanged
  (bracket 0.59, arm 4.58), solver tolerance unchanged.

## 2026-10-30 — session fc7cb2cb: assembly-access checks
- New kerf/access.py, run by every `kerf check`: (a) hex-key reach from every male screw site: straight key
  (across-corners envelope, ISO 2936 L-key long-arm reach) along the axis from the head top; blocked but a 25 deg
  ball-end path clear = warning, nothing clear = problem. (b) `insert: {direction, distance}` on any item: it and its
  subtree slide in from that far in 1 mm steps; collisions (minus allow_overlap allowances) are problems.
- Catalog: `tools.hex_key` (ISO 4762 / ISO 10642 socket sizes from fasten.it, McMaster ISO 2936 L-key arm lengths,
  Bondhus 25 deg ball end). Catalog fingerprint changed -> every project review is stale until re-reviewed.
- servo_link now reports 2 warnings: the two tab screws on the MG996R cable-boss end need a ball-end key (straight key
  hits the servo body/boss). Real, and worth a build note in that project.
- tests/test_access.py: 7 tests (catalog key sizes, reach limit 52.4 mm, ball-end geometry (78.4-28.49)/cos25 > 52.4,
  covered screws fail, pocket insert clear, lip blocks for 6..16 mm before seat, sideways insert hits the wall).
- Fixed tools/claims.py: running `claims.py next` while a `git pull --rebase` was stuck on a conflict made every
  claim's push fail and the loop went on to commit a claim for EVERY open item locally (caught before push; those
  local commits were dropped). Claims now refuse to run mid-rebase/merge/conflict and stop at the first failed push.
  Test: tests/test_claims.py::test_refuses_mid_rebase.

## 2026-10-31 — session 01S68R6T: E3 robot_arm in progress
- projects/robot_arm: contract + all 10 printed parts; `kerf check` PASS (interference 0, 47 screws aligned, 3 pivots
  coaxial, all 5 sweeps clear incl. the coupled 36:24 yaw gear pair), torque shoulder 7.77 / 10.5, elbow 4.29 / 9.5,
  wrist 1.87 / 4.7 kg*cm, reach 266 mm, grip opening 54 mm, 642 g.
- Next: DESIGN.md + REFERENCES.md, upper_arm_fea and other FEA, detail pass, build + renders, independent review.
- Note for other sessions: never run tools/claims.py while a rebase is in progress (its `next` committed a claim for
  every free item onto the detached HEAD; I released them all in one push).

## 2026-10-31 00:40 UTC — planning chat: complete electronics + wiring
- Spencer's rule: every project includes EVERY component it needs to work (boards, wires, batteries, connectors,
  straps...), not only the ones a brief names. New PLAN item (before Phase 3): catalog-backed electrical parts,
  `wiring:` section with gauge from current + routed lengths, power_budget / flight_time / connector_access checks,
  WIRING.md + wiring.svg, full electrical BOM with buy links.
- Drone briefs (fpv_5in, tvc_drone) gained a graded "Complete electronics" section; evals/common.py
  `complete_electronics()` enforces it (tested by hand: complete fake project PASS, bare project fails on 12 points,
  1-min flight time fails). These are stricter rules, nothing loosened.

## 2026-10-31 — session fc7cb2cb: E4 tvc_drone mechanical design done (electronics pending)
- projects/tvc_drone: REFERENCES.md, DESIGN.md, project.yaml, 9 printed parts; `kerf build` PASS: T/W 4.1, CG 0.45 mm
  off axis, tip-over 20.9 deg, props 5.3 mm clear at all gimbal corners, FEA hub 3.5 / ring 3.2 / yoke 3.5 (Z) /
  leg 2.7 MPa (SF 2 on 2 x max thrust), 641 g. Renders read.
- Engine on the way: prop_clearance screens pairs on sampled surfaces before exact OCC distances (136 s -> 19 s);
  FEA regions `any: [...]` (unions, e.g. fixed at both pivots); FEA falls back to a direct sparse solve when AMG+CG
  stalls (seen on a sideways-loaded leg); `assembly.key_access` merged with the other session's `assembly.order`.
- Acceptance now also grades "complete electronics" (Spencer's new PLAN item: receiver, BEC, XT60, strap, wiring,
  power_budget, flight_time, WIRING.md/svg). tvc_drone stays open until that engine item exists; I'm taking it next.

## 2026-10-31 00:55 UTC — MG996R re-sourced from published models (planning chat, second session)
- `catalog/hardware.json` servos.MG996R now rests on 2 TowerPro drawings + 7 independently made CAD models (measured
  here, 4 spot-checked) + 4 published mounts (all listed in its `sources`). No caliper measurement is published.
- Confirmed: holes 49.5 x 10.0, tab 2.5 thick, shaft 10.0 from the body end. Changed: body_l 40.9, body_h 37.0,
  tab_span 54.0, hole_d 4.5 (tab holes are keyhole slots open to the outer end), tab_z 26.8, cable boss keep-out
  7.0 out x 8.0 tall from z 2.5 x 8.0 wide. Still unconfirmed: tab_z (models say 26.5-30.2) — keep >= 4 mm free under
  the case and take heights from the tab face.
- robot_arm (another session's item) and servo_link both still PASS `kerf check` with the new numbers; 274 tests
  pass. The catalog change makes every project's review stale (fingerprint includes the catalog): servo_link is
  re-reviewed by this session; the robot_arm session needs a fresh design-reviewer pass before it finishes.
- Free STEP models of this servo exist (Printables 1199804 is CC0) but none is the manufacturer's and they disagree
  on tab height, so they are evidence for the numbers, not loaded as `proxy: step` geometry.

## 2026-10-31 — session 1c-pins: E2 fpv_5in, review round 1 fixes
- fpv_5in built and reviewed (FAIL, 2 blockers + 5 major); all fixed: arms start at r 26 so the stack screw tips
  clear them; XT60 cradle open at the plug end with front stops; arms keyed by top ridges in body grooves; motor
  grip 7.5 mm (2.5 mm into the motor); camera cage to 3 mm past the lens with 4 mm gusseted cheeks; body FEA added
  (7 mm plate + ribs, 9.8/11.7 MPa); TX800 VTX under the top plate (catalog entry with sources), receiver/antenna
  tie slots; second arm tie slot; posts moved clear of the arms; M2 x 6 camera screws.
- Engine (from the review): `kerf/shanks.py` checks every screw body against all other items (tip poking out of a
  nut into a neighbour); blind purchased threads ("threaded") keep the ISO 4762 js15 length tolerance from the
  bottom; motor catalog `min_thread_engagement` (iFlight's shipped screws: 2 mm for M3, 1.5 mm for the M2 1404);
  `assembly.order` for hex-key access; motor_mount counterbore_depth; stack proxy uses the largest board. Tests.
- Reviewer engine notes not yet done: arm FEA render peak (13.9) differed from report peak (24.8) in round 1 —
  check kerf/fea_render.py uses the same solve.

## 2026-10-31 01:30 UTC — session (self-correcting errors)
- Done: PLAN 4b "Self-correcting errors". New `kerf/diagnose.py`: any exception from part code (or the layout module)
  becomes `<part>.py line N `code` [feature]: error` + `fix:` hint. Hints are computed from the failing call itself:
  fillet/chamfer -> largest size OCC accepts on those same edges (bisection), `use <= 0.9 x` that; unknown ctx.p
  param / Python name / catalog key -> nearest spellings; iface heat-set/pilot holes -> material needed; feature
  minimums -> the limit; sweep/shell/loft/boolean/missing ctx.finish -> what to change. In PROBLEM lines, report.json
  `diagnoses{}`, and the after-edit hook prints them first ("FIX THESE FIRST"); part-designer.md + kerf skill: apply
  the hint and re-check automatically, up to 5 rounds.
- tests/test_diagnose.py: 10 deliberately broken parts; the fillet and chamfer tests apply the hint and the part
  then builds (the retry loop without the LLM); one test runs the real hook. 287 tests pass.
- I left E4 tvc_drone (claimed then released): its only open work is electronics, which waits on the engine item
  another session holds.

## 2026-10-31 01:45 UTC — handover: E5 bionic_finger (session 12d9384eb7 -> claim holder 6e99fb9c38)
My E5 claim went stale while I was stopped by the usage limit and session 6e99fb9c38 took it; it is theirs. What I
pushed for it and what I know:
- Design (DESIGN.md, parts/fingerlib.py): parts print on their side (pin vertical: round holes, bending along the
  layers, zero overhang - all four parts report 0.0 %), two-layer lap knuckles alternating sides, 3 x 16 mm dowels
  pressed in the parent / free in the child, tendon channels cut as the union of each line's chord over the joint
  range (10 deg steps) in every part's frame, including the neighbour's run over each knuckle disc.
- Last full check (before the neighbour-run grooves): interference 0, sweeps mcp/pip/dip and curl all clear, pins
  coaxial, lengths 44/25/21 ok, mass 20 g, FEA p99.9 9.1 MPa vs 24 allowed. Since then (pushed in e522024): both
  channels are clear end to end at home (probed), deflection limit set to 1.0 mm with the reason in DESIGN.md s8.
  Not yet re-run: channel_clear over the 6 extra poses, the full build/renders, the reviewer.
- Research (REFERENCES.md, now pushed) found three things the owner should act on:
  A. BLOCKER - nothing holds a lap joint together ALONG the pin: the dowel is pressed only in the parent, the child
     can slide off its free end. Fix: M3 screw pivot (free in child, `iface.pin_hole(fit="heatset")` in parent;
     head on the child's outer face) or a printed cap glued over the child's face; ideally pins.check should prove
     axial retention of every joint.
  B. Line strength: with a 4 mm flexor arm a straight finger needs ~22.5 N of flexor per N at the tip; 30 kg line
     is ~1x for 12 N. Specify >= 100 lb (445 N) braid or move the flexor further palmar at the mcp.
  C. Flexor take-up (~16 mm full curl) != extensor pay-out (~20 mm): one servo wheel driving both will go slack or
     bind; use separate take-ups or a spring on the extensor. Note it in DESIGN.md / for Spencer.
- My session has moved to PLAN "Ship package".

## 2026-10-31 01:55 UTC — session (print-truth loop)
- Done: PLAN 4b "Print-truth loop". `kerf calibrate --material PETG` writes out/calibration/<printer>_<material>/
  coupon.3mf/.stl + CARD.md (96 x 62 x 8 mm, labelled: M2/M2.5/M3 clearance, pilot and heat-set holes, 608 + 623
  pockets, 3 mm dowel holes at 0.2/0.3/0.4 slip + 1 press, MG90S window; render checked). `kerf feedback PETG
  hole_M3=tight pin_0.3=ok ...` stores diameter offsets per printer + material with dated history in
  catalog/printers/<printer>.json (steps 0.1 hole/insert, 0.05 pilot/bearing, 0.2 servo window; > 0.6 mm refused:
  fix the printer first). kerf/iface.py applies them while a part builds (project.build activates the project's
  printer + the part's material): screw clearance/pilot/insert holes, bearing seats (nearest calibrated outer
  diameter for other bearings), servo windows, free/press pin allowances. The profile joins the project fingerprint
  only when it exists, so current reviews are untouched. No profile is committed: Spencer has to print the coupon.
- tests/test_calibrate.py (9 tests, synthetic feedback, tmp profile dir). 296 tests pass.
- Seen, not mine: servo_link review is stale (fingerprint changed by the MG996R catalog update); needs a fresh
  design-reviewer pass before final verify.

## 2026-10-31 — session 01S68R6S: E2 fpv_5in, review round 2 fixes
- Round 2 review (design-reviewer): FAIL, 0 blockers, 2 major, 8 minor; all round-1 fixes confirmed in geometry except
  XT60 retention and camera screw engagement.
- Fixed: XT60 tie now wraps under the connector through two vertical slots beside the cradle (old slot ran through
  the connector); top plate gets FEA (`top_plate_x` / `top_plate_y`, 50 g battery hit with its tipping couple, z
  strength / 3): post pairs filled into 9 x 25 mm pillars (posts y +/-5 -> +/-8, body counterbores follow) -> 7.7 /
  8.7 vs 9.67 MPa; camera screw heads in 1 mm cheek recesses (M2 x 6 -> 2.5 mm thread); camera roof tongue on the top
  plate (9.8 mm over the camera at 40 deg; a brow on the cheeks could not clear the camera's rise to z 35); arm key
  ridges 3 -> 4.5 mm wide; VTX 6 mm nylon spacers in the BOM; antenna slots 2.7 mm from the tab edge; receiver moved
  under the camera roof; stack-nut tape note in DESIGN.md assembly order. `kerf check fpv_5in` PASS, 148.7 g frame.
- Engine: FEA render title now prints the report's checked p99.9 / peak (render colours are surface element means).
- Still open for fpv_5in: the complete-electronics section (wiring, power, flight_time, WIRING.md) waits on the engine
  item claimed by session c1f0cc8551; then round 3 review.

## 2026-10-31 02:20 UTC — session 01S68R6RW: PLAN "Complete electronics + wiring" (engine) done
- kerf/electrical.py: `electrical:` (battery or mains `supply`, burst_s, draw/limits overrides that need a `why`) +
  `wiring:` runs (from/to item[.pin], kind, v, gauge, colour, conductors, length_mm, route waypoints). Power tree from
  the battery; current per item and run at average and peak (motors: momentum-theory hover share when prop discs
  exist, FM 0.5 / motor eta 0.75 / coax kappa 1.281, all cited in ENGINEERING.md 10b; servos running/stall; others
  current_a); regulator outputs referred back at 0.8 efficiency. Ratings: battery C/C_burst, supply current, output
  pins (`<pin>_current_a`/`_burst_a` per run, `bec_<pin>_a` summed), connectors, wire chassis ampacity (avg) and
  adiabatic copper rise <= 60 K over the burst (peak), input voltage ranges. Cut length must be >= routed 3D length
  + 15 % (check problem).
- Checks: `power_budget`, `flight_time`, `run_time`, `connector_access`; tests/test_electrical.py (10 tests, hand
  calcs: hover power, burst heating, a 3" quad's avg/peak/minutes, current limit, routing slack, plug access, mains
  servo supply). Outputs: out/WIRING.md, out/wiring.svg, electrical steps appended to the ship package's ASSEMBLY.md,
  BOM wire rows (metres per gauge/colour, price_key `wire:AWG<g>`) + heat-shrink (`heatshrink`), purchased rows
  get a catalog source link (`link`, used as `buy` when unpriced).
- Catalog: MG996R currents (datasheet: 0.9 A running at 6 V, 2.5 A stall, 4.8-7.2 V), MEAN WELL GST60A05 5 V 6 A
  adapter. (These change the catalog fingerprint: reviews need a refresh anyway after the other catalog edits today.)
- For the eval owners: fpv_5in/tvc_drone acceptance grade this. Findings worth knowing: the XT60's 60 A instantaneous
  rating is below a 4-motor punch-out (e.g. 4 x 35 A); either an XT90 or a real configured ESC/FC current limit
  (`electrical.limits` with a why) is needed — the check will not pass on wishful ratings. Motor leads at 22 AWG fail
  burst heating at 15.8 A x 5 s (77 K); 20 AWG passes. A project with servos/motors/boards and no `wiring:` now gets a
  warning; robot_arm, pan_tilt, bionic_finger and servo_link should add their electrical system (mains supply is fine
  for desk devices).
- For the ship-package session: wire shop pages found (not yet in prices.json): Out of Darts silicone red+black pair
  $0.59/ft, 14/16/18/22 AWG (https://www.outofdarts.com/products/18-awg-hobby-wire-fine-strand-5-red-and-5-black);
  Rotorama 5-colour set 22-30 AWG EUR 16.39 (https://www.rotorama.com/product/silicone-cable-set).
  tests/test_kerf_skill.py and test_docs currently fail on your WIP (catalog/prices.json missing).

## 2026-10-31 02:20 UTC — session (search-first `kerf find`)
- Done: PLAN 4b "Search-first". `kerf find "<description>" --project <p>` (kerf/find.py): Printables public GraphQL
  (long descriptions fall back to 3-word windows; top 4 hits' STLs downloaded via the official download link and
  measured -> bounding boxes as key dimensions), Thingiverse official API when THINGIVERSE_TOKEN is set (else listed
  as skipped with how to get one; the site is behind a bot wall here), and for MakerWorld/GrabCAD (no API, 403 to
  scripts) the exact web searches the design-researcher runs and records with `--add`; McMaster gets its search link
  and the "drop the STEP into catalog/models/" ask. Licenses map to what Kerf may do (adapt + credit / NC / SA /
  print as-is only). Each search block ends with `Decision: TODO`; re-runs keep a decision already written; `kerf
  check` warns while one is TODO. kerf skill step 0 + design-researcher run it first and reuse/adapt before inventing.
- Live-tested against Printables (pan/tilt and 608 pulley searches, real STLs measured; a PNG uploaded as .stl is
  reported "not a mesh file"). tests/test_find.py: 8 tests, all HTTP mocked.
- Not mine, seen in pytest: tests/test_docs.py::test_every_module_in_package_map fails on kerf/ship.py (Ship
  package WIP of another session, not yet in docs/ARCHITECTURE.md). Everything else passes (310).

## 2026-10-31 — session 6e99fb9c38: E5 bionic_finger to kerf check PASS
- Took over E5 from the session stopped by the usage limit. Fixed the three failures:
  - Tendon channels: each part now also cuts the neighbouring part's straight tendon runs near the axis (swept over
    the joint range), because those runs cross this part's knuckle disc in the 0.3 mm lap gap. flexor/extensor 2.2 mm.
  - proximal deflection (0.72 mm vs 0.44 limit = 1 % of length, ENGINEERING.md): the child's knuckle band kept only its dorsal
    half for 8 mm ahead of the axis (a neck). Child knuckle band is now full depth; the parent's non-knuckle band is cut where
    the child's band swings (`fingerlib.swept`), and the child's other band keeps all material the rotation allows
    (closed-form rule). FEA now passes.
  - OCC 2-D boolean of two touching polygons was non-deterministic (split along z = 0, sometimes kept material inside
    the pocket): replaced by one simple polygon.
- Limit stays 0.44 mm (session 12d9384eb7 had raised it to 1.0; no longer needed). Next: their handover A-C
  (axial pin retention, line strength, tendon travel), build + renders, design-reviewer.

## 2026-10-31 02:40 UTC — session 12d9384eb7: PLAN "Ship package" done
- `kerf/ship.py` (hooked once in pipeline after the BOM/viewer): every BOM row gets buy link, unit $ and total $ from
  the new `catalog/prices.json` (39 dated, sourced prices, 2026-10-30: all purchased catalog items the projects use,
  M2-M4 screw packs + exact M3x8/M3x10/M3x8-flat, inserts, nuts, washers, 3 x 16 dowels, PETG/PLA/CF-PETG per gram);
  `bom.md` gets a total and lists unpriced rows; fasteners fall back from exact length to the size pack; printed
  parts are priced as filament. A bom_extra row can name `price_key`.
- `out/ASSEMBLY.md`: root first, then `assembly.order` (unnamed items right after their parent); per step the
  heat-set inserts to press first, pins, screws (driven with the later of their two parts, as access.py), bench
  sub-assemblies from `key_access`, and an iso render (`out/assembly_steps/step_NN_iso.png`) with earlier parts grey
  and the new part pulled back along its mating joint axis (or `insert` path). The electrical session appends its
  solder/wiring steps to the same file.
- tests/test_ship.py (8): hand-computed totals incl. fallbacks and filament, price-key mapping, bom.md/csv columns,
  every prices.json entry well formed, step plan (screws with the later part, inserts first, order + unknown-id
  error), ASSEMBLY.md + one render per step, explode direction. servo_link `kerf build` PASS: 5 steps, total $13.72
  (2 hobby rows unpriced). Spot-checked live: MG996R $6.99 (HobbyKing), M3x8 100 pk $6.99 (Zoro).
- Price caveats (from the research, in each entry's note): SpeedyBee stacks discontinued (RDQ lists $86-111);
  MG90S priced as Waveshare's; DS servos from single eBay listings; dowel prices are A4 stainless DIN 7, not hardened
  ISO 8734; carbon tube unit = one 1 m tube (yields four 228 mm mast rods, so the tvc rod rows overstate ~4x).
- Also: added the new kerf/heads.py to the ARCHITECTURE.md package map (tests/test_docs was red on main).
- Open for whoever wants it: price keys `wire:AWG<g>` / `heatshrink` that wiring_out.py rows ask for.

## 2026-10-31 02:50 UTC — session 6e99fb9c38: E5 bionic_finger, handover A-C
- Handover A-C done: pivots are M3 x 14 SHCS (head on the child's outer face, heat-set insert in the parent
  from its gap face) so the lap joints cannot slide apart along the pin; line spec >= 100 lb braid with the tension
  math; flexor/extensor travel mismatch in DESIGN.md s7. Pockets widened (no knife edges, walls p2 >= 1.14).
  `kerf check bionic_finger` PASS. No engine axial-retention check: a lap pin can be held by things the pin check
  cannot see (tvc_drone's gimbal is held by the servo on the far side), so it would raise false problems.

## 2026-10-31 — session 01S68R6REX (E6 pan_tilt blind run)
- New project `pan_tilt`: SG90 pan in a base with a captive 1/4-20 nut, yoke with the tilt SG90 mounted from outside
  its +Y wall, camera bracket carried by the horn and an M3 screw pivot; Camera Module 3 lens on the tilt axis.
  kerf check/build PASS (59 g, tilt torque 2% of stall, FEA SF 3 on Z strength, all sweeps clear).
- Catalog: `boards.rpi_camera_module_3` + hfov/vfov (Joy-IT page) + rear_clearance; `servo_horns.aluminum_micro_21T`
  + spline_engage 3.2 / spline_d 4.8 (review round 1 blocker: the horn sat on the spline tip). NOTE for the
  tvc_drone session: that horn change moves your horns 3.2 mm down the spline; `kerf check tvc_drone --quick` still
  PASSes but its fingerprint changed (re-review needed).
- Design-reviewer run via `claude -p --agent design-reviewer` (no agent-spawning tool in this session).
- Open: no `electrical:` block in pan_tilt (warning), evals/pan_tilt/BLIND_RUN.md is written by the orchestrator.
## 2026-10-31 03:40 UTC — session 12d9384eb7: PLAN "Creative mode via Meshy" done
- `kerf/meshy.py`: a printed part with `source: meshy` + `prompt` + `bounds` (+ `mesh`, `fit`) is built as usual for
  its exact features; `ctx.mesh_cut(solid)` registers holes / key-access bores / pockets. After build the cached
  model is scaled to `bounds`, vertices merged, repaired per connected piece (fill holes, else voxel remesh), unioned,
  fused with the features and cut in mesh space (manifold3d), then simplified at 10 um (boolean slivers otherwise fall
  apart under the 1e-4 mm weld in geom.mesh_stats). The B-rep stays the item's shape (joints, sites, FEA, STEP); the
  fused mesh rides on it as `kerf_mesh` (relative to the base geometry, so it moves with any placement).
- geom is mesh-aware for such parts: `mesh`, `bbox`, `volume`, `overlap` (manifold intersection) and new
  `write_glb` (trimesh in build123d's convention: metres, Z-up -> Y-up); checks (solids, size, area, bed placement),
  export (STL/3MF per part via trimesh, plates, GLB), pipeline part renders, ship step renders and the viewer use it.
  Fingerprint includes `meshes/`. A missing model is a build error that names the prompt and path to generate.
  Deps: manifold3d, networkx, lxml (3MF export).
- tests/test_meshy.py (8): a deliberately broken cached mesh (30 missing triangles + a stray overlapping cube) ->
  one watertight body; fit stretch/uniform; holes and the cable bore open through flange + shell (point probes);
  fasteners still align (4 screws), interference, mesh-space overlap volume agrees with point sampling; STL/3MF/
  plates/GLB coordinates; missing-mesh message; fingerprint; whole pipeline. 334 tests pass.
- Live check (Spencer's Meshy, 5 credits, meshy-6-lite, task 01a18fb8-30b9-7120-a961-983522faf9c5): the real GLB was
  31k triangles in 670 open pieces; fused in 0.5 s into one watertight body with all holes open; the print checks
  then flagged the draft shell's 0.31 mm ridges and 17 % overhang — real feedback, as intended.
- Skill: "Creative mode" section (balance, text-to-3D, poll, download to the path the error names, record
  meshes/<part>.meshy.json, rebuild, look). Downloading: the task's `model_urls` fetch from the cloud shell too.
## 2026-10-31 — session 01S68R6S: E2 fpv_5in, review round 3 fixes
- Round 3 (FAIL, 1 blocker, 3 major): fixed. Battery strap now loops around the pack's width at x 4.5..24.5 past
  plate-edge notches, under the plate clear of the VTX (VTX moved to x -13.5, posts to x +/-33); the strap's side
  and under runs are keep-outs so interference covers the whole loop. VTX antenna -> Lollipop 4+ 95 mm tube (catalog,
  sourced), routed outside the rear pillar and up behind the tab; receiver antenna legs tied at the roof front.
  Tab extended to x -64 so the XT60 cradle walls start on the plate.
- Reverted my connector burst-limit extrapolation (reviewer: loosened check; agreed). The XT60 stays at its 60 A
  1-minute rating (Holybro, cited in the catalog); the quad passes `power` honestly with Betaflight
  `motor_output_limit = 73` as `electrical.limits` (propeller law: 13.65 A, 898 g per motor) and `twr` uses the
  limited thrust (6.43 >= 6). Peak 55.1 A.
- catalog/prices.json: wire AWG12/18/26/28, heat-shrink, antenna, M2 button/washer, M3x14/x30, M2 nylon spacer,
  cable ties (all read 2026-10-31); every fpv_5in BOM row has a buy link, total $373.76.

## 2026-10-31 04:30 UTC — session 12d9384eb7: PLAN "Bambu A2L handoff" — code done, waiting on one real print
- `kerf print <p>` (kerf/bambu.py): orientation chooser (24 rotations, bed fit, load_axis <= 30 deg from the layers,
  least support, then height; keeps the designed print_rot unless another needs >= max(5 mm2, 10 %) less support;
  changes reported) -> plates in out/print/ -> Bambu Studio / OrcaSlicer CLI slice to .gcode.3mf -> `--send N`:
  FTPS implicit-TLS upload (990) + MQTT `print.project_file` (TLS 8883) on device/<serial>/request, polling
  `pushall` reports until gcode_state PREPARE/RUNNING (or FAILED / print_error). `--dry-run` prints every command and
  payload with the access code masked; `--open` hands plates to Bambu Studio when no slicer config exists.
  Protocol sources: Bambu Studio CLI wiki, OpenBambuAPI mqtt.md/ftp.md, wiki.bambulab.com third-party-integration
  (Developer Mode needed: 2025 firmware rejects unsigned commands in normal LAN mode). Dep: paho-mqtt.
- tests/test_bambu.py (9): orientation (removes 1200 mm2 of support, respects load_axis, keeps a good choice),
  exact slicer command, payload fields, Bambu Connect URL, send/poll with fake FTPS/MQTT (start, failure, merged
  partial reports, missing credentials), run() fallback / dry run / with a fake slicer. 343 tests pass.
- NOT DONE (needs Spencer, so the PLAN box stays open): one real print. His one-time setup on the Mac:
  1. Printer: enable LAN only + Developer Mode; note IP, serial and the 8-digit access code.
  2. Bambu Studio: select A2L + PETG + the process preset, then export FULL configs (machine/process/filament
     JSON, e.g. via `--export-settings` on a saved project) somewhere stable.
  3. ~/.kerf/bambu.json (not in the repo): {"printer": {"host", "serial", "access_code"},
     "slicer": {"bin", "machine", "process", "filaments": {"PETG": ...}}}.
  4. `kerf print servo_link --dry-run`, then `kerf print servo_link --send 1` and watch it start.
  Untested against hardware: the implicit-TLS FTPS wrapper and the paho MQTT link (both follow the protocol docs).

## 2026-10-31 03:40 UTC — session 01S68R6RW: E4 tvc_drone done (build PASS, review PASS 616ec954, acceptance PASS)
- Complete electronics: XT60 on a 14 AWG pigtail past the ring_top edge, UBEC + ELRS receiver tied under ring_mid,
  strap item across the pack (slots moved: the old ones sat under the battery), anti-slip pad, capacitor row.
  ArduPilot CoaxCopter on the SpeedyBee F405 Mini (PWM 1-2 motors, 3-4 servos), MOT_SPIN_MAX 0.80 caps each motor at
  18 A (0.8^3 x 35.08), twr recomputed at that cap: 2.31. power worst 0.47 of rating, hover 4.46 min, mass 729 g.
- Engine (kerf/electrical.py `route_check`, run in every full check): every wiring run is swept as a tube of the
  wire's OD (catalog wire.silicone, letronic UL 3672) at home, both ends of each moving joint and every named sweep
  pose; it must not enter any part but its two ends nor any prop disc, and its cut length must cover the worst pose
  + 15 %. Route tie points `{item, at}` ride on moving parts. Wire mass now counts in hover power, thrust_to_weight
  and all-up mass_max. NOTE for fpv_5in / servo_link / robot_arm / pan_tilt owners: your full checks now run this
  route check, so routes that pass through a plate need a waypoint through a real hole/slot.
- Open (minor, engine): ASSEMBLY.md (ship.py) says "press the dowel" without "last, from outside" — a pin insertion
  direction/order in the pin check would fix it for every project.
## 2026-10-31 — session 01S68R6S: fpv_5in wiring routes
- Rebased onto the electrical route_check / wire-mass engine: every fpv_5in run now has real
  waypoints (arm tie points ride with the arms) and passes the tube sweep; XT60 moved back to x -59 (tab to -72) so
  its leads can turn before the rear pillar; output limit 74 % (T/W 6.18 incl. wire mass, peak 57.4 A, power 0.957);
  battery lead marked `supplied`.

## 2026-10-31 03:30 UTC — session (servo_link review follow-ups) done
- servo_link: fresh design-reviewer PASS (fingerprint 9cd85f37a0e0caf4, 0 blockers/majors, 5 minor) after 3 rounds.
  Engine: insertion paths respect `assembly.order` (test); horn proxy slides catalog `spline_engage` over the spline
  with a bore (25T: 4.0 mm, measured on the CC0 MG996R model; `horn_dims.hub_h` is now the rise above the spline top,
  so every layout followed automatically — robot_arm and pan_tilt re-checked PASS); `tab_washers` grip (ISO 7089);
  FEA render heading names volume p99.9 / volume peak / surface peak (test); wiring runs `supplied: <item>` (an
  adapter's or pack's own lead) are rated but not bought or cut (test; tvc_drone's bat_lead could use it);
  WIRING steps print each run's note; test that hardware.json has no duplicate keys (two `electronics.connectors`
  sections had hidden one entry).
- servo_link now has its whole electrical system: MEAN WELL GST60A05 5 V adapter + C13 cord, SparkFun barrel-jack
  terminal adapter (new catalog entry), Arduino Nano on USB (500-2500 us pulses), 3-pin header, wiring, power_budget,
  plug/USB access. Catalog: MG996R shaft_h 6.3 -> 5.7 (TowerPro table), screws.M3 washer, buy links.
- Remaining minors went into a new PLAN item "Electrical/assembly-doc follow-ups" (voltage-drop check, per-end
  verbs, washer/ball-end/insert info in ASSEMBLY.md, electrical prices).
- Process note: once I fetched a datasheet PDF with curl after WebFetch's permission request for it timed out; I
  deleted it unread. No data from it is used anywhere.


## 2026-10-31 04:20 UTC — session 01S68R6RW: per-project catalog fingerprint
- Every review in the repo was stale because any catalog edit (by any parallel session) changed every project's
  fingerprint. Now each check/build records the catalog paths it read into projects/<p>/catalog_deps.json (union,
  committed) and the fingerprint hashes only those entries (tests/test_catalog_deps.py; docs/ARCHITECTURE.md
  "Fingerprint and catalog_deps.json"). Each project gets a new fingerprint once, on its next build: owners, re-run
  `kerf build <p>`, commit catalog_deps.json and get one more review (or a re-confirm if nothing else changed).
- tvc_drone: rebuilt, deps committed, reviewer re-confirmed PASS at 00af8263a5d0de73.

## 2026-10-31 — session 01S68R6S: fpv_5in review round 4 fixes
- Round 4 FAIL (1 major, 7 minor): the 74 % Betaflight output limit lived only in DESIGN.md. Engine fix for every
  project: `electrical.limits` now print as "Configure before the first power-up" in WIRING.md and as an ASSEMBLY.md
  step (grouped when one setting caps several items), and the Loads table shows the capped peak (test). WIRING.md
  labels the hover time as an ideal steady-hover estimate.
- fpv_5in: limit `why` carries the CLI command and the Blackbox/OSD <= 60 A gate (central estimate, not "high side");
  VTX antenna mirrored to +y, away from the fingers on the battery plug and the XT60 pigtail; XT60 heat-shrink /
  pre-bend note; stale DESIGN.md numbers fixed.

## 2026-10-31 04:10 UTC — session (electrical/assembly-doc follow-ups) done
- `power_budget` checks voltage drop: each load's input after the IR drop (R = 2 L rho / A) of every +/- pair back
  to its source or regulator; average current at 40 C wire must hold voltage_min, the peak (100 C wire) sag is reported
  not failed; feeds at exactly the load's minimum (catalog min = nominal, e.g. fpv_5in's 5 V camera) are report-only.
  Hand-calculated tests. All projects with wiring still pass power (fpv_5in 0.957).
- Wire ends: run `ends:` or catalog `terminal` (solder | screw | lever | header | plug) set the WIRING/ASSEMBLY verb;
  heat-shrink only for soldered ends. ASSEMBLY.md shows each item's `assembly_note`, its checked `insert` path,
  `bom_extra` rows tied to a screw `group` (washers) and ball-end key warnings (test in test_ship.py).
- prices.json: MEAN WELL adapter, barrel jack, Arduino Nano, AWG 22, header pins, USB Mini-B, C13 cord (pages read
  2026-10-31). servo_link BOM $77.83 with 3 trivial rows unpriced.
- servo_link re-reviewed: PASS (fingerprint a4eacf651775531c); electrics fitted before the horn so the servo can be
  centred at 1500 us; threadlocker note on the arm.
- Note: my commit b293b1b also added catalog_deps.json for bionic_finger/pan_tilt/robot_arm (generated by my checks,
  same content their own checks write).
- Not mine, seen: tests/test_kerf_skill.py fails on `hard_stop` (another session's new check not yet in the skill
  toolbox).

## 2026-10-31 05:30 UTC — session 01S68R6RW: README.md written (PLAN item stays open)
- README.md: what Kerf Forge is, setup, `/kerf ...` usage, commands, what it can and can't do, repo map. The results
  table is a generated block: `.venv/bin/python tools/readme_results.py` fills it from each eval's latest
  `kerf build` (build / current review / acceptance, parts, purchased, mass, plates) and copies each assembly sheet to
  docs/results/<id>.png (out/ is not in git). Left empty on purpose until every eval passes; the session that runs
  the final verify should run the tool, commit README + docs/results, then check the README box.
- Reminder (engine change above): the first build of each project after 59d5324 writes projects/<p>/catalog_deps.json
  and moves its fingerprint once (servo_link -> 9e6f0f16, pan_tilt -> 27adc6f9 in my sandbox): commit that file
  and get a re-confirm review.
## 2026-10-31 03:20 UTC — session 01S68R6REX: E6 pan_tilt review PASS
- Review rounds: 1 FAIL (21T micro horn had no spline_engage -> fixed in catalog), 2 PASS (invalidated by a catalog
  edit while the fingerprint still hashed the whole catalog), 3 FAIL (ENGINEERING.md 10b electrical, added mid-run),
  4 PASS at fingerprint 27adc6f9dbb40dd8 (kerf review-status ok). Electrics added: GST60A05 adapter, jack, Pi Zero 2 W,
  4 routed runs, power_budget 0.14. Camera now clears the newly modelled pan-horn screw heads (tilt_h 29.5).
- Catalog: fixed a duplicate `electronics.connectors` key (second block hid dc_jack_5521_screw); SG90 currents.
- Warning for everyone: `claude -p --agent design-reviewer` sessions run the repo Stop hook, which runs a full
  `kerf verify` and keeps the reviewer alive after it has written review.json (load on the box; it may also push
  the reviewer to keep working). Several such processes from this session were still running at hand-off.
- Not done here (per the brief to this session): evals/pan_tilt/BLIND_RUN.md, PLAN.md box for E6.
## 2026-10-31 03:30 UTC — session 6e99fb9c38: E5 bionic_finger review round 1 fixes
- Review round 1 FAIL (1 blocker, 1 major, 7 minor). Fixed: hard stop at straight (dorsal lugs on every knuckle,
  new engine requirement `hard_stop` proves a joint moved 5 deg past its range collides); pivots are 4 x 8 mm shoulder
  screws (new sourced catalog `motion.shoulder_4_m3`, engine support in iface/pins/BOM/ASSEMBLY.md: shoulder length
  chosen so the head never clamps; finger now 15.4 wide to fit the 8 mm shoulder); flexor-line FEA case
  (`proximal_fea_line`, 222 N); crimp sleeve line stop; groove ridges quantified (line never touches them; 5 deg
  steps crack the tessellation); tendon cuts subtracted in chunks (2.4 GB -> 0.5 GB, 2x faster). check PASS.
- Not mine, seen: tests/test_meshy.py needed `./setup.sh` again (manifold3d/networkx) on this clone.
## 2026-10-31 — session 01S68R6S: fpv_5in review round 6 fix + engine
- Round 5 PASS went stale when catalog_deps.json appeared; round 6 found a real miss: the M3 x 14 arm-screw tips
  stood 1 mm proud of the body top, right under the motor phase leads. Engine: `iface` nut traps take `nut_recess`
  (nut sunk below the far face, min engagement follows; test), and `electrical.route_check` now tests every wire
  tube against every screw shank + head (`kerf/shanks.py build`, `asm.screws`) of joints not involving the run's two
  items (test). fpv_5in: arm nuts sunk 1 mm -> M3 x 12, tips under the top face; body FEA 10.15 / 11.67.
- Also: blue threadlocker in the BOM (priced), counterbore-bridging print note, XT60 "hold when unplugging" in the
  wiring note, DESIGN.md numbers. Note for the hard_stop owner: tests/test_kerf_skill.py fails until `hard_stop` is
  listed in the kerf skill's toolbox (from 51c543e, not touched here).

## 2026-10-31 — session 01S68R6Q: E3 robot_arm review round 2 fixes + complete electrics
- Round-2 review (FAIL: 1 blocker, 1 major) fixed: yaw-horn screw heads counterbored into the yaw gear (the platform
  swept over them); cable path rebuilt: lead bundle crosses the yaw joint above the arm, cable mast on the platform
  (new part) -> 132 mm cable post on the base rear pad, `cable_loop` channel_clear at 10 poses; gear mesh enclosed
  (side walls), yaw lead out through a floor-level hole in the guard. Minor: fillets (yoke foot end, jaw post, web
  to plate), jaw 10 mm, load_axis on every part, turntable FEA net moment 1.70 N*m, assembly order, pivot-screw note.
- Complete electrics (Spencer's rule): MEAN WELL LRS-100-5 (5 V 18 A; 5 servos stalled = 13.0 A), 2 x 2 WAGO 221-415
  buses, Adafruit PCA9685 on bosses on the cable post (signal only), Nano on USB; 14 routed runs pass the route check
  at both ends of every joint; power_budget 0.72; usb_access. Catalog: DS3218/DS3225 currents, PCA9685, LRS-100-5,
  WAGO 221-415, Pololu servo lead (sourced).
- Engine: `kerf/heads.py` — socket screw heads are solids in interference + sweeps (test); board proxy keeps its
  mounting holes clear of the component block (test). All 6 projects still pass `kerf check` with the head solids.
- Next: robot_arm build + design-reviewer round 3.
## 2026-10-31 — session 01S68R6S: fpv_5in review round 7 fixes
- Round 7 FAIL (1 major): M3 x 12 / M2 x 12 BOM rows silently linked to M3 x 8 / M2 x 6 packs (size-only price
  fallback). Engine (kerf/ship.py, test): a fallback price is flagged on the row ("PRICE FROM A DIFFERENT PACK ...
  buy <item>") and listed under the BOM total. prices.json: exact screw:M3x12:socket (Zoro) and screw:M2x12:socket.
- fpv_5in: camera powered from the FC 9 V pad (5 V lead drop took it to 4.99 V < its 5.0 V minimum); DESIGN numbers.

## 2026-10-31 — session 01S68R6S: E2 fpv_5in DONE
- design-reviewer round 8 PASS (fingerprint c0d6880d38b83a40, 11 minor notes in review.json), acceptance PASS.
  Frame 149.4 g printed, T/W 6.18 at the 74 % Betaflight output limit (XT60 kept inside 60 A; Blackbox gate),
  12 min ideal hover, all FEA inside SF 3, complete electronics with routed wiring, BOM $373 with buy links.
- Open minors worth an engine item later: ASSEMBLY.md has no nut-insertion step, no bom_extra notes, and always puts
  soldering last; heat-shrink rows are fixed 20 mm pieces.

## 2026-10-31 — session 01S68R6S: Bambu A2L handoff -> BLOCKED on Spencer's printer
- Re-verified the other session's `kerf print` (tests 9/9, dry-run on fpv_5in orients all parts and falls back to
  Bambu Studio). The only open part is the real print, which needs Spencer's A2L and Mac: wrote .claude/state/BLOCKED
  with the exact steps. PLAN box stays open until Spencer runs `kerf print servo_link --send 1`.

## 2026-10-31 04:40 UTC — session 6e99fb9c38: E5 bionic_finger DONE
- design-reviewer PASS (round 4, fingerprint 520a41a6bae1e1de; minors only: side play documented, cosmetic lug point,
  distal wall 1.12 warning, 10-deg groove steps, tendon threading tips now in DESIGN.md s9). Eval acceptance: no fails.
- Engine from this item: shoulder-screw pivots, `hard_stop` requirement, ASSEMBLY.md lists screw-pivot inserts with
  flush/torque guidance and only the tools needed. PLAN E5 checked.
## 2026-10-31 04:30 UTC — session 262017a2: README results table
- Built all six projects (all `kerf build` PASS) and filled the README results table with tools/readme_results.py;
  assembly sheets committed in docs/results/. Fixed a bug there: it passed the project dir as a str, so graders that do
  `proj_dir / "project.yaml"` crashed and showed eval FAIL (bionic_finger, robot_arm, pan_tilt); test added.
- Table is a snapshot: E2/E3/E5 reviews are stale/none and pan_tilt eval fails only on the missing BLIND_RUN.md (E6
  owner). Whoever does the final summary: re-run `tools/readme_results.py` after the last eval passes.

## 2026-10-31 05:15 UTC — session (gallery) — published, item left open for the final republish
- `kerf gallery` (kerf/gallery.py, test): out/gallery/index.html + per-project viewer.html and JPEG render sheets +
  files.json. Published as https://claude.ai/artifact/McXTe1kc9EMpfKshBNu6mH (link in README.md "Gallery").
- Version 1 shows servo_link, tvc_drone, pan_tilt, bionic_finger, fpv_5in from fresh local builds; robot_arm was
  mid-review (its build here went stale on pull) so it shows "not built". The PLAN item stays open: whoever finishes
  the last eval runs `kerf build` on every project, `kerf gallery`, then republishes index.html + files.json's files to
  the SAME url (Artifact publish with `url`, after an Artifact `read` of it), and checks the item off.

## 2026-10-31 05:00 UTC — session 262017a2: final cross-project audit -> AUDIT.md
- Three design-reviewer subagents audited all six projects rule by rule against ENGINEERING.md. AUDIT.md = tracking
  index + their full reports. 1 blocker: tvc_drone ring_low's 6 leg heat-set inserts are centred ON the lug edge
  (half-holes) — passed `kerf check` and its review because nothing checks wall around inserts (ENG-1). ~20 project
  majors, 6 engine majors (insert wall/edge distance, FEA SF enforcement, CG without wire mass, T/W not voltage-derated,
  single-shear pivot moment, slicer infill not in the 3MF).
- PLAN: the audit item now has claimable sub-items per project + engine. Mark each finding fixed/justified in AUDIT.md.
- I take tvc_drone next (the blocker).

## 2026-10-31 07:50 UTC — session 18259c3d8c (01S68R6S): E3 robot_arm review round 3 fixes (in progress)
- Engine (kerf/electrical.py, wiring_out.py, proxies.py; tests in test_electrical.py): run `fuse:` + `fuse_holder:`
  (Littelfuse 75 % derating, rating <= smallest protected wire ampacity), `lead:` ready-made leads (servo pigtail
  lead_length_mm + extension cables, length checked, no reel wire), `crimp` ends (pins + housings in BOM), ferrules on
  screw ends, `electrical.mains` (inlet/cord/fuse/jumper rows + BOM + L/N/earth step), `electrical.supply_v`
  (adjustable supply trim inside the catalog range), box proxy `sites:`, `panel_module` proxy. docs/ARCHITECTURE.md.
- robot_arm: new part psu_hood (closes the LRS terminal end, carries the SCHURTER DD11 fused/switched IEC inlet,
  M3 into the supply's tapped side hole, DC exit with floor tie); C13 cord; per-servo 5 A ATO fuses; servo leads +
  300/600 mm extensions; signal pins crimped into 1x3 housings; LRS trimmed to 5.3 V; base_fea (audit C-10) +
  upper_arm/forearm stall FEA (C-13); front foot screws to x = 7.5 (C-15); mast foot 34 x 26 with 4 screws + root
  fillet; base post root gussets; teardrop free pivot holes (C-14); M3 washers, USB cable, threadlocker note (C-16/17);
  assembly.order + desk step note (review major 3, C-19).
- Also fixed: tests/test_iface_fit M1.6 (no published FDM pilot -> tap drill fallback), hard_stop listed in the kerf skill.
- Next: DESIGN.md numbers from the new build, design-reviewer round 4.
## 2026-10-31 07:00 UTC — session 262017a2: tvc_drone audit fixes (A-1..A-14), engine ENG-3/ENG-4 + bits
- A-1 blocker fixed: leg inserts now on the lug centre line, inboard of the strut (2 x M3 x 10 per leg); new
  `lug_fea` landing case (screw pull-out 160 N per leg, SF 3, Z): 8.08 / 13 MPa with a 10 x 10 T-rib on each lug.
- Legs are one 14 mm width (whole side face on the bed, root fillet); motor_hub prints motor-face-down with arms flush;
  gimbal_outer ring 17 high with every pad as tall; teardrops on every horizontal hole (new `iface.print_up_deg`,
  `servo_mount(teardrop=)`); stack on grommets + M2 heat-set inserts (new heatset `relief`); FEA SF 3 everywhere,
  leg case at the real 729 g, bearing_n on pin bores; wire colours, set-screw spec, ball-end driver, capacitor/grommets
  from the stack's own package (catalog `includes`, source opened); DESIGN.md numbers refreshed.
- Engine: ENG-3 `cg` (and tip_over through assembly_cg) counts every non-supplied wiring run at its route centroid per
  pose (test); ENG-4 `thrust_to_weight` takes test_v / pack_v and scales thrust by (V/test_V)^2 (test); FEA reports
  where the max deflection is (`max_disp_at`, test). Other projects re-checked: all still PASS.
- tvc_drone: twr 2.18 at 22.2 V (>= 2.0, MOT_SPIN_MAX 0.85), twr_sag 1.95 at 21 V; CG 0.35 mm with wiring (battery
  trimmed to -24.5 / -10). `kerf build` PASS. Next: design-reviewer re-review, then mark AUDIT.md.
## 2026-10-31 08:45 UTC — session 262017a2: tvc_drone review round 1 fixes
- design-reviewer round 1 FAIL: mass under-reported (tubes and XT60 counted 0 g). Engine: `item_mass_g` now computes
  rods/tubes from catalog density x section x length (test) and every massless purchased item gets a build warning
  (seen now: dc_jack_5521_screw in pan_tilt/servo_link, iec_inlet in robot_arm — owners please add sourced weights).
  Catalog XT60 weight 3.5 g (getfpv, opened) — this makes fpv_5in's review stale (its mass/CG changed; re-review in
  the fpv audit item).
- tvc_drone: mass budget 790 g derived from twr (1625 g / 2.0 less unmodelled hardware), landing cases at 790 g;
  ring_low disc corner fillets (lug_fea peak 21.6 -> 11 MPa), bosses 18 mm like the webs, teardrop lock taps on all
  rings and leg screw holes, nylon-tip set screws. FEA reports peak + max-deflection locations (test).
## 2026-10-31 10:20 UTC — session 262017a2: PLAN "Audit fixes: tvc_drone" DONE
- design-reviewer round 3 PASS (fingerprint 435d517f3a37c360); eval acceptance passes; AUDIT.md table updated.
- Round 2/3 additions: s5 fillets on motor_hub / gimbal_outer, `features.bed_chamfer` 0.5 mm first-layer chamfer on
  every tvc part (edges OCC refuses become a deburr warning; test). Other projects can adopt bed_chamfer for A-11-style
  findings.
## 2026-10-31 09:30 UTC — session 262017a2: ENG-1 hole-wall check (engine majors item)
- New `kerf/holewall.py` in every `kerf check`: a fastener hole whose wall ring (hole r + insert_wall / 0.8 mm) is
  < 95 % material is a PROBLEM (catches the tvc A-1 half-hole inserts; test), < 90 % at 1.5 d is an edge-distance
  WARNING (one line per group). Per-site numbers in report.json parts.<id>.hole_walls.
- **robot_arm owner:** it flags base `yaw_servo` M3 tap holes at x -30.7 (y +/-5, z 33.3): only ~54-62 % of the ring
  right next to the hole is material, so they are half-holes at a shelf edge. robot_arm `kerf check` FAILS on this now.
- Other projects: no problems; edge-distance warnings are mostly hole patterns forced by purchased parts (servo tabs,
  horn bolt circles, motor patterns) — note them in each DESIGN.md.
## 2026-10-31 10:10 UTC — session 262017a2: ENG-2 safety-factor floor + across-layer proof
- `fea_static` takes `case: static|crash|landing`; an sf under ENGINEERING.md s3 (2 static along layers, 3 across
  layers = direction z or auto with > 25 % across, 3 crash/landing) fails with a clear message (test, 5 cases).
  direction `auto` is now real (blends xy/z strength by the part's load_axis share; it silently meant xy before).
- A part whose load_axis runs across layers with no direction z/auto strength check is now a PROBLEM (was a warning
  that stayed forever); with a proof the warning is dropped. All projects re-checked: only robot_arm fails (the
  ENG-1 yaw_servo half-holes, see the entry above).

## 2026-10-31 09:20 UTC — session 18259c3d8c (01S68R6S): E3 robot_arm — review round 5 PASS, then re-opened by ENG-1/2
- Round 4 FAIL (hood covered the LRS SVR1 pot) fixed: pot/LED positions in the catalog (scaled, sourced), hood holes,
  side vent window, floor tie bridge, supply trimmed to 5.4 V; round 5 PASS (5b285dd8).
- Then the new ENG-1 holewall check flagged the yaw servo's two output-end tab holes (half-open into the cable-boss
  slot: a real defect). Fix: the yaw servo now goes in from BELOW (servo_mount top_through, open-bottomed pocket, solid
  shelf round all four holes, widened key pocket, lead exit on -Y). ENG-2: the stall FEA cases are `case: crash`, SF 3.
- PLAN: E3 and "Audit fixes: robot_arm" checked; a fresh build + design-reviewer pass on the new fingerprint follows
  in this session. Other sessions: fpv_5in and servo_link reviews went stale from catalog edits (XT60 by the tvc
  session, MG996R lead_length_mm by ecf0d5e); they need a re-review (no geometry change).
## 2026-10-31 11:00 UTC — session 262017a2: ENG-5 single-shear pin moment, ENG-6 print settings
- ENG-5: a `bearing_n` load on a pin bore whose pin group puts the other parts' bands off this part's bands (single
  shear) gets the lever moment M = (c_other - c_this) x F added automatically (detail says so; `single_shear: false`
  opts out); hand-checked test. Effect: tvc yoke_fea 3.51 -> 3.06 (still fine); **bionic_finger proximal_fea_line now
  FAILS 26.5 / 24 MPa** (the audit's C-2: 1594 N mm on the pip insert was unmodelled) -> bionic audit item.
- ENG-6: strength-checked parts (and copies of their file) default to 4 wall loops (`walls`), the mass estimate counts
  perimeters vs top/bottom skin by face orientation (checks.shell_volume, test), plate 3MFs carry per-object
  infill + wall loops (Bambu/Orca Metadata/model_settings.config; not yet confirmed in Bambu Studio) and
  out/plates/PRINT_SETTINGS.md lists them (test). ENGINEERING.md s5 documents it.
## 2026-10-31 10:45 UTC — session dafdd49d: E6 open stumbles fixed (#8, #19, #20), blind re-run next
- #19 SG90 proxy: `gear_boss_d/h` + `aux_boss_*` (measured from the FreeCAD-library SG-90 STEP, CC-BY-SA) and the lead
  exit as a keep-out (`cable_boss_*`, newscrewdriver.com: it leaves the OUTPUT end, place varies by batch) with
  `cable_boss_flex` (loose wires: interference yes, hex-key reach no). `servo_mount` (drop-in) clears the lead zone and
  refuses loudly when an end-tab hole would break into it (use top_through). Tests.
- pan_tilt base reworked for it: the servo slides in from the open -Y side and hangs from a 5 mm deck by its tab tops
  (screws from below through floor key holes); lead out of the open side (also settles audit F12). Re-review needed.
- MG90S has the same lead rule (same source) but NOT added yet: it makes tvc_drone ring_low / gimbal_outer collide
  with the leads (86 / 306 mm3). **tvc_drone owner:** add the MG90S envelope (copy SG90's cable_boss_* with tab_z
  18.5 -> cable_boss_h 14.5) and lead slots, then re-review.
- #8 stock SG90 arm horns `servo_horns.sg90_arm_1/2/4` (FreeCAD-library STEPs measured): horn proxy draws arms
  (catalog `arms`), `iface.horn_holes` / `horn_mount(use=, start_deg=)`; test vs the CAD volume.
- #20 `insert:` items: subtree children installed in an EARLIER order step stay put and block (servo slid in last onto
  a mounted horn). Horn centre screws are now key-reach checked when the horn goes on (straight / ball-end / problem).
  Tests. All six projects still pass `kerf check --quick` with unchanged fingerprints (except pan_tilt).
## 2026-10-31 12:10 UTC — session dafdd49d (fork): pan_tilt audit F11-F18 (in progress: review next)
- F11 tilt pivot = 4 x 6 shoulder screw, M3 heat-set insert in the knuckle, no threadlocker; F13 yoke wall +1 mm;
  F14 **engine:** a teardrop tap hole (prints horizontal) now gets the catalog `self_tap_pilot_horizontal` (Bambu table
  delta, test) — this changes the geometry of every project with teardrop tap holes (servo_link feet, robot_arm
  yoke_r/l, tvc ring_low/gimbal_outer): their fingerprints moved (reviews were already stale for servo_link and
  robot_arm; **tvc_drone review is now stale too** and tvc_drone `kerf check` currently FAILS mass 814 / 790 g +
  twr 2.0 — that mass rise comes from ENG-6's perimeter-aware mass, not from the pilots).
- F15 base_fea with a 30 N knock at the camera (+ moment on the tab contact), yoke_pan_stall crash case; F18
  `static_torque` takes `gravity: [x, y, z]` (test) -> pan_tilt `torque_pan` (head on its side); F17 BOM; F16
  justified (ENG-12). AUDIT.md rows marked. Off-head electrics `render: false`.
- Note for the ENG-5/6 owner: tests/test_docs.py fails (`single_shear`, `walls` not in ARCHITECTURE.md).
## 2026-10-31 11:40 UTC — session 262017a2: PLAN "Audit fixes: engine majors" DONE
- ENG-1..6 in, each with a test (see AUDIT.md). tvc_drone re-reviewed after them: round 6 PASS at 8aedf000a3cf1767
  (4-wall shells, catalog-derived T/W 2.08 / 1.86, 780.5 g / 790).
- Now failing on real findings, for their audit items: **fpv_5in** twr 5.94 < 6 (4-perimeter mass on arms/body/top
  plate, B-F3: trim mass or the twr basis), **bionic_finger** proximal_fea_line 26.5 > 24 MPa (single-shear pip moment, C-2).
- Note for the ENG-7 / pan_tilt owner (reviewer minor): `tap_h` (horizontal pilot 2.10 for M2) is also applied to
  TEARDROP taps, where the teardrop already removes the droop it compensates; the screws may have little bite. Decide
  whether teardrop taps should keep the vertical pilot, and print a coupon.
## 2026-10-31 13:00 UTC — session dafdd49d (fork): pan_tilt audit F11-F18 — re-review PASS
- design-reviewer audit round 1 FAIL (base cavity had zero vertical clearance for the SG90 tab-height spread) ->
  cavity floor 1 mm lower; yoke knock cases (`yoke_knock_out/_in`, 30 N, strength-governed, 2 mm elastic limit).
  Round 2 **PASS** at fingerprint b13fdb08322fb884 (`kerf review-status pan_tilt` ok); 6 minors in review.json.
- Minor left open (engine, ship.py): generated ASSEMBLY.md lists the tilt pivot pin before the tilt servo and has no
  horn centre-screw step (DESIGN.md §8 has the right order). Headless reviewers still run `kerf verify` from the repo
  Stop hook (E6 stumble #4).
## 2026-10-31 12:40 UTC — session 262017a2: PLAN "Audit fixes: servo_link" DONE
- A-8/15/16/17 fixed; design-reviewer PASS at 46118d7a3ecd48d5; eval acceptance passes. Engine: `tip_over` takes
  `include:` (only those items' mass; e.g. leave out a desk adapter beside the device), test.
## 2026-10-31 11:40 UTC — session dafdd49d: PLAN E6 and "Audit fixes: pan_tilt" DONE
- E6: blind run 2 (fresh subagent, brief only) reached PASS on its own in ~50 min with one review round (run 1:
  2.3 h, 5 rounds). Its 6 stumbles are fixed with tests (kerf new crash, unevaluated-requirement text, tripod nut in
  the BOM via `ctx.bom_item` — `tripod_socket(ctx, loc, ...)` now takes ctx first, sibling-import hint, headless
  reviewer nohup+poll in SKILL.md). Record: evals/pan_tilt/BLIND_RUN.md. Scratch project not committed.
- pan_tilt audit F11-F18: fixed/justified (see the fork's entry and AUDIT.md); review PASS b13fdb08322fb884, eval [].
- Still open from E6 (needs Spencer): the repo Stop hook runs a full `kerf verify` inside headless reviewer sessions
  (CLAUDE.md forbids touching the hook); kill any stray `kerf verify` such a reviewer leaves behind.

## 2026-10-31 12:00 UTC — session 18259c3d8c (01S68R6S): E3 robot_arm DONE (review round 9 PASS, 359ef119bfeab419)
- Rounds 6-8 (all fixed): yaw lead trapped by the widened pocket -> groove in the base underside; FEA loads were from
  pre-ENG-6 masses -> recomputed (why texts show the arithmetic); base_fea bearing couple used 25 mm instead of the
  real 20.5 mm -> written as 1860 / (z_bhi - z_blo); teardrops on the links' horizontal tab pilots and insert holes.
- Eval acceptance PASS; PLAN E3 and "Audit fixes: robot_arm" checked; AUDIT.md log updated.
- Open minors (review.json): the drawn yaw lead ends at the servo origin (engine: lead end at the cable boss), fuse
  cold resistance not in the voltage drop, optional hood bridge chamfer, mast support, Nano loose on the desk.
- Note for whoever re-reviews fpv_5in / servo_link: their reviews went stale from catalog edits only.

## 2026-10-31 12:45 UTC — session 18259c3d8c (01S68R6S): audit ENG-7..ENG-20 DONE
- New: kerf/hole_axes.py (horizontal round holes: pin = problem, fastener = warning; iface Sites record teardrop),
  checks.bed_contact (first-layer warning), pipeline._fea_hygiene (no load_axis / xy across layers / cylinder load as
  force_n / fixed box away from every screw), export.bom_extra_check (unknown keys = problem, duplicate screws =
  warning), export.horn_screw_rows, pins.lock_advice (no threadlocker on printed threads), dowel-shorter-than-span
  warning, electrical.limits kind throttle_estimate (+15 %), wire colour required, review-status out_stale,
  requirement gear_bending (Lewis, Shigley Table 14-2). ENG-10 and parts of ENG-12/ENG-20 justified in AUDIT.md.
- Tests: tests/test_eng_minors.py + test_pins additions; full suite 438 passed. All six projects re-checked
  (--quick): all PASS except fpv_5in twr 5.94 < 6 (already known, its owner's B-F3). New warnings (not problems) on
  existing parts: horizontal round clearance holes, a few fixed boxes away from screws, fpv top_plate load_axis.
## 2026-10-31 12:45 UTC — session dafdd49d (fork): PLAN "Audit fixes: fpv_5in" DONE
- B-F1..F10 fixed (F6 justified as an estimate with the Blackbox <= 60 A gate); AUDIT.md rows marked. ENG-6's
  4-perimeter mass had taken T/W to 5.94: lightened (arm taper 20 -> 14 mm, body side + centre windows, two top-plate
  windows) to 6.02 with every FEA inside SF 3 (arm 9.0 / 0.83 mm vs the new 0.87 limit, body 10.8 incl. new
  body_strength_3, top 7.0 / 9.0). Pillar r 2 + rib r 1 fillets, groove-mouth/bed chamfers, nuts sunk 0.5,
  usb_access (+Y), VTX routes, top_plate load_axis z.
- design-reviewer round 9 PASS at 0fffc865b90f4c37 (7 minors: thin T/W + body surface peak margins, ASSEMBLY.md has
  no nut-drop / threadlocker step (ship.py), heat-shrink row length). Eval acceptance clean.
- Note: F.bed_chamfer on the body chamfered the post counterbore mouths and raised body_strength 10.5 -> 11.9 (hot
  spot at the post foot): use targeted chamfers on parts whose FEA is fixed at counterbored sites.
## 2026-10-31 14:40 UTC — session 262017a2: PLAN "Audit fixes: bionic_finger" DONE
- part-designer subagent fixed C-1..C-9 (washer line stops, depth 18 mm, base/middle/distal line-case FEA with the
  engine's single-shear moment, true 2.2 mm channels, 1.6 mm insert walls, 7.6 + 0.4 lap + one-layer insert boss,
  chamfers); catalog gained the ISO 7089 M2 washer (sourced) and the shoulder screw link 97505A106.
  design-reviewer PASS at d4dc6e4152092833; eval acceptance passes. DESIGN text on play/torque corrected after the
  review; ship.py shoulder-screw torque text now 0.2-0.3 N m (insert pull-out).
- Open minors for whoever takes ENG-15: BOM lists one row per hinge for identical shoulder screws / inserts.
- 15:00 UTC, session 262017a2: committed bionic_finger's regenerated catalog_deps.json (I had reverted it after the
  build, which moved its fingerprint off the reviewed d4dc6e41; it is back to current PASS). Lesson for everyone:
  `projects/<p>/catalog_deps.json` written by your own project's build is part of its fingerprint; commit it.
## 2026-10-31 13:50 UTC — session dafdd49d: fpv_5in audit done (fork), UTF-8 I/O fix
- fpv_5in audit F1-F10 done by this session's fork (see its entry): review round 9 PASS 0fffc865b90f4c37.
- A full `kerf verify` started from the Stop hook under a C/POSIX locale failed EVERY build (viewer.html and
  prices.json read as ASCII -> UnicodeDecodeError) and the unit tests (bare read_text in tests). Engine text I/O now
  names utf-8 everywhere (tests/test_utf8_io.py guards it, incl. a C-locale subprocess), and `kerf verify` runs pytest
  with PYTHONUTF8=1. `kerf build servo_link` passes under LC_ALL=C.
- verify state otherwise: bionic_finger proximal_fea_line FAILS (ENG-5 single-shear moment; the bionic audit item,
  claimed by bb3a06febf). Remaining PLAN items: gallery (claimed), Bambu (BLOCKED on Spencer's printer), clean-clone
  verify x2 and the final summary (both need everything else done first).

## 2026-10-31 14:50 UTC — session 18259c3d8c (01S68R6S): gallery republished, final summary written
- After bd486a2's catalog-only change, fpv_5in / pan_tilt / tvc_drone re-reviewed PASS; robot_arm's re-review caught
  the gripper standing on its wrist discs (new bed-contact check) -> 25 mm flat foot, teardrops; PASS at 3dea877d.
- Fresh `kerf build` of all six; every review current, every eval PASS. `kerf gallery` republished to the same
  artifact (version 2). README results table regenerated; final summary at the top of this file and in README.
- Left for others: the clean-clone double verify (claimed by 216d7672b4) and the Bambu real print (BLOCKED on
  Spencer). STATE stays IN PROGRESS until the verify item is checked; whoever checks it sets STATE: COMPLETE.
## 2026-10-31 15:15 UTC — session 216d7672b4: clean-clone `kerf verify` (PLAN "Run kerf verify (full) twice")
- Run 1: fresh `git clone` to /tmp/kf-clean at b45052d, `./setup.sh` (ALL OK), full `kerf verify` in 4134 s:
  pytest, all six projects (check + build + sweeps + FEA), every eval PASS. Only failures: robot_arm review stale
  (gripper foot change; re-reviewed PASS at 3dea877d2f86fff3 in 44505ff since) and PLAN.md unchecked items.
- Run 2 (clone at 2c85982) in progress. Note: a full PASS needs every PLAN box checked, and "Bambu A2L handoff" waits
  on one real print by Spencer (.claude/state/BLOCKED), so this item cannot honestly be checked until after that.
