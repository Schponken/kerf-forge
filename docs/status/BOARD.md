# Kerf board (written by the Kerf manager; sessions read this instead of long logs)
Updated 2026-11-02 21:55 UTC. Sessions are named by their task (claim id in brackets).

## Who is on what
| Name | Who | Working on |
|---|---|---|
| **Morphing-wing drone** | Claude [89febfe77c] | drone_foldable_wings |
| **FPV flying wing (E7)** | Claude [4c4e3822c9] | fpv_wing follow-ups just finished (review round 7 PASS); no open claim |
| **Scenario intake** | Codex [codex-scenario-intake] | scenario-only brief → questions → 2-3 options |
| **Mixed manufacturing** | Codex [codex-mixed-manufacturing] | laser-cut / CNC / carbon-plate parts as DXF / STEP |
| **Fast tests** | Codex [codex-fast-tests-refresh] | PR #4 refresh (pytest-xdist, markers) |

## Pull requests
- Merged this run: #5 catalog-edit fingerprints, #6 repo hygiene, #7 firmware proven, #9 Studio Work + Codex, #10 module library.
- Waiting on Codex: #3 (conflict in tools/mac/start.sh), #4 (conflict in tests/test_fea.py), #8 (move the
  "Resource review" note out of CLAUDE.md). Merge on the next manager run once updated.

## Known failure on main (fix first)
- tests/test_catalog.py::test_board_proxy_keeps_mounting_holes_clear FAILS on main (PCA9685 below-board pin height
  vs. mounting holes; predates today's merges). Needs a sourced catalog fix, not a loosened test. Free for a session.

## Batch verify
- ON HOLD (Spencer) until the other sessions finish; `tools/batch_verify.py status` shows HELD. No batch recorded yet.
- Usage budget switch: off (`tools/budget.py status`).

## Most valuable free items
1. The PCA9685 catalog test above.
2. Showcase rework, robot_arm (upper_arm + forearm from fork_link).
3. fpv_5in arm_resonance / arm_breaks_first real findings.
