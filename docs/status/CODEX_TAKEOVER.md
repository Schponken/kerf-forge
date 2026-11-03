# Codex takeover (Claude offline from 2026-11-02 ~20:15 ET / 01:15 UTC)

Snapshot of where Claude left off, the priority list, and the prompts to start Codex tasks. Rules: AGENTS.md + CLAUDE.md.

## State at handoff (main 7135982)
- **22 open Codex PRs, none merged since #11** (#3, #4, #8, #12-#30). The Claude manager can't run now; this backlog is
  job 1. Board (docs/status/BOARD.md, 22:05 UTC) says #3 conflicts in tools/mac/start.sh, #4 in tests/test_fea.py;
  #4 also fixes the known test_studio progress-order failure on main. #16 targets the known
  test_catalog board-proxy failure.
- **hawk_wing** (Claude session 89febfe77c, claim heartbeat 00:47 UTC -> stale at 02:17 UTC): research, catalog, DESIGN.md,
  project.yaml, layout.py done; wing, aileron, glove, tail (hstab, elevator, fin, rudder, tail_mount), pinion, skid
  designed. **Still `ctx.stub` placeholders: pod, hub, cap, fuselage, nose, hatch, motor_mount, boom_clamp.** Then wiring
  routes, `kerf check` PASS, `kerf build`, read the renders, leave design-reviewer for Claude (AGENTS.md).
- **portable_launcher_gets** (same Claude session): REFERENCES.md + catalog parts + `bungee_launch` requirement
  (kerf/req_launch.py) done; no DESIGN.md / project.yaml / parts yet.
- **drone_launching_system** (same Claude session): claimed, no project folder yet. It overlaps portable_launcher_gets
  (both are bungee V-slot rail launchers); build portable_launcher_gets first and make drone_launching_system a cradle /
  setting for drone_foldable_wings on it (check with Spencer before building a second rail).
- Other Claude claims: Studio layout + flying wings (session 4c4e3822c9, heartbeat ~01-02 22:48 UTC, stale).
- Paused by Spencer: all stress sims (PAUSED.json). Batch verify HELD. Budget switch OFF (leave it off: it blocks Codex too).

## Priority list for worker tasks
1. Manager: merge the PR backlog (oldest first, #4 and #16 early since they fix failures on main).
2. Known failures on main (BOARD.md "Known failures") if their PRs don't fix them.
3. hawk_wing: de-stub the 8 parts above, one part per commit, `kerf check hawk_wing --quick` after each.
4. portable_launcher_gets: DESIGN.md -> project.yaml contract -> parts (kerf skill workflow).
5. Learning Mode phases 1, 4-8 (PLAN "Learning Mode"; spec: https://claude.ai/artifact/XvvyTbvfankNwgmmjXCL8n, decisions there are final; phases 2-3 are done: kerf/diary.py, kerf/lessons.py). Spencer moved the start up: build now with Codex.
6. Free PLAN items not PAUSED and not needing Claude-only tools (`tools/claims.py next`).

## Prompts (one Codex task each, in the kerf-forge environment)

### Manager
You are the Kerf manager for Schponken/kerf-forge while Claude is offline. Read AGENTS.md ("Claude offline mode") and
docs/status/MANAGER_PROMPT.md, then do steps 2-6 of MANAGER_PROMPT.md with yourself as the reviewer: list open PRs
(`gh pr list`), oldest first; for each ready Codex PR you did not write, check it against the step-4 reject rules, rebase
it on main if it conflicts (keep both sides' intent), run only its changed tests + `kerf check` for changed projects,
squash-merge when green, otherwise comment why. Rewrite docs/status/BOARD.md, write MANAGER_LAST, push. Repeat until
no ready PR is left, then stop. Never merge a PR you authored; never force-push.

### hawk_wing
Continue Claude's hawk_wing project in Schponken/kerf-forge. Read AGENTS.md, CLAUDE.md, docs/status/CODEX_TAKEOVER.md,
projects/hawk_wing/DESIGN.md and its STATUS.md entry. After 02:17 UTC the Claude claim is stale: take it with
`tools/claims.py take "\`hawk_wing\`"`. Replace each remaining `ctx.stub` part (pod, hub, cap, fuselage, nose, hatch,
motor_mount, boom_clamp) with real geometry from layout.py and the interface table, following .claude/agents/part-designer.md
and docs/ENGINEERING.md; `kerf check hawk_wing --quick` after each; PR per 2-3 parts. Finish at `kerf build` PASS with
renders read; leave the design-reviewer line for Claude. No faked passes, catalog numbers only.

### Launcher
Build `portable_launcher_gets` in Schponken/kerf-forge. Read AGENTS.md, CLAUDE.md, docs/status/CODEX_TAKEOVER.md and
projects/portable_launcher_gets/REFERENCES.md. Take the claim once stale (after 02:17 UTC). Follow
.claude/skills/kerf/SKILL.md: DESIGN.md with sizing math (kerf/req_launch.py `bungee_launch`), project.yaml contract,
parts, `kerf check` to PASS, `kerf build`. PRs as you go; design-reviewer left for Claude.

### Worker (any number)
Work on Schponken/kerf-forge. Read AGENTS.md and docs/status/CODEX_TAKEOVER.md, then `tools/claims.py next` (skip
PAUSED and Claude-only items) and finish that item as one PR with tests. Release, then take the next.

## Automatic takeover in Studio (kerf/agent.py)
`kerf agent` shows the mode (auto default). In auto, Studio's new designs / quotes / edits / fixes run on Claude Code, and on
ChatGPT Codex (`codex exec --json --sandbox workspace-write`, network on) when Claude's usage is out; a Claude job cut off mid-way is
continued by Codex at once. `kerf agent codex` forces Codex. Needs the `codex` CLI on the Mac's PATH, signed in.
