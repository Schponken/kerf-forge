# References — rack-and-pinion parallel gripper for the desk robot arm

Research date 2026-10-31. Every design below is also a row in `references/INDEX.md` (measured = taken from the
published STL/STEP with trimesh in /tmp/refs; read = stated on the linked page). Kerf borrows layouts, proportions and
published numbers from them; no geometry or code is copied, so no teardown was needed (Robo9's CERN-OHL-P-2.0 would
allow copying with its notice; the others are CC BY / BY-NC / proprietary).

## References studied

| Reference | License | Why it matters here |
|---|---|---|
| Robo9 SO-ARM100/101 parallel gripper — https://github.com/roboninecom/SO-ARM100-101-Parallel-Gripper | CERN-OHL-P-2.0 hardware | Same layout as ours, proven and documented: one pinion, two racks on opposite sides, each rack fixed to one printed clamp, both clamps sliding on the same two rods (Ø6 × 125 tubes, 32 mm apart, 16 mm bores). Measured 18-tooth module-0.8 pinion, 61 mm racks; 84 mm stroke, 120 N, 170 g. Rod fit chosen with a printed 6.0-6.3 mm test plate; two MF106ZZ bearings on the frame appear to back the racks (inferred from the assembly renders); servo torque limited to 50 %. |
| Rack & Pinion Robotic Gripper Jaw (MG996R) — https://www.printables.com/model/403482-rack-pinion-robotic-gripper-jaw (same design: https://makerworld.com/models/940813) | CC BY (Printables) | The proven MG996R version (984 downloads, 4.8 stars on MakerWorld). Measured 14-tooth module-1 pinion pressed on the bare spline, 56 mm racks sliding in printed channels. Its users report the printed pinion SPINNING on the spline. |
| SG90 Parallel Robot Gripper Claw, 60 mm — https://www.printables.com/model/1871958-sg90-parallel-robot-gripper-claw-60mm-opening | CC BY | Read: 24-tooth module-0.7 pinion, ~26 mm per jaw for 180° of servo, 33 × 36 mm jaw faces; tips: TPU/rubber on the jaw faces, limit closing angle in code instead of stalling. |
| Pololu Micro Gripper #3551 — https://www.pololu.com/product/3551 | proprietary (drawing published) | Commercial servo pinion + opposing racks: its 32 mm stroke needs 0.5-2.4 ms pulses (nearly the servo's whole travel) — the stroke-vs-servo-travel trap. |
| AR Gripper (open hardware) — https://www.printables.com/model/657807-ar-gripper-open-hardware-adaptive-electric-paralle | CC BY | Measured 14-tooth pinion (tip Ø18.2); pads 2-3 mm foam rubber + 3M grip tape; the author broke many PETG fingers and moved fingers/sliders to CF filament; stops on contact. |
| ROBOTIS OpenManipulator-X gripper — https://emanual.robotis.com/docs/en/platform/openmanipulator_x/specification/ | proprietary docs | Contrast: NOT rack and pinion (crank arm + link rods + rail blocks), stroke 20-75 mm, rubber pads. |
| Parallel Gripper for EEZYbotARM MK2 — https://www.printables.com/model/275802-parallel-gripper-for-eezybotarm-mk2 | CC BY-NC | Contrast (four-bar linkage). Measured flex-filament finger pad 22.9 × 9.5 × 3.3 mm. |
| Dynamixel Parallel Gripper (GripSense) — https://www.printables.com/model/1802484-dynamixel-parallel-gripper | CC BY-SA | Rack and pinion with printed rail; deliberate weak link (fingers snap above ~3 kg) plus a servo current limit. |
| LeRobot SO-101 stock gripper (pivoting jaw), EEZYbotARM claw — already in INDEX (https://github.com/TheRobotStudio/SO-ARM100) | Apache-2.0 / not stated | Pivoting jaws, not parallel; no new numbers needed. MeArm and Yale OpenHand were not studied (pivot claw / underactuated fingers: different mechanism). |
| Starkit and fd.iwth rod lessons — https://github.com/mikuel210/starkit ; https://github.com/minu920/tvc-drone (INDEX rows) | not stated / GPL-3.0 | Rod fit in printed holes varies with print orientation and moisture: lock rods mechanically, don't rely on a press fit. |
| desk robot arm wrist — projects/robot_arm (DESIGN.md, parts/gripper.py, parts/layout.py, project.yaml) | this repo | The interface the new gripper must copy exactly (below). |
| Stoimenov et al. 2024, Tribology in Industry 46(1) — https://www.tribology.rs/journals/2024/2024-1/2024-1-09.html | CC BY-NC | PETG on steel, dry: static COF 0.27 / 0.24 / 0.29 at 30 / 50 / 70 N (kinetic 0.20 / 0.18 / 0.26). |
| Engineering ToolBox friction table — https://engineeringtoolbox.com/friction-coefficients-d_778.html | not stated | Rubber on cardboard 0.5-0.8, rubber on rubber 1.16, nylon on steel 0.4, glass on glass 0.9-1.0. |
| igus "The 2:1 Rule" (DryLin) — https://www.igus.com/contentData/wpck/pdf/US_en/DryLin%20Linear%20Bearings%202-1%20Rule.pdf | vendor doc | Drive/load force more than 2× the bearing length from the fixed rail → binding or chatter; fixed/floating bearing pairs. |
| gearpy Lewis factors — https://gearpy.readthedocs.io/en/latest/mechanical_objects/SpurGear/lewis_factor.html ; Sovol gear guide — https://www.sovol3d.com/blogs/news/3d-printing-gears-that-actually-work-backlash-orientation-and-material-tips | not stated | Y = 0.308 (18 T), 0.314 (19), 0.320 (20), 0.484 (~rack). Sovol: module 1.5-2 for a 0.4 mm nozzle, 0.2-0.4 mm total backlash, face ≥ 3-5 × circular pitch, 4-6 walls. |
| Guide rod: ServoCity 4 mm stainless precision shafting — https://www.servocity.com/4mm-stainless-steel-precision-shafting/ ; hardened alternative Ondrives Z-4-300A — https://ondrives.com/z-4-300a | vendor pages | Catalog `rods.ss_rod_4` (added): Ø4, stocked 25/50/100/150/200/250 mm, $2.79 per 100 mm; Rockwell 83B, tolerance not published. Ondrives: 4 mm h6 (0/-0.008), 62 HRC, 300 mm, 0.099 kg/m. |

Not reachable from this session: MakerWorld and GrabCAD model pages (HTTP 403; found via search snippets only, e.g.
GrabCAD user luca.delbarba's servo + pinion + MGN7C-rail parallel grippers), Grobotronics 3 × 100 mm g6 shaft page.

## Decisions this supports

1. **Layout: one printed pinion on the servo, two racks on opposite sides, one rack per jaw carriage, both carriages
   on the same two steel rods.** Proven by Robo9 (rods) and Printables 403482 (MG996R, printed channels); jaws stay
   parallel and self-centre by construction.
2. **Wrist interface copied from the current gripper** (projects/robot_arm/parts/gripper.py, layout.py,
   project.yaml): plate A takes the wrist horn `servo_horns.aluminum_25T` via `iface.horn_mount(..., group="wr_horn")`
   (4 × M3 × 10, DESIGN.md interface table), plate B takes the M3 × 14 pivot screw in an M3 heat-set insert
   (`iface.pin_hole(ctx, "M3", ..., "wr_pivot", fit="heatset")`), body width across the fork `grip_w` = 35 mm,
   plates `plate_t` = 7 mm, wrist discs r = `link_h`/2 = 17 mm, 25 mm flat print foot (`FOOT_L`). Same group names
   and params so the forearm needs no change.
3. **Pinion module 1.5, 20 teeth (19 acceptable, 18 marginal).** Module ≥ 1.5 is the Kerf rule (docs/ENGINEERING.md
   §8, Sovol). Travel: per-jaw travel = pitch radius × servo angle. MG996R ≈ 120° at 1000-2000 µs (catalog
   `servos.MG996R` note, nominal). 18 T (pitch Ø27): 120° gives 2 × 28.3 = 56.5 mm of opening change; 2 → 58 mm
   needs 56 mm = 118.8°, about 1° of margin. 19 T (Ø28.5): 59.7 mm, needs 112.6°. **20 T (Ø30, tip Ø33,
   root Ø26.25): 62.8 mm, needs 107.0° — 13° of margin** for unit-to-unit travel and end-stop slack. Hobby grippers
   use module 0.7-1.0 (Robo9 0.8, 403482 1.0, SG90 claw 0.7) only with fine layers; Kerf keeps 1.5.
   (Contract as of 686f23b: 20 T and 2-54 mm = 52 mm of change → 99.3° of servo, ~21° of margin.)
4. **Pinion bolted to the aluminium 25T horn, never pressed on the spline** (403482 users: printed pinion spins on
   the spline; Robo9 fixes its gear to the servo disc with 4 set screws). Horn: 4 × M3 tapped on a 14 mm bolt circle
   + centre screw (catalog `servo_horns.aluminum_25T`). With 5.5 mm M3 socket heads (catalog `screws.M3`)
   counterbored in the pinion face, the wall from a ~Ø6 counterbore to the tooth root is 13.13 − 10 = 3.1 mm at
   20 T but only 11.63 − 10 = 1.6 mm at 18 T — another reason for 20 T.
5. **Gear and rack strength (PETG, printed flat, teeth in the XY plane).** At MG996R stall (9.4 kg·cm = 0.922 N·m @
   4.8 V, catalog) the two racks share the torque: F per mesh = T / (2 r) = 30.7 N (20 T) / 34.1 N (18 T). Lewis
   sigma = F / (b m Y): 20 T, b = 8 mm → 8.0 MPa (SF 6.0 on PETG 48 MPa XY, catalog `materials.PETG`); b = 10 → 6.4 MPa
   (SF 7.5). Sovol's face width ≥ 3-5 × circular pitch (14-24 mm at m 1.5) is aimed at gears that tilt on a shaft;
   ours is bolted to a 20 mm horn and the racks are rod-guided, so **b = 8-10 mm** is enough (references run 6-7 mm).
   Separating force per rack F tan 20° ≈ 11 N at stall: something must hold each rack in mesh (Robo9 appears to use
   bearings behind the racks; here the carriage on the rods does it, so keep each rack close to its rod). Print pinion and
   racks with 4-6 walls (Sovol); Robo9 prints gear and racks at 100 % infill. 0.3 mm total backlash (ENGINEERING.md §8).
   Use `kerf.drives.rack_pinion` (added in 686f23b, py_gearworks involute rack, same 0.3 mm backlash).
6. **Grip force: ample at stall, so hold by position, not by stalling.** Friction grip on two jaw faces needs
   N per jaw ≥ SF × m g / (2 mu). For 150 g: bare PETG (mu 0.24, PETG-steel low value, Stoimenov 2024) → 6.1 N at
   SF 2 / 9.2 N at SF 3; rubber-like pad (mu 0.5, low end of rubber-cardboard, Engineering ToolBox) → 2.9 / 4.4 N.
   Available at stall: 30.7 N per jaw (20 T) before friction losses — 3.3× the bare-PETG SF 3 need, 7× with pads.
   Command the jaws to just past contact (robot_arm DESIGN.md: stall draws ≈ 2.5 A and heats the servo); Robo9 sets Max
   Torque Limit 500 (50 % if the register is 0-1000, inferred), the SG90 claw limits the angle. FEA load case for jaws/carriages: 30.7 N (34.1 N if 18 T) on the
   pad, servo at stall.
7. **Pads: separately printed TPU 95A (catalog `materials.TPU`), 2-3.5 mm thick, mechanically retained** (dovetail or
   screws, not glue). Every reference with pads uses a 2-3.3 mm compliant layer (AR Gripper 2-3 mm foam + grip tape;
   EEZYbot flex pad 3.3 mm measured; ROBOTIS rubber pads; SG90 claw tip). The compliance also hides the jaw tilt
   (decision 9). No adhesive pad sheet added to the catalog: TPU needs no extra purchase.
8. **Guide rods: 2 × Ø4 × 100 mm stainless (`rods.ss_rod_4`, ServoCity 2100-0004-0100, $2.79 each).** 100 mm is a
   stocked length; Ø4 is (4/3)^4 = 3.2× stiffer than Ø3; 9.9 g each (7.9 g/cm³). Rod tolerance is not published:
   size the carriage bores from a printed test coupon with the real rod (Robo9 test plate; ENGINEERING.md §6 snug slip
   +0.2, free +0.3-0.4). Capture both rod ends in blind holes in the end cheeks so they cannot walk out (Starkit /
   fd.iwth: printed rod fits vary, lock mechanically). Hardened h6 alternative: Ondrives Z-4-300A cut to length.
9. **Carriage bore length vs. rod length vs. jaw length (2:1 rule).** Both carriages share the rods, so the free rod
   length between cheeks F must hold both bores plus the stroke: F ≥ 2 L_b + 56 + ~0.5 mm. A 100 mm rod with ~6 mm
   in each cheek gives F ≈ 88 → L_b ≤ ~15.7 mm per carriage (Robo9: 125 mm rods, 84 stroke, 16 mm bores — the same
   budget). igus 2:1: the force that slides a carriage must act within 2 L_b of its rod. The rack force (drive) is
   easy to keep close to a rod. The pad reaction acts a whole jaw length ahead (e.g. 40 mm > 2 × 15.7) but only after
   contact, when the carriage is no longer sliding; what it does cause is jaw tilt in the bore clearance:
   0.2 mm / 15.7 mm ≈ 0.7° → ~0.5 mm at a 40 mm pad tip. Rod bending is small by comparison (stall couple
   30.7 N × 40 mm shared by two Ø4 rods ≈ 0.07 mm at the tip, simply-supported estimate). Better option within the
   same rod length: **igus fixed/floating pairing** — each carriage gets a long "fixed" bore (e.g. 24 mm) on the rod
   next to its own rack and a short "floating" guide (e.g. 7 mm, slotted) on the other rod, so each rod carries
   24 + 7 + 56.5 ≈ 88 mm: tip tilt drops from ~0.5 to ~0.33 mm and the rack sits next to its fixed rod. Keep the pad centre as close to the rod
   axis as the reach allows.
   (Contract as of 686f23b: `carr_len` 14 → 0.2 / 14 ≈ 0.8° → ~0.57 mm at a 40 mm pad tip. `rod_y` 21 vs pinion tip
   radius 16.5 leaves 4.5 mm radially between the tooth tips and a rod axis — a rack body in the same plane as the
   rods would not fit there (Robo9's rack is 9.35 deep), so the racks must sit in a different plane along the pinion
   axis or the rods move out.)
10. **Mass budget (≤ 125 g).** MG996R 55 g + horn 3 g + 2 rods 19.9 g = 77.9 g leaves ≤ 47 g for every printed part
    plus screws and pads; today's gripper is 31 g + 5 g printed (robot_arm DESIGN.md) and Robo9 is 170 g. If over,
    Robo9's precedent is Ø6 × 1 aluminium or carbon tubes (catalog `rods.cf_tube_6x4`: 2.4 g per 100 mm), at the cost
    of larger bores. The wrist MG996R currently runs at 20 % of stall (robot_arm DESIGN.md), so a few grams over does
    not threaten the wrist; the shoulder (39 %) is the joint to re-check.
11. **Print orientation:** pinion flat (Sovol); racks flat with the tooth profile in the XY plane; carriages with the
    rod bores vertical so they print round (no teardrop on a sliding bore); 100 % infill or 4-6 walls on teeth.

## Open questions

- Real MG996R travel between 1000 and 2000 µs on Spencer's unit (catalog: ~120°, nominal): measure before fixing the
  tooth count; the 20 T margin (107° needed) covers ±6°.
- ServoCity rod diameter tolerance is unpublished: print the bore coupon (and use `kerf calibrate` offsets).
- Static friction of TPU 95A on glass / smooth plastic was not found in an opened source (TPU is harder than the
  rubber in the Engineering ToolBox table): check with a tilt test (mu = tan of the slip angle) before trusting 0.5.
- Mass: does the body + carriages + pinion + pads fit in ~47 g with steel rods? If not: CF tubes, or relax to ~130 g
  and re-check the shoulder torque.
- Jaw length (pad centre ahead of the rod axis) sets tilt and the 2:1 ratio; choose it with the robot_arm reach and the
  desk-clearance note in robot_arm DESIGN.md.
- MakerWorld 940813 licence unknown (pages block scripted reads); the Printables copy is CC BY. Only ideas are used.
- Bambu A2L TPU printing (external spool vs. AMS) not checked here; a cut neoprene/rubber sheet is the fallback.

## Existing designs (kerf find)

### `kerf find "servo rack and pinion parallel jaw gripper for robot arm"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [rack and pinion (Linear Servo Actuator)](https://www.printables.com/model/730367-rack-and-pinion-linear-servo-actuator) | CC-BY-NC | adapt OK, credit, non-commercial | box.stl: 80.5 x 48.6 x 16.9 mm; rack.stl: 80.5 x 14.5 x 12 mm; pinion.stl: 34.2 x 34.2 x 7.5 mm | 53 likes, 804 downloads |
| Printables | [Simple Rack and Pinion Focuser for Hadley Telescope](https://www.printables.com/model/241467-simple-rack-and-pinion-focuser-for-hadley-telescop) | CC-BY-NC | adapt OK, credit, non-commercial | no STL files | 95 likes, 628 downloads |
| Printables | [Rack and Pinion Gear - Educational Model](https://www.printables.com/model/792603-rack-and-pinion-gear-educational-model) | CC-BY-NC | adapt OK, credit, non-commercial | Pinion.stl: 48 x 47.2 x 23.6 mm; Rack1.stl: 200 x 17 x 10 mm; Bracket1.stl: 88.1 x 60 x 21.5 mm | 77 likes, 1535 downloads |
| Printables | [Rack and pinion stage module for Galileo Microscope](https://www.printables.com/model/767301-rack-and-pinion-stage-module-for-galileo-microscop) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | Lower rail.stl: 110 x 10.9 x 6 mm; Knob lower (x2).stl: 49.5 x 49.5 x 5 mm; Upper rail.stl: 76 x 10 x 6 mm | 134 likes, 458 downloads |
| Printables | [Rack and Pinion Steering](https://www.printables.com/model/229023-rack-and-pinion-steering) | CC-BY | adapt OK, credit | — | 138 likes, 1157 downloads |
| Printables | [Rack And Pinion](https://www.printables.com/model/322882-rack-and-pinion) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | — | 55 likes, 900 downloads |
| Printables | [Rack And Pinion Skeletonized](https://www.printables.com/model/323520-rack-and-pinion-skeletonized) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | — | 61 likes, 432 downloads |
| Printables | [Print in place Rack and Pinion Lid (Box file available on Patreon)](https://www.printables.com/model/955011-print-in-place-rack-and-pinion-lid-box-file-availa) | CC-BY-NC-ND | print as-is only (no remix) | — | 31 likes, 123 downloads |
| Printables | [Rack & Pinion Robotic Gripper Jaw (MG996R)](https://www.printables.com/model/403482-rack-pinion-robotic-gripper-jaw) | CC-BY | adapt OK, credit | measured STL: pinion 14T m1 (tip 16.3) x 6.5 face, pressed on the bare spline; rack 56 x 9.7 x 10.3; jaw 56 x 24 x 45; base 80 x 36 x 22; racks slide in printed base channels (no rods) |  |
| MakerWorld | [Rack & Pinion Robotic Gripper Jaw (same design as Printables 403482)](https://makerworld.com/models/940813) | not stated (page blocks scripted reads) | check license (not stated (page blocks scripted reads)) | read (search snippet): MG996R, both jaws on one pinion, 1.1 h print, 0.2 mm, 15% infill; 4.8 stars / 10 ratings |  |
| GitHub | [Robo9 SO-ARM100/101 parallel gripper](https://github.com/roboninecom/SO-ARM100-101-Parallel-Gripper) | CERN-OHL-P-2.0 (hardware) | adapt OK, credit | measured STL/read docs: pinion 18T m0.8 x ~6 face; racks 61 x 9.35 x 4.5; clamps 46 x 80 x 16 with 6.1 star bores 32 apart, 16 long; 2 rods 6x125; 84 mm stroke; 120 N; 170 g |  |
| Pololu | [Pololu Micro Gripper (servo pinion + opposing racks, commercial)](https://www.pololu.com/product/3551) | proprietary (drawing published) | check license (proprietary (drawing published)) | read drawing: 32 mm opening needs 0.5-2.4 ms pulses; 48.3 x 62.3 x 45.6 overall; paddles 30 long; POM |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com servo rack and pinion parallel jaw gripper for robot arm`
- web search: `site:grabcad.com/library servo rack and pinion parallel jaw gripper for robot arm`
- web search: `servo rack and pinion parallel jaw gripper for robot arm STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/servo-rack-and-pinion-parallel-jaw-gripper-for-robot-arm/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new, borrowing the layout and proportions of Robo9's SO-ARM101 parallel gripper (one pinion between two racks, both carriages on two shared rods; CERN-OHL-P-2.0) and Printables 403482 (MG996R rack-and-pinion jaw, CC BY, credited): neither fits the arm's wrist fork, horn and pivot or Kerf's module >= 1.5 rule, so no geometry is copied.

### `kerf find "servo parallel gripper rack and pinion"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [SG90 Parallel Robot Gripper Claw - 60 mm opening](https://www.printables.com/model/1871958-sg90-parallel-robot-gripper-claw-60mm-opening) | CC-BY | adapt OK, credit | read: 24T m0.7 pinion, ~26 mm per jaw for 180 deg, closes to ~7-10 mm, jaw faces ~33 x 36, 76 x 82 x 40 overall, M3 x 35 into heat-set inserts (STEP only, no STL) |  |
| Printables | [Dynamixel Parallel Gripper (GripSense, rack and pinion)](https://www.printables.com/model/1802484-dynamixel-parallel-gripper) | CC-BY-SA | adapt OK, credit, share-alike | measured STL: enclosure 130 x 55.9 x 51 (finger/gear STLs empty); read: fingers slide in a drafted printed rail, relief cuts snap above 3 kg, current limit 120 units |  |
| Printables | [Rack & Pinion Robotic Gripper Jaw (MG996R)](https://www.printables.com/model/403482-rack-pinion-robotic-gripper-jaw) | CC-BY | adapt OK, credit | see the first search: 14T m1 pinion, 56 mm racks in base channels |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com servo parallel gripper rack and pinion`
- web search: `site:grabcad.com/library servo parallel gripper rack and pinion`
- web search: `servo parallel gripper rack and pinion STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/servo-parallel-gripper-rack-and-pinion/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new, same as the first search: Robo9 / 403482 give the architecture, the part code is our own around the robot_arm wrist interface.

### `kerf find "MG996R gripper"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Arm Gripper MG996R v1](https://www.printables.com/model/1645415-arm-gripper-mg996r-v1) | CC0 | adapt OK, credit | bearing holder.stl: 81.3 x 46.4 x 19 mm; GripperBase.stl: 90.4 x 51.2 x 22.4 mm; holder.stl: 81.3 x 55.1 x 24.5 mm | 0 likes, 38 downloads |
| Printables | [Rack & Pinion Robotic Gripper Jaw (MG996R)](https://www.printables.com/model/403482-rack-pinion-robotic-gripper-jaw) | CC-BY | adapt OK, credit | measured STL: 14T m1 pinion x 6.5; rack 56 long; jaw 56 x 24 x 45; base 80 x 36 x 22 |  |
| MakerWorld | [Rack & Pinion Robotic Gripper Jaw (MakerWorld copy)](https://makerworld.com/models/940813) | not stated (page blocks scripted reads) | check license (not stated (page blocks scripted reads)) | read (search snippet): MG996R, 1.1 h print |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com MG996R gripper`
- web search: `site:grabcad.com/library MG996R gripper`
- web search: `MG996R gripper STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/mg996r-gripper/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new: 403482 proves an MG996R inline rack-and-pinion layout, but its pinion is pressed on the spline (users report it spinning), so ours bolts to the aluminium horn with 4 x M3.

### `kerf find "robot arm gripper parallel jaw"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Omron Adept6-Axes Robot Arm & Schunk Gripper PC-Max Interface](https://www.printables.com/model/1051-omron-adept6-axes-robot-arm-schunk-gripper-pc-max-) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | adept-6-axes-adapter.stl: 83.3 x 83.3 x 25 mm; schunk-grip-adapter.stl: 100 x 100 x 50 mm | 0 likes, 24 downloads |
| Printables | [3d Printed robot arm and gripper](https://www.printables.com/model/1362622-3d-printed-robot-arm-and-gripper) | CC-BY | adapt OK, credit | print in place gripper V4.stl: 139 x 99.9 x 33 mm; print in place gripper servocase.stl: 54.4 x 32 x 19 mm; Robot all in one joint.stl: 72 x 44 x 22 mm | 2 likes, 19 downloads |
| Printables | [XRP Robot Servo Arm with Grippers](https://www.printables.com/model/919002-xrp-robot-servo-arm-with-grippers) | CC0 | adapt OK, credit | Arm Linkage 2.stl: 46 x 6 x 4.9 mm; Base Arm Shaft.stl: 38 x 9.4 x 9.4 mm; Gripper Jaw.stl: 64.8 x 24 x 9 mm | 97 likes, 446 downloads |
| Printables | [Soft Touch Grippers for MOVEO Robot Arm](https://www.printables.com/model/784762-soft-touch-grippers-for-moveo-robot-arm) | CC-BY | adapt OK, credit | Gripper Right.stl: 55.7 x 20.8 x 18 mm; Gripper Left.stl: 55.7 x 20.8 x 18 mm | 19 likes, 56 downloads |
| Printables | [AR4 Robot Servo Gripper Small Enclosure](https://www.printables.com/model/1349275-ar4-robot-servo-gripper-small-enclosure) | CC-BY-SA | adapt OK, credit, share-alike | — | 1 likes, 11 downloads |
| Printables | [AR4 MK3 Robot Auxiliary Enclosure for Servo Gripper only](https://www.printables.com/model/1404143-ar4-mk3-robot-auxiliary-enclosure-for-servo-grippe) | CC-BY-NC | adapt OK, credit, non-commercial | — | 2 likes, 13 downloads |
| Printables | [robotic arm gripper assembly](https://www.printables.com/model/167131-robotic-arm-gripper-assembly) | CC-BY-SA | adapt OK, credit, share-alike | — | 72 likes, 605 downloads |
| Printables | [Robotic Arm Remix : Simple Gripper Design with Gear Ratio 2 and Customized for Hardware changes](https://www.printables.com/model/990682-robotic-arm-remix-simple-gripper-design-with-gear) | CC-BY-SA | adapt OK, credit, share-alike | — | 17 likes, 180 downloads |
| GitHub | [Robo9 SO-ARM100/101 parallel gripper](https://github.com/roboninecom/SO-ARM100-101-Parallel-Gripper) | CERN-OHL-P-2.0 (hardware) | adapt OK, credit | measured: 18T m0.8 pinion, 2 rods 6 x 125 (32 apart), clamps 16 long, MF106ZZ rollers back the racks; read: 84 stroke, 120 N, 170 g |  |
| Printables | [Parallel Gripper for EEZYbotARM MK2 (SG90, linkage)](https://www.printables.com/model/275802-parallel-gripper-for-eezybotarm-mk2) | CC-BY-NC | adapt OK, credit, non-commercial | measured STL: palm 43.2 x 58 x 26.2; finger 17.8 x 57.2 x 12.7; flexible pad 22.9 x 9.5 x 3.3 (printed in flex filament) |  |
| Printables | [AR Gripper (Feetech SM85CL, rack-and-slider, open hardware)](https://www.printables.com/model/657807-ar-gripper-open-hardware-adaptive-electric-paralle) | CC-BY | adapt OK, credit | measured STL: pinion 14T tip 18.2; slider 67.5 x 15.5 x 13.9; finger 32 x 90 x 44; read: 103 stroke, 570 g, foam rubber 2-3 mm + 3M grip tape pads |  |
| ROBOTIS | [ROBOTIS OpenManipulator-X gripper (crank + rail blocks, not rack)](https://emanual.robotis.com/docs/en/platform/openmanipulator_x/specification/) | proprietary docs (CAD published by ROBOTIS) | check license (proprietary docs (CAD published by ROBOTIS)) | read: stroke 20-75 mm, XM430-W350-T, 500 g arm payload, 2 rail blocks + crank arm + link rods, rubber pads x2 |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com robot arm gripper parallel jaw`
- web search: `site:grabcad.com/library robot arm gripper parallel jaw`
- web search: `robot arm gripper parallel jaw STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/robot-arm-gripper-parallel-jaw/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new: the wrist half must be the robot_arm gripper's own interface (projects/robot_arm/parts/gripper.py), which no published gripper has.

### `kerf find "gripper jaw pad"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [EEZYbot parallel gripper finger pad (flex filament)](https://www.printables.com/model/275802-parallel-gripper-for-eezybotarm-mk2) | CC-BY-NC | adapt OK, credit, non-commercial | measured STL: pad 22.9 x 9.5 x 3.3 mm |  |
| Printables | [AR Gripper pads (foam rubber + 3M gripping tape)](https://www.printables.com/model/657807-ar-gripper-open-hardware-adaptive-electric-paralle) | CC-BY | adapt OK, credit | read: foam rubber sheet 2-3 mm + double-sided tape + 3M gripping material gray 25 mm wide (~45 cm per gripper) |  |
| MakerWorld | [TPU V-groove vise jaws (not a gripper; pad idea only)](https://makerworld.com/models/1991237) | not stated (page blocks scripted reads) | check license (not stated (page blocks scripted reads)) | read (search snippet): TPU, V-groove for round/hex parts, 100 x 19 mm |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com gripper jaw pad`
- web search: `site:grabcad.com/library gripper jaw pad`
- web search: `gripper jaw pad STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/gripper-jaw-pad/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new: none of the finds fits our jaw; grip surface = V-ridged PETG pad face (meets the 150 g hold at mu 0.24 with 2.5x margin at half stall, DESIGN.md); a separately printed TPU 95A pad (2-3.5 mm, as the references use) is the documented upgrade.

### `kerf find "linear guide rod carriage printed"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [V-Spooler-X gantry linear rod guide](https://www.printables.com/model/1400599-v-spooler-x-gantry-linear-rod-guide) | CC0 | adapt OK, credit | rail_mount.stl: 28 x 14.6 x 10 mm; guide.stl: 34.7 x 19 x 16.5 mm | 2 likes, 12 downloads |
| Printables | [Creality Sprite Mount and cable guide for 3dFused linear rail mod to Ender 3](https://www.printables.com/model/325976-creality-sprite-mount-and-cable-guide-for-3dfused-) | CC-BY | adapt OK, credit | 3dFused_Creality_Sprite_Mount_V6.stl: 76.6 x 53.1 x 41.6 mm; Extruder_Cable_Support_V5.stl: 53.7 x 39.7 x 34.8 mm | 23 likes, 262 downloads |
| Printables | [TenLog D3-Pro Linear-Guide-Mod](https://www.printables.com/model/351946-tenlog-d3-pro-linear-guide-mod) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | LinGuide_Base2.stl: 110 x 16 x 6 mm; LinearGuidePlate_R2.stl: 140 x 55 x 8 mm; LinGuide_Base1.stl: 100 x 16 x 6 mm | 16 likes, 101 downloads |
| Printables | [Lineal guides Mod Anycubic Predator, Chema remix](https://www.printables.com/model/264596-lineal-guides-mod-anycubic-predator-chema-remix) | CC-BY | adapt OK, credit | guia_lineal.stl: 42 x 15 x 10 mm; patin_v4.stl: 70 x 39 x 10 mm; soporte_bltouch_v3.stl: 39.2 x 17.7 x 17 mm | 1 likes, 22 downloads |
| Printables | [X-End with square nuts for Prusa MIN linear guide mod](https://www.printables.com/model/807052-x-end-with-square-nuts-for-prusa-min-linear-guide) | CC-BY-SA | adapt OK, credit, share-alike | — | 3 likes, 25 downloads |
| Printables | [Afterburner - Stealthburner with BLtouch - x carriage Anet E10 X-Axis Guide Rod System](https://www.printables.com/model/589164-afterburner-stealthburner-with-bltouch-x-carriage-) | GPL 3.0 | adapt OK, credit, share-alike | — | 9 likes, 67 downloads |
| Printables | [Mod for the HevOrt printer for the x carriage HD9 toprail](https://www.printables.com/model/358454-mod-for-the-hevort-printer-for-the-x-carriage-hd9-) | CC-BY-NC | adapt OK, credit, non-commercial | — | 3 likes, 32 downloads |
| Printables | [Anycubic Chiron printed Y-Axis Linear Rail Mod Carriage Printbed](https://www.printables.com/model/1553230-anycubic-chiron-printed-y-axis-linear-rail-mod-car) | CC-BY | adapt OK, credit | — | 0 likes, 11 downloads |
| GitHub | [Robo9 gripper clamp (printed carriage on 2 rods)](https://github.com/roboninecom/SO-ARM100-101-Parallel-Gripper) | CERN-OHL-P-2.0 (hardware) | adapt OK, credit | measured STL: clamp 46 x 80 x 16, star bores for 6.0-6.3 rods (test plate 100 x 20 x 16.2 picks the size), bores 32 apart and 16 long |  |
| MakerWorld | [Parametric linear bushing (shaft d + height inputs)](https://makerworld.com/models/2530000) | not stated (page blocks scripted reads) | check license (not stated (page blocks scripted reads)) | read (search snippet): parametric shaft diameter and bushing height; no numbers |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com linear guide rod carriage printed`
- web search: `site:grabcad.com/library linear guide rod carriage printed`
- web search: `linear guide rod carriage printed STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/linear-guide-rod-carriage-printed/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new: Robo9's rod clamp is a proportion reference only (bore length vs rod diameter, printed fit-test plate); our carriages are sized by kerf's pin check and the jaw FEA.

### `kerf find "parallel gripper servo"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [SG90 Parallel Robot Gripper Claw - 60 mm opening](https://www.printables.com/model/1871958-sg90-parallel-robot-gripper-claw-60mm-opening) | CC-BY | adapt OK, credit | read: 24T m0.7, 26 mm/jaw per 180 deg |  |
| Printables | [Rack & Pinion Robotic Gripper Jaw (MG996R)](https://www.printables.com/model/403482-rack-pinion-robotic-gripper-jaw) | CC-BY | adapt OK, credit | measured: 14T m1 pinion, 56 mm racks |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com parallel gripper servo`
- web search: `site:grabcad.com/library parallel gripper servo`
- web search: `parallel gripper servo STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/parallel-gripper-servo/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new (duplicate of the first two searches; same finds, same reasoning).

### `kerf find "rack and pinion gripper"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Simple Rack and Pinion Focuser for Hadley Telescope](https://www.printables.com/model/241467-simple-rack-and-pinion-focuser-for-hadley-telescop) | CC-BY-NC | adapt OK, credit, non-commercial | no STL files | 95 likes, 628 downloads |
| Printables | [Rack and Pinion Gear - Educational Model](https://www.printables.com/model/792603-rack-and-pinion-gear-educational-model) | CC-BY-NC | adapt OK, credit, non-commercial | Pinion.stl: 48 x 47.2 x 23.6 mm; Rack1.stl: 200 x 17 x 10 mm; Bracket1.stl: 88.1 x 60 x 21.5 mm | 77 likes, 1535 downloads |
| Printables | [Rack and pinion stage module for Galileo Microscope](https://www.printables.com/model/767301-rack-and-pinion-stage-module-for-galileo-microscop) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | Lower rail.stl: 110 x 10.9 x 6 mm; Knob lower (x2).stl: 49.5 x 49.5 x 5 mm; Upper rail.stl: 76 x 10 x 6 mm | 134 likes, 458 downloads |
| Printables | [Rack and Pinion Steering](https://www.printables.com/model/229023-rack-and-pinion-steering) | CC-BY | adapt OK, credit | Gear.STL: 33.9 x 33.7 x 10 mm; Track_Middle.STL: 96.2 x 75 x 30 mm; Wheel.STL: 100 x 99.9 x 45 mm | 138 likes, 1157 downloads |
| Printables | [rack and pinion (Linear Servo Actuator)](https://www.printables.com/model/730367-rack-and-pinion-linear-servo-actuator) | CC-BY-NC | adapt OK, credit, non-commercial | — | 53 likes, 804 downloads |
| Printables | [Rack And Pinion](https://www.printables.com/model/322882-rack-and-pinion) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | — | 55 likes, 900 downloads |
| Printables | [Rack And Pinion Skeletonized](https://www.printables.com/model/323520-rack-and-pinion-skeletonized) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | — | 61 likes, 432 downloads |
| Printables | [Print in place Rack and Pinion Lid (Box file available on Patreon)](https://www.printables.com/model/955011-print-in-place-rack-and-pinion-lid-box-file-availa) | CC-BY-NC-ND | print as-is only (no remix) | — | 31 likes, 123 downloads |
| Printables | [Rack & Pinion Robotic Gripper Jaw (MG996R)](https://www.printables.com/model/403482-rack-pinion-robotic-gripper-jaw) | CC-BY | adapt OK, credit | measured: 14T m1 pinion, 56 mm racks |  |
| MakerWorld | [Rack And Pinion Parallel Grabber (DC BO motor)](https://makerworld.com/models/2188993) | restrictive (search snippet: no sharing of prints) | check license (restrictive (search snippet: no sharing of prints)) | read (search snippet): two racks + central pinion, BO gear motor, not self-locking |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com rack and pinion gripper`
- web search: `site:grabcad.com/library rack and pinion gripper`
- web search: `rack and pinion gripper STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/rack-and-pinion-gripper/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new (duplicate of the first two searches; same finds, same reasoning).
