# Desk robot arm (E3) — design

## Requirements (from evals/robot_arm/brief.md)
| Requirement | Number | Where it is proven |
|---|---|---|
| Joints | base_yaw ±90°, shoulder ±60°, elbow ±60°, wrist ±75°, grip 0–65° | joint tree + sweeps (all clear) |
| Reach | 230–300 mm, shoulder axis → tcp, arm stretched out | `reach` = 266 mm |
| Payload | 150 g at the tcp, arm stretched out horizontally, every servo ≤ 50 % of stall | `torque_*` |
| Gripper | two fingers, ≥ 40 mm opening | `grip_open` = 63.8 mm |
| Desk | bolts (4 × M4 / wood screws) or clamps (rear pad) to a desk | base holes |
| Strength | FEA on every structural part (base included), SF per ENGINEERING.md §3; link FEA also at servo stall | `*_fea`, `*_stall_fea` |
| Electrics | complete: mains inlet with switch + fuse, cord, supply, buses, per-servo fuses, leads, driver, Nano + USB cable | `power`, `mains_access`, `usb_access`, WIRING.md |

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

Yaw bearings (2 × 6001, C0 ≈ 2.4 kN): tipping moment ≈ 7.8 kg·cm about the shoulder + 0.45 kg × 2.5 cm ≈ 0.85 N·m
→ ±34 N on each bearing over the ~25 mm spacing; negligible.

Servo travel: the wrist needs ±75° = 150°: drive the MG996R with 500–2500 µs pulses (catalog note: ~180° there,
~120° at 1000–2000 µs). Yaw ±90° needs only ±60° at the servo. Grip uses 0–65° (round 2: at 55° a 40 mm object only fit at the finger tips).

Power: see 'Electrics' — five servos stalled together draw 13.0 A (catalog stall currents), so the supply is a
MEAN WELL LRS-100-5 (5 V, 18 A).

## Part list
| Part | Job | Material | Print orientation | Approx. |
|---|---|---|---|---|
| base | desk plate, bearing tower, yaw-servo pocket, cable post | PETG 30 % | upright, supports under shelf/bore ceiling | 130 g |
| turntable | spindle, 24 T gear, platform | PETG 40 % | upside down (platform on bed) | 37 g |
| retainer | washer under the lower inner race | PETG 100 % | flat | 1 g |
| yaw_gear | 36 T gear on the yaw horn | PETG 50 % | flat | 15 g |
| yoke_r / yoke_l | shoulder cheeks (servo / pivot) | PETG 40 % | on the cheek's outer face | 20 / 22 g |
| upper_arm | fork L1 = 85 | PETG 30 % | on edge (print_rot [90,0,0]); free pivot hole teardrop | 47 g |
| forearm | fork L2 = 80 | PETG 30 % | on edge; free pivot hole teardrop | 40 g |
| gripper | fork + palm + fixed jaw | PETG 30 % | on edge, supports under the jaw | 22 g |
| finger | moving finger | PETG 40 % | flat | 4 g |
| cable_mast | post on the platform the lead bundle is tied across (foot 34 × 26, 4 screws) | PETG 30 % | on its side, support under the column (it is centred on the wider foot) | 7 g |
| psu_hood | closes the supply's terminal end, carries the IEC inlet | PETG 30 % | standing on its end wall (inserts vertical) | 61 g |

Masses are report.json's (all within 10 %); the arm on its base is 693 g (`arm_mass`, limit 900).

