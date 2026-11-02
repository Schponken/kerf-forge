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
| Prop on the ground | accepted: may touch on a belly landing (see "Prop strike") | - |
| Electrical ratings | every wire, pad, BEC, connector, pack C | `power` |
| Motor mount, pod | FEA at their real load cases | `mount_strength`, `pod_strength` |

## Architecture and why

- **Tailless swept wing, reflexed airfoil.** MH 45 (9.85 %, reflexed: pitch-stable without a tail), 28 deg LE sweep,
  250 / 120 mm chords (taper 0.48), -2.5 deg washout so the tips stall last. 18.5 dm², aspect ratio 5.4,
  MAC 192.6 mm at y 220.7, neutral point x 165.5 (kerf/aero.py `Planform.geometry`).
- **Pod + 4 wing segments**, each fits the A2L standing on its end (wing segments 230 / 220 mm tall), so a crashed
  segment is reprinted alone. The pod carries the battery, avionics and motor; the wing halves bolt to its sides.
- **Two carbon spars per side**: 8 x 6 mm at 28 % chord carries bending, 6 x 4 mm at 60 % holds twist and lines the
  segments up. Left and right tubes stop 8 mm off the centreline inside one wall-to-wall printed sleeve per pair, which
  carries the moment across the middle (below).
- **One pusher 2806.5 / 7 in tri-blade on 6S**, behind the pod so the prop is out of the camera view; elevons inboard
  of the fins, clear of the 178 mm disc. The thrust line sits level with the CG (see "Prop strike").

## Purchased parts and sizing

| Item | Catalog | Why / sizing |
|---|---|---|
| Motor | drone.motors.2806_5_1300kv_7in | thrust on the prop actually fitted (catalog `thrust_by_prop`): 2319 g on the HQ 7x4x3 at 23.42 V -> 2084 g at 22.2 V (the Gemfan 7040 gives only 2058 g -> 1849 g, too little); TWR >= 1.5 needs <= 1389 g all-up |
| Prop | drone.props.hq_7x4x3 | the prop iFlight tested this motor on; 178 mm disc, 25 mm clear of everything in the air (prop_clear) |
| ESC | drone.escs.skywalker_60a_v2 | 60 A cont. / 80 A vs the motor's 48.3 A peak; its BEC is not used |
| FC | drone.fcs.f405_wmo | 90 A PDB/current sensor carries the whole pack current; Vx 4.5 A BEC for the servos, 5 V 2 A for GPS/RX/VTX |
| Servos | servos.KST_X08_Plus | 8 mm thick fits the 17-19 mm deep section between the spars; 3.85 kgf.cm at 6 V (hinge moment below) |
| Battery | drone.batteries.6S_1800 | CNHL MiniStar 1800 (302 g): the 2200 (372 g) put the all-up mass over 1400 g and TWR under 1.5 once the review's fixes were in; ~15 min at 80 km/h cruise (flight_time), 120 C |
| GPS | drone.gps.m9n_5883 | on the shelf front, under plain PLA (no carbon over it), away from the ESC |
| Camera, VTX, RX, antenna | micro_19mm, tx800, elrs_nano, lollipop4p_mmcx_95 | as on fpv_5in |
| Spars | rods.cf_tube_8x6 / 6x4 | lengths `main_len` / `rear_len` from the layout (one 1 m tube of each size gives both halves) |

