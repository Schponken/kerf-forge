# E6 pan_tilt — blind run record

## Run 1 (2026-10-31, ~2.3 h, 231 tool calls)

**Setup.** A fresh general-purpose subagent got only the brief's request text, "use the `kerf` skill in this repo"
(path to SKILL.md), "read CLAUDE.md", the project name and the finish line (check + build PASS, renders looked at,
design-reviewer PASS, `review-status` ok). Operational rules only: the claim is held for it, commit/push every
~30 min, don't edit the engine/skill/evals/tests (record stumbles instead), never loosen a check.

**Result: PASS on its own.** `kerf check` and `kerf build` PASS; design-reviewer PASS (round 5, minors only);
`review-status` ok at fingerprint 1dc98e4ae7048aca.

- Base: holds the pan SG90 upright over a captive 1/4-20 nut (hex pocket on a 1.5 mm floor, so the tripod screw
  pulls the nut onto the floor). Yoke on the pan horn carries the tilt SG90 on one wall and an M3 × 12 screw pivot
  on the other. Bracket on both, Camera Module 3 lens on the tilt axis.
- Range pan ±90° (brief ±80°), tilt −35..+65° (brief −30..+60°), all sweeps and 4 corner poses clear.
- Tilt torque 0.02 kg·cm vs 0.9 allowed (50 % of 1.8 stall). Head 59.3 g. FEA (SF 3, PETG Z, 13 MPa allowable):
  bracket 2.2 MPa / 0.05 mm, yoke 2.6 MPa / 0.21 mm (limit 0.3), base 1.1 MPa. Head CG 13.5 mm off the pan axis.
- Electrics: 5 V adapter → barrel-jack terminal → both servos; Pi Zero 2 W drives the signals; 4 routed runs.

**Review rounds:** 1 FAIL (horn proxy had no spline engagement → catalog `spline_engage`); 2 PASS, invalidated by
another session's catalog edit; 3 FAIL (new ENGINEERING.md §10b electrics rule → added electrics); 4 PASS,
invalidated by the fingerprint scheme change; 5 PASS.

## Stumbles and what was done about each (run 1)

| # | Stumble | Fix |
|---|---|---|
| 1 | No subagent tool inside a subagent: the skill assumes researcher / part-designer / reviewer subagents | SKILL.md "No subagent tool?" paragraph: do research and parts yourself per `.claude/agents/*.md`, run the reviewer headless |
| 2-3 | Headless reviewer: no write permission; `--allowedTools` swallowed the prompt argument | SKILL.md gives the working command (comma list, prompt on stdin) |
| 4 | Repo Stop hook runs a full `kerf verify` inside each headless reviewer; two reviewer processes outlived the run | Documented "wait for it, never leave one running". **Open:** the hook itself was not changed (CLAUDE.md forbids editing it) — see Open items |
| 5 | `claims.py beat` dirtied the tree, so `pull --rebase` after a commit failed | `beat` now stages the claim file; CLAUDE.md says beat before `git commit` |
| 6 | `kerf new` writes `root: TODO`; the edit hook complains until stubs exist | SKILL.md says this is expected until step 2 |
| 7 | No tripod-thread interface; 1/4-20 pocket cut by hand | `iface.tripod_socket()` (captive catalog nut over a clearance hole, lead-in) + test; listed in the skill |
| 8 | Only an ESTIMATE micro horn; no proxy for stock plastic arm horns | **Open** (catalog/proxy work) |
| 9 | Camera board proxy's generic 90 % component block covered the mounting holes | Board proxy models the lens housing for camera boards (`lens_housing_square` at `lens_offset`) + test |
| 10 | No frustum keep-out; board proxy has only a `bottom` joint | `view_cone` proxy (FOV frustum from catalog hfov/vfov) and a `lens` joint on camera boards + test, in ARCHITECTURE.md |
| 11 | "BAD 0.8 (limit 0.8)": failure hidden by rounding | Check output now says "misses the limit by less than the shown rounding; add margin" + test |
| 12 | `export.bom()` crashed (`NoneType.__format__`) on a pin with no valid length | BOM writes "? (no stocked length fits…)"; the pin problem reports it + test |
| 13 | Screw-pivot length rule opaque; warning said "head clamps the moving part" | Problem lists each hole's length and needed cover and the span rule; warning names the clamped stack + test |
| 14 | Exact-45° chamfers / teardrop roofs counted as overhang; `pin_hole(fit='tap')` silently dropped `teardrop`; `horn_mount` had none | 0.25° slack in `geom.overhang`; tap + heat-set holes take a teardrop, other kinds refuse it loudly; `horn_mount(teardrop=)`; tests. `load_axis` warning after a passing Z-direction FEA left as is (a warning, by design) |
| 15 | Whole-catalog fingerprint invalidated reviews on unrelated edits | Already fixed mid-run by another session (`catalog_deps.json`) |
| 16 | Rules/engine changed mid-run (§10b, screw heads, spline_engage) | Expected with parallel sessions; no fix |
| 17 | Duplicate `connectors` key in hardware.json silently dropped a section | `catalog.load()` refuses duplicate keys + test |
| 18 | Param expressions in wire-route waypoints mis-evaluated | Route points (`{item, at}` and plain lists) evaluate expressions + test |
| 19 | SG90 proxy lacks the gear boss and lead exit; thin tap walls fail | **Open** (catalog data needed with sources) |
| 20 | `assembly.order` can't express "servo in last onto a placed horn"; horn centre screws unchecked for key access | **Open** |
| 21 | Off-device electrics shrank the head in every render | Item `render: false` keeps it out of the views (still in checks/STEP/BOM) + test, documented in ARCHITECTURE.md |
| 22 | `kerf build` up to 604 s under load; one Chromium render crash | **Open** (load from parallel sessions) |
| 23-25 | Shared catalog edits ripple; conflict markers left in STATUS.md by another session | Process; no engine fix |