## Interfaces
| A | B | Call | Group | Hardware |
|---|---|---|---|---|
| base | yaw servo | `servo_mount` (tap, top-in, slot for the cable boss) | yaw_servo | 4 × M3×8 thread-forming |
| yaw horn | yaw_gear | `horn_mount` counterbored (heads 0.3 mm under the gear face: the platform turns over them) | yaw_horn | 4 × M3×8 |
| base | 2 × 6001 | `bearing_seat` press (+0.05) | — | — |
| turntable | retainer | `bolt_pattern` heat-set / clearance | retainer | M3×8 + insert |
| turntable | yoke_r / yoke_l | `bolt_pattern` heat-set / clearance (teardrops); front screw 6.5 mm from the foot end | yoke_r_foot / yoke_l_foot | 3 × M3×10 + inserts each |
| yoke_r | shoulder DS3225 | `servo_mount` top-through, tap | sh_servo | 4 × M3×8 |
| shoulder horn | upper_arm | `horn_mount` | sh_horn | 4 × M3×10 |
| yoke_l / upper_arm | shoulder pivot | `pin_hole` free / heat-set | sh_pivot | M3×14 + insert |
| upper_arm | elbow DS3218 | `servo_mount` top-through, tap | el_servo | 4 × M3×8 |
| elbow horn | forearm | `horn_mount` | el_horn | 4 × M3×10 |
| upper_arm / forearm | elbow pivot | `pin_hole` | el_pivot | M3×14 + insert |
| forearm | wrist MG996R | `servo_mount` top-through, tap | wr_servo | 4 × M3×8 |
| wrist horn | gripper | `horn_mount` | wr_horn | 4 × M3×10 |
| forearm / gripper | wrist pivot | `pin_hole` | wr_pivot | M3×14 + insert |
| gripper palm | grip MG996R | `servo_mount` top-through (from below), tap | gr_servo | 4 × M3×8 |
| grip horn | finger | `horn_mount` | gr_horn | 4 × M3×8 |
| turntable | cable_mast | `bolt_pattern` heat-set / clearance | cable_mast | 4 × M3×10 + inserts |
| base post | PCA9685 board | `bolt_pattern` tap (4 bosses) + board proxy | driver | 4 × M2×5 thread-forming |
| psu (tapped case hole) | psu_hood | box proxy `sites` (catalog holes_side_m3, max 5 deep) / clearance | psu_side | 1 × M3×6 |
| psu_hood (bosses) | iec_inlet flange | `bolt_pattern` heat-set / `panel_module` flange | inlet | 2 × M3×8 + inserts |

Fork widths are computed in `parts/layout.py` from the catalog: horn face = tab-top face − tab_t + case top + spline
+ horn hub; each fork leaves `side_gap` = 1.5 mm on the pivot side so a 5.5 mm-tall horn (catalog spread 4.5–5.5)
still fits — take up the play with M3 washers on the pivot screw.

## Joint tree
base → (2 × bearing, yaw servo → yaw_drive → horn → yaw_gear), base → **base_yaw** → turntable → (retainer, yoke_r →
shoulder servo → **shoulder** → horn → upper_arm → elbow servo → **elbow** → horn → forearm → wrist servo → **wrist** →
horn → gripper → grip servo → **grip** → horn → finger; yoke_l). `yaw_drive` follows `base_yaw` × −24/36 in the sweep
(coupled gears). tcp = rigid joint on the gripper between the jaws.