**Elevon hinge moment** (servo sizing): at 150 km/h (q = 1065 Pa), elevon 300 x 40 mm (0.012 m²), hinge-moment
coefficient 0.4 at full throw: H = q Ch S c = 1065 x 0.4 x 0.012 x 0.040 = 0.20 N m = 2.1 kgf.cm at the hinge. The
linkage gears it down: horn hole 12 mm under the hinge, servo arm hole 8 mm from the spline (use that hole of the
KST arm), so the servo sees 2.1 x 8 / 12 = 1.4 kgf.cm = 36 % of its 3.85 kgf.cm at 6 V (ENGINEERING.md s3: <= 50 %).
KST publishes no hole radii for its stock arms (checked: KST/OpenELAB product pages, servodatabase.com list no horn dimensions), so the builder measures the arm and uses the hole at 8-11 mm: at 11 mm the servo sees 2.1 x 11 / 12 = 1.9 kgf.cm = 50 %, the ENGINEERING.md limit. The pushrod leaves the pocket through a 5 mm slot in its aft wall, open to the bottom skin, stopping short of the rear spar channel (the reviewer found the rod's line ran 0.65 mm into the wall at full throw). Bridge the F405-WMO's Vx=6V pads so the servos run at 6 V. 1.3 mm horn holes on 1.2 mm wire: ~0.1 mm play, under
0.5 deg at the surface. Fly with rates (60-70 %) above ~180 km/h.

**Cruise power**: P = W V / (L/D) / eta = 1331 g x 9.81 x 22.2 m/s / 6 / 0.5 = 96.7 W (electrical.cruise). SonicModell
publishes 81 W at 75-80 km/h for its 1 m AR Wing Pro, so L/D 6 / eta 0.5 is on the safe side.

## Load paths and strength

- **Spar** (`spar_bending`): 1331 g x 6 g on an elliptical lift distribution gives 6.48 N m per half where the tubes
  leave the pod (y 50). The tubes share it by E I (same modulus): 8 x 6 mm 137 MPa, 6 x 4 mm 103 MPa against
  400 MPa / 1.5 = 267 MPa (Easy Composites' LOW figure for these exact tubes): 52 % of allowable.
- **Across the middle**: left and right tubes stop 8 mm off the centreline, inside ONE V-shaped PLA sleeve per tube
  pair that runs from side wall to side wall (main 16 mm, rear 13 mm round: 4 / 3.5 mm walls, teardrop underside so it
  prints without support). The moment goes tube -> sleeve -> the other half's tube; the side walls only carry shear.
  Hand check at the centreline: main share 73 % x 6.48 N m = 4.73 N m on a 16 / 8.2 mm PLA tube (I = 2995 mm^4) =
  12.6 MPa against PLA 48 MPa / 2 = 24 MPa. `pod_strength` (FEA, right bores loaded with the half-wing's lift + root
  moment, left bores held): 2.25 MPa p99.9 against 19.5 allowed. (A first version with separate sleeves ending at the
  side walls put the whole moment into the wall junction: 28.6 MPa p99.9, 2.3 mm - it failed and was replaced.)
- **Pod skins**: the build calls the pod overbuilt for the 6 g case (8 % of allowable). The 1.7 mm skin (4 perimeters, solid) is set by
  the other jobs it has: belly landings on grass and gravel, the battery's inertia in a nose-in arrival, heat-set
  insert bosses and a stiff enough box for the root bolts; thinner than 4 perimeters would also print poorly standing 310 mm tall.
- **Wing skins**: 1 wall + 3 % infill, like the Darkwing; the spars take the bending, the skin only air pressure and
  handling. The wing segments' layers are the airfoil outlines (printed standing), so skin stress lies in the layers.
- **Motor mount** (`mount_strength`): 6 mm PETG plate, 45.5 N (2 x full thrust) along the motor axis at the motor
  screws, held at the 4 pod bolts, crash SF 3.0 (for a pusher the thrust presses the plate onto the pod; the case
  that pulls the screws is a nose-in crash throwing motor + prop aft, 64 g x 50 g = 31 N, covered by the 45.5 N): 1.5 MPa of 16. The build calls it overbuilt; it stays 6 mm on purpose: the motor screws need
  3 mm counterbores (heads flush against the pod) over 3 mm of grip for a stock M3 x 5 (ASSEMBLY.md's computed length), and a stiff plate keeps prop
  imbalance from buzzing the tail. It weighs 11.5 g.
- **Wing root**: two M3 per side from inside the pod (reached from above through the hatch) into heat-set inserts in
  the inner segment's root face; they only keep the segment on the tubes (the tubes carry lift and moment). The
  inserts, the servo pocket, the splice inserts and the elevon horn slots have 100 % infill **modifiers** in
  project.yaml, which `out/plates/PRINT_SETTINGS.md` lists with where and how big - set them in the slicer.
- **Pod walls**: 4 perimeters (1.7 mm skin = solid), 15 % infill elsewhere, 100 % modifier on the spar sleeves, so the
  FEA's solid model is what prints (fea_static now fails a part with < 4 walls).

## Part list and print orientation

Plates are one material each (PLA / PETG / TPU need different temperatures).

| Part | Material | Print | Notes |
|---|---|---|---|
| pod | PLA, 4 walls, 15 % (+ modifiers) | standing on its rear face, supports under the centre-section TE only | shelf, ledges and bosses vertical; boss ends 45 deg cones; sleeves teardrop; 310 mm tall: brim |
| hatch | PLA, 2 walls | standing on its side edge (skin vertical) | rests on the pod's ledges; rear tongue under the skin, 2 x M3 at the front |
| wing_l1 / r1 | PLA, 1 wall, 3 % (+ modifiers) | standing on the root face | servo pocket, lead channel, root and splice inserts |
| wing_l2 / r2 | PLA, 1 wall, 3 % (+ modifier) | standing on the joint face, supports up the elevon slot under the TE stub | fin slot, splice insert |
| elevon_l / r, elevon_lo / ro | PLA, 1 wall, 5 % | standing on the outboard end (120 / 180 mm tall), brim | joined by two 3 mm carbon rods (4 and 10 mm aft of the hinge); the inner half has the horn slot |
| horn_l / r | PETG, solid | flat | glued into the elevon slot; holes 9 / 12 / 15 mm under the hinge |
| splice_l / r | PETG, 4 walls | flat | 2 x M3 up into the two segments |
| fin_l / r | PETG, 2 walls | flat | stiffer than TPU at speed; glued into the tip slots |
| nose | TPU, 2 walls | standing on its rear face | camera flush in a square window, cheeks, 2 cooling vents, 4 screw lugs with key channels |
| motor_mount | PETG, 4 walls, 40 % | flat on its aft face | counterbores up |

## Interfaces

| Between | How | Group |
|---|---|---|
| pod - wing_x1 | 2 x M3 from inside the pod through the side wall into heat-set inserts in the root face | wing_root_l / wing_root_r |
| pod - spars | tubes slide into close-fit bores in the sleeves (OD + 0.2) | - |
| wing_x1 - spars | slip fit (OD + 0.3), epoxied | - |
| wing_x1 - wing_x2 | outer segment slides on the tubes (not glued); the splice plate's 2 x M3 hold it: bolt-on, replaceable | splice_l / splice_r |
| wing_x1 - elevon_x | bottom hinge tape (hinge line from aero.elevon_split); elevon_xo joined to elevon_x by two 3 mm carbon rods (joiner_x, joiner2_x): epoxied (5-min, glue:epoxy_5min) in the inner half, reamed push fit in the outer half | joint elevon_l / elevon_r |
| elevon_x - horn | horn tab glued into the slot under the inner half | - |
| wing_x2 - fin | fin tab glued in the tip slot | - |
| pod - hatch | rear tongue under the pod skin + 2 x M3 at the front into inserts in the ledge blocks | hatch |
| pod - nose | 4 x M3 from the nose lugs into heat-set inserts in the front bosses (washers on TPU) | nose |
| pod - motor_mount | 4 x M3 from the aft face into heat-set inserts in the tail bosses | motor_mount |
| motor_mount - motor | 4 x M3 from the mount's front face (counterbored), screwed on the bench first | motor |
| wing_x1 - servo | glued in the pocket by its case; arm out of the bottom, 1.2 mm pushrod to the horn | - |
| pod - battery | 20 mm strap through two floor tabs, over the pack | - |

Edge distances: the nose and motor-mount insert rings sit within 1.5 d of a free edge where the bosses meet the skin
(bosses on a thin skin; the boss itself is 10 mm round a 4 mm insert, 3 mm of wall). The motor's 19 mm pattern puts
its counterbores 2.3 mm from the centre hole: the motor's pattern forces it.

## Prop strike (accepted, Spencer 2026-11-01)

The 178 mm prop hangs ~30 mm below the belly. Raising the motor on a pylon so it clears was tried: the thrust line
then sits ~60 mm above the CG, and on a slow, full-throttle hand launch the pitch-down moment (~0.6-0.8 N m) is more
than the elevons can answer at 40 km/h (~0.3 N m) - a nose-in launch. A folding prop has no published thrust on this
motor. So, as on most pusher FPV wings: the thrust line stays level with the CG, you land with the motor stopped
(INAV: motor stop on low throttle), and the cheap nylon prop flexes or breaks before the motor shaft does. Spares come
in the 4-pack.

## Cooling

Air comes in through two 8 mm vents in the nose's lower sides, runs along the bay past the ESC and VTX on the shelf,
and leaves through two 30 x 8 mm slots in the belly behind the shelf.

## Joint tree

pod (root) -> spars (rigid), hatch, nose -> camera, motor_mount -> motor -> prop disc, battery, strap, XT60, ESC, FC,
RX, GPS, VTX, antenna (rigid); pod -> wing_l1 / wing_r1 (rigid) -> wing_l2 / wing_r2 (rigid) -> fins; wing_x1 -> servo,
splice (rigid), elevon_l / elevon_r (revolute about the hinge line, +-25 deg) -> horn, two joiner rods, outer half (rigid).

## CG and balance

The CG is the assembled CG of every item and wire (kerf/req_balance.py). The battery is the only heavy thing that
moves: `bat_x` sets it. Each 10 mm of battery moves the CG 2.2 mm (302 / 1356 g), i.e. about 1.2 % MAC. Balance point
for the first flight: CG at the value `static_margin` reports (cg_x_mm), 10-13 % MAC ahead of the neutral point;
mark it under the wing.

## Assembly order

Pod -> spars into the sleeves -> inner segments on the tubes (epoxy), root bolts from above -> servos in their pockets
(centre them first) -> outer segments slid on, splice plates bolted -> horns glued into the inner elevon halves ->
elevons taped on (hinge tape), joiner rods (both epoxied into the inner half), outer halves (bores reamed 3.0 mm first) -> fins -> motor on its mount (bench) -> mount on the pod ->
shelf electronics (GPS, FC, RX, ESC, VTX), antenna -> battery, strap, XT60 -> hatch -> camera in the nose -> nose.

### Elevon joint: no free play (review 2026-11-02)

The outer elevon half (60 % of the surface) is driven only through the joiner rods, and free play on a control surface
is the classic cause of flutter/buzz at 150-180 km/h. So: **two** 3 mm carbon rods (rods.cf_rod_3, 50 mm), one 4 mm and
one 10 mm aft of the hinge in plan (the aft one as far back as the section allows a 3.1 mm bore with ~0.9 mm wall;
at 16 mm the section is only 4 mm thick). Both are **epoxied into the inner half** (5-min epoxy, bores +0.1 mm). In the
**outer half** the bores print at 3.0 mm nominal (FDM holes come out ~0.1 mm small) and are **reamed with a 3.0 mm
drill** to a push fit on the rods (catalog: rods are -0.03/-0.1 mm undersize), so the outer half slides off for crash
repair but has no clearance to rattle in. With a single slip-fit rod at 5.3 mm the play was +-1.35 deg; any residual
reaming clearance (<= 0.05 mm radial) at the 10.5 mm aft rod is < 0.3 deg, and a 25 mm hinge-tape band wrapped across
the split on both skins preloads it to zero. Crash repair: cut the band, slide the outer half (with its outer wing
segment) off the rods, re-tape after.
