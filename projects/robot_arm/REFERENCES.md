# References — desk robot arm (E3)

The designs below were studied for the shared library (`references/INDEX.md`, rows marked robot_arm); this project
uses their lessons, not their geometry.

| Reference | License | Why |
|---|---|---|
| LeRobot SO-101 arm — https://github.com/TheRobotStudio/SO-ARM100 | Apache-2.0 | Link proportions (shoulder→elbow 116, elbow→wrist 135 mm) for a ~250 mm desk arm; real payload ~200 g with 16.5 kg·cm servos; the shoulder is the most-stressed joint. |
| EEZYbotARM MK2 — https://www.myminifactory.com/object/3d-print-46620 | not stated (reference only) | Hobby servos on a serial arm are "shaky" without side support; servo outputs need help carrying bending loads. |
| BCN3D Moveo — https://github.com/BCN3D/BCN3D-Moveo | MIT | Yaw carried on bearings, not on the motor shaft; heat-set inserts throughout. |
| Thor — https://github.com/AngelLM/Thor | CC BY-SA 4.0 | Dedicated yaw bearing parts; accuracy falls off toward the wrist. |
| HowToMechatronics DIY arm — https://howtomechatronics.com/projects/diy-arduino-robot-arm-with-smartphone-control/ | not stated | Cautionary: MG996R shoulder "at its limit" (needed a rubber band), no base bearing, 2 A supply too small. |
| Sovol FDM gear guide (via `kerf/drives.py`) | — | 0.2–0.4 mm total backlash, module ≥ 1.5 for a 0.4 mm nozzle (yaw gear pair). |
| Catalog entries `servos.DS3225/DS3218/MG996R`, `servo_horns.aluminum_25T`, `bearings.6001`, `fdm_holes.M3` | see catalog sources | Every purchased-part dimension and torque. |

## Decisions these support
- Torque sized from the catalog stall values with the arm stretched out: DS3225 (21 kg·cm) shoulder, DS3218 (19) elbow,
  MG996R (9.4) wrist — each asked for at most half of stall (SO-101 and HowToMechatronics lessons).
- Turntable on two 6001 bearings 25 mm apart on a 12 mm spindle; the yaw servo only turns it through a gear pair
  (Moveo/Thor lesson: the motor shaft never carries the arm's tipping moment).
- Every arm joint is a fork: servo on one side, an M3 screw pivot coaxial on the other (EEZYbot "shaky" lesson,
  docs/ENGINEERING.md section 8).

## Open questions (measure before the final print)
- DS3218/DS3225 tab hole diameter is scaled from a drawing and MG996R tab spacing is borrowed from the DS3218 drawing
  (catalog notes: UNVERIFIED). Print the yoke_r cheek first and test-fit a servo.
- Horn hub height spreads 4.5–5.5 mm between vendors (catalog note); a 5.5 mm horn moves each link 1 mm outward —
  the 0.5 mm fork gaps would close. Measure the horn you buy.
