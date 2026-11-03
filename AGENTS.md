# Kerf Forge: instructions for ChatGPT Codex (and any non-Claude agent)

Codex reads this file automatically. **CLAUDE.md is the rulebook for every agent here, Codex included**: read its
"Non-negotiables", "Batched testing", "Parallel sessions", "Commands", "Paused work" and the project workflow. This file
only says how those rules translate for Codex and what changes while Claude is offline.

## What Codex doesn't have, and what to do instead

| Claude has | Codex does instead |
|---|---|
| Stop hook that blocks quitting with work unfinished | Enforce it yourself: before you end, the item's tests pass, its claim is beat/released, everything is pushed (PR or main as below). |
| Subagents (`.claude/agents/part-designer.md`, `design-researcher.md`) | Read the agent file and do that role yourself, one part at a time. |
| `design-reviewer` subagent (only it writes `review.json`) | **Never write or edit `review.json`.** When a project reaches `kerf build` PASS, add a sub-line under its PLAN item: `- [ ] design-reviewer pass (waiting for Claude; build PASS at <sha>)`, leave the main box unchecked, release the claim. |
| Skills (`.claude/skills/kerf/SKILL.md`, `ponytail/`, `teardown/`) | Open the SKILL.md as a normal file and follow it. The kerf skill is the design workflow. |
| Claude in Chrome / Meshy / Higgsfield MCP tools | Skip items that need them; note it in STATUS.md. |

Identity: claims record Codex automatically from `CODEX_THREAD_ID`. If it is missing, `export CODEX_THREAD_ID=codex-<short-task-name>`
before `tools/claims.py` so the claim shows as Codex, not Claude.

## Start of every Codex task (fast path)

1. `git pull --rebase`. Run `./setup.sh` only if `.venv/bin/kerf doctor` fails.
2. Read `docs/status/BOARD.md`, the last ~5 STATUS.md entries, `grep -n '^- \[ \]' PLAN.md`, `git log --oneline -15`,
   `.venv/bin/python tools/claims.py list`, `tools/budget.py status`, `tools/batch_verify.py status`.
3. Claim before working: `.venv/bin/python tools/claims.py take "<item start>"` (or `next`). `beat "<what you're doing>"`
   before each commit. A claim with no heartbeat for 90 min is stale and may be taken over (that is how you continue
   Claude's unfinished work: read its STATUS entry, DESIGN.md and WIP commits first, keep its files, finish them).
4. Per change run only the tests for files you touched plus `kerf check <p>` for projects you touched. Never the full
   suite per change; the batch run (`tools/batch_verify.py run`) is the only full run, and only when status says it's due
   and not HELD/RUNNING.
   For checkout/import preflight and exact-head receipts, see [Focused testing](docs/status/FOCUSED_TESTING.md).

## CLAUDE OFFLINE MODE (on from 2026-11-02 ~20:15 ET until Claude's usage resets and a Claude session says so here)

Spencer, 2026-11-02: Claude is out of usage; Codex takes over development and continues where Claude left off.
While this section is present:

- **Code still goes in PRs** (one item per PR, tests included, PLAN box + short STATUS.md entry in the PR). Claims stay
  pushed straight to main as before.
- **One Codex task is the manager** (prompt: `docs/status/CODEX_TAKEOVER.md`, "Manager"). It replaces the Claude "Kerf
  manager": it reviews and merges other tasks' ready PRs using `docs/status/MANAGER_PROMPT.md` step 4 rules (reject if it
  loosens a test/check/threshold/catalog value, edits review.json, rewrites a shared file, commits > 1 MB binaries, or
  strays outside its claim; otherwise run the changed files' tests + `kerf check` for changed projects, merge if green).
  **A task never merges a PR it wrote itself.** Squash-merge, no force-push, no reverts; on conflict, the manager
  rebases the branch itself (keep both sides' intent) or asks the PR's task to.
- Worker tasks pick from the priority list in `docs/status/CODEX_TAKEOVER.md`.
- Keep usage-heavy steps (full builds of every project, full pytest) to the batch run only.

**Ending it (for the first Claude session back):** delete this section, set CLAUDE.md's manager role back, and add a
STATUS.md entry listing what Codex merged (`git log --merges --since=2026-11-02`).

## Resource review

- Assembly demonstrations (2026-11-02): reviewed; keep the existing viewer and catalog-backed interface coordinates. Procedural tool illustrations preserve exact alignment and replay without adding an asset pipeline. Revisit only if the guide needs tool shapes or hand motions that the current viewer cannot explain clearly. No external resource lookup or installation was needed.

- Strength runtime (2026-11-02): reviewed; improve the existing pause/report freshness path and keep gmsh + scikit-fem. The current solver already has analytical validation and bounded-memory safeguards; the concrete gap is saved paused evidence surviving activation. No migration or additional tool is justified. Revisit only for a reproduced solver accuracy or capacity failure after this activation fix.
