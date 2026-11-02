# Kerf Forge plan

The job is complete when every box below is checked, `.venv/bin/kerf verify` prints `VERIFY PASSED`, and all work is
pushed. Check a box only when the item works and a test, check or eval covers it. Items already checked were built and
tested before handoff.

## Phase 0 — foundation (done before handoff)
- [x] Toolchain pinned and installable with `./setup.sh` (build123d 0.13, bd_warehouse, py_gearworks, build123d-mcp, trimesh)
- [x] `kerf doctor` self-test: libraries, catalog completeness + sources, headless renderer, git remote
- [x] Verified hardware catalog with source URLs (`catalog/hardware.json`)
- [x] Engine core: part contract (`ctx`), project loader, joint-tree solver, interference, motion sweeps, coupled-pose sweeps, fastener alignment + screw sizing
- [x] Print checks per part: single solid, valid, fits printer, watertight, overhang %, wall thickness, mass
- [x] Mass input validation: reject invalid infill, fractional/negative wall counts and nonfinite/negative explicit purchased masses before geometry and direct mass/print output; preserve valid defaults, zero boundaries and consistent numeric strings; synthetic and adjacent print-package tests.
- [x] Requirement checks: mass_max, size_max, distance, clearance_min, static_torque, thrust_to_weight
- [x] FEA: linear static stress/deflection (gmsh mesh + scikit-fem quadratic tets) validated against beam theory and axial bars (`tests/test_fea.py`); `fea_static` requirement with regions by box, fastener group or joint, layer-direction-aware strength
- [x] Exports: STEP assembly, STL + 3MF per part, A2L plate packing, GLB, BOM (printed, purchased, screws, inserts)
- [x] Headless renders: assembly sheet, exploded sheet, keep-outs, each joint at min/max, each part sheet
- [x] Interface library seed: bolt patterns (clearance, counterbore, countersink, heat-set, tap, nut trap), servo tab mount, horn mount, bearing seat, motor/stack mounts
- [x] Purchased-part proxies: servos, horns, bearings, motors, prop keep-outs, flight stacks, batteries, rods, boards, steppers
- [x] Seed project `servo_link` (E1) passes check, build, review and eval
- [x] Stop gate, edit hook, design-reviewer, part-designer and design-researcher subagents, `kerf` skill, Ponytail skill

## Phase 1 — engine depth (make every eval possible)
- [x] Interface tests: for EVERY function in `kerf/iface.py`, a pytest that builds both sides, assembles them, and proves alignment + correct fit clearance from the catalog
- [x] Pin / shaft joints for printed hinges (pin through clearance hole on one side, press or heat-set on the other), with a fastener-style alignment check
- [x] Belt/gear helpers using py_gearworks (spur gear pair at correct center distance; GT2 pulley + belt length) with tests
- [x] New requirement checks, each with a test that has a known hand-calculated answer:
  - [x] `cantilever_stress`: bending stress at a named section of an arm/beam under a named load case vs. material strength (layer-direction aware) with safety factor
  - [x] `cg`: assembled center of gravity (all items incl. purchased) relative to a reference joint or axis, with lateral/vertical limits
  - [x] `tip_over`: static tip-over angle from CG height and support polygon (legs, base) — minimum angle
  - [x] `channel_clear`: a declared internal channel (tendon, wire) is open end to end for a given diameter
  - [x] `prop_clearance`: minimum distance between prop discs and between each prop disc and any other item, at home and over sweeps
- [x] Layer-direction check: parts may declare a `load_axis`; warn when the main load runs across layers in the print orientation
- [x] Detailed-modeling helpers in `kerf/features.py`, each with a test that builds it and checks size/validity: swept channels along a 3D path (tendons, wires), shell with uniform wall, ribs/gussets between two faces, teardrop horizontal holes, threads (bd_warehouse) incl. printed coarse threads, gear pairs at the right centre distance (py_gearworks), snap-fit cantilever hooks with a strain check, living hinges, embossed/debossed text labels, lightening pockets that keep a minimum web, and a safe fillet/chamfer helper that applies edge groups one by one and reports any that failed instead of crashing
- [x] Vendor CAD proxies: `proxy: step` loads a STEP file from `catalog/models/` (sources + licenses in `catalog/models/SOURCES.md`), fails if its bounding box differs from the catalog entry by more than 0.5 mm, and keeps catalog-driven joints and fastener sites
- [x] FEA load-case helpers and output: bearing-seat radial loads, torque about a joint, pressure on a face; a von Mises colour render per FEA check saved to `out/renders/fea_<id>.png` for the reviewer
- [x] Reference library `references/INDEX.md`: every open design studied (link, license, measured key dimensions, lessons) so later projects reuse the research
- [x] `kerf check` total time for `servo_link` under 60 s; profile and cache tessellation/overlaps if slower
- [x] Assembly-access checks, each with a test: (a) hex-key reach — a straight key of the screw's size along each screw
  axis from the head side must clear every other item for its working length (report screws that need a ball-end
  driver); (b) insertion paths — parts declared with `insert: {direction: [x, y, z], distance: mm}` in project.yaml
  are swept along that path into their seat and must not collide (catches e.g. a servo body/cable boss that cannot
  pass its window)
- [x] `servo_mount`: 0.5 mm lead-in chamfer on the window's entry face (elephant-foot allowance on bed-side faces);
  then rebuild `servo_link`, fix arm.py's stale test-mass comment (wire loop / S-hook), and get a fresh PASS review

