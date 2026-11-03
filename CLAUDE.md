# Kerf Forge — instructions for Claude Code

Kerf Forge turns a plain-language description ("a 4-axis desk robot arm that lifts 150 g") into a complete,
engineered, printable multi-part assembly: every printed part, the purchased parts it uses, how they fasten and move,
proof that it fits and works, and files ready for a Bambu Lab A2L. The owner is Spencer. He wants finished, verified
work, never a roadmap and never "should work".

## Non-negotiables

1. **Never stop with work unfinished.** Your item is done when its tests and checks pass, its PLAN box is checked,
   its claim is released, and everything is committed and pushed. A Stop hook enforces this (and runs a batched full
   test run when one is due). If it blocks you, read the reason and keep working. Do not argue with it, weaken it, or edit it.
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
2. Read STATUS.md (recent entries only; older ones are archived in docs/status/), the OPEN PLAN items only
   (`grep -n '^- \[ \]' PLAN.md`), then `git log --oneline -15`. Open docs/ARCHITECTURE.md / ENGINEERING.md only at
   the section your item needs (grep it), never whole. Helpers: part-designer and design-researcher run on Sonnet
   (cheaper); the design-reviewer, the quality gate, keeps the main model.
3. Several sessions may work on this repo at once. Claim your work before starting it:
   `.venv/bin/python tools/claims.py next` claims the first open PLAN item nobody is working on (or `take "<item text>"`
   for a specific one) and pushes the claim. Work only on what you claimed. See "Parallel sessions" below.
4. Run `.venv/bin/python tools/batch_verify.py status`. If the last batch FAILED, fixing it is your first job.

## Batched testing (Spencer, 2026-11-02)

Full `kerf verify` runs are expensive, so they are batched: one run covers many sessions' features.
- **Check before you start any test run** (Spencer, 2026-11-02): `tools/batch_verify.py status` says "RUNNING NOW"
  while any session holds the full-suite lock (claims/batch-verify.json, all machines): never start a second full
  run, wait for its result. For targeted runs, `ps aux | grep [p]ytest` first: don't start the same files twice.
- **Per change:** run only what the change touches: the test files for the code you changed (`.venv/bin/pytest -q
  tests/test_<x>.py ...`), new tests for your feature, and `kerf check <project>` / `kerf build <project>` for projects
  you changed. Never the full suite for a single change.
- **Per batch:** `tools/batch_verify.py run` runs the full suite (pytest without stopping at the first failure, every
  project, reviews, evals) once 4+ PLAN items have been checked off since the last batch, or untested work is 24 h old.
  It records verify/BATCH.json with the batch's commits as suspects. The Stop hook tells you when one is due.
- **A failed batch blocks new work:** fix each failure at its cause (never by loosening a check), push, then
  `tools/batch_verify.py run --force` to confirm.
- `kerf verify` still defines a finished repo; batching changes when it runs, not what it checks.

## Parallel sessions

Other Claude sessions may be working in this repo at the same time. To never break, undo or duplicate their work:
- **ChatGPT Codex works here too** (Spencer, 2026-11-02): it claims PLAN items with `tools/claims.py` like any
  session (claims are pushed straight to main), delivers code as pull requests, and never merges its own PRs; the
  "Kerf manager" scheduled session reviews and merges them. Treat a Codex claim exactly like a Claude claim.
  While AGENTS.md has a "CLAUDE OFFLINE MODE" section, a Codex manager task merges instead (see AGENTS.md); the
  first Claude session back ends that mode as AGENTS.md describes.
- **Claim before you work** (`tools/claims.py next` / `take`); `tools/claims.py list` shows who holds what. A claim is
  stale after 90 minutes without a heartbeat and may then be taken over.
- **Pull before you push, never force:** `git pull --rebase` then `git push`. Never `push --force`, `reset --hard` to
  origin, revert or rewrite someone else's commit, or delete files you didn't create in this session. If a rebase
  conflicts, keep both sides' intent and re-run the checks.
