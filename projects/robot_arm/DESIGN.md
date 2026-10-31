# Desk robot arm (E3) — design

## Requirements (from evals/robot_arm/brief.md)
| Requirement | Number | Where it is proven |
|---|---|---|
| Joints | base_yaw ±90°, shoulder ±60°, elbow ±60°, wrist ±75°, grip 0–55° | joint tree + sweeps (all clear) |
| Reach | 230–300 mm, shoulder axis → tcp, arm stretched out | `reach` = 266 mm |
| Payload | 150 g at the tcp, arm stretched out horizontally, every servo ≤ 50 % of stall | `torque_*` |
| Gripper | two fingers, ≥ 40 mm opening | `grip_open` = 55.6 mm |
| Desk | bolts (4 × M4 / wood screws) or clamps (rear pad) to a desk | base holes |
| Strength | FEA on every structural part, SF per ENGINEERING.md §3 | `*_fea` |

Home pose (all joints 0) = arm stretched out horizontally along +X: the worst case for every gravity torque.

## Architecture
Options considered: (a) servos directly on each joint, cantilevered on the servo spline (HowToMechatronics — fails:
"servos at their limit", wobble); (b) parallel four-bar with servos in the base (EEZYbot — light, but the brief wants
4 independent axes and the four-bar limits wrist range); (c) **serial arm, servo per joint, every joint a fork**:
servo on one plate, coaxial M3 screw pivot on the other, so the servo output carries torque only
(ENGINEERING.md §8). Picked (c). The turntable runs on **two 6001 bearings 25 mm apart on a 12 mm printed spindle**
(Moveo/Thor lesson: the yaw motor never carries the tipping moment); the yaw servo drives it through a **36:24
module-1.5 gear pair** (`kerf.drives.spur_pair`, 0.3 mm backlash), which also turns the MG996R's standard ±60° into
±90° at the turntable.

Every servo is mounted **top-first from outside the fork** (`servo_mount(top_through=True)`): only the case top passes
the window, so the forks are ~9 mm narrower per joint than tabs-inside mounting and the MG996R cable boss never has to
pass a window.

## Purchased parts and sizing
Masses from the catalog and from the part geometry (report.json); torque = Σ m·g·r with the arm stretched out
(`static_torque` computes it from the assembled CGs):

| Joint | Servo (catalog) | Stall kg·cm | Worst need kg·cm | Use | Margin |
|---|---|---|---|---|---|
| shoulder | DS3225 | 21.0 @5 V | 7.80 | 37 % | ask ≤ 50 % ✓ |
| elbow | DS3218 | 19.0 @5 V | 4.30 | 23 % | ✓ |
| wrist | MG996R | 9.4 @4.8 V | 1.87 | 20 % | ✓ |
| grip | MG996R | 9.4 | grip force 18.4 N at the 50 mm finger tip | — | jaw and finger FEA at stall |
| base yaw | MG996R + 36:24 gears | 9.4 → 6.3 at the turntable | no gravity torque (vertical axis) | — | — |

Hand check (shoulder): payload 0.15 kg × 26.6 cm = 4.0 kg·cm; the rest of the arm ≈ 0.49 kg at ≈ 7.8 cm ≈ 3.8 kg·cm;
total ≈ 7.8 — matches the check.

Yaw bearings (2 × 6001, C0 ≈ 2.4 kN): tipping moment ≈ 0.64 kg × 9.81 × 0.10 m ≈ 0.63 N·m → ±25 N on each bearing
over the 25 mm spacing; negligible.

Servo travel: the wrist needs ±75° = 150°: drive the MG996R with 500–2500 µs pulses (catalog note: ~180° there,
~120° at 1000–2000 µs). Yaw ±90° needs only ±60° at the servo. Grip uses 0–55°.

Power: five standard servos stall at ~2.5 A each; use a 5–6 V supply rated ≥ 5 A (BOM), never a microcontroller pin.

## Part list
| Part | Job | Material | Print orientation | Approx. |
|---|---|---|---|---|
| base | desk plate, bearing tower, yaw-servo pocket | PETG 30 % | upright, supports under shelf/bore ceiling | 88 g |
| turntable | spindle, 24 T gear, platform | PETG 40 % | upside down (platform on bed) | 40 g |
| retainer | washer under the lower inner race | PETG 100 % | flat | 1 g |
| yaw_gear | 36 T gear on the yaw horn | PETG 50 % | flat | 15 g |
| yoke_r / yoke_l | shoulder cheeks (servo / pivot) | PETG 40 % | on the cheek's outer face | 19 / 21 g |
| upper_arm | fork L1 = 85 | PETG 30 % | on edge (print_rot [90,0,0]) | 48 g |
| forearm | fork L2 = 80 | PETG 30 % | on edge | 41 g |
| gripper | fork + palm + fixed jaw | PETG 30 % | on edge, supports under the jaw | 22 g |
| finger | moving finger | PETG 40 % | flat | 4 g |