## Phase 2 — design from a description
- [x] servo_link review follow-ups (review of fingerprint 43b35f19, all minor): `access.insertion_paths` skips subtree items that `assembly.order` installs later (test), then declare the servo's top-first insert + order in servo_link; horn proxy seats ON the spline instead of sliding over it (~4 mm too far out) — add a spline-engagement value to the horn catalog entry (sourced) and use it in the proxy; FEA render titles show surface peak, volume peak and the p99.9 value used for pass/fail; project.yaml bom_extra washer text says 4.2 mm holes (now 4.5 mm keyhole slots); count the washer in tab-screw grip; then rebuild servo_link and get a fresh PASS review
- [x] Electrical/assembly-doc follow-ups (servo_link review 3, engine, all minor): `power_budget` adds a voltage-drop check (IR drop of every run on the feed path at peak vs the load's voltage_min, test with a hand-calculated answer); WIRING.md / ASSEMBLY.md pick the verb per end (screw terminal, header, solder) instead of always 'solder'; ASSEMBLY.md screw steps pull in bom_extra items for that group (washers), ball-end key warnings and the item's `insert` direction (test); prices.json entries for the electrical items now in BOMs (adapters, jack, Nano, wire, header, cords)
- [x] `kerf` skill (`.claude/skills/kerf/SKILL.md`) drives the full workflow from a one-paragraph description: design-researcher (REFERENCES.md) → DESIGN.md with spec-driven sizing and trade-offs → project.yaml → parallel part-designer subagents → integrate → FEA on structural parts → detail pass → build → design-reviewer → summary for Spencer
- [x] docs/ARCHITECTURE.md and docs/ENGINEERING.md complete and accurate for everything the engine now does

- [x] Complete electronics + wiring for EVERY project that moves or powers anything (engine feature, applies to all
  evals): the `kerf` skill derives the full electrical system from the description, never only the parts the brief
  names. (a) Every component is a catalog-backed purchased item with a source: controller/flight controller, ESCs or
  motor drivers, receiver + antenna(s), video TX + antenna + camera where FPV, BEC/regulator for servos and logic,
  battery, battery strap + pad, power switch/connector (XT30/XT60/JST), fuses where needed, sensors. Add missing
  catalog entries with sources first. (b) `wiring:` section in project.yaml: every connection (from pin/pad → to
  pin/pad, signal or power, voltage, peak current); wire gauge chosen from current with a cited ampacity table; each
  run routed through declared channels/keep-outs with its 3D length + 15 % slack. (c) New checks with hand-calculated
  tests: `power_budget` (peak + average current per rail vs. battery C-rating, BEC rating, connector rating, wire
  ampacity), `flight_time` / `run_time` estimate from capacity and average draw, `connector_access` (battery plug and
  USB port reachable with the frame assembled). (d) Outputs: BOM gets every electrical item, wire (gauge, colour,
  cut length), connector, heat-shrink, strap, with buy links + cost; `out/WIRING.md` + `out/wiring.svg` diagram
  (pins, colours, gauges); ASSEMBLY.md includes the solder/wiring steps. Purchased-parts-only builds (no printed
  parts) still produce this package

## Phase 3 — the eval projects (each: REFERENCES.md from the design-researcher, `kerf build` PASS, design-reviewer PASS, `evals/<id>/acceptance.py` PASS)
- [x] E2 `fpv_5in` — 5" freestyle FPV quad frame (evals/fpv_5in/brief.md)
- [x] E3 `robot_arm` — 4-axis desk robot arm with gripper (evals/robot_arm/brief.md)
- [x] E4 `tvc_drone` — coax thrust-vectoring rocket-style drone (evals/tvc_drone/brief.md)
- [x] E5 `bionic_finger` — tendon-driven 3-segment finger (evals/bionic_finger/brief.md)
- [x] E6 `pan_tilt` — BLIND test of the tool: a fresh general-purpose subagent with no prior context is given only evals/pan_tilt/brief.md and told to use the `kerf` skill; it must reach PASS on its own. Record its transcript summary and anything it got stuck on in evals/pan_tilt/BLIND_RUN.md, then fix the skill/engine for every stumble (and re-run blind if fixes were needed)

## Phase 4 — Spencer can see and use it
- [x] Assembly viewer: `kerf build` also writes `projects/<p>/out/viewer.html` — a self-contained page (no network) showing the assembly with part list, explode slider, a slider per moving joint (uses joint axes from the report), part visibility toggles, BOM table and per-part print info
- [x] Publish one combined Kerf Forge gallery page as a claude.ai artifact (Artifact tool) with every eval project's viewer, renders and BOM; put the link in README.md
- [x] README.md: what it is, setup, how to ask for a design (`/kerf ...` in Claude Code), what it can and can't do, results table for every eval (pass/fail, parts, mass, print plates), links to renders

## Phase 4b — features from the competitor study (Zoo, AdamCAD, Leo AI, MakerWorld, Fusion; see docs/COMPETITORS.md)
- [x] Search-first: before a part is designed, `kerf find "<description>"` searches Printables, Thingiverse, GrabCAD, MakerWorld and vendor STEP files (McMaster etc.) and writes candidates (link, license, key dimensions) into the project's REFERENCES.md; the `kerf` skill reuses or adapts a fitting part instead of generating one, and records why when it doesn't. Sources by access: Thingiverse (official API), Printables (public GraphQL), MakerWorld/GrabCAD (web search + page fetch); McMaster blocks automated downloads, so list the part number + link and ask Spencer to drop the STEP into catalog/models/
- [x] Creative mode via Meshy: parts declared `source: meshy` with a prompt are generated through the Meshy MCP tools for organic/cosmetic shells and fused with the exact mounting features into ONE printable body. Proven approach (docs/prototypes/mesh_merge.py, 2026-10-30): do the booleans in mesh space with `manifold3d` (0.2-1.6 s for 80k-330k triangles, watertight single body, M3 holes probed exact), NOT through the B-rep kernel (34 s at 20k triangles). Repair ladder per connected piece: merge verts + fill holes, else voxel remesh; then union the pieces (a broken mesh with a stray overlapping piece otherwise yields 2 bodies). Holes/bosses/keep-outs come from the part's build123d features, tessellated fine; scale the mesh to declared bounds first. Output STL/3MF for printing; STEP holds the mechanical features only. Fastener/interference checks use the merged mesh. Add manifold3d + networkx to setup. Test with a cached broken mesh so CI needs no Meshy call
- [x] Self-correcting errors: every build/check failure raised from part code names the part, the feature and the fix hint (e.g. "fillet on edge group 'top' failed: radius 3 > wall 2.4; use <= 1.1"), and the part-designer loop feeds it back and retries automatically; test with deliberately broken parts
- [x] Click-to-edit in the viewer: clicking a face in `viewer.html` shows which part file, feature and parameter produced it, and lets Spencer copy a ready-made edit request ("arm.py: arm_length 120 -> 130") for Claude Code
- [x] Bambu A2L handoff: `kerf print <project>` auto-orients each part (min supports, load_axis aware), slices with the A2L profile (Bambu Studio / OrcaSlicer CLI) to .gcode.3mf, then sends over the printer's official LAN / developer mode (MQTT + FTPS; see wiki.bambulab.com third-party-integration and enable-developer-mode) and polls status. Fallback when LAN access is off: write the sliced file and open it in Bambu Studio for one-click send. Dry-run tested in CI; one real print verified with Spencer — CLOSED by Spencer's decision (2026-10-31): he moves files to the printer himself, so no real print through `kerf print` is required. Shipped: orient + plates + slice-when-configured + open in Bambu Studio; LAN send (FTPS/MQTT) is tested against fakes only, never against a real printer
- [x] Print-truth loop: `kerf calibrate` builds a small A2L coupon (M2/M2.5/M3 clearance + tap + heat-set holes, 608 and 623 bearing pockets, 0.2/0.3/0.4 mm slip-fit pins, a servo-tab window). Spencer reports what fit (`kerf feedback <material> hole_M3=tight ...`); offsets are stored per printer+material in catalog/printers/ with the date and applied by iface, so every later design fits his real printer, not a textbook one. Tests use synthetic feedback
- [x] Ship package: BOM gains buy links and unit/total cost for every purchased item (catalog sources), and `kerf build` writes `out/ASSEMBLY.md` — step-by-step assembly order with an exploded render per step and the screw/insert list for each step

## Phase 4c — adopted from the text-to-cad teardown (docs/teardowns/text-to-cad.md)
- [x] Engineering drawings: add `cadgen==0.8.4` (MIT, same build123d 0.13; see the teardown) and have `kerf build` write
  `out/drawings/<part>.pdf` for every printed part with `cadgen.eng_drawing` (three views + iso, overall dimensions,
  hole callouts taken from the part's interface sites, material/print orientation in the title block). Test: a drawing
  of a test part has the expected views and a hole callout per hole group; Studio Files tab lists the PDFs
- [x] URDF export for every project with moving joints: `kerf build` writes `out/<project>.urdf` (links = items moving
  together, joints from the joint tree with limits, inertials from part masses / CG / inertia of the meshes, visual and
  collision meshes from the part STLs, metres + kg), validated with `cadgen.urdf_source.validate_urdf_file`, and loads
  in PyBullet (`pybullet.loadURDF`) in a test. For Spencer's simulators (robot arm, TVC drone RL training)
- [x] Per-part build cache (the memo idea at Kerf scale): key = part source + resolved params + catalog deps + engine
  version; store the built shape as BREP under .cache/parts; `kerf check` / Studio "Try" rebuild only changed parts.
  Tests: unchanged part = cache hit with identical geometry; editing a param that the part reads = miss; engine change
  = miss. Measure robot_arm check cold vs warm in STATUS.md

## Phase 6 — design depth and output quality (two independent reviews, 2026-11-01: docs/reviews/2026-11-01.md)
Spencer: "not just simple parts slapped together; every design choice should have a purpose and intention". Engine
already added: FEA stress map + "overbuilt" warning (kerf/stressmap.py), sharp-inside-corner warning (kerf/edges.py),
design-intent scores required on every review (cli.intent_scores), Load → section table + `# why:` comments in the
workflow. Each item below: implement, test, update docs, then re-check the projects it touches.
- [x] Section generators in kerf/features.py: `beam(path, section="I|T|C|box|tube", depth=f(s), width=f(s), wall)` by
  sweep/loft, `fork_link(L, ends, section, taper)` (pivot bosses, closed/I body, root fillets, cable channel) and
  `rib_along(face, path, h)`. Tests: area and second moment against hand formulas via requirements.section_props;
  prints on its intended side with no support
- [x] Mechanical idiom library (kerf/features.py or kerf/idioms.py): `yoke_cheek`, `servo_cradle`, `clevis`, `boss`
  (root fillet built in), `cable_saddle` / strain relief, `grip_pad` (serrations or TPU-insert pocket). Replace the
  copy-pasted robot_arm `yoke()` (yoke_l/yoke_r) and `plate()` (upper_arm/forearm) with them. Tests per idiom
- [x] Feature intent ledger: `ctx.add(shape, why=, kind=)` / `ctx.cut(shape, why=, kind=)` (iface calls register
  themselves); the table goes into report.json and the part sheet; the after-edit hook warns on a body boolean with no
  `why=` and no `# why:` comment. Test
- [ ] Showcase rework, robot_arm: upper_arm + forearm from `fork_link` (closed section against torsion, depth tapered
  with the moment, pockets in the stress map's cold zones, servo lead in a channel), gripper + finger (real grip surface,
  tapered finger, root fillets, one swept jaw), base (thin floor + ribs from the bearing tower to the 4 feet, tower
  gussets, filleted rib roots). Re-run every FEA case; design-review PASS with scores >= 4 on these parts
- [ ] Showcase rework, fpv_5in arm: fillet the key-ridge roots, move the wire path out of the mid-depth shear zone into
  a covered groove, skid under the motor pad; keep the deflection limit; review PASS
- [ ] Every project: DESIGN.md "Load → section" table and `style` radii; each part's "overbuilt" and "sharp inside
  corner" warnings fixed or justified in DESIGN.md; pan_tilt bracket camera M2 tap holes (22 % edge ring: bosses or
  through-bolts with nuts); re-review all six with the intent scores (all >= 3). Then make a
  sharp inside corner in a hot zone a problem (not a warning) and keep every project passing
- [x] BOM: every catalog item has a priced shop link (not a datasheet); total shown as priced + estimated range plus
  what the packs actually cost; duplicate rows merged and quantities aggregated; human names instead of catalog ids;
  units on sizes; no internal notes or TODOs leak to the maker. Shoulder screws: a part number per length (sourced)
- [x] ASSEMBLY.md: off-board items (PSU, jack, Pi on the bench) under "Bench electronics (not mounted)"; steps ordered
  by sub-assembly with no forward references; servo centring before horns; step 0 = test-fit / `kerf calibrate`
  advice; long steps split; tightening in feel terms ("snug, then 1/8 turn") alongside N·m. Generate a bring-up and
  sweep-test program (Arduino .ino or Pi Python) for every project with a controller, referenced by the steps
- [x] WIRING.md: routes described by landmarks, not coordinates; physical pin numbers next to GPIO/BCM; every
  electrical BOM item used in a step and every wire/extension a step uses in the BOM
- [x] Print package: per plate print time and grams (slice with Bambu Studio / OrcaSlicer CLI when installed, else a
  documented estimate), layer height, temperatures, supports on/off, brim in PRINT_SETTINGS.md; printer/filament
  settings in the 3MF; orientation in words ("on its back face"). Studio shows time, grams and cost per project
- [x] Report wording for makers: mass split into printed / on-board / off-board (`off_board:` items, viewer headline too); every check value with its unit and whether the limit is a min, max or range; warnings that change what the builder does rewritten as "For you" notes (Studio Checks tab), the rest labelled for the designer; every purchased item held (screw/pin, `held_by:` or `off_board:`) or warned. Tests: tests/test_maker_output.py. (pan_tilt camera tap holes: moved to the per-project warnings item below; it is a geometry change that needs a re-review.)
- [x] Renders: assembly-step images framed on the step's parts (off-board items excluded), the step's new parts and
  fasteners highlighted with labels; purchased parts readable on dark; part sheets with overall dimensions and an
  on-the-bed view
- [x] Studio: welcome / empty state; time estimates on Build and Build-all (from past runs); units on parameters;
  versions (git-backed history with renders and metric diffs, one-click revert) and tried-vs-saved comparison; cost /
  print time / filament summary; export a zip; which checks a parameter affects
- [x] Smarter new design: intake questions before the run (budget, parts on hand, power, mounting, environment,
  printer, material), then 2–3 candidate architectures with estimated cost, print hours and part count to pick from
  ("quote first"); parts-on-hand inventory the BOM prefers; auto-fix common findings (edge distance -> boss, round ->
  teardrop hole, risky tap -> heat-set insert) before the reviewer sees them

## Requests from Spencer (Kerf Studio)
- [ ] `robotic_gripper_desk` — robotic gripper for the desk robot arm (Studio request 2026-10-31): REFERENCES.md, DESIGN.md, `kerf build` PASS, design-reviewer PASS
- [ ] `robotic_gripper_claw` — geared two-finger claw for the desk robot arm (Studio request 2026-10-31, "a robotic gripper claw"): REFERENCES.md, DESIGN.md, `kerf build` PASS, design-reviewer PASS, tests/test_claw_fits_arm.py
- [ ] `drone_foldable_wings` — morphing-wing drone: wings spread for long stable flight, fold back like a hawk for controlled dives, asymmetric fold for extra control (Studio request 2026-11-01): REFERENCES.md, DESIGN.md, `kerf build` PASS, design-reviewer PASS
- [ ] `hawk_wing` — ~1 m swing-wing FPV plane, outboard-pivot sweep on a fixed glove (F-14 style), conventional tail, wings spread on failsafe, field-swappable panels (Studio request 2026-11-02, picked option 0): REFERENCES.md, DESIGN.md, `kerf build` PASS, design-reviewer PASS
- [ ] `drone_launching_system` — bungee rail catapult for drone_foldable_wings: 3 m folding V-slot rail on a bipod, rolling sled + saddles, latex bungee over a front pulley, latch + pull-cord trigger, PETG on the A2L (Studio request 2026-11-02, picked option 0): REFERENCES.md, DESIGN.md, `kerf build` PASS, design-reviewer PASS, tests/test_launcher_fits_drone.py
- [ ] `portable_launcher_gets` — portable folding no-power launcher for many fixed-wing drones (foam, up to 2 kg, pusher or tractor, high or low wing): 3 m V-slot rail in four hinged sections on a bipod + staked foot, V-wheel sled, latex strands over a nose pulley to a notched anchor (strands x notch setting per drone), 2:1 cocking strap, safety pin + foot-pedal release while holding the radio, shock-cord brake, swappable cradle per drone from a template, PETG on the A2L (Studio request 2026-11-02, picked option 0): REFERENCES.md, DESIGN.md, `kerf build` PASS, design-reviewer PASS
- [x] Repo cleanup (Spencer, 2026-11-02): remove old / unnecessary tracked files (committed build outputs, scratch / backup copies, unreferenced part files, dead modules, stale claims for checked-off items), each verified unreferenced; .gitignore entries so generated outputs stay out
- [x] "How Kerf decided" readable and steerable (Spencer, 2026-11-02: "difficult to follow, shaking violently, labels unreadable"): replace the force-directed web with a calm, fixed-layout decision trail (your request -> questions it researched, each with what it found and its sources -> options weighed with chosen / set aside and why -> what it is building), labels always readable, no motion except new items fading in; opens by itself as a compact strip the moment a design job starts researching, expands to the full trail; steer by marking a question or option "focus" / "skip" (saved for the job to read at its next stage change, no extra model turns, never interrupts it); tests (layout stable, labels not overlapping, auto-open, steer file)

## Studio + viewer features (Spencer's picks, 2026-11-01)
- [x] Studio journey reliability: keep navigation current during delayed project, inventory and guide requests; show recoverable loading failures; cover mocked desktop/mobile journeys.

- [x] Tune experience: a deliberate parameter workbench with reversible draft changes, accessible value errors, clear units and ranges, and truthful recorded-trial context; mocked desktop/mobile checks only.

- [x] Project workspace redesign: readable keyboard-accessible descriptions, contained keyboard tabs, a responsive model workspace, and truthful build/check context with clear next steps; preserve existing project actions and verify desktop/mobile fixtures.
- [x] Viewer cut-away: a slider slices the model on X / Y / Z (flip side), cut faces drawn solid so walls, channels and inserts read as a section; works with explode, joints and every other mode
- [x] Viewer stress colours: each FEA-checked part coloured on the 3D model by how much of its allowed stress it uses (worst load case), legend, value under the pointer; parts without FEA say so
- [x] Studio "Do it": the viewer's edit requests (parameter change or described change) start a Claude Code edit job from Studio instead of being copied; a general "Change something" box too; the job carries KERF_STUDIO_JOB=<project> (a scoped stop-gate mode needs Spencer's OK: agents may not edit the hook; see STATUS 2026-11-01)
- [x] Before/after compare: the previous version (any History build, or the saved design next to a Try) drawn as a see-through ghost over the current one, changed areas coloured by how far they moved, per-part change list
- [x] Material picker per printed part (catalog materials, with their strength XY / Z, stiffness, density and price): Try re-runs strength, weight and cost with the new materials; Save writes them into project.yaml
- [x] Duplicate / remix a project: copy the design (sources only) under a new name, optionally with a described change that starts a Claude Code edit job on the copy
- [x] Project thumbnails: a framed picture of the 3D model on every project card (captured from the viewer, kept per geometry fingerprint), and an all-projects grid with big cards
- [x] Done notifications: a Mac notification (and Linux notify-send) plus an in-page chime when a long job finishes; one switch turns both off
- [x] Step-by-step assembly animation in the viewer: parts fly in along the way they go on, screws turn into their holes, moving joints demonstrate their travel, the camera frames each step, the ASSEMBLY.md text for the step, Next / Back / Play, keyboard, a still-to-come ghost, per-step done ticks

