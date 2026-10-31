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
| 2 Contract | you | `projects/<p>/project.yaml` + stub parts | `kerf check <p> --quick` runs (stubs may collide) |
| 3 Parts | part-designer subagents in parallel | `projects/<p>/parts/*.py` | each part's own problems gone |
| 4 Integrate | you | fixes at the owning part | `kerf check <p>` PASS |
| 5 Strength + detail | you / part-designers | FEA + detail features | `kerf check <p>` PASS, FEA margins in DESIGN.md |
| 6 Build + look | you | `projects/<p>/out/` | you Read every render and fix what looks wrong |
| 7 Review | design-reviewer subagent | `projects/<p>/review.json` | PASS, `kerf review-status <p>` ok |
| 8 Deliver | you | commit + push, summary for Spencer | — |

Start with `.venv/bin/kerf new <p> "<Title>"` (creates the folder and a skeleton project.yaml).

## 0. Research first
Read `references/INDEX.md` — the library of open designs already studied (dimensions, licenses, failure lessons per
device type). Then run the design-researcher subagent with the brief: it reuses the index, studies what is missing,
appends new designs to the index, adds every purchased-part dimension to `catalog/hardware.json` with its source,
and writes `projects/<p>/REFERENCES.md` (references, decisions they support, open questions). Borrow architecture,
proportions and known-good numbers; avoid the failure points others hit. Only copy geometry from permissive licenses.

## 1. Understand and size (`projects/<p>/DESIGN.md`)
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
parts (boxes with the right joints and interface calls) and run `kerf check <p> --quick` to prove the tree, joint
frames and fastener groups line up before any detailed geometry.

## 3. Parts in parallel
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
- Detail pass, re-checking after each change: fillets on every inside corner of a load path (`features.safe_fillet`
  reports edges it could not do), chamfered bed edges, teardrop horizontal holes, cable routes and zip-tie points,
  lightening `pockets` only where FEA shows margin, part name/version `label`, screw access confirmed in assembly
  order. Organic/cosmetic surfaces CAD can't reasonably express: note them for Spencer to generate with Meshy.

## 6. Build and look
`kerf build <p>`. Read the assembly sheet, exploded sheet, keep-out render, every joint pose (min/max) and every
part sheet in `out/renders/`, and `out/report.json` warnings (layer direction, overhang, thin walls, part notes).
Fix anything that looks wrong even if the checks pass.

## 7. Independent review
Run the `design-reviewer` subagent on the project. Fix all blocker/major findings, rebuild, and re-review until
PASS. `kerf review-status <p>` must be ok (the review is tied to the geometry fingerprint).

## 8. Deliver
Commit and push. Tell Spencer in plain words: what it is and how it works; the key numbers with margins (mass,
reach/thrust, torque used vs stall, FEA safety factors); the shopping list (`out/bom.md`); what to print
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

Always-on checks (no yaml needed): print checks per part (one solid, bed fit, watertight, overhang, wall thickness,
`load_axis` across layers), interference at home, motion sweeps of every joint, fastener alignment + screw lengths,
pin alignment + pin lengths.

Interfaces (`kerf/iface.py`, both sides use the same group): `bolt_pattern` with `rect`/`square`/`circle` points
(clearance, counterbore, countersink, heatset, tap, nut_trap), `servo_mount`, `horn_mount`, `bearing_seat`,
`motor_mount`, `stack_mount`, `pin_hole` (printed hinges: `press` or `heatset`/`tap` on the side that holds the pin,
`free` on the side that turns; the revolute axis must be the pin axis; the knuckle span should equal a stocked pin
length from the catalog `lengths`).

Drives (`kerf/drives.py`): `spur_pair` (gears at the right centre distance), `belt_length`, `belt_teeth`,
`center_for_belt`, `belt_keepout` for GT2 belts.

Features (`kerf/features.py`): `channel`, `shell`, `gusset`, `teardrop_hole`, `threaded_rod`/`threaded_hole`
(printed, >= M6), `gear_pair`, `snap_hook` and `living_hinge` (strain-checked), `label`, `pockets`, `safe_fillet`.
