# Diary: robotic_gripper_desk

11 problems recorded (8 open). Found at: before parts 0, rough 0, detail 0, final review 11.
Estimated active fix time 270 min; parts redrawn: none. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| f24b60f8 | 2026-11-01 | FAIL | 8 |
| a6e3413c | 2026-11-01 | FAIL | 8 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | major | jaw_r | final review | resolved | 90 |  | The claimed grip force ignores friction and tilt in the guide bores. In DESIGN.md 'Grip fo |
| 2 | minor | jaw_l | final review | open |  |  | Same STL as jaw_r, so the guide-bore finding above applies equally. Jaw deflection use is  |
| 3 | minor | gripper | final review | resolved | 90 |  | Margins of the swap on the real arm are thin and only hand-checked: gripper_mass passes at |
| 4 | minor | gripper | final review | open |  |  | 78 sharp inside corners remain (19 in a stressed zone, e.g. [52, 21, -24.7], [72, -17.6, 6 |
| 5 | minor | pinion | final review | open |  |  | The part docstring and DESIGN say the pinion prints flat on its horn (back) face, but prin |
| 6 | minor | rod_keeper | final review | open |  |  | A plain 3 mm bar: it has no locating feature, and the rods sit 0.86 mm below the cheek fac |
| 7 | minor | stand | final review | open |  |  | The stand is not free-standing with the gripper on it (head and payload about 110 mm ahead |
| 8 | minor | gripper | final review | resolved | 90 |  | There is no mechanical stop at the closed end: if the servo is driven past 0 deg the pads  |
| 9 | major | jaw_r | final review | open |  |  | The friction-corrected grip force in DESIGN.md 'Grip force' is still materially wrong, and |
| 10 | minor | gripper | final review | open |  |  | Mass-budget change (130 -> 166 g, torque_wrist 0.30 -> 0.25 of stall). Re-deriving both ca |
| 11 | minor | gripper | final review | open |  |  | The generated bring-up sketch maps joint degree 0 to 1500 us and allows 0..100 'deg' at 5. |
