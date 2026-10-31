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
- [ ] New requirement checks, each with a test that has a known hand-calculated answer:
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
- [ ] servo_link review follow-ups (review of fingerprint 43b35f19, all minor): `access.insertion_paths` skips subtree items that `assembly.order` installs later (test), then declare the servo's top-first insert + order in servo_link; horn proxy seats ON the spline instead of sliding over it (~4 mm too far out) — add a spline-engagement value to the horn catalog entry (sourced) and use it in the proxy; FEA render titles show surface peak, volume peak and the p99.9 value used for pass/fail; project.yaml bom_extra washer text says 4.2 mm holes (now 4.5 mm keyhole slots); count the washer in tab-screw grip; then rebuild servo_link and get a fresh PASS review
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
- [ ] E2 `fpv_5in` — 5" freestyle FPV quad frame (evals/fpv_5in/brief.md)
- [ ] E3 `robot_arm` — 4-axis desk robot arm with gripper (evals/robot_arm/brief.md)
- [x] E4 `tvc_drone` — coax thrust-vectoring rocket-style drone (evals/tvc_drone/brief.md)
- [ ] E5 `bionic_finger` — tendon-driven 3-segment finger (evals/bionic_finger/brief.md)
- [ ] E6 `pan_tilt` — BLIND test of the tool: a fresh general-purpose subagent with no prior context is given only evals/pan_tilt/brief.md and told to use the `kerf` skill; it must reach PASS on its own. Record its transcript summary and anything it got stuck on in evals/pan_tilt/BLIND_RUN.md, then fix the skill/engine for every stumble (and re-run blind if fixes were needed)

## Phase 4 — Spencer can see and use it
- [x] Assembly viewer: `kerf build` also writes `projects/<p>/out/viewer.html` — a self-contained page (no network) showing the assembly with part list, explode slider, a slider per moving joint (uses joint axes from the report), part visibility toggles, BOM table and per-part print info
- [ ] Publish one combined Kerf Forge gallery page as a claude.ai artifact (Artifact tool) with every eval project's viewer, renders and BOM; put the link in README.md
- [ ] README.md: what it is, setup, how to ask for a design (`/kerf ...` in Claude Code), what it can and can't do, results table for every eval (pass/fail, parts, mass, print plates), links to renders

## Phase 4b — features from the competitor study (Zoo, AdamCAD, Leo AI, MakerWorld, Fusion; see docs/COMPETITORS.md)
- [x] Search-first: before a part is designed, `kerf find "<description>"` searches Printables, Thingiverse, GrabCAD, MakerWorld and vendor STEP files (McMaster etc.) and writes candidates (link, license, key dimensions) into the project's REFERENCES.md; the `kerf` skill reuses or adapts a fitting part instead of generating one, and records why when it doesn't. Sources by access: Thingiverse (official API), Printables (public GraphQL), MakerWorld/GrabCAD (web search + page fetch); McMaster blocks automated downloads, so list the part number + link and ask Spencer to drop the STEP into catalog/models/
- [x] Creative mode via Meshy: parts declared `source: meshy` with a prompt are generated through the Meshy MCP tools for organic/cosmetic shells and fused with the exact mounting features into ONE printable body. Proven approach (docs/prototypes/mesh_merge.py, 2026-10-30): do the booleans in mesh space with `manifold3d` (0.2-1.6 s for 80k-330k triangles, watertight single body, M3 holes probed exact), NOT through the B-rep kernel (34 s at 20k triangles). Repair ladder per connected piece: merge verts + fill holes, else voxel remesh; then union the pieces (a broken mesh with a stray overlapping piece otherwise yields 2 bodies). Holes/bosses/keep-outs come from the part's build123d features, tessellated fine; scale the mesh to declared bounds first. Output STL/3MF for printing; STEP holds the mechanical features only. Fastener/interference checks use the merged mesh. Add manifold3d + networkx to setup. Test with a cached broken mesh so CI needs no Meshy call
- [x] Self-correcting errors: every build/check failure raised from part code names the part, the feature and the fix hint (e.g. "fillet on edge group 'top' failed: radius 3 > wall 2.4; use <= 1.1"), and the part-designer loop feeds it back and retries automatically; test with deliberately broken parts
- [x] Click-to-edit in the viewer: clicking a face in `viewer.html` shows which part file, feature and parameter produced it, and lets Spencer copy a ready-made edit request ("arm.py: arm_length 120 -> 130") for Claude Code
- [ ] Bambu A2L handoff: `kerf print <project>` auto-orients each part (min supports, load_axis aware), slices with the A2L profile (Bambu Studio / OrcaSlicer CLI) to .gcode.3mf, then sends over the printer's official LAN / developer mode (MQTT + FTPS; see wiki.bambulab.com third-party-integration and enable-developer-mode) and polls status. Fallback when LAN access is off: write the sliced file and open it in Bambu Studio for one-click send. Dry-run tested in CI; one real print verified with Spencer
- [x] Print-truth loop: `kerf calibrate` builds a small A2L coupon (M2/M2.5/M3 clearance + tap + heat-set holes, 608 and 623 bearing pockets, 0.2/0.3/0.4 mm slip-fit pins, a servo-tab window). Spencer reports what fit (`kerf feedback <material> hole_M3=tight ...`); offsets are stored per printer+material in catalog/printers/ with the date and applied by iface, so every later design fits his real printer, not a textbook one. Tests use synthetic feedback
- [x] Ship package: BOM gains buy links and unit/total cost for every purchased item (catalog sources), and `kerf build` writes `out/ASSEMBLY.md` — step-by-step assembly order with an exploded render per step and the screw/insert list for each step

## Phase 5 — final audit
- [ ] Run `kerf verify` (full) twice from a clean clone (`git clone` to /tmp, `./setup.sh`, `kerf verify`) — both PASS
- [ ] design-reviewer subagent does a final cross-project audit against docs/ENGINEERING.md and writes AUDIT.md; every finding fixed or explicitly justified
- [ ] STATUS.md final summary for Spencer: what was built, results, known limits, how to print each eval project
