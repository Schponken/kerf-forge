# Kerf Forge

Kerf Forge turns a plain-language description — "a 4-axis desk robot arm that lifts 150 g", "a 5-inch freestyle FPV
frame", "a pan-tilt head for a Raspberry Pi camera" — into a complete, engineered, printable multi-part assembly:

- every **printed part** as parametric build123d code, oriented for printing, with STEP / STL / 3MF and packed
  **Bambu Lab A2L plates**;
- every **purchased part** (servos, motors, bearings, screws, boards, batteries, connectors, wire) as a proxy built from
  `catalog/hardware.json`, where every number has a source URL;
- **proof that it fits and works**: zero interference, fasteners aligned and sized, pinned hinges coaxial, every
  moving joint swept collision-free, hex-key reach, insertion paths, engineering requirements (torque, thrust/weight,
  reach, centre of gravity, tip-over, prop clearance, FEA strength, tendon/wire channels);
- the **complete electrical system**: power tree, current per wire and part, ratings (battery C, BEC/ESC outputs,
  connectors, wire heating), flight/run time, routed wire lengths that clear every part at every pose, a wiring
  diagram and solder steps;
- a **ship package**: priced BOM with buy links, step-by-step `ASSEMBLY.md` with a render per step, a self-contained
  3D viewer, and an independent engineering + visual review.

## Setup

```bash
git clone https://github.com/Schponken/kerf-forge && cd kerf-forge
./setup.sh                 # idempotent: Python venv, build123d, gmsh/scikit-fem, Node renderer; ends with ALL OK
.venv/bin/kerf doctor      # environment self-test
```

## Asking for a design

In Claude Code, inside this repo:

```
/kerf a pan-tilt head for a Raspberry Pi Camera Module 3 on a 1/4-20 tripod screw, two micro servos
```

The `kerf` skill (`.claude/skills/kerf/SKILL.md`) runs the whole workflow: research of proven open designs and
datasheets (design-researcher subagent) → sizing and `DESIGN.md` → the `project.yaml` contract → parts in parallel
(part-designer subagents) → `kerf check` until PASS → FEA and detail pass → `kerf build` and a look at every render →
independent review (design-reviewer subagent) → commit. You get `projects/<name>/` with everything below.

| Command | What it does |
|---|---|
| `kerf check <p> [--quick]` | build every part and run every check (motion sweeps, requirements, wiring routes) |
| `kerf build <p>` | check + STEP, per-part STL/3MF, A2L plates, BOM, WIRING.md, ASSEMBLY.md, renders, viewer → `projects/<p>/out/` |
| `kerf print <p> [--dry-run]` | orient, slice for the A2L and send over LAN (or open in Bambu Studio) |
| `kerf calibrate` / `kerf feedback` | print a fit coupon, report what fit; later designs use your printer's real offsets |
| `kerf find "<description>"` | search open model sites for an existing design first |
| `kerf verify` | the definition of done: tests, every project, every review current, every eval |
| `kerf status` | one-screen overview |

What to open after a build: `out/viewer.html` (assembly with joint sliders and explode), `out/bom.md` (shopping
list), `out/ASSEMBLY.md`, `out/WIRING.md` + `out/wiring.svg`, `out/plates/*.3mf` (open in Bambu Studio).

## What it can and can't do

Can:
- Multi-part mechanisms with screws, heat-set inserts, nut traps, bearings, dowel/screw pivots, servo and motor
  mounts, printed gears and GT2 belts, tendon channels, snap hooks and living hinges.
- Prove geometry (fits, clearances, motion over the whole range, tool access) and first-order engineering (static
  torque vs stall, thrust/weight, CG, tip-over, beam and FEA stress against layer-direction strength, electrical
  ratings and hover/run time).
- Use your printer's measured fits once you print the calibration coupon.

Can't (yet), or only roughly:
- Dynamics: vibration, control-loop behaviour, crash loads beyond the stated static cases. Flight tuning is yours.
- Hover/run time are momentum-theory estimates (figure of merit and motor efficiency from published ranges), not
  thrust-stand data.
- Purchased-part numbers marked UNVERIFIED in the catalog (some servo horn and tab heights, a few current draws) are
  the best published figures; each project's `DESIGN.md` lists what to measure before printing.
- Organic / cosmetic surfaces are generated through Meshy only when asked for; CAD stays the engineering truth.
- A real print on Spencer's A2L through `kerf print` is still to be done once with him.

## Gallery

All projects on one page, with status, renders, requirements, BOM and each 3D viewer: [Kerf Forge Gallery](https://claude.ai/artifact/McXTe1kc9EMpfKshBNu6mH) (private to Spencer's claude.ai account until shared). To refresh it: `kerf build` the projects, `.venv/bin/kerf gallery`, then publish `out/gallery/index.html` with the files listed in `out/gallery/files.json` to that same URL (Artifact tool, `url`).

## Final summary (2026-10-31)

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

## Results — the eval projects

Each eval is a brief in `evals/<id>/brief.md` graded by `evals/<id>/acceptance.py`. The table is generated by
`.venv/bin/python tools/readme_results.py` from the latest `kerf build` of each project (Build = `kerf build`
passes, Review = the design-reviewer's PASS is current for this exact geometry, Eval = acceptance passes; mass is
printed + purchased parts without wire).

<!-- RESULTS:START -->
| Project | Build | Review | Eval | Printed parts | Purchased | Mass (g, parts) | Plates | Renders |
|---|---|---|---|---|---|---|---|---|
| bionic_finger | PASS | PASS | PASS | 4 | 0 | 28.8 | 1 | [assembly](docs/results/bionic_finger.png) |
| fpv_5in | PASS | PASS | PASS | 6 | 13 | 574.6 | 1 | [assembly](docs/results/fpv_5in.png) |
| pan_tilt | PASS | PASS | PASS | 3 | 8 | 387.3 | 1 | [assembly](docs/results/pan_tilt.png) |
| robot_arm | PASS | PASS | PASS | 12 | 18 | 1206.0 | 1 | [assembly](docs/results/robot_arm.png) |
| servo_link | PASS | PASS | PASS | 3 | 5 | 515.2 | 1 | [assembly](docs/results/servo_link.png) |
| tvc_drone | PASS | PASS | PASS | 9 | 16 | 718.4 | 3 | [assembly](docs/results/tvc_drone.png) |
<!-- RESULTS:END -->

Regenerated 2026-10-31 14:45 UTC after every eval was finished: all six build, pass a current independent review and pass
their acceptance graders. The gallery page above shows the same builds.

The design notes, sizing math, assembly order and what to measure first are in each `projects/<id>/DESIGN.md`.

## Repo map

- `kerf/` — the engine (see `docs/ARCHITECTURE.md` for every module and the `project.yaml` schema)
- `docs/ENGINEERING.md` — the engineering rules every design follows (safety factors, fits, fasteners, layers,
  electrical)
- `catalog/hardware.json` — purchased parts with sources; `catalog/prices.json` — dated prices
- `projects/<id>/` — the designs; `evals/<id>/` — briefs and graders
- `PLAN.md`, `STATUS.md` — what is done and the running log
