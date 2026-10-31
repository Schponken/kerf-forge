# Pan-tilt camera mount — DESIGN

Brief (Spencer, via evals/pan_tilt/brief.md): "a pan-tilt camera mount for a Raspberry Pi Camera Module 3 driven by two
SG90-class micro servos, that screws onto a standard 1/4-20 tripod thread. Pan at least ±80°, tilt from straight
down-ish -30° to +60°."

Nobody was available for questions, so every open choice below is an **assumption** (marked A1...). Change them in
project.yaml params where a param exists.

## 1. Requirements (numbers)
| # | Requirement | Value | Checked by |
|---|---|---|---|
| R1 | Pan range | ≥ ±80° (built ±90°, the SG90's full travel) | joint `pan` range + sweep |
| R2 | Tilt range | -30° (down) to +60° (up) (built -35..+65) | joint `tilt` range + sweep + `cam_clear*` |
| R3 | Camera | Raspberry Pi Camera Module 3 (standard lens), 4 x M2 on 21 x 12.5 | `cam_mount` fastener group |
| R4 | Mount | female 1/4-20 UNC tripod thread in the base | captive ASME 1/4-20 hex nut (catalog `tripod_nut_1_4_20`) |
| R5 | Actuators | 2 x SG90 (catalog `servos.SG90`, 1.8 kg·cm stall @ 4.8 V) | purchased items |
| R6 | Holding torque | gravity torque on tilt, and on pan with the head tipped on its side, ≤ 50% of stall (ENGINEERING.md §3) | `torque_tilt`, `torque_pan` (gravity [0, 1, 0]) |
| R7 | Strength | stall-torque reactions and handling loads with SF 3 across layers | `bracket_fea`, `yoke_fea`, `yoke_pan_stall`, `base_fea`, `bracket_arm` |
| R8 | Stiffness | ≤ 0.3 mm deflection of the yoke/bracket at full stall (image stability) | FEA `max_disp_mm` |
| R9 | Mass | ≤ 90 g complete (small tripods, desk clamps) | `mass` |
| R10 | Moving clearance | ≥ 0.5 mm printed-to-printed over the whole range, camera ≥ 1 mm from the yoke | `cam_clear`, `cam_clear_base`, sweeps |

Assumptions:
- **A1** "Down-ish -30°" = camera optical axis 30° below horizontal; positive tilt = up. Pan 0 = camera looking +X.
- **A2** Supported tripod-screw protrusion: 5.5-8 mm above the tripod plate (typical quick-release plates are
  4.5-7 mm; no standard value was found - see REFERENCES.md). Below ~5.5 mm the screw engages fewer than 3 threads
  of the nut (the nut sits on a 1.5 mm floor, top 7.24 mm above the underside). The pan servo body sits 10 mm above the base underside
  (`servo_floor_z`), leaving ≥ 2 mm over an 8 mm screw tip. A longer screw would hit the pan servo: check yours.
- **A3** Horns: a 21T CNC aluminium micro disc horn on each servo (catalog `servo_horns.aluminum_micro_21T`). Its
  bolt circle (12 mm), M2 thread and 4 mm hub height are catalog ESTIMATES; the hub slides the full 3.2 mm SG90
  spline length over the spline (catalog `spline_engage`, added after review round 1), so each horn face sits 0.8 mm
  above its spline top; the plastic arm horns that come with an SG90
  are not used (they cannot be bolted, and glued horns are not serviceable).
- **A4** Camera cable: the standard FPC hangs from the bottom edge of the camera; ~10 g of cable drag at the camera
  seat is added to the tilt torque case.
- **A5** Indoor use, PETG, room temperature; no weather sealing.
- **A6** Servo power: 5 V, ≥ 1 A for the pair, 470-1000 µF across the servo supply (INDEX lesson: brownouts).

## 2. Architecture
Options considered:
1. **Stacked, servo-in-base + side-wall tilt servo, tilt carried on both sides** (picked). Same topology as the
   traxrobotics turret and Adafruit kit (REFERENCES.md), plus the inertiarobotics lesson: the tilt load is shared by
   the servo horn and an opposite M3 pivot, so the micro spline does not carry the bracket's side load alone.
2. Bearings on both axes (inertiarobotics A/B): 4 extra bearings and a taller head; overkill for a 4 g camera — the
   turning head is 34 g with its CG 15 mm off the pan axis (0.05 kg·cm overturning moment on the pan servo's output
   bearing), well under ENGINEERING.md §8's thresholds (60 mm link / 100 g) for a separate bearing.
3. Single-sided tilt on the horn only (Adafruit kit): simplest, but known neck wobble; rejected.

The camera's lens centre sits on the tilt axis (bracket camera seat is offset by the lens's 2.47 mm off-centre
position), so tilting keeps the image centre in place and the tilt servo carries almost no gravity torque.

