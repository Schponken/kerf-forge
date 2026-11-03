---
name: kerf
description: Design a complete 3D-printable mechanical assembly (drones, robot arms, brackets, grippers, enclosures, mechanisms) from a plain-language description, with verified fits, motion, strength and print files. Use when Spencer asks to design, model, make or print a part or a multi-part device.
argument-hint: "<what to build, in plain words>"
---

# kerf: description → engineered, printable assembly

You are the systems engineer. Turn a one-paragraph request into a finished Kerf project that passes `kerf build`
and the design-reviewer. Ask Spencer only about real choices that change the design (budget class, which actuators
he already owns, size limits), at most once, up front; when nobody can answer, decide, and write the assumption in
DESIGN.md. Work through the steps in order; each has an output file and a gate.

| Step | Who | Output | Gate |
|---|---|---|---|
| 0 Research | design-researcher subagent | `projects/<p>/REFERENCES.md`, new rows in `references/INDEX.md`, catalog entries | every purchased-part number in the catalog with a source |
| 1 Size | you | `projects/<p>/DESIGN.md` | sizing math shows margin on every requirement |
| 2 Contract | you | `projects/<p>/project.yaml` + stub parts (`ctx.stub`) | `kerf check <p> --quick` runs (stub collisions fold into one "design in progress" line) |
| 3 Parts | part-designer subagents in parallel | `projects/<p>/parts/*.py` | each part's own problems gone |
| 4 Integrate | you | fixes at the owning part | `kerf check <p>` PASS |
| 5 Strength + detail | you / part-designers | FEA + detail features | `kerf check <p>` PASS, FEA margins in DESIGN.md |
| 6 Build + look | you | `projects/<p>/out/` | you Read every render and fix what looks wrong |
| 7 Review | design-reviewer subagent | `projects/<p>/review.json` | PASS, `kerf review-status <p>` ok |
| 8 Deliver | you | commit + push, summary for Spencer | — |

Start with `.venv/bin/kerf new <p> "<Title>"` (creates the folder and a skeleton project.yaml). Its `root: TODO`
makes the edit hook report "assembly.root 'TODO' is not a part" until the contract and stub parts exist (step 2);
that is expected, not a problem to chase.

**No subagent tool?** (You are yourself a subagent, or the Agent/Task tool is missing.) Do the researcher and
part-designer work yourself, following `.claude/agents/<name>.md`. The review must still come from a separate
design-reviewer agent: run it headless with the prompt on stdin (`--allowedTools` takes several values and would
swallow a prompt argument): `claude -p --agent design-reviewer --allowedTools "Read,Glob,Grep,Bash,Write" < prompt.txt`.
A review takes ~10 min, the Bash tool's foreground limit, so start it with `nohup ... > review_out.txt 2>&1 &` and poll
(`sleep 240; pgrep -f "agent design-reviewer"`) until it has exited and review.json is written. Never finish while
it (or a `kerf verify` its session started) is still running.

## Quote mode ("QUOTE ONLY" in the request)
Kerf Studio asks for options before a long run. Do step 0's research (light: the reference index, catalog, a few
searches), then write the JSON file the request names and STOP (no project folder, no part files):
```json
{"request": "<the request in one line>",
 "options": [{"title": "Rack-and-pinion parallel jaws", "summary": "<2-3 plain sentences: how it works, why>",
              "parts_printed": 6, "purchased": [{"key": "servos.MG996R", "qty": 1}, {"key": "screw:M3x8:socket", "qty": 12}],
              "cost_usd": 24.5, "cost_note": "kerf price total; 2 parts not priced yet", "print_g": 120,
              "print_hours": 6.5, "print_note": "how you estimated it (kerf price gives the lower bound)",
              "risks": ["<what could make it fail or cost more>"]}],
 "recommended": 0, "assumptions": ["<anything you had to decide>"]}
```
2-3 genuinely different architectures (not sizes of one). Price them with `.venv/bin/kerf price <key:qty ...>
--grams <estimated printed grams> --material <m>` (it counts Spencer's parts on hand and prints the filament cost and
the print-time lower bound); keys come from catalog/prices.json. Prefer the parts on hand the brief lists. Say in
`cost_note` / `print_note` what is estimated. When he picks one, the full design starts with that option in the brief.