## Strength (FEA, report.json)
| Check | Load case | Result (p99.9, deflection) | Allowable |
|---|---|---|---|
| upper_arm_fea | 2 × (3.87 N at the elbow servo tabs + 3.87 N at the elbow pivot) + 2 × 4.31 kg·cm elbow torque as a pure couple on the tab screws; plate A held at the 4 shoulder-horn screws, plate B only at its pivot bore, so plate B's share goes through the webs | 5.65 MPa (peak 7.9), 0.42 mm | 24 MPa (xy, SF 2), 0.85 mm |
| forearm_fea | same pattern at the wrist (2.86 N ×2 sites, 1.87 kg·cm ×2), held the same way at the elbow | 1.8 MPa (peak 3.0), 0.16 mm | 24 MPa, 0.8 mm |
| yoke_r_fea | shoulder servo **stall** 21 kg·cm (couple on the 4 tab screws) + 5.9 N down, feet bolted | 6.6 MPa (peak 17.7 at the cheek's base where the foot ends: a local corner value, under the 39 MPa z strength), 0.46 mm | 13 MPa (z, SF 3), 0.5 mm |
| yoke_l_fea | 5.9 N on the pivot | 0.8 MPa | 13 MPa |
| gripper_fea | grip **stall**: 18.4 N on the jaw tip, held at the servo tabs | 5.1 MPa (peak 14.6 at the jaw root's side corners, local: SF 2.7 on the 39 MPa across-layer strength), 0.30 mm | 13 MPa (z: the jaw post bends across layers, SF 3), 1.0 mm |
| finger_fea | 18.4 N at the finger tip | 8.4 MPa (peak 13.9), 0.77 mm | 24 MPa, 1.0 mm |
| base_fea | ±68 N bearing couple (2 × 0.85 N·m over the 25 mm seat spacing) + 34 N gear-mesh force on the upper seat, 12.8 N on the upper seat floor, yaw servo at stall (9.4 kg·cm couple + 34 N) on its tab screws; held at the 4 M4 holes | 1.2 MPa (peak 4.8), 0.12 mm | 13 MPa (z, SF 3), 0.3 mm |
| upper_arm_stall_fea | fault case (crash): elbow servo at **stall** 19 kg·cm + 2 × the static loads | 13.4 MPa (peak 18.8), 1.03 mm | 24 MPa (xy, SF 2); deflection not a criterion in a fault (2 mm cap) |
| forearm_stall_fea | wrist servo at **stall** 9.4 kg·cm + 2 × the static loads | 5.3 MPa (peak 8.6), 0.50 mm | 24 MPa |
| turntable_fea | 2 × arm weight 12.8 N on the yoke feet + 2 × 0.85 N·m tipping moment (net 1.70 N·m about Y in report.json: the couples are 920 N·mm each because the 12.8 N acts behind the axis); spindle held only on the two bearing lands + collar | 3.7 MPa (peak 10.1 at the step), 0.21 mm | 13 MPa (z, SF 3), 0.3 mm |

Applied resultants are checked in report.json (`applied_force_n`): torques are pure couples (engine fix in this
round: a torque on screw sites off the axis used to add a spurious net force).

Every load-path inside corner has a fillet: cheek-to-foot 2 mm and foot-end 4 mm on both yokes, web-to-plate 1.5 mm
on the upper arm and forearm, jaw post to palm 2 / 1.5 mm and a 4 mm wedge under the jaw root on the gripper (jaw 10 mm thick across
the grip load), 0.3 mm at the spindle step. Every printed part
declares `load_axis`; base and turntable load their towers/spindle across layers (warned), which is why their FEA
uses the z (across-layer) strength with SF 3.

The turntable FEA holds the collar face fixed (it can pull as well as push there, which the real collar can't); the
upper bearing land carries the moment either way. The retainer screw pre-load is not modelled: tighten the M3 under
the spindle only snug (about 0.3 N·m) — it only has to stop the stack lifting, and more puts the spindle's layers
in tension.

The arm links are stiffness-limited, not strength-limited; the stresses are low because a fork of two 7 mm plates
34 mm tall is deep in bending.

## Cables
The five servo leads form one bundle that crosses the yaw joint ABOVE the arm: from the desk, up behind the PCA9685
board on the base's cable post (132 mm tall, on the rear pad, outside the circle the turntable sweeps), across the
post top to the top of the **cable mast** (bolted to the platform just behind the yaw axis, same height), then down
the outside of each fork's plate A (tie-slot pairs on the upper arm and forearm), hopping each joint 24-30 mm above
its axis so it never crosses a plate end. Because the mast top is only 10 mm from the yaw axis, the free span between
the two posts changes only between 82 and 93 mm over ±90° of yaw, so the loop stays short and hangs well above the
platform. `cable_loop` (channel_clear, 5 mm bundle) proves that span is clear at 10 poses; every run's route is also
checked against every part at both ends of every joint's range (electrical route check).

The gear mesh is enclosed: the guard ring round the yaw gear plus two side walls past the turntable gear (2.9 mm
from its tips), the platform above. The yaw servo's own lead leaves the housing's front exit, runs back inside the
ring along the housing at floor level and out through a hole in the ring's −Y side, 40 mm below the gears.

## Electrics
| Item | Catalog | Job |
|---|---|---|
| iec_inlet | SCHURTER DD11.0121.1111: IEC C14 inlet + 2-pole switch + 2 × T3.15 A fuses (5 × 20 mm) | mains in, on/off, mains fuse; in the PSU hood's end wall |
| cord | Tripp Lite P006-006, C13 to NEMA 5-15P, 18 AWG, 10 A | wall plug |
| psu | MEAN WELL LRS-100-5, trimmed to 5.3 V (adjustable 4.5–5.5 V), 18 A | servo power, on the desk behind the base, its terminal end closed by the printed **psu_hood** |
| mains jumpers | 3 × 100 mm UL1015 18 AWG (600 V), 4.8 mm insulated FASTONs on the inlet tabs, WAGO 216-203 ferrules in the supply's L / N / FG screws | L, N and protective earth: the earth bonds the supply's metal case to the plug's earth pin |
| bus_arm / bus_yaw | 2 + 2 × WAGO 221-415 lever splices (32 A) | +5 V and GND buses: arm servos / yaw servo + driver GND reference |
| fuses | 5 × Littelfuse 257005 5 A ATO in FHAC0001ZXJ inline holders | one per servo, in its red wire right at the bus |
| leads | each servo's own 300 mm lead + a Pololu extension (300 mm shoulder/elbow/yaw, 600 mm wrist/grip) | no wire is cut from a reel for the servos |
| driver | Adafruit PCA9685 | servo pulses only: each lead's orange wire is crimped into a 1 × 3 housing on its channel's PWM pin; the board's V+ rail is not used (no published rating) |
| nano | Arduino Nano (A000005, mini-B), USB cable SparkFun CAB-11301 1.8 m | I2C master, powered from the PC; I2C to the PCA9685 with crimped 0.1 in housings |

Power budget (report.json `power`): all five servos stalled together = 13.0 A (each servo's highest published stall
current; running currents are not published, so stall is used for the average too: 8.2 A worst-case average). The
supply gives 18 A at 5 V (≈ 17 A at 5.3 V for its 90 W), 30 % above 13 A. Every fuse carries its servo's stall current
inside Littelfuse's 75 % derating (DS3225: 2.9 A vs 3.75 A) and is smaller than the 7 A rating of the 22 AWG lead it
protects: a shorted or pinched lead in the moving bundle blows its 5 A fuse (200 % → 0.15–5 s, Littelfuse ATO data)
instead of cooking the lead until the supply's 110–150 % overload trips. The 16 AWG supply-to-bus runs are inside the
supply's own overload limit (22 A chassis rating vs ≤ 27 A trip, for seconds) and never leave the desk.
Mains side: the LRS draws 1.9 A at 115 VAC; the T3.15 A fuses run at 60 % (≤ 75 %), the inlet (7 A UL), the cord
(10 A) and the 18 AWG jumpers are all above it (report rows `mains ...`). The supply output is trimmed to 5.3 V with
its SVR pot (set it with a meter before connecting the servos): at 5.0 V the long wrist/grip leads (900 mm) would
drop the stalled servos below their 4.8 V minimum. All servos are rated to 6.8 V or more.

The PSU hood (printed): a box over the supply's terminal end. The supply's case is 129 × 97 × 30 ± 1 mm (catalog);
the hood's side walls slide 42 mm over it and one M3 × 6 goes into the supply's tapped side hole (MEAN WELL: max
5 mm deep) so the hood cannot be pulled off. The top covers only the terminal block, so the rest of the case top
stays open for cooling. The inlet sits in the 3 mm end wall (SCHURTER panel range 2.5–8 mm) on two M3 heat-set
inserts in bosses (2.5 mm wall round each insert; flange screws ≤ 0.5 N·m). The DC wires leave through a teardrop
hole in the side and are tied to the floor through two slots right inside it, so a pull on them never reaches the
screw terminals. `mains_access` proves a C13 plug and its cord bend (50 mm) fit in front of the inlet.

Where things sit on the desk: the supply + hood 225 mm behind the yaw axis (the arm never reaches there), the WAGO
splices and fuse holders beside the base's rear pad, the Nano near them. Put the Nano in a small case or on a
non-conductive pad, not loose against the WAGO splices; screw the supply to the desk or a board through its base.

## Assembly order
1. Press both 6001 bearings into the base tower (lower one from below, up to its shoulder; upper one from the top).
2. Drop the yaw servo into its pocket (cable boss through the slot), 4 × M3 × 8 thread-forming screws into the shelf.
   Centre it (1500 µs), press the aluminium horn on and fit its centre screw; bolt the yaw gear on (4 × M3 × 8,
   counterbored: an M3 × 10 would reach the servo case under the horn).
3. Melt the turntable's 11 inserts (3 + 3 yoke feet, 4 cable mast, 1 spindle end) and the 3 pivot inserts (upper
   arm, forearm, gripper). Slide the spindle down through both bearings, meshing the gears with the arm pointing +X at
   servo centre; fit the retainer + M3 × 8 from below — the base is still loose, the bore is under it.
4. **Now bolt or clamp the base to the desk**: the front M4 holes at x = 30 are still reachable because the platform
   ends at x = 15 and the yokes are not on yet. Near the desk edge if you want the full shoulder range (see 'Use notes').
   Taking the turntable out later means unbolting the base first.
5. Bolt the cable mast to the platform (4 × M3).
6. Bolt the shoulder servo to yoke_r from outside (top through the window), then yoke_r to the platform (3 × M3).
7. Shoulder horn on the spline at centre, upper arm onto the horn (4 × M3 × 10 from inside the fork — an L-key or
   ball-end key reaches through the open fork).
8. Work outward: elbow servo into the upper arm, forearm horn at centre, forearm; wrist servo, gripper; grip servo,
   finger. Each pivot: M3 × 14 through the free hole into the insert, washers to take up the 1.5 mm side gap, a drop
   of medium threadlocker on the screw TIP only (it sits in the brass insert; keep it off the printed bores), then
   back off 1/8 turn so the joint turns freely.
9. yoke_l onto the platform with the upper arm's pivot in it (pivot screw through yoke_l).
10. PCA9685 onto the post bosses (4 × M2 thread-forming). Route and tie the leads as in 'Cables'.
11. Electrics, per out/WIRING.md: inserts into the hood's bosses; mains jumpers (FASTON on the inlet, ferrules into
    the supply's L / N / FG), inlet into the hood, hood over the supply (M3 × 6 side screw); DC pairs (ferrules) out
    through the exit and tied; WAGO buses; a fuse holder at the bus end of each servo's red wire; orange wires crimped
    into housings on the driver; I2C to the Nano. Check every + to − pair with a meter, set the supply to 5.3 V with no
    servos plugged in, then plug the servo leads in. Centre every servo (1500 µs) before fitting its horn.

## Use notes
- Desk limit (software): the shoulder axis is 100 mm above the desk and the arm reaches 266 mm, so on a desk top
  (not at an edge) the gripper hits the desk below about shoulder −22° with the arm stretched out (asin(100 / 266)),
  and a crash stalls the elbow/shoulder (the stall FEA cases cover that, the desk does not care). In the inverse
  kinematics reject any solution whose tool point or wrist pivot is below z = 15 mm (desk = 0, gripper jaws ~12 mm
  below the tcp line when the wrist is horizontal), or mount the base at the desk edge to use the full −60°.
- Grip: command the finger to just touch the object (the servo then holds with little current); commanding it past
  contact holds the MG996R at stall (≈2.5 A, heat). The fixed jaw/finger are FEA-checked at stall anyway.
- The tcp sits ~21 mm to the side of the yaw axis (fork stacking): include that offset in the inverse kinematics.
- Yaw gear backlash 0.3 mm ≈ 1° at the turntable ≈ ±2.5 mm at full reach (plus the servo's own deadband): that is the
  expected side-to-side positioning accuracy. The yaw gear's lower face turns 1.2 mm above the fixed tower top.
- Servo tab screws are thread-forming M3 into 2.6 mm PETG pilots (the normal way servos are mounted); for frequent
  servo swaps, drill the pilots to 4.0 mm and use M3 heat-set inserts (7 mm plates take them).

## Risks / measure first
- DS32xx tab holes (scaled from a drawing) are UNVERIFIED in the catalog; the MG996R hole pattern (49.5 × 10) is
  confirmed by 2 TowerPro drawings + 7 CAD models, its tab height is not: print yoke_r and test-fit a servo first.
- Horn hub height 4.5–5.5 mm by vendor: measured horn + washers on the pivots.
- The M3 pivots are screws turning in 3.35 mm printed holes (ENGINEERING.md: metal pin, allowed). Wear check: the
  pivot carries ≤ 6 N (2× static) over a 7 mm long hole → 6 / (3 × 7) ≈ 0.3 MPa bearing pressure, oscillating ±60°
  at low speed — a light duty, so the thread wears the hole slowly (expect some play after long use). DIN 912 M3 screws
  this short are fully threaded (thread length 18 mm), so there is no partly threaded M3 × 14 to buy; a little grease
  in the free hole helps, and an ISO 7379 shoulder screw would need the free holes opened to its shoulder diameter.
- Gripper and forearm need some support material (jaw overhang, window bridges); bridges are ≤ 41 mm.
