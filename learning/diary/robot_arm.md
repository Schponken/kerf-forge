# Diary: robot_arm

54 problems recorded (0 open). Found at: before parts 0, rough 0, detail 0, final review 54.
Estimated active fix time 2260 min; parts redrawn: base, cable_mast, forearm, gripper, layout, psu_hood, turntable, upper_arm, yaw_gear, yoke_l, yoke_r. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| 718d8fc3 | 2026-10-31 | FAIL | 12 |
| 6de8d59e | 2026-10-31 | FAIL | 7 |
| c8134eee | 2026-10-31 | FAIL | 8 |
| 7b72d266 | 2026-10-31 | FAIL | 6 |
| 1eb5887e | 2026-10-31 | PASS | 6 |
| bb3def5f | 2026-10-31 | FAIL | 9 |
| 7c4e94ff | 2026-10-31 | FAIL | 9 |
| 27c2c507 | 2026-10-31 | FAIL | 10 |
| 9fb5968d | 2026-10-31 | PASS | 7 |
| 123d4b1e | 2026-10-31 | FAIL | 10 |
| 44505ff4 | 2026-10-31 | PASS | 9 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | major | base | final review | resolved | 35 | 5: forearm, layout, upper_arm... | The bore between the two 6001 seats is only 14 mm (bearing_seat through= with the default  |
| 2 | major | turntable | final review | resolved | 35 | 5: forearm, layout, upper_arm... | There is no cable path (docs/ENGINEERING.md section 10: 'Cable path from base to wrist tha |
| 3 | major | turntable | final review | resolved | 35 | 5: forearm, layout, upper_arm... | turntable_fea does not test the real load. (1) The torque_nmm loads sit on the yoke foot s |
| 4 | minor | yoke_r | final review | resolved | 35 | 5: forearm, layout, upper_arm... | Same torque-on-offset-sites effect: yoke_r_fea reports applied_force_n z = +21.3 N, but th |
| 5 | minor | upper_arm | final review | resolved | 35 | 5: forearm, layout, upper_arm... | upper_arm_fea fixes BOTH plates rigidly at the shoulder. In reality plate B is pinned on t |
| 6 | minor | upper_arm | final review | resolved | 35 | 5: forearm, layout, upper_arm... | All servo tab screws are thread-formed into PETG (kind='tap'). They carry the joint torque |
| 7 | minor | gripper | final review | resolved | 35 | 5: forearm, layout, upper_arm... | The grip is a single swinging finger against a fixed jaw. At 55 deg open, the gap measured |
| 8 | minor | gripper | final review | resolved | 35 | 5: forearm, layout, upper_arm... | The fixed-jaw post stands along gripper +Y, which is print Z when printed with print_rot [ |
| 9 | minor | yoke_l | final review | resolved | 35 | 5: forearm, layout, upper_arm... | Inside corners on load paths are sharp: cheek-to-foot on both yokes, web-to-plate on upper |
| 10 | minor | yoke_l | final review | resolved | 35 | 5: forearm, layout, upper_arm... | The three pivots are fully threaded M3x14 screws turning in 3.35 mm printed holes. The thr |
| 11 | minor | yaw_gear | final review | resolved | 66 | 6: forearm, layout, upper_arm... | The 0.3 mm backlash at the 18 mm pitch radius of the 24 T gear gives about 0.95 deg of fre |
| 12 | minor | upper_arm | final review | resolved | 35 | 5: forearm, layout, upper_arm... | Proportions: the forks nest inside each other, so the upper arm is 89.5 mm wide and the sh |
| 13 | blocker | yaw_gear | final review | resolved | 18 | 3: base, cable_mast, turntable | The yaw horn screws (yaw_horn group, 4 x M3x10, plain clearance holes) seat ON the yaw gea |
| 14 | major | base | final review | resolved | 18 | 3: base, cable_mast, turntable | The cable path (round-1 major) is only partly fixed. (1) The service-loop anchor (tie slot |
| 15 | minor | yoke_r | final review | resolved | 36 | 5: base, cable_mast, turntable... | yoke_r_fea: the hot spot in fea_yoke_r_fea.png is at the base of the cheek's inner face ne |
| 16 | minor | turntable | final review | resolved | 18 | 3: base, cable_mast, turntable | turntable_fea is now a sound load case (pure couples, held at the bearing lands, render ma |
| 17 | minor | gripper | final review | resolved | 82 | 8: base, cable_mast, forearm... | The fixed-jaw post still meets the palm at a sharp inside corner (part_gripper sheet). Rou |
| 18 | minor | base | final review | resolved | 18 | 3: base, cable_mast, turntable | Desk mounting order: the front M4 holes at (30, +/-40) sit under the upper-arm plates at h |
| 19 | minor | yoke_l | final review | resolved | 36 | 5: base, cable_mast, turntable... | The pivot-wear risk is accepted in DESIGN.md with a bearing-pressure estimate, which is fi |
| 20 | major | psu | final review | resolved | 105 | 1: psu_hood | The electrical system is not complete (ENGINEERING.md 10b: 'power connector, switch/fuse w |
| 21 | major | wiring | final review | resolved | 105 | 1: psu_hood | WIRING.md contradicts the BOM and gives unsafe terminations. (1) psu_arm/psu_yaw say 'sold |
| 22 | major | base | final review | resolved | 117 | 9: base, cable_mast, forearm... | DESIGN.md assembly step 0 (new this round) says to bolt or clamp the base to the desk firs |
| 23 | minor | cable_mast | final review | resolved | 117 | 9: base, cable_mast, forearm... | The mast is a 61 mm column 8 x 10 mm on a 28 x 10 x 5 mm foot, held by 2 M3 that both lie  |
| 24 | minor | base | final review | resolved | 117 | 9: base, cable_mast, forearm... | The cable post is a 126 mm upright cantilever (10 x 26 mm) printed with its layers across  |
| 25 | minor | nano | final review | resolved | 105 | 1: psu_hood | The Nano (bare board, pins down), the four WAGO splices and the 90 W supply are 'off the b |
| 26 | minor | yaw_gear | final review | resolved | 105 | 1: psu_hood | DESIGN.md is out of step with the geometry in places. Assembly step 2 says to bolt the yaw |
| 27 | minor | yoke_r | final review | resolved | 117 | 9: base, cable_mast, forearm... | Accepted, recorded for the record. yoke_r_fea volume peak is 15.0 MPa and gripper_fea is 1 |
| 28 | major | psu_hood | final review | resolved | 40 | 2: base, psu_hood | The hood blocks the supply's output adjustment. The MEAN WELL LRS-100 drawing (datasheet p |
| 29 | minor | psu_hood | final review | resolved | 40 | 2: base, psu_hood | (1) The -Y sleeve wall bears flat on the supply's datasheet side face over x 0-42. The dra |
| 30 | minor | wiring | final review | accepted at PASS |  |  | The IR-drop rows leave out resistances that are in the catalog or certain to be there. The |
| 31 | minor | cable_mast | final review | accepted at PASS |  |  | The docstring still says 'foot and column flush (10 mm) so it needs no support'. The foot  |
| 32 | minor | nano | final review | accepted at PASS |  |  | Carried over and accepted: the Nano, the 4 WAGO splices and the 5 inline fuse holders are  |
| 33 | minor | psu_hood | final review | resolved | 61 | 1: base | The SVR hole (d 8 at x 5.1, y 9.6) and the LED hole (d 3.5 at x 11.1, y 9.9) are 6.0 mm ap |
| 34 | minor | psu_hood | final review | resolved | 61 | 1: base | The assembly order (project.yaml assembly_note, ASSEMBLY step 26) says to slide the hood o |
| 35 | blocker | base | final review | resolved | 32 | 1: base | The yaw lead exit faces the guard ring with almost no gap. I measured the base STL in worl |
| 36 | minor | base | final review | resolved | 32 | 1: base | base.py hard-codes the cable boss protrusion as 6.6 mm (boss_x1 = xc + L/2 + 6.6 + 0.6). T |
| 37 | minor | wiring | final review | resolved | 32 | 1: base | The last two route points of pwr_yaw and sig_yaw are [-34.4, -12, 10] and then [-55.2, 0,  |
| 38 | minor | base | final review | resolved | 32 | 1: base | In the upright print, the shelf underside is the face the tab tops clamp against, and it i |
| 39 | minor | psu_hood | final review | accepted at PASS |  |  | Round-5 items verified. The pot hole is now 7 mm and the LED hole 2.5 mm (web 6.007 - 3.5  |
| 40 | minor | upper_arm | final review | accepted at PASS |  |  | For the record: at the new crash-case SF 3, upper_arm_stall_fea p99.9 is 13.42 MPa against |
| 41 | major | upper_arm | final review | resolved | 38 | 4: base, forearm, gripper... | The FEA load cases are no longer 2x the real static loads. After the ENG-6 perimeter-aware |
| 42 | minor | base | final review | resolved | 38 | 4: base, forearm, gripper... | Stale cut. The old yaw-lead hole through the gear guard ring is still there: base.py lines |
| 43 | minor | base | final review | resolved | 38 | 4: base, forearm, gripper... | The yaw lead bends hard at the grommet. The pocket's +X end wall is at x -27.4 (STL), only |
| 44 | minor | wiring | final review | accepted at PASS |  |  | Round-6 route item, only partly fixed. pwr_yaw and sig_yaw now pass base.yaw_boss (-30.4,  |
| 45 | major | base | final review | resolved | 29 |  | base_fea applies about 80 % of its stated tipping-moment load. Both the why text and DESIG |
| 46 | minor | turntable | final review | resolved | 29 |  | The tipping-moment arithmetic is slightly low, and its wording is wrong. The turntable_fea |
| 47 | minor | upper_arm | final review | resolved | 29 |  | The load 'why' texts leave out the servo body that hangs on each link's far end. The 'roun |
| 48 | minor | upper_arm | final review | resolved | 29 |  | Several holes print horizontally but are cut round without compensation (ENGINEERING.md s4 |
| 49 | minor | base | final review | resolved | 105 | 6: base, cable_mast, forearm... | DESIGN.md's Strength table gives base_fea deflection as 0.11 mm, but report.json has 0.129 |
| 50 | major | gripper | final review | resolved | 15 | 6: base, cable_mast, forearm... | In print orientation (print_rot [90,0,0], out/parts/gripper.stl) the lowest geometry is th |
| 51 | minor | upper_arm | final review | resolved | 15 | 6: base, cable_mast, forearm... | Not seen in round 9 (engine check added after it): the horn clearance holes (sh_horn on up |
| 52 | minor | base | final review | accepted at PASS |  |  | Not seen in round 9: the engine warns that base_fea's fixed boxes hold none of base's fast |
| 53 | minor | gripper | final review | accepted at PASS |  |  | DESIGN.md 'Use notes' tells the IK to reject poses whose tcp or wrist pivot is below z = 1 |
| 54 | minor | gripper | final review | accepted at PASS |  |  | 11.1 % of the surface still prints on support: the palm underside (11 mm above the bed bet |