## Run 1 open items, closed before run 2 (2026-10-31, session dafdd49d)
- #8 stock SG90 arm horns: `servo_horns.sg90_arm_1/2/4` measured from the FreeCAD-library STEPs; the horn proxy
  draws arms, `iface.horn_holes`, `horn_mount(use=, start_deg=)`; test against the CAD volume.
- #19 SG90 gear boss (`gear_boss_*`, `aux_boss_*`, same CAD source) and lead exit (`cable_boss_*` keep-out on the
  output end, newscrewdriver.com; `cable_boss_flex`: loose wire counts for interference, not for tool reach).
  `servo_mount` clears the lead zone and refuses a drop-in plate whose end-tab hole would break into it. This found a
  real defect in the run-1 pan_tilt: its base screwed the output-end tab right over the lead; the base was reworked
  (servo hangs from a deck by its tab tops, lead out of the open side).
- #20 an `insert:` item's children installed in an earlier order step stay put and block it; horn centre screws
  are key-reach checked when the horn goes on. Tests for each.
- Still open: #4 (the repo Stop hook runs `kerf verify` inside a headless reviewer session; CLAUDE.md forbids editing
  the hook, so it needs Spencer's OK) and #22 (build time under parallel load).

## Run 2 (2026-10-31 10:18-11:07 UTC, ~50 min, ~75 tool calls)

**Setup.** As run 1: a fresh general-purpose subagent got the brief (request + grading contract), "read CLAUDE.md
and use the `kerf` skill (.claude/skills/kerf/SKILL.md)", project name `pan_tilt_b2`, the finish line (check + build
PASS, renders read, headless design-reviewer PASS, `review-status` ok, eval acceptance clean). Rules: no access to
projects/pan_tilt or this file, no git writes, no engine/skill/test edits (record stumbles instead), catalog additions
only with an opened source, never loosen a check. The scratch project was not committed (it duplicates pan_tilt).

**Result: PASS on its own, first review round.** check + build PASS (fingerprint 0576ddf6aa3c47f6), design-reviewer
round 1 PASS (8 minors, no major/blocker), `review-status` ok, acceptance `[]`.
- Design: 5 PETG parts. Base with `iface.tripod_socket` (captive catalog 1/4-20 nut on a 2 mm floor); a 5 mm deck
  that the pan SG90 hangs under, screwed from below (it chose top-through itself after `servo_mount`'s new
  lead-exit error), deck screwed to heat-set inserts in the base rim; yoke on the stock SG90 2-arm horn
  (`sg90_arm_2`, new this pass), tilt SG90 inside upright A, a 4 x 4 shoulder-screw pivot in an M3 insert in upright
  B; a cradle wrapping the yoke with the lens on the tilt axis, plus a bolted cheek for the pivot.
- Numbers: pan -90..+90, tilt -35..+65, all sweeps + 4 corner poses clear; 22 screws aligned; torque_tilt 0.04 of
  0.9 kg cm; 93.3 g on the tripod (limit 110); FEA yoke 2.16 / 13 MPa (stall + 5 N, across layers, SF 3), cradle
  3.1 / 24 (0.33 mm), cheek_b 1.75, deck 2.24, base 0.23; power_budget 0.12 (5 V 6 A adapter, Pi 4 PWM).
- Compared with run 1: 50 min vs 2.3 h, 75 vs 231 tool calls, 1 review round vs 5, 6 stumbles vs 25, none of them a
  design-blocking engine gap.

### Run 2 stumbles and fixes
| # | Stumble | Fix |
|---|---|---|
| 1 | `kerf new` crashed (UnboundLocalError: `main()` rebound the name `new` in a later loop) | renamed the loop variables in kerf/cli.py + test that runs `kerf new` through `main()` |
| 2 | A requirement that could not be evaluated printed "BAD None (limit None) - misses the limit by less than the shown rounding" | `req_line` says "not evaluated - the reason is in the PROBLEM lines" + test |
| 3 | The catalog camera's product-brief PDF could not be fetched (permission timeout) | none (web access); it used another vendor page |
| 4 | `tripod_socket` cut the nut pocket but the nut never reached the BOM | `tripod_socket(ctx, loc, ...)` registers the nut via the new `ctx.bom_item` (rows land in bom.md per part copy); passing a Location first raises a clear TypeError; test |
| 5 | A part file importing a sibling part (`from deck import X`) failed with a bare ModuleNotFoundError | diagnose hint: "part files can't import each other; put shared values in the layout module" + test (parts stay isolated on purpose: a shared sys.path would leak modules between projects in one verify run) |
| 6 | The headless reviewer takes ~10 min = the Bash foreground cap; the waiting call was killed | SKILL.md: start it with nohup, poll with pgrep until it exits, never finish while it or its `kerf verify` runs |

No re-run needed for these: none changed what a designer has to do, only error text, the BOM and one CLI crash, each
covered by a test.