## 3. Purchased parts and sizing
| Item | Catalog | Qty | Sizing |
|---|---|---|---|
| Micro servo | `servos.SG90` | 2 | Tilt: worst gravity torque 0.02 kg·cm (camera 4 g + bracket 6 g, lens on the axis, + 10 g cable drag at 13.5 mm) vs 0.9 limit (50% of 1.8) → 2% of stall. Pan: vertical axis, no gravity torque; with the tripod laid on its side the head's 34 g at 15 mm = 0.05 kg·cm (3% of stall). Speed 0.1 s/60°. |
| Disc horn 21T, 4 x M2 | `servo_horns.aluminum_micro_21T` | 2 | estimate geometry (A3); pan: 4 x M2 x 8 from the yoke top; tilt: 4 x M2 x 6 from the bracket inside |
| Camera Module 3 | `boards.rpi_camera_module_3` | 1 | 4 g; 4 x M2 x 5 into standoff pilots |
| 1/4-20 hex nut | `tripod_nut_1_4_20` | 1 | ASME B18.2.2, 11.13 AF / 5.74 max; pocket +0.2 on AF |
| 4 x 6 mm shoulder screw, M3 thread + M3 heat-set insert | `motion.shoulder_4_m3`, fdm_holes.M3 insert | 1 + 1 | tilt pivot (audit F11). The ground 4 mm shoulder turns in the yoke's -Y wall (free fit); the M3 thread goes into a CNC Kitchen M3 insert in the bracket knuckle and the shoulder end bottoms on it, so the screw is locked by its own seat, never clamps the wall (shoulder 6 = 5 wall + 0.9 gap + 0.1 play; picked by kerf/pins.py) and needs no threadlocker (anaerobic lockers crack PETG, Henkel 243 TDS). |
| M2 screws | screws.M2 | 2+2+4+4+4 | lengths picked by the fastener check (out/bom.md): servo tabs M2 x 6, horns M2 x 8 / x 6, camera M2 x 5 |

Mass: 59.3 g complete (report.json), printed parts base 14.2 g, yoke 12.8 g, bracket 6.0 g (40% infill estimate).

## 4. Printed parts
| Part | Job | Material | print_rot | load_axis | Envelope |
|---|---|---|---|---|---|
| base | screws onto the tripod; holds the pan servo hung from a 5 mm deck by its tabs (slides in from the open -Y side, 0.5 mm per side); captive 1/4-20 nut | PETG, 40% | [0,0,0] (bottom on bed) | Z | 40.2 x 26.2 x 33.0 |
| yoke | pan-horn plate (front notch for the camera FPC); +Y wall carries the tilt servo (mounted from outside); -Y wall carries the M3 pivot | PETG, 40% | [0,0,0] (plate on bed) | Z, X | 30 x 72.8 x 40.6 |
| bracket | U that holds the camera; +Y arm on the tilt horn, -Y arm knuckle on the pivot | PETG, 40% | [0,0,0] (flat bottom on bed) | X, Z | 24.5 x 34 x 26 |