### Scenario options ("SCENARIO OPTIONS" / Request kind: scenario)
A problem is not yet a part specification. Use the supplied success criteria, priority and effort answers. Research
ready-made solutions and existing/free designs before proposing custom work; open the original pages, check the
license before recommending reuse, and explain what each source actually establishes. Do not fabricate a source,
price, availability or performance claim. Buying a solution is a valid recommendation, and is never an order.

Use the quote shape above with `request_kind: "scenario"`, **2-3 options**, one `route: "buy"` and at least one
`route: "adapt"` or `route: "build"`. Each option also needs:
- `fit`: how it meets the stated outcome and where evidence is still missing.
- `effort`: hands-on setup/build time, skills and maintenance; distinguish this from print time and delivery time.
- `sources`: `[{"title": "<original page>", "url": "<https URL you opened>", "finding": "<what it supports, date checked; reuse license where relevant>"}]`.
- `risks` and `next_steps`: nonempty lists in plain words.
- `cost_note` and `print_note`: evidence and estimate basis, including exclusions. Unknown `cost_usd` / `print_hours`
  are JSON `null` with the missing evidence explained, never zero. A buy-only option has 0 printed parts / print hours;
  an option that needs a printed adapter uses `adapt`. A quote is an estimate, not proof that the scenario works.

At the top level add `recommendation_reason`, tying the zero-based `recommended` option to the user's priorities,
`assumptions` (nonblocking, explicitly unverified), and `questions` (only unanswered questions that must be settled
before a design can start). Studio shows those questions and waits for an updated comparison. Ask only what changes
the choice: for "my plants die when I travel", likely trip duration, plant count/water needs, indoor/outdoor use,
available water/power and tolerance for leaks. The user's success/notes fields can answer them; don't ask again.
Do not create a project, buy anything, or send printer commands. Validate the saved JSON before stopping:
`python -c 'import json; from kerf.quotes import validate; validate(json.load(open("<quote path>")), scenario=True)'`.

## 0. Research first
Read `references/INDEX.md` — the library of open designs already studied (dimensions, licenses, failure lessons per
device type). Then run the design-researcher subagent with the brief: it reuses the index, studies what is missing,
appends new designs to the index, adds every purchased-part dimension to `catalog/hardware.json` with its source,
and writes `projects/<p>/REFERENCES.md` (references, decisions they support, open questions). Borrow architecture,
proportions and known-good numbers; avoid the failure points others hit. Only copy geometry from permissive licenses.

Search first, per part: for the whole device and for each printed part or sub-assembly in the part list run `.venv/bin/kerf find "<short description>" --project <p>` (Printables measured, Thingiverse with a token, plus the MakerWorld/GrabCAD searches the researcher runs and adds with `--add`). If a candidate fits the contract (dimensions, interfaces, load) and its license allows it, reuse or adapt it — rebuild its proven geometry and numbers in the part code with credit — instead of inventing one. Either way fill in its `Decision:` line in REFERENCES.md (reuse / adapt / design new, and why); `kerf check` warns while one is TODO. Purchased hardware with a McMaster STEP: ask Spencer to drop the file into catalog/models/.

## 1. Understand and size (`projects/<p>/DESIGN.md`)
- **Use story first** (project.yaml `use_story`, required for new projects; kerf/usestory.py): who uses it, where,
  how often, what goes wrong (drop, crash, heat, rain, gloves, other). Each hazard becomes checks: `heat_limit`
  (material HDT from the datasheet), `rain_cover`, `access_opening` (38 mm gloved finger), `impact_case` (a
  `fea_static` with `case: drop|crash` must carry story_drop_n / story_crash_n), or `survive: false` with the
  consequence (what breaks, how it is fixed; it goes into ASSEMBLY.md). Ask the user when the story is unclear.
- **Requirements** in numbers: function, loads/payloads, motion ranges, size limits, mass budget, environment.
- **Architecture**: 2-3 options in one line each, the pick and why (cite REFERENCES.md).
- **Purchased parts** from the catalog with the sizing math shown, e.g. servo torque = Σ m·g·r at the worst pose
  (arm stretched horizontal) + payload, ask <= 50% of stall; thrust/weight; reach; bearing loads. Missing hardware:
  research it and add it to the catalog with a source URL first.