- **Stay in your lane:** edit the files your item needs. Shared files (kerf/*.py, PLAN.md, STATUS.md, CLAUDE.md, docs/)
  get small, targeted edits — never rewrites — so concurrent changes merge cleanly. New engine features go in new
  functions or new modules where possible. STATUS.md: append your own dated entry; don't edit others' entries.
- **Heartbeat:** run `tools/claims.py beat` before each commit (it stages the claim file, so run it before `git commit`, not after) so your claim stays fresh.
  Add a short activity sentence, for example `tools/claims.py beat "Checking wing clearances; wiring checks next"`,
  so Studio's Work page can explain current work. Codex's thread id and Claude's explicit runtime identity are
  recorded automatically when present. Keep remaining work as real PLAN checkboxes; never invent completion
  percentages or time estimates for a claim.
- **Finishing an item:** check it off in PLAN.md, `tools/claims.py release`, push, then `tools/claims.py next`.
  When every open item is claimed by other active sessions and your work is pushed, the Stop hook lets you stop.

## Commands (always use the venv: `.venv/bin/kerf`, `.venv/bin/python`, `.venv/bin/pytest`)

| Command | What it does |
|---|---|
| `kerf check <p>` | build all parts + every check incl. motion sweeps; prints PASS/FAIL with problems |
| `kerf check <p> --quick` | same without motion sweeps (fast inner loop) |
| `kerf req <p> [id ...]` | just the named requirements (ids or check names) on the assembled project: one number after an edit (a mass, a margin, one FEA) in seconds; `kerf check` still decides PASS |
| `kerf build <p>` | check + STEP, per-part STL/3MF, A2L plates, BOM, renders → `projects/<p>/out/` |
| `kerf verify [--fast]` | definition of done: pytest, all projects, all reviews current, all evals, PLAN.md complete |
| `kerf review-status <p>` | whether the visual review matches the current geometry fingerprint |
| `kerf doctor` | environment self-test |
| `kerf status` | one-screen overview: PLAN progress, each project's build/review/eval state |

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
  writing new code; no speculative abstractions; but never cut validation, checks, engineering margins, or the
  detail features docs/ENGINEERING.md requires (those count as asked for). Vendored Ponytail 5.3.3 (DietrichGebert/ponytail
  @96608e0, MIT); subagents don't load skills on their own, so part-designer.md tells them to read it.
- Keep the engine general. A fix that only makes one project pass is wrong if the same problem would hit the next project.
- Every new engine feature gets a test in `tests/`.
- Plain-language explanations in user-facing text; Spencer is technical but not a mechanical engineer by training.

## Vision and budget

- The target is docs/VISION.md (selectable modes, use-story design, scenario-to-solution, wider reach). PLAN.md
  "Kerf vision" lists the steps; claim them like any other item. **Ship it is opt-in only**: never a default, never
  started without the user's explicit choice.
- Budget: Spencer caps Claude usage at **60 % of the weekly limit**. Sessions cannot read the meter, so keep each
  session's work tight (no repeated full builds when a quick check or one requirement shows the answer), push
  often, and stop starting new items when Spencer says the cap is near. The switch is `tools/budget.py stop "<why>"
  [--until "YYYY-MM-DD HH:MM"]` (UTC, shared via git; `resume` clears it; a local `.claude/state/BUDGET_STOP` works
  too). While it is on, `claims.py next/take` refuse and the full batch run waits: finish and push the current item,
  release, then stop (the Stop hook does not honour it yet - that hook edit needs Spencer's go-ahead).
- Don't start what a limit would cut off: before a long step (a full build, a design-reviewer round, a batch run)
  check `tools/budget.py status`; commit + push before it so nothing is lost. `kerf verify` resumes a cut-off run
  on the same commit from its checkpoint, and the batch run waits until other sessions are done (Spencer, 2026-11-02).

## Paused work

- **Stress simulations are paused** (Spencer, 2026-11-02, "we will work on that later"): `PAUSED.json` at the repo
  root turns off every FEA-backed check (fea_static, impact_fea, stop_impact, natural_freq, drop_impact, weak_link);
  they report PAUSED / NOT RUN and the report warns that strength is unproven. Don't run them (`KERF_STRESS=1`), don't
  claim `PAUSED:` PLAN items, and don't call a part strong because a paused check shows no failure. Delete the key to resume.

## Escape hatch (rare)

Only if progress needs something outside this repo that you cannot get (credentials, a paid service, a website that is
blocked), write `.claude/state/BLOCKED` with the exact blocker and what you tried, commit, push, and work on every other
item first. The Stop hook only lets you stop on BLOCKED after everything else in PLAN.md is done.
