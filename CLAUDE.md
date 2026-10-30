# Kerf Forge — instructions for Claude Code

Kerf Forge turns a plain-language description ("a 4-axis desk robot arm that lifts 150 g") into a complete,
engineered, printable multi-part assembly: every printed part, the purchased parts it uses, how they fasten and move,
proof that it fits and works, and files ready for a Bambu Lab A2L. The owner is Spencer. He wants finished, verified
work, never a roadmap and never "should work".

## Non-negotiables

1. **Never stop with work unfinished.** The job is done only when `.venv/bin/kerf verify` prints `VERIFY PASSED`,
   every box in PLAN.md is checked, and everything is committed and pushed. A Stop hook enforces this. If it blocks
   you, read the reason and keep working. Do not argue with it, weaken it, or edit it.
2. **Never fake a pass.** Do not loosen a check, threshold, eval acceptance file, catalog value, or test so that something
   passes. Do not write review.json yourself (only the design-reviewer subagent does). Do not mark a PLAN item done
   unless the thing works and is covered by a test or check. If a limit is genuinely wrong, fix it with a cited source
   and say so in STATUS.md.
3. **Real numbers only.** Every dimension of a purchased part comes from `catalog/hardware.json`, and every catalog
   entry has a `source` URL you opened. Need a new part? Research it, add it with its source, then use it. No guessed
   servo/motor/bearing sizes in part code.
4. **Engineering quality, not shapes.** Follow docs/ENGINEERING.md: load paths, safety factors, fits, fastener rules,
   print orientation vs. layer strength, wall thickness. A part that builds but would snap, not fit, or not print is a fail.
5. **Check your work every time.** After editing any part: `kerf check <project>`. Before calling a project finished:
   `kerf build <project>`, look at the renders yourself (Read the PNGs), then have the design-reviewer subagent review it.
6. **Save progress constantly.** Commit and push after every meaningful step (at least every ~30 minutes of work)
   with a clear message. Update STATUS.md (what's done, what's next, open problems) before each push. Another session
   may pick up from your last push at any time.

## Start of every session

1. `./setup.sh` (idempotent; ends with `kerf doctor` → must print `ALL OK`; fix anything it reports first).
2. Read STATUS.md and PLAN.md, then `git log --oneline -15`. Continue from the first unchecked PLAN item.
3. Run `.venv/bin/kerf verify --fast` to see the current state before changing anything.

## Commands (always use the venv: `.venv/bin/kerf`, `.venv/bin/python`, `.venv/bin/pytest`)

| Command | What it does |
|---|---|
| `kerf check <p>` | build all parts + every check incl. motion sweeps; prints PASS/FAIL with problems |
| `kerf check <p> --quick` | same without motion sweeps (fast inner loop) |
| `kerf build <p>` | check + STEP, per-part STL/3MF, A2L plates, BOM, renders → `projects/<p>/out/` |
| `kerf verify [--fast]` | definition of done: pytest, all projects, all reviews current, all evals, PLAN.md complete |
| `kerf review-status <p>` | whether the visual review matches the current geometry fingerprint |
| `kerf doctor` | environment self-test |

## How a project is made (read docs/ARCHITECTURE.md for the full schema)

- `projects/<p>/project.yaml`: shared params, printed parts, purchased parts (catalog-backed proxies), keep-out volumes
  (prop discs, camera view, wire paths), the joint tree, allowed overlaps (with a reason), and engineering
  `requirements` (torque, thrust/weight, reach, strength, CG...).
- `projects/<p>/parts/<part>.py`: `def build(ctx)` returns `ctx.finish(shape)`, written with build123d.
- Mating features come from `kerf/iface.py` (bolt patterns, heat-set inserts, nut traps, bearing seats, servo mounts,
  horn mounts, motor mounts, stack mounts, pins). Both sides of a connection use the same interface call with the same
  group name, so they line up by construction and the fastener check can prove it.
- Purchased parts are modelled as proxies from the catalog (`kerf/proxies.py`) so collisions and masses are real.

## Workflow for a new design (this is also what the `kerf` skill does for Spencer)

0. **Research** with the design-researcher subagent: proven open designs, datasheets, vendor STEP models, rules of
   thumb → `projects/<p>/REFERENCES.md`. Design from evidence; don't invent what already exists and works.
1. **Plan** (write `projects/<p>/DESIGN.md` first): requirements with numbers, the architecture choice and why,
   purchased-part selection from the catalog with the sizing math (torque, thrust, reach), the part list, an interface
   table (which part meets which, how, which group name), the joint tree, and print orientation per part.
2. **Contract**: write project.yaml (params, items, joints, requirements) before any part geometry.
3. **Parts**: one part-designer subagent per independent part, in parallel, each given its contract from DESIGN.md.
4. **Integrate**: `kerf check`, fix collisions and alignment problems at the part that owns them, iterate to PASS.
5. **Strength + detail**: `fea_static` on every structural part with its real load case; then the detail pass
   (see the kerf skill) and re-check.
6. **Build + self-review**: `kerf build`, Read every render (assembly sheet, exploded, each pose, each part).
7. **Independent review**: run the design-reviewer subagent; fix every finding; re-review until PASS.
8. Commit, push, update STATUS.md.

## Style

- Ponytail rules apply (`.claude/skills/ponytail`): use what exists (build123d, bd_warehouse, py_gearworks) before
  writing new code; no speculative abstractions; but never cut validation, checks, or engineering margins.
- Keep the engine general. A fix that only makes one project pass is wrong if the same problem would hit the next project.
- Every new engine feature gets a test in `tests/`.
- Plain-language explanations in user-facing text; Spencer is technical but not a mechanical engineer by training.

## Escape hatch (rare)

Only if progress needs something outside this repo that you cannot get (credentials, a paid service, a website that is
blocked), write `.claude/state/BLOCKED` with the exact blocker and what you tried, commit, push, and work on every other
item first. The Stop hook only lets you stop on BLOCKED after everything else in PLAN.md is done.
