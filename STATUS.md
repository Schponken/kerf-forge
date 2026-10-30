STATE: IN PROGRESS

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
