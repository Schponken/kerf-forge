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

## 2026-10-30 — assembly viewer (parallel session, PLAN Phase 4 item 1)
- `kerf build` now writes `projects/<p>/out/viewer.html` (new `kerf/viewer.py`, `tools/render/viewer_template.html`):
  one self-contained ~1.2 MB page, no network. Orbit/pan/zoom, explode slider, one slider per moving joint, part list
  with visibility toggles and click-to-inspect print info (material, size, mass, print rotation, overhang, walls,
  files), requirements/problems tab, BOM tab, print plates, light/dark, phone layout.
- Joint motion is not re-derived from build123d's joint maths: `viewer._measure` reads it off the real solver
  (`assembly.solve`) as a rigid motion in the parent frame and refuses to write the page if that model is off by
  more than 1 µm anywhere in the joint's range. `viewer.fk` is the same maths in Python.
- three.js + OrbitControls are bundled/minified once with esbuild (new pinned devDependency in tools/render; the
  bundle is cached in gitignored `tools/render/.cache/`). `tools/render/viewer_check.mjs` drives a built page headlessly.
- Tests (`tests/test_viewer.py`): linear + tilted-axis revolute chain with non-zero homes; FK matches the solver
  (<1e-6 mm) at 5 poses; meshes complete; the real page in Chromium poses every part like the solver (<1e-3 mm,
  float32), no JS errors, no network requests, dark + explode + phone screenshots. A flipped joint axis fails the test.
- Verify state: `pytest` 86 passed; `kerf build servo_link` PASS (viewer.html written, checked visually).
- Open: none for this item. The gallery item (Phase 4 #2) can reuse `viewer.model()` per project with one shared
  copy of `viewer.lib()`.
