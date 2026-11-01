# fpv_wing: 1 m 6S FPV flying wing

A printed FPV flying wing in the class of MakerWorld's Darkwing-1 (published specs only, see REFERENCES.md):
1000 mm span, one pusher motor on 6S, elevons, thin-wall PLA wing segments on carbon spars, a PLA pod, TPU where it
lands. Every number below is either a param in project.yaml, a catalog value, or computed by the checks named.

## Requirements (eval E7 contract + our own targets)

| Requirement | Target | Check id |
|---|---|---|
| Span | 950-1050 mm | `span` (size_max) |
| All-up mass | <= 1400 g (aim ~1300) | `auw` |
| Static margin | 5-15 % MAC (aim 10 %) | `static_margin` |
| Wing loading | <= 75 g/dm² (RazorBlade 72.7) | `wing_loading` |
| Stall speed | <= 45 km/h (brief 55) | `stall_speed` |
| Spar strength | 6 g, SF 1.5 on the low strength figure | `spar_bending` |
| Thrust / weight | >= 1.5 | `twr` |
| Flight time | >= 12 min at 80 km/h cruise | `flight_time` |
| Prop clearance | 5 mm to everything, elevons at full throw | `prop_clear` |
| Electrical ratings | every wire, pad, BEC, connector, pack C | `power` |
| Motor mount, pod | FEA at their real load cases | `mount_strength`, `pod_strength` |

## Architecture and why

- **Tailless swept wing, reflexed airfoil.** MH 45 (9.85 %, reflexed: pitch-stable without a tail), 28 deg LE sweep,
  250 / 120 mm chords (taper 0.48), -2.5 deg washout so the tips stall last. 18.5 dm², aspect ratio 5.4,
  MAC 192.6 mm at y 220.7, neutral point x 165.5 (kerf/aero.py `Planform.geometry`).
- **Pod + 4 wing segments**, each fits the A2L standing on its end (wing segments 230 / 220 mm tall), so a crashed
  segment is reprinted alone. The pod carries the battery, avionics and motor; the wing halves bolt to its sides.
- **Two carbon spars per side**: 8 x 6 mm at 28 % chord carries bending, 6 x 4 mm at 60 % holds twist and lines the
  segments up. Left and right tubes stop 8 mm off the centreline in printed sleeves; the pod box carries the moment
  across the middle (below).
- **One pusher 2806.5 / 7 in tri-blade on 6S**, behind the pod so the prop is out of the camera view and clear of the
  ground on a belly landing; elevons inboard of the fins, clear of the 178 mm disc.

## Purchased parts and sizing