## Fixed-wing aircraft + calmer Studio (Spencer, 2026-11-01: "build things like the Darkwing-1 on MakerWorld")
- [x] Studio layout: calmer and less overwhelming: one primary action, secondary actions in a menu, fewer chips and banners, plainer tabs, the 3D viewer's own header and button rows trimmed when it sits inside Studio
- [x] Flying wings (kerf/aero.py): airfoils from the UIUC database (catalog/airfoils, sourced) and NACA 4-digit, swept / tapered / twisted wing lofts, split into printable segments, spar-tube channels, elevon cut + hinge joint, servo bays; wing geometry (area, MAC, neutral point); checks `static_margin`, `wing_loading`, `stall_speed`, `spar_bending`, each with a hand-calculated test
- [x] E7 `fpv_wing` — 1 m 6S FPV flying wing in the class of MakerWorld's Darkwing-1 (evals/fpv_wing/brief.md): REFERENCES.md, DESIGN.md, `kerf build` PASS, design-reviewer PASS, acceptance.py PASS
- [x] fpv_wing follow-ups from review round 5 (PASS with minors): assembly order (strap before battery; spar tubes fitted dry, epoxied only at the inner segment's step), kerf/ship.py never splits an assembly_note at a colon, assembly_notes for the segments' and fins' epoxy, front elevon joiner 4 -> 4.6 mm aft, splice-plate landing ramp; re-build + re-review
- [ ] fpv_wing finish items (smaller, need research or a new part): TPU belly skid; screws / inserts / glue / tape in the mass model with sourced weights (engine: fastener masses from the catalog); tall slender parts spaced on plates so one toppling can't hit another (engine rule, with a reason); hatch tongue printed without support, flush hatch screw heads, side lip; splice-plate screw heads flush; elevon aft joiner (JOINER_L 40 mm or rod centred between the skins outboard: wall 0.92 mm, web 1.0 mm) + elevon.py docstring numbers; tube-epoxy note: paste wax / petroleum jelly on the pod-side tube length instead of tape (the sleeve is a 0.1 mm/side fit), slide each tube out of the pod first

## Kerf vision: problem in, working thing out (Spencer, 2026-11-01; docs/VISION.md)
Work these in order unless one is blocked; each item is done only with tests and a project or eval that uses it.
- [x] Modes: `kerf run <p> --mode sketch|print|check|simulate|kit|ship` (pipeline stages switched per mode, results reusable when upgrading to a deeper mode); `ship` refuses without an explicit `--ship` / Studio confirmation and is never a default; tests per mode (which stages ran, which files exist)
- [x] Studio mode picker: next to Build, each mode with its usual time + cost shown before it starts; "Upgrade to Build kit" reuses the finished stages; Ship it behind its own confirm (prints on the user's printer); smoke test
- [x] Check it on a user's own design: import STEP/STL + a short yaml (parts, purchased items, joints) and run fit / strength / balance / wiring checks without designing; one eval on an imported model
- [ ] Use story in project.yaml (`use_story`: who, where, how often, what goes wrong) turned into requirements (crash / drop, heat, rain, gloves); required for new projects; fpv_wing and robot_arm get one
  - [x] kerf/usestory.py + checks heat_limit / rain_cover / access_opening / impact_case / story_covered, Studio intake + detail, ASSEMBLY.md accepted failures, tests/test_usestory.py; robot_arm and fpv_5in have stories
  - [ ] fpv_wing gets its use story (after its E7 owner finishes, so its review is not made stale mid-way)
- [ ] Simulate it moving: dynamic load cases from the use story (drop / crash impulse with contact time, hard stops from joint speed and inertia, vibration: first natural frequency vs motor / prop excitation) as requirement checks with hand-calculated tests
  - [x] kerf/req_dynamic.py: impact_fea, stop_impact, natural_freq from one FEA solve's stiffness (fea.static reports f.u); story impact_case accepts impact_fea; tests/test_dynamic.py hand checks (3EI/L^3, impact formulas, end-axis inertia, KV rotor rates)
  - [ ] PAUSED: stress simulations (Spencer 2026-11-02) - fpv_5in arm_resonance PASSES (now FAILS on a real finding: arm f_n 186 Hz is 7 % from the 200 Hz hover rotor rate; needs >= 20 %)
  - [ ] PAUSED: stress simulations (Spencer 2026-11-02) - a project uses impact_fea and stop_impact (a surviving drop / a driven hard stop)
- [ ] Failure modes: per-part failure table in the report (how it fails, what it takes with it, repair time); `weak_link` requirement proving the cheap part fails before the expensive one under the crash case
  - [x] kerf/failure.py: report.json `failure_modes` (governing case, use, how by print direction, bought parts it takes with it + price, screws to undo, reprint time lower bound + filament cost) in ASSEMBLY.md "If it breaks" and the review pack; `weak_link` (stress uses at the same applied force); tests/test_failure.py
  - [ ] PAUSED: stress simulations (Spencer 2026-11-02) - fpv_5in `arm_breaks_first` PASSES (now FAILS on a real finding: under the arm crash event the body uses 94 % of its limit, the arm 76 %: the body would break first)
- [ ] Design for life: fatigue check for flexing parts (living hinges, snap fits), creep limit for plastic under constant load, vibration rule for screws (threadlocker / nyloc / inserts), heat limit by material Tg vs the use story
  - [x] kerf/req_life.py: flex_strain (snap 1.5ty/L^2, hinge ta/2L vs 70 % yield / 50 % break strain, halved across layers, fatigue data required for cycles > 1), creep_limit (documented creep-rupture stress / SF 3; PLA point sourced), screw_locking (metal-thread groups on vibrating projects; ASSEMBLY.md lists the locking); heat limit is the use story's heat_limit (ISO 75 HDT); tests/test_life.py; fpv_5in screws_stay_put PASSES
  - [ ] PAUSED: stress simulations (Spencer 2026-11-02) - creep_limit and flex_strain used by a project (needs sourced PETG creep data for a PETG constant-load part; no project has a snap fit or living hinge yet)
- [x] Optimise then explain: `kerf optimise <p>` searches declared params (mass / cost / a requirement margin) within every check, writes the trade-off table; tested on a small project
- [x] Human factors: reach / access checks from the use story (battery swap with gloves, tool access), carry and repair notes in ASSEMBLY.md
- [x] Learn from results: `kerf feedback` takes logs / photos / notes, records what failed where, and turns repeated findings into ENGINEERING.md rules or catalog corrections (with the evidence)
- [ ] Scenario intake + options: from a scenario-only brief, ask what matters, generate 2-3 options incl. buy-vs-build (search for existing / free designs first), compare cost / time / risk / fit, recommend one; Studio flow; eval E8 (scenario only: "my plants die when I travel")
  - [x] Studio scenario flow: success/priorities/effort intake, researched buy/adapt/build quote contract, sources/fit/risks/unknown estimates, server-checked selection and no design job for buy-only options; targeted API/browser tests
  - [ ] E8 real scenario run: researched options from "my plants die when I travel", clarified constraints, chosen solution built/checked/reviewed and scenario acceptance passed (the intake test fixture is not this evaluation)
- [ ] Module library: proven modules extracted from finished projects (power system, servo joint, gripper, wing panel, motor mount, enclosure, drive train) with their contracts and checks; a new project can instantiate them; tests
  - [x] Module instance workflow: inspect source interfaces, parameters, checks and actual review freshness; instantiate an independent editable bench servo joint from servo_link with full contract, dependency closure and historical provenance, without transferring approval; CLI, tests and full scratch check
  - [ ] Extend the library with the remaining module families from currently reviewed sources and support composing their interfaces into a new checked system
- [ ] Whole-system output: flight-controller / microcontroller config and controller tuned in simulation (INAV / Betaflight diff for drones and wings, Arduino / Pi code for gadgets), checked by a sim test
- [ ] Check against the scenario: scenario requirements (run time on the stated duty, capacity of a tank, coverage of a sensor) evaluated for E8
- [ ] Conventional planes + VTOL: tail volume coefficients and sizing, landing gear, transition thrust; eval E9 (trainer plane)
- [ ] Ground robots: wheel / track sizing, slope tip-over, self-balancing (inverted pendulum) check; eval E10 (rover or balance bot)
- [ ] Gearboxes: planetary and worm sets, strength-checked (Lewis / AGMA-style) and printable; used by one project
  - [x] drives.planetary (sun / planets / ring meshed by py_gearworks, tooth-count + assembly + neighbour rules) + planetary_bending (most loaded planet, K_gamma from a sourced 3-planet case); drives.worm (printable thread) + worm_numbers + worm_drive (wheel Lewis, efficiency, self-locking); tests/test_planetary.py
  - [ ] worm wheel geometry (throated / helical wheel meshed to drives.worm, interference-checked)
  - [ ] a project uses a planetary or worm set
- [ ] Mixed manufacturing: laser-cut / CNC / carbon-plate parts as DXF / STEP for order services alongside printed parts, priced
- [ ] Watertight + thermal: seal / gasket design rules and checks, wall thickness for water, component heat (ESC / motor / regulator) vs enclosure; used by one project
- [ ] Ship it printer loop (opt-in only): print fit coupons on the A2L through the Bambu integration, read the measurements (entered or camera), apply them (`kerf calibrate`), send the final plates; dry-run tested
- [ ] Self-growing catalog: research a missing part, validate against the vendor's STEP (bbox + holes), add it with sources automatically; tested on one new part

## Prove the whole system: code, motion, aero, flight, electronics (Spencer, 2026-11-01; Project doc kerf-tool-gaps.md)
Each tool is adopted only where it beats what Kerf already does; the reason goes in STATUS.md. Reachable from the cloud: downloads.arduino.cc, PyPI, apt, firmware.ardupilot.org, gitlab.com/kicad (github.com source archives are blocked by the proxy).
- [x] Firmware proven: `kerf firmware-check <p>` compiles every generated Nano / PCA9685 sketch with arduino-cli (arduino:avr core + library index from downloads.arduino.cc, pinned versions, installed by setup.sh) and runs the Nano build in simavr (apt), recording the servo pulse widths on every signal pin during centre + sweep and checking them against the joint ranges and PULSE_LIMITS; Pi scripts byte-compile and run against a stub GPIO that records the same; part of `kerf build` when a project has firmware; tests incl. a deliberately broken sketch that must FAIL (Wokwi rejected: its CLI needs a paid CI token)
- [x] Motion simulated: `kerf simulate <p>` loads the URDF Kerf already exports into MuJoCo (pip `mujoco`, pinned) with real masses / inertias from the parts and catalog, servo torque and speed limits from the catalog; requirement kinds `grip_hold` (object of the stated mass / friction held under 1 g shake without slipping), `joint_speed` (move between poses within the stated time without exceeding servo torque) and `drop_impact` (peak contact force from a drop of the stated height, fed to fea_static as a load case); hand-checked tests (pendulum period, static holding torque); used by robot_arm and robotic_gripper_desk
  - [ ] Motion simulated follow-ups (2026-11-01): `grip_hold` on robotic_gripper_desk once its design settles (parallel jaws: needs grip_hold on a geared / prismatic jaw pair, today it takes a revolute finger); robot_arm 300 mm handling drop of the gripper end fails drop_impact (212 N peak vs 128 N the gripper's crash FEA allows at SF 3), decide the design fix or the drop height with Spencer before adding it as a requirement
- [ ] Aero upgraded (after the "Flying wings (kerf/aero.py)" item is pushed; build on it, don't replace it): NeuralFoil polars for every catalog airfoil at the wing's Reynolds numbers and AeroSandbox vortex-lattice analysis of the actual wing (lift slope, neutral point, Cm-alpha, trim alpha, induced drag) replacing hand-estimate inputs where they disagree, each cross-checked against the hand calculation in a test (within a stated tolerance with the reason for the gap); `static_margin` and `stall_speed` report both; used by fpv_wing
- [ ] Flight tuned in simulation: prebuilt ArduPilot SITL binaries (firmware.ardupilot.org, version pinned) driven through ArduPilot's JSON physics backend by Kerf's own model of the airframe (mass, inertia, motor / prop thrust from the catalog; MuJoCo from the motion item when present), autotune / scripted manoeuvres via pymavlink, output a `.param` file (rates, PIDs, filters, failsafes) plus FLIGHT_SETUP.md; check `sim_hover` (copter holds position within stated drift) / `sim_trim` (plane holds level at cruise); tested on fpv_5in or tvc_drone and fpv_wing; Betaflight / INAV get the matching CLI diff derived from the tuned rates with the mapping documented
- [x] Electronics as a real circuit: KiCad 3D models (kicad-packages3D from gitlab.com/kicad, sourced, cached under catalog/models/kicad/) for every board / connector proxy that has one, replacing plain boxes in renders and the internals view (bbox checked against the catalog entry); SKiDL (pip, pinned) + KiCad symbol libraries (apt `kicad-symbols`) turn project.yaml `wiring:` into a KiCad schematic / netlist and run ERC (unconnected pins, two outputs on one net, power pin with no source) as a check; schematic exported as PDF/SVG next to wiring.svg; tests incl. a wiring error ERC must catch

## Watch the cloud sessions work (Spencer, 2026-11-02)
- [x] Studio "Follow live": a toggle in a project's 3D view (off by default); while on, `git fetch` at most every 60 s, fast-forward (clean tree only, else "can't update: local changes" and stop) when origin commits touch projects/<p>/, rebuild ONLY the changed parts (geometry + meshes, no checks), swap them into the viewer in place with the camera kept, highlight ~2 s, one line with the commit subject + time; a part that fails mid-edit keeps its last good mesh ("being edited"); placeholders "being designed"; no timeline/scrubber; tests
  - [x] Follow live control layout: keep checkbox, label and status helper readable without overlap across native WebKit and browser widths; preserve click and keyboard behavior.
- [x] Studio "Work" tab (read-only, same shared fetch): PLAN done/total, sessions working (fresh claims), items checked off today; a card per fresh claim (item, time since that session's last commit, stale past STALE_MIN, project snapshot + "View 3D" opening Follow live); feed of the last ~20 commits marking PLAN check-offs; all from git (log, claims/, PLAN.md); tests
- [x] Studio Work overview (Spencer, 2026-11-02): show Codex sessions alongside Claude claims and local jobs, clear task ownership and activity, evidence-based progress/remaining work and time estimates, attention states, responsive intuitive page; backend and browser tests.
- [x] Codex executable discovery: prefer PATH and fall back to the verified local macOS app bundle so Work can read sessions under the native launcher PATH; no installation or startup mutation.
- [x] Codex CLI compatibility: replace removed --full-auto with workspace-write sandbox arguments for Studio exec/resume; preserve network and explicit overrides, verify generated argv without starting a model.
- [x] Studio Checks tab in plain words (Spencer, 2026-11-02): every problem and failed requirement as a card a non-engineer understands at a glance (which part, what is wrong in one sentence, why it matters, what fixes it; the raw check text folded under "details"), and a work status per card: "being fixed" (a Studio fix / edit job running, or a fresh claim naming the project) or "nobody on it" with the Fix button; rules in a new kerf/explain.py so the CLI and review pack can use them; tests
- [x] The 3D model first (Spencer, 2026-11-02): every run that makes a viewer writes a preview viewer.html as soon as the parts are built and placed (before print checks), Studio switches to it at once and folds the job panel while checks, files and renders carry on in the background; the full viewer replaces it at the end; a cold build of a big project reaches the model in minutes, not after every part's extras; tests
- [x] Viewer "Build it" tab beefed up (Spencer, 2026-11-02): labels never cover the part they name (offset with a leader line), each step's camera shows the new part at a useful angle (more candidate views, square to how it goes on, not hidden), small parts get a close-up framing, and parts don't appear / vanish between steps when they matter (bench steps keep the build visible as context, nothing relevant drops out); checked on fpv_wing / robot_arm step by step with screenshots; tests
- [ ] Beginner visualizer (Spencer, 2026-11-02, approved plan; Claude session owns it): a newcomer can follow every Studio job and tab. Done so far: the live "How Kerf decided" thought web (kerf/thoughtweb.py), plain-language job narration, workshop stage scenes, jargon underlines + glossary (kerf/glossary.py; test: every check has an entry), Tune effects with better/worse arrows, Files one-liners, "Explain this page" + first-run tour, ready-to-print certificate, Activity lists sessions working on a project. Still to do: 3D guided tour, History comic strip, new-design briefing room; builds on kerf/explain.py (no duplicate Checks wording); tests
  - [x] New-design briefing: brief-first intake, focused clarification and evidence-led option selection with preserved scenario safeguards and browser coverage.
- [x] Realistic limits (Spencer, 2026-11-02: "what unrealistic restraints are we putting on the tool"): requirements can be `advisory: <why>` (a miss is a warning, never for strength / stress checks); the thin-wall minimum applies to load-carrying parts only, others go down to one line width (sourced); items can declare `compress_mm` + `compress_why` (foam, straps, wire bundles) so a press-in up to that depth isn't a collision; tests, docs
- [x] Realistic limits 2 (Spencer, 2026-11-02: "continue"): near-miss scale on failed requirements (how far short, in %), infill-aware strength (printed walls + infill instead of solid plastic, sourced), crash energy budget with bumper credit (sourced), vibration rule reviewed (it already uses the hover rate and a cited 20 % separation; Betaflight filtering cleans the gyro, not the frame, so it stays); each with tests; nothing loosened without a cited source
- [x] Specific advice (Spencer, 2026-11-02: "give better feedback and advice when an issue is identified instead of a blanket repair statement"): every failed requirement gets advice worked out from its own numbers and settings (how much thicker / which material / which servo / how far to move the battery ...; kerf/advice.py), overlaps say how deep, along which axis and which part to cut (the bought part can't change); shown on Studio cards and under `kerf check`; tests
- [x] User-facing bug sweep (Spencer, 2026-11-02: "look for bugs the user might cause or complain about and fix"): double clicks, clashing jobs on one project, odd input (names, descriptions, values), stale screens, failed requests; each fix with a test
- [x] Visual pass (Spencer, 2026-11-02: "do visual checks of each major page/screen and fix the easy things"): screenshot every Studio screen (project tabs, new design, My parts, Work, all projects, modals, light theme, small window), fix layout / overlap / overflow / contrast slips; tests where behaviour changes

## Engine speed (Spencer, 2026-11-02: "optimize the core system so it does this faster")
- [x] Faster collision checks: cache each shape's own-frame box (OCC re-derived an optimal box on every call, >90 % of interference time) and reject non-touching pairs with a mesh prefilter (manifold3d, tessellated once to 0.02 mm) before the exact boolean; hits and volumes stay exact (A/B on drone_foldable_wings: identical hits over 6 poses, interference 48 s -> 13 s, each sweep step 3.6-4.2 s -> 0.03-0.06 s); tests/test_overlap_fast.py
- [x] Part cache keyed on the engine modules a part actually uses (not every kerf/*.py), so an unrelated engine edit stops rebuilding every part of every project (drone_foldable_wings: 163 s cold vs 0.9 s cached); tests. Done: sys.monitoring records the engine files each build ran (+ their imports); measured on drone_foldable_wings: cold 180 s, warm 1.3 s, after an fea.py edit 2.2 s (20/20 cached; before: full rebuild), after req_aero.py 51 s (17/20), after iface.py (used by every part) 156 s (0/20, correct)
- [x] `kerf req <p> [id ...]`: just the named requirements on the assembled project (cached parts, no interference / sweeps / print checks), so checking one number after an edit takes seconds; tests/test_req_cmd.py
- [x] Check in order of redesign cost (Spencer, 2026-11-02: "look in the places that would require the most work to redesign first"): `kerf check` / `kerf build` run the concept requirements (mass, thrust/weight, endurance, power, balance, wing loading, actuator torque) and then the structural ones of the most connected parts (FEA, spar / hinge / gear strength) right after the parts build, before print / fit / motion / wiring checks, and stop there with "fix these first" when one fails (`--all` runs everything); `--quick` now includes those core FEA cases (explicit sketch / print modes keep skipping FEA); kerf skill + design-reviewer follow the same order; tests/test_redesign_first.py
- [x] prop_clearance screens gaps with a branch-and-bound on each part's surface mesh (1-Lipschitz bound, longest-edge splits, within 0.5 mm) instead of subdividing every surface to 1 mm (one long wing triangle became ~1e5 pieces); reported gaps still come from the exact OCC distance: drone_foldable_wings 173 s -> 25 s, same 27.5 mm; tests incl. exact and parallel-face cases
- [x] FEA memory halved (~85 -> ~40 kB per quadratic tet): the intorder-4 stress-sampling basis is built per chunk of elements after the solve instead of for the whole mesh up front, and the stiffness matrix is summed per chunk with 32-bit indices; identical stresses (test: chunked == one basis; drone mount at 2.4 / 3.0 / 4.0 mm: same values). drone_foldable_wings mount_fea (70k tets) was killed for memory on a 7 GB machine, now peaks at 2.7 GB
- [x] Printed-part mass cached on the shape per spec (checks.item_mass_g): every mass / CG / thrust / endurance requirement recomputed every part's face areas (~5 s each on drone_foldable_wings, ~10 of them per check); now the first pays once and the rest take ~0 s, same values (test: cached == fresh, moved part keeps it, spec or geometry change recomputes)
- [x] clearance_min screens every pose with geom.mesh_gap (cached 0.02 mm meshes, manifold3d min_gap: ~0.4 s vs 25-42 s for OCC's exact distance on a lofted wing) and measures exactly only at poses within GAP_SCREEN_MM of the smallest, so the reported value is still exact: drone_foldable_wings fold_tail_clear_r + _l ~720 s -> ~72 s, same 62.09 mm; and when even the smallest mesh gap clears the limit by more than GAP_SCREEN_MM the mesh value is reported (labelled, within 0.04 mm of exact; the verdict cannot change): ~18 s; tests (mesh gap vs exact at random placements, near-limit == every-pose-exact, far-from-limit labelled)
- [x] Full suite: viewer click-to-edit (kerf/attribution.py: every part rebuilt under a line tracer and once per param, 29 s on servo_link, 303 s on pan_tilt) is skipped by `kerf verify` and the tests (KERF_NO_ATTRIBUTION; it cannot change a result: its failures only show in the viewer); `kerf build` keeps it; tests that exercise it through the viewer turn it back on; the drawings + intent + live + modes test group 194 s -> 43 s
- [x] geom.mesh_gap widens manifold3d's min_gap search radius from 1 mm (x4 until the gap is inside it) instead of searching 1e4 mm at once: two close curved parts took 3.7 s per pose against 0.004 s, so the mesh screen had made pan_tilt cam_clear slower than exact; now 100 s -> 20 s (the rest is the exact check its near-limit 0.9 mm gap needs), same values

## Learning Mode (Spencer, 2026-11-02; plan doc https://claude.ai/artifact/XvvyTbvfankNwgmmjXCL8n)
- [x] Learning Mode phase 2, the diary: `kerf diary <p>` / `--all` rebuilds each project's diary from git history (review.json versions, check results, commits touching the project): every problem with the stage it was found at (before parts / rough / detail / final review) and its cost (wall time to the resolving commit, parts redrawn; historical costs marked as estimates); `kerf diary --log-session` sums a Claude Code session log's token usage into the diary; output in `learning/diary/<p>.json` + `.md`; tests/test_diary.py
- [x] Learning Mode phase 3, look-back and the lesson ladder: `kerf lookback <p>` turns each diary problem into a plain-language lesson with the earliest stage it could have been caught and what would have caught it, groups similar problems across all projects (rule-based, no AI calls), keeps `learning/lessons.json` (note -> instruction -> proposed gate, never auto-enforced) and writes `learning/LESSONS.md`; acceptance: the drone_foldable_wings look-back surfaces the 2026-11-02 hand-found lessons; tests/test_lessons.py

- [ ] Learning Mode phase 1, stage gates (Codex OK): risky-parts-first gates (strength sizing for load-carrying parts, a moving-parts test with blocks, wire paths in the layout, rough review) must pass before detail work unlocks; only where they matter (a cable clip skips strength sizing); only projects started after the gate lands; tests (a test project is blocked until gates pass, a simple part is not)
- [ ] Learning Mode phase 4, scorecards (Codex OK): each lesson / gate / strategy in learning/lessons.json tracks times applied, what it caught, work saved, times it blocked good work; strong ones promoted, dead or blocking ones flagged; Studio panel; tests
- [ ] Learning Mode phase 5, practice engine (Codex OK): `kerf learn pick` draws from learning/ideas.json (ideas from Printables / MakerWorld / Thingiverse categories, FIRST / VEX rules, catalog categories, Studio requests; ideas only, never files; no weapons), a coverage map whose categories grow, 1 in 5 random wildcard, a "too similar" alarm, mix new / revisit / drill a third each with a 15 % floor; practice projects live in practice/ (skipped by tests, PLAN and batch verify); revisits saved as new versions Spencer accepts in Studio; tests
- [ ] Learning Mode phase 6, surprise exam (Codex OK for the grader code; the exam set lives in private repo kerf-exam that Spencer creates; until then `kerf learn exam` says so): scheduled exam runs, scores tracked over time; tests with a fake exam set
- [ ] Learning Mode phase 7, learning how to learn (Codex OK): per-project numbers (usage, review rounds, problems found late, exam score); when they stall, change one learning setting at a time and compare; strategies tagged with where they work; proven parts become modules (kerf/modules.py); test: a deliberately bad setting is noticed and corrected
- [ ] Learning Mode phase 8, the switch (Codex OK): Studio corner switch (budget in tokens / runs per week, overnight 1-7 am ET, steps aside when other Kerf jobs run, what it's doing now, weekly report card whose claims match the diary, undo, off); `kerf learn run` is the local runner Studio starts, using kerf/agent.py (Claude, or Codex when Claude's usage is out); fences enforced in code: never edits checks / thresholds / catalog values / tests / review.json, no purchases or prints; tests

## Phase 5 — final audit
- [x] Work source visibility: qualify partial overview counts near the summary and make project shortcuts show all matching work, preserving honest ownership and progress.

- [x] Codex source-read optimization: remove repeated copying and scanning of bounded session responses, preserve protocol and limits, and measure the local reader with synthetic data.
- [x] Work overview clarity: improve multi-job ownership, attention, observed changes and remaining-work scanning without inventing progress or finish times.
- [x] Work active-run identity: combine one running Studio Codex job with its exact observed chat without duplicate counts, retaining job controls, live context and per-owner scopes; keep ambiguous and historical runs separate.
- [x] Studio job descriptions: preserve public progress notes alongside bounded current action labels in Work; keep pause and continuation status authoritative, with actual serialization and browser evidence.
- [x] Work ownership breakdown: show each linked claim owner, activity, freshness and remaining steps within a shared Codex chat; preserve truthful live state, attention filters, search and responsive details.
- [x] Work activity descriptions: preserve Codex public progress messages alongside separate bounded tool-action labels; keep live/saved distinctions, claim replacement, search and responsive rendering truthful.
- [x] Work chat navigation: link observed Codex sessions to the documented existing-chat route and show their full chat IDs; reject unsafe routes and verify keyboard/phone behavior without opening production chats.
- [x] Work job compatibility: show actual Codex or Claude providers, usage pauses and observed continuation jobs with honest reset/retry information, preserving existing Work navigation and session ownership.

- [x] Studio agent executable discovery: reuse the Work reader's verified bundled Codex helper when PATH has no executable; preserve PATH preference and fallback, with fake-bundle command tests only.

- [x] Mobile Studio sidebar sizing: size the narrow-screen sidebar to its content within the existing height ceiling, preserving project and Activity access without wasting Work viewport space or changing desktop layout.
- [x] Mobile Work navigation: use existing All projects navigation instead of the redundant sidebar catalog while Work is rendered on narrow screens; retain Activity and utility controls, and restore catalog on other pages or wider screens.
- [ ] Fast tests (Spencer, 2026-11-02, efficiency): the suite runs in parallel (pytest-xdist, pinned) with slow / browser / all-project tests marked so `pytest -m "not slow"` is the per-change default; shared expensive fixtures (built projects, browsers) cached per session; report the before/after wall time in STATUS.md; no test removed or loosened
- [x] Reviews go stale only for real changes (Spencer, 2026-11-02, efficiency): a project's geometry fingerprint hashes only the catalog entries that project actually uses (plus its own files), so editing an unrelated catalog part no longer forces a re-review of every project; tests prove a used-entry change still invalidates and an unused one does not
- [x] Studio shell redesign: replace decorative visual chrome with a coherent neutral workbench identity, clear navigation and responsive control hierarchy; preserve all existing workflows and accessible controls.
- [ ] Fresh-eyes usability pass (Spencer, 2026-11-02; IN PROGRESS in ChatGPT Codex, delivered as pull requests - Claude sessions: don't start it, review/merge its PRs instead): look at Kerf as a first-time user (README, setup, Kerf Studio every screen at desktop + phone width, viewer, CLI help and error messages, output files) for what is confusing, overwhelming or unintuitive and for likely user mistakes / failure paths (port in use, Claude not signed in, job running, dirty repo, missing build, bad input); fix each with a test, leaving the Checks tab wording, Follow live and Work tab to their claimed items (findings for those go in their sessions' STATUS notes)
  - [x] Build it placement guide: select each hardware installation site, name its receiving part, and retain exact-location and insertion-direction cues with local context; browser regression.
  - [x] Studio redesign integration: combine reviewed shell, project workspace and Work clarity changes; verify user journeys, native layout and responsive states without live builds or remote merges.
  - [x] First-use studio guidance: contextual help, optional keyboard-accessible tour and glossary, evidence-aware welcome and compact readiness guidance; mocked desktop/mobile browser coverage
  - [x] Immediate word definitions: show beside every marked term on hover, focus or one tap without a menu or search
- [x] Fresh-eyes follow-up: Stop and authentication failures keep the project busy until the child process exits; preserve final outcome and cleanup output, with real-process regression tests (`tests/test_studio_lifecycle.py`).
- [x] Cancellation takeover compatibility: keep project locks through child exit and preserve explicit stop/auth outcomes alongside usage pause and Codex handoff.
- [x] Automatic resume setting: recheck the current switch when a queued usage retry dispatches; preserve manual Resume and re-enabled queued retries, with mocked timer tests only.

- [x] Shared claims on PR branches: take, heartbeat and release update the shared main claim without publishing feature code; fresh ownership and budget controls hold across dirty worktrees and concurrent pushes; real-git tests.
- [x] Studio shared-claim compatibility: project ownership, edit guards and Activity read shared main consistently with Work; exclude budget/control records from task cards and preserve offline source honesty.
- [ ] Run `kerf verify` (full) twice from a clean clone (`git clone` to /tmp, `./setup.sh`, `kerf verify`) — both PASS
- [x] design-reviewer subagent does a final cross-project audit against docs/ENGINEERING.md and writes AUDIT.md; every finding fixed or explicitly justified
  - [x] Audit run: three design-reviewer subagents, AUDIT.md written (index + full reports)
  - [x] Audit fixes: tvc_drone (A-1 blocker, A-2..A-7, A-9..A-14 in AUDIT.md), re-review PASS
  - [x] Audit fixes: servo_link (A-8, A-15..A-17), re-review PASS
  - [x] Audit fixes: fpv_5in (B-F1..F10), re-review PASS
  - [x] Audit fixes: pan_tilt (B-F11..F18), re-review PASS
  - [x] Audit fixes: bionic_finger (C-1..C-9), re-review PASS
  - [x] Audit fixes: robot_arm (C-10..C-20; coordinate with the E3 owner), re-review PASS
  - [x] Audit fixes: engine majors ENG-1..ENG-6 (each with a test), re-check every project
  - [x] Audit fixes: engine minors ENG-7..ENG-20 (each fixed with a test or justified in AUDIT.md)
- [x] STATUS.md final summary for Spencer: what was built, results, known limits, how to print each eval project

- [x] Studio making handoff: task-based Files & guides, build provenance and purchased-parts clarity, accessible file disclosures, truthful missing/unproven states; fixture browser coverage.

- [x] Studio History redesign: readable saved-build story, honest comparisons and intentional parameter restore.

- [x] Active job story redesign: concise current action and recorded stages, expandable research and decision evidence, accessible steering acknowledgements; fixture-only browser checks.

- [x] Viewer stage redesign: put real geometry center stage with compact contextual tools, accessible disclosures, optional part colors and grid, and current-template delivery for compatible saved viewers; preserve inspection, motion, cut, stress, assembly and engineering warnings; targeted browser tests.

- [x] Focused test workflow: bind pytest imports to the active worktree and provide a read-only checkout/test preflight plus exact-head review receipts; preserve all existing test selection and coordination rules.

- [x] Viewer direct definitions: selected technical terms reveal existing glossary meanings on hover, focus or one tap in offline saved viewers.

- [x] Assembly guide integration: verify exact placement and tool demonstrations together, install tested guide in Studio, and preserve saved geometry.
- [x] Build it site metadata: include catalog-backed screw-pivot heat-set insert locations once per physical site, with stable identities and exact part transforms; focused producer regressions.

- [x] Build it pivot metadata: directed catalog-backed shoulder/screw pivot seats and honest unknown states for pins whose axial placement is unrecorded; producer tests.

- [ ] Studio round 2 export handoff: integrate declared-source and contained-output fixes, close remaining download gaps with fixture coverage

  - [x] Complete Studio source exports: preserve declared imported assets and nested design dependencies in downloaded project archives; reject missing or escaping sources without exporting caches or stale review approval.

  - [x] Maker download containment: refuse linked or special generated output files so a project ZIP contains only regular files within its own output tree; preserve valid nested maker outputs and explain invalid exports.
