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

## Stumbles and what was done about each

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

## Open items for a later pass
- Stop hook inside headless subagent sessions (#4): it should recognise a non-interactive reviewer session and not
  run `kerf verify` there. Needs Spencer's OK to touch the hook.
- Arm-horn proxy (#8), SG90 gear boss + lead exit (#19), order-insert semantics (#20).