| Item | Catalog | Why / sizing |
|---|---|---|
| Motor | drone.motors.2806_5_1300kv_7in | 2319 g at 23.42 V -> 2084 g at 22.2 V; TWR 1.57 on 1331 g (brief >= 1.5; the Darkwing's 3:1 would need a 2814-class motor and ~120 g more) |
| Prop | drone.props.7in | 178 mm disc behind the pod: 23 mm clear of everything (prop_clear) |
| ESC | drone.escs.skywalker_60a_v2 | 60 A cont. / 80 A vs the motor's 48.3 A peak; its BEC is not used |
| FC | drone.fcs.f405_wmo | 90 A PDB/current sensor carries the whole pack current; Vx 4.5 A BEC for the servos, 5 V 2 A for GPS/RX/VTX |
| Servos | servos.KST_X08_Plus | 8 mm thick fits the 17-19 mm deep section between the spars; 3.85 kgf.cm at 6 V (hinge moment below) |
| Battery | drone.batteries.6S_2200 | 2200 mAh x 0.8 / 5.2 A = 20 min cruise; 40 C x 2.2 Ah = 88 A >> 49.5 A peak |
| GPS | drone.gps.m9n_5883 | on the shelf front, under plain PLA (no carbon over it), away from the ESC |
| Camera, VTX, RX, antenna | micro_19mm, tx800, elrs_nano, lollipop4p_mmcx_95 | as on fpv_5in |
| Spars | rods.cf_tube_8x6 / 6x4 | lengths `main_len` / `rear_len` from the layout (one 1 m tube of each size gives both halves) |

**Elevon hinge moment** (servo sizing): at 150 km/h (q = 1065 Pa), elevon 300 x 40 mm (0.012 m²), hinge-moment
coefficient 0.4 at full throw: H = q Ch S c = 1065 x 0.4 x 0.012 x 0.040 = 0.20 N m = 2.1 kgf.cm, under the X08's
3.85 kgf.cm at 6 V (5 V Vx: ~3.3 by the datasheet's voltage scaling). Fly with rates (60-70 %) above ~180 km/h.

**Cruise power**: P = W V / (L/D) / eta = 1331 g x 9.81 x 22.2 m/s / 6 / 0.5 = 96.7 W (electrical.cruise). SonicModell
publishes 81 W at 75-80 km/h for its 1 m AR Wing Pro, so L/D 6 / eta 0.5 is on the safe side.

## Load paths and strength

- **Spar** (`spar_bending`): 1331 g x 6 g on an elliptical lift distribution gives 6.48 N m per half where the tubes
  leave the pod (y 50). The tubes share it by E I (same modulus): 8 x 6 mm 137 MPa, 6 x 4 mm 103 MPa against
  400 MPa / 1.5 = 267 MPa (Easy Composites' LOW figure for these exact tubes): 52 % of allowable.
- **Across the middle**: each tube's moment goes tube -> PLA sleeve (42 mm of engagement, bearing ~2 MPa) -> side wall
  -> the pod box (top and bottom skins ~300 mm wide at +-40 mm: I ~ 2.3e6 mm^4, ~0.1 MPa from the root moment).
  `pod_strength` checks it by FEA (right sleeves loaded with the half-wing's lift and root moment, left sleeves held).
- **Wing skins**: 1 wall + 3 % infill, like the Darkwing; the spars take the bending, the skin only air pressure and
  handling. The wing segments' layers are the airfoil outlines (printed standing), so skin stress lies in the layers.
- **Motor mount** (`mount_strength`): 6 mm PETG plate, 45.5 N (2 x full thrust) on the motor screws, held at the 4 pod
  bolts, crash SF 3.0.
- **Wing root**: two M3 per side from inside the pod into heat-set inserts in the inner segment's root face; they only
  keep the segment on the tubes (the tubes carry lift and moment). **Maker note:** add a 100 % infill modifier
  (10 mm cylinder) round each root insert and round the servo pocket - the 3 % infill gives an insert nothing to grip.

## Part list and print orientation

| Part | Material | Print | Notes |
|---|---|---|---|
| pod | PLA, 2 walls, 15 % | standing on its rear face | shelf and bosses vertical, boss ends 45 deg cones; 310 mm tall on a 48 x 50 mm foot: use the brim |
| wing_l1 / r1 | PLA, 1 wall, 3 % | standing on the root face | servo pocket, lead channel, root inserts |
| wing_l2 / r2 | PLA, 1 wall, 3 % | standing on the joint face | fin slot |
| elevon_l / r | PLA, 1 wall, 5 % | standing on its inner end (square to the hinge) | horn under the surface; 1.0 mm TE is the thinnest wall (two perimeters) |
| fin_l / r | TPU, 2 walls | flat | glued into the tip slots |
| nose | TPU, 2 walls | standing on its rear face | camera cheeks, 4 screw lugs with key channels |
| motor_mount | PETG, 4 walls, 40 % | flat on its aft face | counterbores up |

## Interfaces

| Between | How | Group |
|---|---|---|
| pod - wing_x1 | 2 x M3 from inside the pod through the side wall into heat-set inserts in the root face | wing_root_l / wing_root_r |
| pod - spars | tubes slide into close-fit bores in the sleeves (OD + 0.2) | - |
| wing segments - spars | slip fit (OD + 0.3), epoxied | - |
| wing_x1 - wing_x2 | epoxied butt joint on both spars | - |
| wing_x2 - elevon | bottom hinge tape (hinge line from aero.elevon_split, same cut on both) | joint elevon_l / elevon_r |
| wing_x2 - fin | fin tab glued in the tip slot | - |
| pod - nose | 4 x M3 from the nose lugs into heat-set inserts in the front bosses (washers on TPU) | nose |
| pod - motor_mount | 4 x M3 from the aft face into heat-set inserts in the tail bosses | motor_mount |
| motor_mount - motor | 4 x M3 x 6 from the mount's front face (counterbored), screwed on the bench first | motor |
| wing_x1 - servo | glued in the pocket by its case; arm out of the bottom, 1.2 mm pushrod to the elevon horn | - |

Edge distances: the nose and motor-mount insert rings sit within 1.5 d of a free edge where the bosses meet the skin
(they are bosses on a 2.4 mm skin; the boss itself is 10 mm round a 4 mm insert, 3 mm of wall). The motor's 19 mm
pattern puts its counterbores 2.3 mm from the centre hole: the motor's pattern forces it.

## Joint tree

pod (root) -> spars (rigid), wing_l1 / wing_r1 (rigid) -> wing_l2 / wing_r2 (rigid) -> elevon_l / elevon_r
(revolute about the hinge line, +-25 deg), fin_l / fin_r (rigid); wing_x1 -> servo (rigid); pod -> nose -> camera,
pod -> motor_mount -> motor -> prop disc; pod -> battery, XT60, ESC, FC, RX, GPS, VTX, antenna (rigid).

## CG and balance

The CG is the assembled CG of every item and wire (kerf/req_balance.py). The battery is the only heavy thing that
moves: `bat_x` sets it. Each 10 mm of battery moves the CG 2.8 mm (372 / 1331 g), i.e. 1.45 % MAC. Balance point
for the first flight: CG at the value `static_margin` reports (cg_x_mm), 10-13 % MAC ahead of the neutral point;
mark it under the wing.

## Assembly order

Pod -> spars into the sleeves -> inner segments (on the tubes, root bolts from inside) -> servos in their pockets
(centre them first) -> outer segments (epoxy) -> elevons (hinge tape) -> fins -> motor on its mount (bench) -> mount on
the pod -> shelf electronics (GPS, FC, RX, ESC, VTX), antenna -> battery + XT60 -> camera in the nose -> nose.