Orientation notes: every part prints as assembled. The base deck legs over the servo cavity are 4.5 mm ledges
off the end and back walls (short bridges; a little sag only lowers the tab seat). The yoke's
horizontal holes are teardrops (pivot) or small (M2 pilots); its servo window top is a 12.8 mm bridge. The bracket's
knuckle and camera standoffs are teardrop prisms pointing down (52° flanks) and the horizontal key/centre-screw holes
have 45° roofs. kerf reports 3.5% "overhang" on the bracket: it is the exact-45° chamfer and teardrop faces plus the
roofs of 2-3 mm horizontal holes, all printable without support (see the stumble list in the run record).
Layer direction: base, yoke walls and bracket arms all see in-plane stress with a Z component, so every FEA check is
judged against PETG's Z strength (39 MPa) with SF 3 (ENGINEERING.md §3, across layers).

## 5. Interfaces
| Part A | Part B | Interface | Group | Fasteners |
|---|---|---|---|---|
| base | pan_servo tabs | `iface.servo_mount(kind="tap", top_through=True)`, servo slides in from -Y, tab tops under the deck | `base_pan` | 2 x M2 x 6 from below into deck pilots |
| yoke plate | pan_horn face | `iface.horn_mount` (clearance + centre-screw access) | `yoke_pan` | 4 x M2 x 8 |
| yoke +Y wall | tilt_servo tabs | `iface.servo_mount(kind="tap", top_through=True, teardrop=print_up_deg)` (horizontal pilots, F14), `tab_screws_from: bottom`; wall top 5 mm above the upper pilot (F13) | `yoke_tilt` | 2 x M2 x 6 from outside |
| bracket +Y arm | tilt_horn face | `iface.horn_mount` | `bracket_tilt` | 4 x M2 x 6 |
| bracket -Y knuckle | yoke -Y wall | `iface.pin_hole("motion.shoulder_4_m3")`: `heatset` (+ teardrop) in the knuckle, `free` + teardrop in the wall | `tilt_pivot` (pin) | 4 x 6 shoulder screw, M3 insert |
| bracket standoffs | camera | `iface.bolt_pattern(kind="tap", teardrop=print_up_deg)` on the catalog hole list: horizontal pilots get the horizontal pilot size (catalog `self_tap_pilot_horizontal`, audit F14); standoffs r 2.8, trimmed where they would enter the camera rear-parts zone | `cam_mount` | 4 x M2 x 5 |
| base | tripod | hex pocket on a 1.5 mm floor + 6.9 mm clearance hole | — | the tripod's own 1/4-20 screw |

## 6. Joint tree
base → pan_servo (rigid, `base.pan_seat`) → **pan** (revolute, servo output, -90..+90, home 0) → pan_horn → yoke
(rigid) → tilt_servo (rigid, `yoke.tilt_seat`) → **tilt** (revolute about -Y so + = up, -35..+65, home 0) → tilt_horn →
bracket (rigid) → camera (+ keep-outs `cam_lens`, `cam_rear`, `cam_view` + `cam_view_far` owned by the camera; the two
view boxes contain the 66 x 41° view cone from the 5.75 mm lens out to 30 mm).
Coupled poses swept: all four pan/tilt corners (`corners` sweep).

## 7. Requirements in project.yaml
`torque_tilt` (static_torque, 50% stall), `torque_pan` (static_torque with gravity across the pan axis: the head tipped on its side), `yoke_pan_stall` (FEA), `mass` (≤ 90 g), `cam_clear` (bracket-yoke ≥ 0.8 mm over tilt; measured 0.9 = the pivot gap),
`cam_clear_base` (camera-yoke ≥ 1 mm), `bracket_fea`, `yoke_fea`, `base_fea` (SF 3, Z strength), `bracket_arm`
(cantilever sizing check), `head_cg` (turning head CG ≤ 20 mm from the pan axis).