- **Electrical system** (anything that moves or is powered): derive EVERY part it needs to work, not only the ones
  the brief names — controller/FC, ESCs or servo/motor drivers, receiver + antenna, VTX + antenna + camera for FPV,
  BEC/regulator for servos and logic (servo stall current x count), battery (capacity from the run/flight time
  target), strap + pad, power connector, switch, fuse where needed, sensors. Each is a catalog item with a source.
  Draw the power tree (battery -> connector -> distribution -> loads) and pick wire gauges from current
  (docs/ENGINEERING.md 10b); it becomes `electrical:` + `wiring:` (docs/ARCHITECTURE.md "Electrical") with
  `power_budget`, `flight_time`/`run_time` and `connector_access` requirements. Leave wire channels and tie points
  in the parts for every run.
- **Part list**: each printed part, its job, material (docs/ENGINEERING.md section 2), `print_rot`, `load_axis`,
  rough envelope.
- **Load → section** table, one row per structural part: the loads entering and leaving it, the bending moment /
  torque along it (where it peaks), the section chosen (I / C / box / tube / ribbed plate / solid) and why, and how
  the section changes along the length (taper, ribs, pockets). The part-designers shape from this, not from boxes.
- **Style**: `style: {radii: [...], edge_break: mm}` in project.yaml, one fillet/edge language for the whole product.
- **Interface table**: every connection — part A, part B, interface call (toolbox below), group name, screw/pin
  size and count.
- **Joint tree** with ranges and home, plus coupled poses worth checking (gimbal corners, finger curl).
- **Requirements list** for project.yaml (all numeric), including `fea_static` on every structural part with its
  real load case × the safety factor of ENGINEERING.md section 3, and a `cantilever_stress` hand check to size it.
- **Assembly order** step by step (which screw goes in when, and from which side).
- **Risks / unverified numbers** Spencer should measure before the final print (catalog notes marked UNVERIFIED).

## 2. Contract (`projects/<p>/project.yaml`)
Params, printed parts (`material`, `print_rot`, `load_axis`, `infill`), purchased items (catalog proxies with joints
and fastener `groups:`), keep-outs (prop discs with `owner`, camera view, finger zones), the joint tree, allowed
overlaps (only with a physical reason), sweeps/poses, and requirements. Schema: docs/ARCHITECTURE.md. Write stub
parts (boxes with the right joints and interface calls, each calling `ctx.stub("why")` before `ctx.finish`) and run
`kerf check <p> --quick` to prove the tree, joint frames and fastener groups line up before any detailed geometry.
Stubs show in the report and in Studio as ONE "design in progress" problem ("being designed"), never as a list of
collisions; replacing a stub with the real part removes its `ctx.stub` call. A project is never left with a stub.
Realistic limits: soft things (foam pads, battery straps, wire bundles) get `compress_mm` + `compress_why` instead of an
overlap allowance; a requirement that is a preference, not a safety or function limit (a target weight, a nice-to-have
flight time), may be `advisory: "<why a miss is acceptable>"` (never a strength check); thin walls only block on parts
a strength check loads (`structural: true` for one that carries load without a check).

## 3. Parts in parallel
**Most expensive to redesign first** (Spencer, 2026-11-02). Before detailing anything, prove the concept numbers
(mass, thrust/weight, flight or run time, power, CG / static margin, wing loading, servo torque) with
`kerf req <p>` on the stubs, then design the load-carrying parts that the most others mate with (frame, spine, hub)
and prove their FEA with `kerf req <p> <id>` before launching the leaf parts. `kerf check` follows the same order:
it runs these requirements first and stops before the detail checks when one fails (`--all` to run everything).
Launch one `part-designer` subagent per independent printed part in a single message. Give each its contract from
DESIGN.md: envelope, every interface (exact iface call, group, location and frame), loads and load path, print
orientation, material, and which other parts it must clear. Parts that depend on each other's geometry go to the
same subagent. Every mating feature comes from `kerf/iface.py` with the same group on both sides.

