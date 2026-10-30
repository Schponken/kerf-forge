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