FEA load cases (all SF 3 on PETG Z strength 39 MPa → allowable 13 MPa):
| Check | Fixed | Load | Result |
|---|---|---|---|
| bracket_fea | camera standoff tops (camera jammed) | 176.5 N·mm (SG90 stall) as a torque on the horn contact face | 1.99 MPa p99.9 (peak 3.6), 0.04 mm |
| yoke_fea | pan-horn screw holes | 176.5 N·mm stall reaction at the tilt tab screws + 5 N down on the 4 mm shoulder bore (+ the engine's single-shear lever moment, 32 N·mm) | 2.44 MPa (peak 4.0), 0.22 mm (limit 0.3) |
| yoke_pan_stall (crash case) | tilt tab screws + pivot bore (head blocked) | 176.5 N·mm pan stall torque at the pan-horn screws | 0.86 MPa, 0.03 mm |
| base_fea | underside on the tripod plate | 176.5 N·mm pan stall at the tab screws; a 30 N sideways knock **at the camera** (IEC 62368-1 external-force level, UL tech brief; 100 N is for hand-held equipment) = 30 N at the tab screws + 30 N × 42.0 mm lever (deck to tilt axis) as a moment on the tab-top contact under the deck | 6.08 MPa p99.9 (peak 9.1 at a pilot), 0.12 mm (limit 0.2) |
| bracket_arm | section 5.5 mm ahead of the tilt axis | 13 N at the camera seat (stall torque / 13.5 mm), kt 1.5 | 0.2 MPa |
The yoke first failed its stiffness limit (0.56 mm, the 4 mm plate twisting under the tilt-servo reaction); the plate
went to 6 mm and widened to ±15 mm outside the camera's view: 0.23 mm.

Hand check, tripod nut floor: tightening a tripod screw by hand to ~300 N clamps the 1.5 mm floor between nut and
tripod plate (pure compression) over a ring 6.9 → 11.1 mm across flats ≈ 60 mm² → 5 MPa vs 39 MPa.

## 8. Assembly order
1. **Base**: slide the 1/4-20 nut in through the open -Y side and drop it into its floor pocket (flats across Y).
2. Slide the pan servo in from the open -Y side, output end toward +X, its case top into the deck slot, tab tops up
   against the deck; the lead (it leaves the servo's output end below the tabs) hangs out of the open side.
   2 x M2 x 6 from below through the tabs into the deck pilots: the 1.5 mm key goes up through the two holes in the
   floor.
3. Centre both servos electrically (1500 µs) before fitting horns.
4. **Bench**: screw the tilt horn to the bracket's +Y arm, 4 x M2 x 6 from the inside; the 1.5 mm key reaches them
   straight through the four access holes in the -Y arm. Screw the pan horn under the yoke plate, 4 x M2 x 8 from
   the top.
5. Press the pan horn (with the yoke, camera direction +X) onto the pan spline; drive the horn's centre screw through
   the hole in the middle of the yoke plate.
6. Hold the bracket between the yoke walls (horn toward the +Y wall). Push the **tilt servo** into the +Y wall from
   OUTSIDE, top first: its case top passes the window and its spline slides into the horn hub. 2 x M2 x 6 through the
   tabs from outside. (The servo goes in last because the bracket has only 0.6 mm of axial room: it could not be
   slid onto a spline already in place.)
7. Drive the tilt horn's centre screw with a 1.5 mm key through the -Y wall's pivot hole and the 2.4 mm hole in the
   knuckle floor.
8. Shoulder screw (4 x 6, M3 thread) through the -Y wall into the knuckle's heat-set insert (press the insert in
   at the bench before step 4); tighten until the shoulder end bottoms on the insert. The shoulder is 0.1 mm longer
   than wall + gap, so the head never clamps the wall; the 0.9 mm knuckle-to-wall gap is the axial play. No
   threadlocker (anaerobic lockers stress-crack PETG).
9. Camera: 4 x M2 x 5 into the standoffs, FPC connector at the bottom. Run the FPC down through the notch in the
   front edge of the yoke plate (outside the pan horn) and leave a ≥ 60 mm slack loop below it for ±90° pan before it
   goes to the Pi (use a ≥ 300 mm FPC).
10. Tie the tilt servo lead to the yoke ledge (2.5 mm tie through the two slots), leave a loop down to the base.
11. Screw the base onto the tripod.

## 8b. Electrics (`electrical:` + `wiring:` in project.yaml)
- Supply: MEAN WELL GST60A05 5 V 6 A desktop adapter (catalog `electronics.supplies.meanwell_gst60a05`) → SparkFun
  5.5 x 2.1 barrel-jack screw-terminal adapter (`electronics.connectors.dc_jack_5521_screw`, 10 A) → both servos'
  V+/GND. A 470-1000 µF capacitor across the jack terminals (BOM) buffers servo start-up current (INDEX lesson).
- Load: 2 x SG90, stall 0.36 A each (catalog, ProtoSupplies measured), so the adapter runs at 14% of its rating at
  double stall (`power` = power_budget 0.143). Wires: the servos' own leads + 300 mm 22 AWG servo extensions.
- Control: Raspberry Pi Zero 2 W (`boards.rpi_zero_2w`) on its own USB supply drives the servo signals (GPIO18 /
  GPIO19 hardware PWM, 50 Hz, 500-2500 µs for the full travel) with its GND tied to the supply minus, and reads the
  camera over a ≥ 300 mm FPC. The adapter, jack and Pi are modelled 150 mm below the head (strapped to the tripod
  column or on the desk); `mass` counts only the head.
- Routes (route_check, worst pose): pan lead out of the base's open -Y side, 190 mm routed (cut ≥ 219); tilt lead tied on
  the yoke ledge and then a free loop to the column, 248 mm routed at pan -90° (cut ≥ 286): a 300 mm extension on
  each servo covers both.

## 9. Review history
- Round 1 (design-reviewer, FAIL, 1 blocker): the 21T horn catalog entry had no `spline_engage`, so the horn proxy
  sat on the spline tip and every horn-derived position was 3.2 mm off. Fixed in the catalog (sourced spline length);
  the layout follows automatically. Minors fixed: duplicate pivot screw in bom_extra, FPC notch + loop length,
  base pocket 0.5 mm/side and 4.7 mm lead slot, pivot gap 0.9 mm (cam_clear ≥ 0.8), tripod protrusion range (A2).
  After a concurrent engine change (kerf now models screw heads) the camera touched a pan-horn screw head at
  tilt -35°: the tilt axis went up 1.5 mm (`tilt_h` 29.5), camera-to-yoke clearance now 3.3 mm.
- Round 3 (FAIL, 1 major): ENGINEERING.md 10b (added by another session during this run) now requires the electrical
  system: added §8b (supply, jack, Pi, four routed runs, power_budget), SG90 currents in the catalog.

## 10. Risks / numbers to measure before the final print
- Horn (A3): measure bolt circle, thread and hub height of the horns you buy; if they differ, the catalog entry and
  both horn mounts change.
- SG90 tab hole and output offset were scaled from a drawing (catalog note) — print the base first and test-fit.
- SG90 gear boss (catalog gear_boss_d / aux_boss_*, measured from a CAD model): the yoke window has a 14 mm, 1.2 mm
  deep relief for it; if your servo's boss is larger, the tilt servo will not sit flat.
- SG90 lead exit (catalog cable_boss_*, keep-out envelope): the lead leaves the output end below the tabs at a
  place that varies between batches, right under the output-end tab screw. So the pan servo hangs from the base deck
  by its tab tops (screws from below) and the lead leaves through the open side: no wall or screw near it.
- Camera rear-parts depth 3.2 mm is approximate: the standoffs give 3.5 mm.
- Tripod screw protrusion ≤ 8 mm (A2).
- Printed-pilot M2 threads wear: the servo tab screws are meant to go in a few times only.