## 4. Integrate
`kerf check <p>` until PASS. A part that fails to build reports its file line, the operation and a `fix:` line (e.g. the largest fillet those edges take): apply the fix and re-check before anything else. Fix every problem at the part that owns it. Never widen an allowed overlap, loosen a
limit or edit the catalog to make a check pass unless the physics says so (write why in DESIGN.md, with a source).

## 5. Strength, then detail
- Run `fea_static` for every structural part (fixed at its fastener group / joint, loaded where the load enters).
  If it fails, change geometry (section depth, ribs, fillets, orientation) before reaching for a stronger material.
- Read each part's stress summary and hot zones (out/review/PACK.md; the full `stress` block is in out/report.json) and its "overbuilt" / "sharp inside corner" warnings: move
  material from the cold zones to the hot ones (pockets, thinner walls, deeper ribs) and fillet the stressed corners,
  then re-run the FEA. Uniformly 10x-overbuilt parts are a design failure, not a safety margin.
- Detail pass, re-checking after each change: fillets on every inside corner of a load path (`features.safe_fillet`
  reports edges it could not do), chamfered bed edges, teardrop horizontal holes, cable routes and zip-tie points,
  lightening `pockets` only where FEA shows margin, part name/version `label`, screw access confirmed in assembly
  order. Organic/cosmetic surfaces CAD can't reasonably express: use creative mode (below).

### Creative mode (Meshy shells fused with exact features)
For an organic or cosmetic part (a sculpted cover, a hand-shaped grip, a character shell), declare it `source: meshy`
with a `prompt`, `bounds` (where the shell goes, part frame) and optionally `fit: uniform`. Its part file builds
only the exact features (flanges, bosses, joints, `iface` fastener/pin sites) and calls `ctx.mesh_cut(...)` for
every screw hole, a hex-key access bore above every screw head the shell would cover, cable holes and keep-out
pockets. Keep the features reaching into the shell so the result is one body; the shell carries no structural load
(FEA, fasteners and STEP use the features only). When `kerf check` reports the model missing:
1. Check the Meshy credit balance, then run Meshy text-to-3D with the yaml `prompt` (preview, then refine for the
   final texture-free mesh), poll the task until it succeeds, and download the model as GLB to the path the error
   names (`meshes/<part>.glb`).
2. Write `meshes/<part>.meshy.json`: task id(s), prompt, mode, date, so the shell can be regenerated or refined.
3. `kerf check <p>`: the engine scales, repairs and fuses it (kerf/meshy.py) and the print checks, interference,
   key access and exports all run on the fused body. Look at its part render; if the shell hides a feature or
   looks wrong, change the prompt or bounds and regenerate.

**Auto-fix pass** (before the build and the review): `.venv/bin/kerf fixes <p>` turns the last check's common
findings into edits of the part code: horizontal holes cut round get `teardrop="auto"` (`--apply` writes these),
self-tapping holes near an edge can become heat-set inserts (`--apply --heatset`; the insert's bore is larger, so the
check that follows must still pass, else revert and grow a boss), and it lists what needs you (bosses, fillets).
Re-run `kerf check <p>` after applying.

## 6. Build and look
`kerf build <p>`. Read `out/review/PACK.md` (report.json digested: requirements, warnings, part and stress
summary), the `*_sheet.png` renders (assembly, exploded, every part) and `out/review/contact_*.png` (FEA plots, joint
poses, keep-outs on a few sheets). They cost a fraction of the tokens of report.json and the single views; open a
single view or a report.json section only to check a detail. Fix anything that looks wrong even if the checks pass.

## 7. Independent review
Run the `design-reviewer` subagent on the project. Fix all blocker/major findings, rebuild, and re-review until
PASS. `kerf review-status <p>` must be ok (the review is tied to the geometry fingerprint).

## 8. Deliver
Commit and push. Tell Spencer in plain words: what it is and how it works; the key numbers with margins (mass,
reach/thrust, torque used vs stall, FEA safety factors); the shopping list with links and cost (`out/bom.md`, priced from `catalog/prices.json`; add a dated, sourced price for any row it lists as unpriced); the step-by-step build (`out/ASSEMBLY.md`); what to print — and print it: `kerf print <p>` orients, plates and slices, `kerf print <p> --send 1` starts plate 1 on the A2L over LAN (Developer Mode; config in ~/.kerf/bambu.json), otherwise `--open` hands the plates to Bambu Studio;
(`out/plates/*.3mf`, open in Bambu Studio; material, orientation); the assembly steps; numbers to measure on real
hardware first; known limits. If `catalog/printers/` has no profile for his printer + the project's material yet, tell him to print the fit coupon first (`kerf calibrate --material <m>`, then `kerf feedback ...`) and rebuild: holes then fit his printer, not a textbook one.

