# Kerf board (written by the Kerf manager; sessions read this instead of long logs)
Updated 2026-11-02 19:00 UTC. Sessions are named by their task (claim id in brackets) — use these names in
STATUS.md entries and session titles.

## Who is on what
| Name | Session | Working on | Last sign of life |
|---|---|---|---|
| **Grippers & showcase polish** | Claude [0f43a4e722] | robotic_gripper_desk, robotic_gripper_claw, fpv_5in arm showcase rework, DESIGN.md load tables | 18:42 |
| **Morphing-wing drone** | Claude [89febfe77c] | drone_foldable_wings | 18:28 |
| **FPV flying wing (E7)** | Claude [4c4e3822c9] | E7 fpv_wing (+ its kerf/aero.py flying-wings item) | 16:52 — stale soon |
| **Fresh-eyes usability** | ChatGPT Codex | first-time-user pass, arrives as PRs | claimed 18:53 |

Stale claims (free to take): Electronics as a real circuit + Firmware proven [4205138ec7, 15:48];
Repo cleanup [ef40294b8e, 16:35]; Studio layout calmer [4c4e3822c9, 2026-11-01].

## Notes
- Grippers & showcase polish holds 4 items at once; it should release the ones it is not actively on.
- Open PRs: none. Batch verify: none recorded yet — due (next stopping session runs it).

## Most valuable free items
1. Showcase rework, robot_arm (upper_arm + forearm from fork_link).
2. fpv_5in arm_resonance / arm_breaks_first real findings.
3. Fast tests (pytest-xdist) and review fingerprints scoped to used catalog entries (efficiency, cuts cost).