## Interfaces
| A | B | Call | Group | Hardware |
|---|---|---|---|---|
| base | yaw servo | `servo_mount` (tap, top-in, slot for the cable boss) | yaw_servo | 4 × M3×8 thread-forming |
| yaw horn | yaw_gear | `horn_mount` | yaw_horn | 4 × M3×10 |
| base | 2 × 6001 | `bearing_seat` press (+0.05) | — | — |
| turntable | retainer | `bolt_pattern` heat-set / clearance | retainer | M3×8 + insert |
| turntable | yoke_r / yoke_l | `bolt_pattern` heat-set / clearance (teardrops) | yoke_r_foot / yoke_l_foot | 3 × M3×10 + inserts each |
| yoke_r | shoulder DS3225 | `servo_mount` top-through, tap | sh_servo | 4 × M3×8 |
| shoulder horn | upper_arm | `horn_mount` | sh_horn | 4 × M3×10 |
| yoke_l / upper_arm | shoulder pivot | `pin_hole` free / heat-set | sh_pivot | M3×12 + insert |
| upper_arm | elbow DS3218 | `servo_mount` top-through, tap | el_servo | 4 × M3×8 |
| elbow horn | forearm | `horn_mount` | el_horn | 4 × M3×10 |
| upper_arm / forearm | elbow pivot | `pin_hole` | el_pivot | M3×12 + insert |
| forearm | wrist MG996R | `servo_mount` top-through, tap | wr_servo | 4 × M3×8 |
| wrist horn | gripper | `horn_mount` | wr_horn | 4 × M3×10 |
| forearm / gripper | wrist pivot | `pin_hole` | wr_pivot | M3×12 + insert |
| gripper palm | grip MG996R | `servo_mount` top-through (from below), tap | gr_servo | 4 × M3×8 |
| grip horn | finger | `horn_mount` | gr_horn | 4 × M3×10 |

Fork widths are computed in `parts/layout.py` from the catalog: horn face = tab-top face − tab_t + case top + spline
+ horn hub; each fork leaves `side_gap` = 1.5 mm on the pivot side so a 5.5 mm-tall horn (catalog spread 4.5–5.5)
still fits — take up the play with M3 washers on the pivot screw.

## Joint tree
base → (2 × bearing, yaw servo → yaw_drive → horn → yaw_gear), base → **base_yaw** → turntable → (retainer, yoke_r →
shoulder servo → **shoulder** → horn → upper_arm → elbow servo → **elbow** → horn → forearm → wrist servo → **wrist** →
horn → gripper → grip servo → **grip** → horn → finger; yoke_l). `yaw_drive` follows `base_yaw` × −24/36 in the sweep
(coupled gears). tcp = rigid joint on the gripper between the jaws.

## Strength (FEA, report.json)
| Check | Load case | Result | Allowable |
|---|---|---|---|
| upper_arm_fea | 2 × (3.87 N + 4.29 kg·cm elbow torque) at the elbow, shoulder held | 2.6 MPa, 0.15 mm | 24 MPa (xy, SF 2), 0.85 mm |
| forearm_fea | 2 × (2.86 N + 1.87 kg·cm) at the wrist | 0.9 MPa, 0.05 mm | 24 MPa, 0.8 mm |
| yoke_r_fea | shoulder servo **stall** 21 kg·cm + 5.9 N | 4.2 MPa, 0.24 mm | 13 MPa (z, SF 3), 0.5 mm |
| yoke_l_fea | 5.9 N on the pivot | 0.7 MPa | 13 MPa |
| gripper_fea | grip **stall**: 18.4 N on the jaw tip | 4.4 MPa, 0.58 mm | 24 MPa, 1.0 mm |
| finger_fea | 18.4 N at the finger tip | 8.4 MPa, 0.77 mm | 24 MPa, 1.0 mm |
| turntable_fea | 2 × arm weight 12.8 N + 1.28 N·m tipping moment, spindle held | 2.7 MPa, 0.23 mm | 13 MPa (z), 0.3 mm |

The arm links are stiffness-limited, not strength-limited; the stresses are low because a fork of two 7 mm plates
34 mm tall is deep in bending.

## Assembly order
1. Press both 6001 bearings into the base tower (lower one from below, up to its shoulder; upper one from the top).
2. Drop the yaw servo into its pocket (cable boss through the slot), 4 × M3×8 thread-forming screws into the shelf.
   Center it (1500 µs), press the aluminium horn on and fit its centre screw; bolt the yaw gear on (4 × M3×10).
3. Melt the 3 + 3 yoke inserts and the spindle insert into the turntable. Slide the spindle down through both bearings,
   meshing the gears with the arm pointing +X at servo centre; fit the retainer + M3×8 from below.
4. Bolt the shoulder servo to yoke_r from outside (top through the window), screws from behind the tabs.
5. Melt the pivot inserts into the upper arm, forearm and gripper bosses. Bolt each horn to its link plate first
   (4 × M3×10 from inside the fork — an L-key or ball-end key reaches through the open fork; for the gripper, through
   the access holes in the forearm and gripper B plates).
6. Work outward: elbow servo into the upper arm, forearm horn onto it at centre, elbow pivot screw (+ washers to take up
   axial play, medium threadlocker, back off 1/8 turn); same for the wrist and the gripper/finger.
7. Bolt yoke_l and yoke_r to the platform with the upper arm between them (shoulder horn onto the spline at centre,
   pivot screw through yoke_l).
8. Bolt or clamp the base to the desk, near the desk edge if you want the full shoulder range (stretched out at
   shoulder −60° the gripper reaches below the desk top — limit that pose in software otherwise).

## Risks / measure first
- DS32xx tab holes (scaled from a drawing) and MG996R tab spacing (borrowed from the DS3218 drawing) are UNVERIFIED in
  the catalog: print yoke_r and test-fit a servo before printing everything.
- Horn hub height 4.5–5.5 mm by vendor: measured horn + washers on the pivots.
- The M3 pivots are screws turning in 3.35 mm printed holes (ENGINEERING.md: metal pin, allowed); a real shoulder
  screw (ISO 7379) would wear less — swap in if you have one.
- Gripper and forearm need some support material (jaw overhang, window bridges); bridges are ≤ 41 mm.