## Toolbox

Requirement checks (`requirements:` in project.yaml; arguments in each function's docstring):

| check | proves |
|---|---|
| `mass_max` | estimated assembled (or `include`d) mass under a limit |
| `size_max` | assembled bounding box under a limit |
| `distance` | distance between two joint origins (reach, link lengths, grip opening) at a pose |
| `clearance_min` | smallest gap between two items at home and over joint sweeps |
| `static_torque` | worst gravity torque on a revolute joint (downstream mass + payload) vs servo stall × fraction |
| `thrust_to_weight` | total thrust / all-up mass |
| `fea_static` | finite-element stress + deflection of one printed part, layer-direction aware |
| `cantilever_stress` | beam-theory stress at a named section (sizing hand check) |
| `cg` | assembled centre of gravity vs a reference line (lateral, height), over poses |
| `tip_over` | static tip-over angle from CG height and the support polygon |
| `channel_clear` | an internal channel (tendon, wire) is open end to end for a diameter, over poses |
| `prop_clearance` | prop discs clear each other and every other item, at home and over sweeps |
| `power_budget` | battery C, BEC/ESC outputs, connectors, wire ampacity + burst heating, input voltages hold at avg and peak |
| `flight_time` | hover minutes on 80 % of the pack (momentum-theory hover power + every other load) |
| `run_time` | minutes on 80 % of the pack at every load's average draw (robots, gadgets) |
| `connector_access` | a plug / cable / finger reaches the battery plug or USB port with the device assembled |
| `hard_stop` | a joint moved past an end of its range collides, i.e. a real mechanical stop holds it there |
| `gear_bending` | Lewis tooth bending of a printed spur pair at the driving servo's stall torque |
| `heat_limit` | (use story heat) every part's material heat deflection temperature above the stated max |
| `rain_cover` | (use story rain) rain-sensitive electronics roofed from above |
| `access_opening` | a 32 mm (38 mm gloved) finger opening to a handled item, clear to outside |
| `impact_case` | (use story drop / crash) a strength case carries the stopping force, or an impact_fea simulates it |
| `story_covered` | (use story "other") the named requirements exist |
| `impact_fea` | drop / crash: impact force from the part's own FEA stiffness, scaled stress vs strength / sf |
| `stop_impact` | a joint driven into its hard stop: inertia beyond it + stall torque on the stop |
| `natural_freq` | first bending mode with a carried mass vs rotor / blade-pass (or stated) excitation |
| `weak_link` | the cheap part uses more of its limit than the expensive ones under one event |
| `flex_strain` | snap-fit / living-hinge root strain vs permissible strain |
| `creep_limit` | a constant-load case under the material's documented creep-rupture stress / sf |
| `screw_locking` | every metal-thread fastener group on a vibrating build names its locking |
| `repair_access` | field-repair parts come off the finished device with a hex key |
| `planetary_bending` | planetary set buildable + Lewis stress on the most loaded planet |
| `worm_drive` | worm wheel Lewis stress, efficiency, self-locking when required |

Always-on checks (no yaml needed): print checks per part (one solid, bed fit, watertight, overhang, wall thickness,
`load_axis` across layers), interference at home, motion sweeps of every joint, fastener alignment + screw lengths,
pin alignment + pin lengths.

Interfaces (`kerf/iface.py`, both sides use the same group): `bolt_pattern` with `rect`/`square`/`circle` points
(clearance, counterbore, countersink, heatset, tap, nut_trap), `servo_mount`, `horn_mount` (disc horns, or the stock
SG90 arm horns servo_horns.sg90_arm_1/2/4: pass horn_mount the same use / start_deg as the horn item's use_holes /
hole_start_deg), `bearing_seat`,
`motor_mount`, `stack_mount`, `pin_hole` (printed hinges: `press` or `heatset`/`tap` on the side that holds the pin,
`free` on the side that turns; the revolute axis must be the pin axis; the knuckle span should equal a stocked pin
length from the catalog `lengths`), `tripod_socket` (1/4-20 camera-tripod mount: captive catalog nut over a
clearance hole).

Drives (`kerf/drives.py`): `spur_pair` (gears at the right centre distance), `belt_length`, `belt_teeth`,
`center_for_belt`, `belt_keepout` for GT2 belts.

Features (`kerf/features.py`): `channel`, `shell`, `gusset`, `teardrop_hole`, `threaded_rod`/`threaded_hole`
(printed, >= M6), `gear_pair`, `snap_hook` and `living_hinge` (strain-checked), `label`, `pockets`, `safe_fillet`.

### Motion and aircraft checks

| Check | Inputs | What it checks |
|---|---|---|
| `grip_hold` | `joint` (the grip servo's joint), `pads` [moving jaw point, fixed jaw point] (item.label), `mass_g`, `friction` (number or catalog `friction.<jaw>-<object>`), `width_mm`, `size_mm`, `pad_t_mm`, `pad_mm`, `pose`, `torque_fraction` (0.5), `shake_g` (1), `shake_hz` (2), `max_slip_mm` (1), `actuator` | worst slip of the object across the jaws under gravity + the shake on three axes (mm) |
| `joint_speed` | `end` (pose), `max_s`, `start` (pose, default home), `payload_g`, `payload_at`, `band_deg` (3) | time until every servo joint stays within band_deg of `end` (s; none = never) |
| `drop_impact` | `part`, `at` (item.label hit point), `height_mm`, `radius_mm` (surface radius at the hit), `subtree` (joint: what falls; default all), `pose`, `down` (assembly-frame direction to the floor), `floor` (rigid or a catalog material), `payload_g`, `payload_at`, `fea` {`fixed`, `direction`, `sf`, `max_disp_mm`, `mesh_size`, `radius`} or `max_force_n` | peak contact force (N); limit = the force the part's FEA (crash case) allows |
| `prop_ground` | `min_mm`, `props`, `up` | lowest prop disc above the ground plane the airframe stands on (mm) |
| `static_margin` | `min` (0.05), `max` (0.15), `wing` (param prefix, `wing_`) | (neutral point x - assembled CG x) / MAC (range) |
| `wing_loading` | `max_g_dm2`, `wing` | all-up mass / wing area (g/dm²) |
| `stall_speed` | `max_kmh`, `cl_max` (wing; else 0.9 x airfoil clmax x cos quarter-chord sweep), `airfoil`, `wing` | sea-level stall speed (km/h) |
| `spar_bending` | `tubes` (catalog tube paths in one half), `y_root` (mm, where they leave the centre section), `load_factor` (6), `sf` (1.5), `wing` | spar stress at y_root under load_factor g, elliptical lift, tubes sharing by E I / (strength / sf) |
| `static_margin_tail` | `min`, `max`, `wing`, `tail` (param prefixes, `htail_` with its own `x_le0`), `halves` {right: item, left: item} + `root_y` (pivoting wing halves), `pose`, `eta_t` (0.9), `downwash`, `fuselage` {length_mm, width_mm, k_fus} | (NP - CG) / spread MAC of a wing + tail aircraft at the pose; NP from Raymer 12.6 lift slopes, 2 a / (pi A) downwash, strip-theory wing AC |
| `fold_hinge_moment` | `joint`, `item`, `side`, `speed_kmh`, `cd`, `cl`, `actuator` or `stall_kgcm`, `ratio`, `max_fraction` (0.5), `root_y` | worst aerodynamic moment (kg·cm) about a wing sweep / fold joint over its range vs stall x ratio x fraction |
| `bungee_launch` | `elastic` (catalog force_curve), `strands`, `rest_mm`, `start_mm`, `end_mm`, `payload_g`, `moving`, `angle_deg`, `rolling_mu`, `notch`, `notches`, `notch_pitch_mm`, `min_speed_m_s`, `max_g`, `brake` | exit speed (m/s) of an elastic launcher at its strands x notch setting, peak g, the setting table, brake stop distance |
