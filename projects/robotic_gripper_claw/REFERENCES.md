# References — robotic_gripper_claw (symmetric geared two-finger claw for the desk robot arm)

Research 2026-10-31. Designs were measured from their published files (repos shallow-cloned to /tmp/refs, Printables
STLs downloaded through the Printables API, sections and bounding boxes with trimesh/ezdxf); "read" means the number is
stated on the linked page. MakerWorld, Thingiverse, MyMiniFactory and Instructables refused scripted access (403), so
only search-result snippets were available from them. Opening widths are not published for D1-D5 and cannot
be derived from unassembled part files; the only openings read are the commercial claw (50 mm, P11) and MakerWorld
940813's alternate jaw (~70 mm). Every design below is also a row in references/INDEX.md. The
`kerf find` search log (with its `Decision:` lines, left for the designer) is at the end.

## References

| # | Reference | Link | License | Why relevant (what was taken) |
|---|---|---|---|---|
| D1 | Robot Gripper (Lovro Jančić), Printables 912645, 144 likes | https://www.printables.com/model/912645-robot-gripper | CC BY-NC | Closest precedent: symmetric claw, each curved finger one piece with its own **14 T module-1.5 gear** (measured tip Ø24.06, root r 8.65), 6 mm gear face, Ø3.0 bore at the gear + coaxial Ø5.0 bore in a bottom hub 54 mm lower (axis held at both ends), drive finger on 4 horn screws (~17 mm circle), gear axis → tip 72.7, finger bar 7.6 thick; TPU 30D grip strips 2.2 thick with r 1.25 ribs at 2.5 pitch (flat back, glued, inferred) |
| D2 | Vector Concept Robot ARM CLAW (standard servo), Printables 1180059, 109 likes | https://www.printables.com/model/1180059-vector-concept-robot-arm-claw-standard-servo | CC0 | Top plate (73 × 50.8 × 8.2) + bottom plate (101 × 83.7 × 28.2) carry every pivot on both sides: precedent for the C-frame palm. 36 T gears (tip Ø40.3), 8 mm face, Ø6 bores, 8 × M3. Parallel four-bar, not a claw |
| D3 | MeArm V3 claw (laser-cut DXF + Instructions 3.0) | https://github.com/mearm/mearm | CC BY-SA 3.0 | The classic geared claw: 1:1 cog sectors in the fingers (centre distance 19.45, tip Ø21.5, root Ø14.6, 8 teeth per turn, not involute), drive finger on the horn, idler on a screw (Ø2.4 hole), **fingers sandwiched between the servo plate and a bottom plate** (instruction steps 20-22), gear axis → tip 43.7, three r 1.0 bumps at 2.46 pitch at the tip |
| D4 | EEZYbotARM MK2 claw STLs (rookidroid/armstrong mirror) | https://github.com/rookidroid/armstrong | not stated (original licence not opened) | Module 1.5 printed gears on an SG90 (drive 10 T, tip Ø18.1, 5 thick; driven 16 T, 7 thick); fingers 3 mm plate + 9 mm flange on M3 pivots (Ø3.2) **in one base plate only**; pivot → tip 47-49 |
| D5 | Arm Gripper MG996R v1, Printables 1645415 | https://www.printables.com/model/1645415-arm-gripper-mg996r-v1 | CC0 | MG996R gripper sized with 12 T **module 2, 15 mm wide** gears (tip Ø28.1) on M3 (Ø3.3); serrated hard jaws, no pad |
| D6 | Rack & Pinion Robotic Gripper Jaw (MG996R), MakerWorld 940813 (= Printables 403482, already in INDEX) | https://makerworld.com/models/940813 | MakerWorld page not readable; Printables copy CC BY | Failure lesson: a printed pinion pressed onto the bare MG996R spline spun (user comment) → drive finger must bolt to the metal 25T horn |
| D7 | Clamp-On Vise, Printables 1140362, 2099 likes | https://www.printables.com/model/1140362-clamp-on-vise-fully-3d-printable | CC BY-NC-ND (numbers only) | Proven slide-in **TPU dovetail pad**: TPU grip = 2.0 base + 3.75 rib, neck 5.06 → 6.96 (~19° flanks); printed slot 5.38 → 7.34, 3.9 deep: **~0.15-0.2 mm per side, 0.15 mm at the bottom** (measured) |
| D8 | Robotic Claw Pads (SparkFun Claw MkII), Printables 127059 | https://www.printables.com/model/127059-robotic-claw-pads | CC BY-SA | Alternative pad: hard printed carrier pinned to the jaw + mouse-pad rubber on double-stick tape |
| P1 | Suder et al. 2021, MM Science Journal, DOI 10.17973/MMSJ.2021_12_2021127 | https://www.mmscience.eu/2021127 | not stated (open access) | Measured μ against a steel object (15/35/50 N per jaw): **printed PLA jaws 0.15-0.21; TPU 30D knurled 0.69-0.79; TPU 30D smooth 0.46-0.61; TPE 88 knurled 0.31-0.51; TPE 88 smooth 0.25-0.39**; slide-in replaceable inserts, 100 % infill, 0.2 mm layers, 2 perimeters; no slip in 500 robot cycles |
| P2 | Stoimenov et al. 2024, Tribology in Industry 46(1):97-106 | https://www.tribology.rs/journals/2024/2024-1/2024-1-09.html | CC BY-NC | Printed **PETG on steel, dry: static μ 0.27 / 0.24 / 0.29** at 30 / 50 / 70 N, kinetic 0.20 / 0.18 / 0.26; PLA static 0.30 / 0.22 / 0.20 |
| P3 | Engineering ToolBox friction table | https://engineeringtoolbox.com/friction-coefficients-d_778.html | not stated | Rubber on cardboard 0.5-0.8, rubber on rubber 1.16, glass on metal 0.5-0.7, polyethylene on steel 0.2 (no TPU/glass/aluminium polymer pairs) |
| P4 | Gallagher, Polyurethane's Coefficient of Friction | https://gallaghercorp.com/polyurethane-coefficient-of-friction/ | not stated | Harder polyurethane → lower COF; kinetic 0.2-2.5 overall: TPU 95A will grip less than the 30D/88A Suder tested |
| P5 | Modern Robotics (Lynch and Park) §12.2.1 | https://modernrobotics.northwestern.edu/nu-gm-book-resource/12-2-1-friction/ | not stated | Friction angle α = tan⁻¹ μ (friction cone) → jaw-angle rule below |
| P6 | gearpy Lewis form factor table (20°) | https://gearpy.readthedocs.io/en/latest/mechanical_objects/SpurGear/lewis_factor.html | not stated | Y = 0.276 (14 T), 0.289 (15 T), 0.295 (16 T) |
| P7 | Sovol, 3D Printing Gears That Actually Work | https://www.sovol3d.com/blogs/news/3d-printing-gears-that-actually-work-backlash-orientation-and-material-tips | not stated | Module 1.5-2.0 for a 0.4 mm nozzle; 0.2-0.4 mm total flank clearance; face 3-5 × circular pitch; 4-6 walls; print flat for tooth accuracy; PETG teeth flex rather than snap |
| P8 | MG996R TowerPro datasheet (Cornell copy) + towerpro.com.tw product page | https://people.ece.cornell.edu/land/courses/ece4760/FinalProjects/f2017/kmv48_rp625/kmv48_rp625/kmv48_rp625/MG996RTowerPro.pdf | not stated | Datasheet: "Metal Gear Dual Ball Bearing Servo", stall 9.4 kgf·cm (4.8 V) / 11 (6 V), stall current 2.5 A (6 V); **no radial or side-load figure**. The current TowerPro product page mentions no bearings at all |
| P9 | Gogo:Tronics, MG996R bearing change | https://sparks.gogo.co.nz/servo/bmg996r-bearing-change.html | not stated | Clone MG996Rs: metal bushing at the top of the output shaft, plastic bushing at the bottom (no ball bearings); upgrade MR106 6 × 10 × 2.5. No load figure |
| P10 | Pololu forum, gripper servo very hot when closed (2020) | https://forum.pololu.com/t/micro-gripper-kit-with-position-feedback-servo-servo-is-very-hot-when-the-gripper-is-closed/18765 | not stated | Holding an object at stall: servo "very hot in 2 or 3 minutes"; fix = back the target off to just under the object width after contact |
| P11 | ThinkRobotics metal MG996R claw (commercial benchmark) | https://thinkrobotics.com/products/mechanical-claw-for-robot-arm-with-mg996r-servo-online | proprietary | Aluminium claw for this servo class: 50 mm maximum opening, 60 g (read). Our ≥ 60 mm target is above it |
| C | Kerf catalog: servos.MG996R, servo_horns.aluminum_25T, motion.pin_3mm, fdm_fits.pin, materials.PETG / TPU | catalog/hardware.json | — | Stall 9.4 kg·cm = 0.922 N·m; horn 4 × M3 on 14 mm circle; dowel 3.0 m6; press +0.05 / free +0.35 on diameter; PETG 48 MPa XY; TPU 95A (Bambu TDS) |

## Decisions this supports

1. **Architecture: 1:1 geared fingers, both finger axes held at both ends in a two-plate palm.** Precedents: MeArm V3
   (servo plate + bottom plate, D3), Vector Concept (top + bottom plates, D2), Printables 912645 (coaxial bores 54 mm
   apart, D1). The single-plate EEZYbot claw (D4) is the outlier. Kerf rule ENGINEERING.md §8 (servo output carries
   torque only) and the MG996R facts below say the same.

2. **The MG996R must not carry the drive finger's side load.** No source gives a radial or side-load rating (P8, P9);
   the datasheet claims "dual ball bearing", but clones use a bronze bushing on top and a plastic one below (P9). Loads
   at stall (calculated): contact force up to 8.4 N plus the gear mesh force (tangential 41 N in a symmetric grip,
   82 N if the idler finger is blocked alone; separating force = tangential × tan 20° = 15-30 N). Put a coaxial M3
   pivot in the opposite plate (as on the arm's forks) and keep the gear close to a supported plate.

3. **Drive finger bolts to the 25T aluminium horn (4 × M3 on 14 mm), never a printed gear on the bare spline.** D6
   reports a pressed-on printed pinion spinning on the MG996R spline. At stall each horn screw sees 0.922 N·m /
   (4 × 7 mm) = 33 N of shear (calculated): trivial for steel M3.

4. **Gear: module 1.5, 15-16 teeth, face ≥ 8 mm, printed flat.** Module 1.5 matches D1 (14 T) and D4 (10/16 T) and
   P7 / ENGINEERING.md §8 (module ≥ 1.5, ≥ 10 teeth, 0.3 mm total backlash). Centre distance for a 1:1 pair = m·z:
   21.0 / 22.5 / 24.0 mm for 14 / 15 / 16 T. Lewis tooth bending, worst case = whole stall torque through the mesh
   (idler finger blocked alone), σ = F_t / (b·m·Y), Y from P6, PETG 48 MPa XY (teeth printed flat), SF ≥ 2 for static
   XY load (ENGINEERING.md §3):

   | teeth | pitch r | F_t at stall | b = 6 mm | b = 8 mm | b = 10 mm |
   |---|---|---|---|---|---|
   | 14 | 10.5 mm | 87.8 N | 35.3 MPa, SF 1.36 | 26.5 MPa, SF 1.81 | 21.2 MPa, SF 2.26 |
   | 15 | 11.25 mm | 81.9 N | 31.5 MPa, SF 1.52 | 23.6 MPa, SF 2.03 | 18.9 MPa, SF 2.54 |
   | 16 | 12.0 mm | 76.8 N | 28.9 MPa, SF 1.66 | 21.7 MPa, SF 2.21 | 17.4 MPa, SF 2.76 |

   So 15-16 teeth with an 8 mm face (or 14 teeth with 10 mm) meets SF 2 even at stall; D1 runs 14 T × 6 mm in real
   use, which is the empirical floor. Sovol's 3-5 × circular pitch (14-24 mm at m1.5, P7) is a conservative rule the
   precedents all ignore. 4-6 walls in the gear zone (P7).

5. **Squeeze force halves compared with the old single-finger gripper; size it.** One servo drives two fingers, so
   per-finger squeeze F = T / (2 r_c) (virtual work; r_c = gear axis to contact point). MG996R stall 0.922 N·m: 8.4 N
   at 55 mm, 10.2 N at 45 mm (old gripper: 18.4 N at its 50 mm tip, one finger against a fixed jaw, robot_arm
   DESIGN.md). At the arm's ≤ 50 %-of-stall rule: 4.2 N at 55 mm, 5.1 N at 45 mm, 5.8 N at 40 mm.

6. **Pads must be TPU, and contact should sit ≤ ~45 mm from the gear axis.** Holding 150 g (1.47 N) hanging between
   the pads needs 2 μ F ≥ SF × 1.47 N. Safety factor at 50 % of stall (calculated from 5.):

   | μ (source) | r_c 40 mm | 45 mm | 50 mm | 55 mm |
   |---|---|---|---|---|
   | 0.15 printed PLA jaws on steel (P1) | 1.17 | 1.04 | 0.94 | 0.85 |
   | 0.24 printed PETG on steel (P2) | 1.88 | 1.67 | 1.50 | 1.37 |
   | 0.30 assumed TPU 95A design value (between TPE 88 knurled 0.31 and PETG 0.29) | 2.35 | 2.09 | 1.88 | 1.71 |
   | 0.46 TPU 30D smooth, lowest (P1) | 3.60 | 3.20 | 2.88 | 2.62 |
   | 0.69 TPU 30D knurled, lowest (P1) | 5.40 | 4.80 | 4.32 | 3.93 |

   ENGINEERING.md §3 has no friction-hold row: SF 2 is proposed by analogy with its static-load (XY) row.
   Bare PETG or serrated PETG cannot reach SF 2 within the 50 % budget; TPU pads can if the contact centre is
   ≤ 45 mm from the gear axis (55 mm fingers: put the pad on the inner part, the hooked tip beyond it). Knurled/ribbed
   faces beat smooth (P1: 0.69-0.79 vs 0.46-0.61): ribs ~r 1.0-1.25 at ~2.5 pitch (D1, D3), running across the
   direction the object would slip (horizontal when the gear axes are vertical).

7. **Pad retention: slide-in TPU 95A dovetail, no glue.** D7's measured fit: 2.0 mm base under the face, 3.75 mm
   rib, neck ~5.1 widening to ~7.0 (~19° flanks), slot 0.15-0.2 mm larger per side and 0.15 mm deeper. P1 also used
   slide-in replaceable inserts. Run the slot along the finger (perpendicular to the gear axis, so the object's weight
   loads the dovetail sideways, not along it), close it at one end and slide the pad in from the other, held by the
   hooked tip or a screw. Alternatives: glued strips (D1), rubber on tape (D8).

8. **Jaw angle: keep the pad faces within ±16.7° of parallel (μ 0.3), or converging toward the tips.** P5 gives the
   friction angle α = tan⁻¹ μ; an object between two faces that open toward the tips at half-angle θ is squeezed out
   when tan θ > μ (derived: normal-force component along the V, N sin θ, exceeds the friction limit μ N cos θ).
   α = 13.5° (μ 0.24, PETG), 16.7° (0.30), 24.7° (0.46), 34.6° (0.69). With 1:1 fingers each face turns with the
   servo: Δφ ≈ (w − w₀) / (2 r_c); faces parallel at w₀ ≈ 35 mm with r_c 50 mm keeps 10-60 mm objects within ±14.3°
   (calculated). Curved / hooked tips (D1, D3) make the faces converge for small objects and add a geometric stop.

9. **Idler finger on the 3 mm steel dowel, pressed in both palm plates.** catalog motion.pin_3mm (ISO 8734 m6),
   fdm_fits.pin: press hole 3.05 in the plates, free bore 3.35 in the finger; 0.5 mm axial clearance / washers
   (ENGINEERING.md §8). Precedents ran on screws in plastic: MeArm Ø2.4 (D3), EEZYbot Ø3.2 (D4), D1 Ø3.0 + Ø5.0.

10. **Opening ≥ 60 mm is above the commercial benchmark (50 mm, P11) and needs ~±15-25° of finger swing**: each finger
    turns with the servo 1:1, so the MG996R's ~120° at 1000-2000 µs (catalog note) is ample. D1 reaches 72.7 mm from
    axis to tip; MeArm 43.7 and EEZYbot 47-49 are shorter, lighter-duty claws.

11. **Grip control: never hold at stall.** P10: a gripper servo held at stall got "very hot in 2 or 3 minutes"; the
    MG996R stalls at 2.5 A (6 V). Close to contact, then hold a target just past the object width (≤ 50 % stall); this
    is also why 6. uses the 50 % figure.

## Open questions

1. **μ of Bambu TPU 95A against the real objects is not published.** All μ data above is against steel and for
   softer elastomers (TPU 30D ≈ low-80s Shore A, TPE 88A); P4 says harder PU grips less. Tilt-test a printed pad
   (μ = tan of the slip angle) against plastic, cardboard, an aluminium can and glass before fixing the contact radius.
   If μ < 0.3, print the pad in a softer TPU or move the contact closer to the axis (table in 6.).
2. TPU or rubber against glass, aluminium and plastic: nothing found beyond Engineering ToolBox's rubber-cardboard
   0.5-0.8 and glass-metal 0.5-0.7 (P3).
3. Inertial loads while the arm moves (the object accelerating at the TCP) are not quantified; SF 2 on friction is
   assumed to cover them.
4. Which MG996R Spencer has (ball bearings or bushings, P9) is unknown; the design must not rely on either.
5. Gear face: 6 mm is proven in use (D1), 8-10 mm is what Lewis asks at worst-case stall (4.): choose from the palm
   height available between the plates.
6. Comments on Printables 912645 / 1180059 were not read (no failure data); MakerWorld, Thingiverse, MyMiniFactory and
   Instructables pages were blocked; EEZYbotARM MK2's original licence (Thingiverse thing:1454048) is unverified.

## Existing designs (kerf find)

### `kerf find "robot claw gripper MG996R"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Robot Gripper Claw (100% 3D Printed)](https://www.printables.com/model/1285991-robot-gripper-claw-100-3d-printed) | Standard Digital File | print as-is only (no remix) | Base Piece - Print One.stl: 350 x 150 x 40 mm; Claw Piece - Print Two.stl: 150 x 100 x 21 mm; Short Connector - Print Four.stl: 92.5 x 60 x 9 mm | 20 likes, 100 downloads |
| Printables | [SG90 Parallel Robot Gripper Claw – 60mm Opening](https://www.printables.com/model/1871958-sg90-parallel-robot-gripper-claw-60mm-opening) | CC-BY | adapt OK, credit | no STL files | 3 likes, 36 downloads |
| Printables | [Vector Concept Robot ARM CLAW (standard servo) - 109 likes](https://www.printables.com/model/1180059-vector-concept-robot-arm-claw-standard-servo) | CC0 | adapt OK, credit | measured: gear-link 36 T, tip dia 40.3 (about m1.06), 8 mm face, 6.0 bore; finger 82.2 x 34.1 x 22.4; top plate 73 x 50.8 x 8.2 and bottom plate 101 x 83.7 x 28.2 carry every pivot on both sides; parallel four-bar fingers, gears couple the two gear-links 1:1; 8 x M3 |  |
| Printables | [Arm Gripper MG996R v1](https://www.printables.com/model/1645415-arm-gripper-mg996r-v1) | CC0 | adapt OK, credit | measured: spur 12 T m2.0 (tip dia 28.1), 15 mm face, 3.3 bore on an M3 screw, one piece with a 50 mm link (four-bar); finger 59.7 x 21.4 x 20.1 with a serrated face; 6203RS bearing holder |  |
| MakerWorld | [Rack & Pinion Robotic Gripper Jaw (MG996R)](https://makerworld.com/models/940813) | not opened (MakerWorld 403) | check license (not opened (MakerWorld 403)) | read (search snippet only): MG996R pinion drives both parallel jaws by racks; alternate jaw about 70 mm open, closes to about 22 mm; 0.2 mm layers, 2 walls, 15 % infill; a maker's pinion spun on the spline (2019 comment) |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com robot claw gripper MG996R`
- web search: `site:grabcad.com/library robot claw gripper MG996R`
- web search: `robot claw gripper MG996R STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/robot-claw-gripper-mg996r/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new, proportions borrowed. No hit fits the contract: the claw must bolt onto the arm's own wrist (25T horn + M3 pivot, 35 mm fork) and the arm's grip MG996R; the CC0 hits (Vector Concept 1180059, 1645415) are four-bar / single-plate grippers with other servo mounts, and 940813 is rack-and-pinion with an unreadable licence. Taken as numbers only: the two-plate support of every pivot (1180059) and the lesson to bolt the drive to the metal horn (940813).

### `kerf find "servo gripper gear fingers"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Robot Gripper (Lovro Jancic) - 144 likes](https://www.printables.com/model/912645-robot-gripper) | CC-BY-NC | adapt OK, credit, non-commercial | measured: two curved claw fingers 73.4 x 51 x 60, each with its own 14 T m1.5 gear (tip dia 24.06, root r 8.65), 6 mm face on top of the finger, 3.0 bore; gear axis to tip 72.7; finger bar 7.6 thick; TPU (Fiberflex 30D) strips 60 x 8.5 x 2.2, flat back, r 1.25 ribs at 2.5 pitch |  |
| GitHub | [MeArm V3 claw (laser-cut DXF)](https://github.com/mearm/mearm) | CC-BY-SA-3.0 | adapt OK, credit, share-alike | measured (DXF): two gear-sector fingers 1:1, centre distance 19.45, tip dia 21.5, root dia 14.6, 8 cog teeth per turn (not involute), 3 mm acrylic; drive finger on the horn, idler on a 2.4 hole; gear axis to tip 43.7; three r 1.0 bumps at 2.46 pitch near the tip |  |
| GitHub | [EEZYbotARM MK2 claw STLs (rookidroid/armstrong mirror)](https://github.com/rookidroid/armstrong) | not stated | check license (not stated) | measured: SG90 drive gear 10 T m1.5 (tip dia 18.1), 5 thick; driven gear 16 T m1.5 (tip r 13.5), 7 thick; fingers 3 mm plate + 9 mm flange, pivots 3.2 (M3), pivot to tip 47-49; claw base 54 x 25 x 25, one plate under the fingers |  |
| MakerWorld | [3D Printed Servo Gripper (gear-driven four-bar)](https://makerworld.com/models/2189961) | not opened (MakerWorld 403) | check license (not opened (MakerWorld 403)) | read (search snippet only): spur-gear-driven four-bar clamp; servo limited to 35-120 deg (120 = fully open) |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com servo gripper gear fingers`
- web search: `site:grabcad.com/library servo gripper gear fingers`
- web search: `servo gripper gear fingers STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/servo-gripper-gear-fingers/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new with kerf.drives.spur_pair (involute m1.5 16:16, 12 mm face). 912645 (CC BY-NC) and MeArm (CC BY-SA) are the right precedents but their licences and servo mounts do not fit; ideas and numbers only (gear module, both finger axes held at both ends, the curved finger with the gear in the same piece). EEZYbot's single-plate pivots are what we avoid.

### `kerf find "gripper TPU finger pad"` (2026-10-31)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [TPU straps for swimming finger paddles](https://www.printables.com/model/692385-tpu-straps-for-swimming-finger-paddles) | CC-BY-SA | adapt OK, credit, share-alike | no STL files | 16 likes, 71 downloads |
| Printables | [Clamp-On Vise - TPU grips in dovetail slots (2099 likes)](https://www.printables.com/model/1140362-clamp-on-vise-fully-3d-printable) | CC-BY-NC-ND | print as-is only (no remix) | measured: TPU grip 75 x 27.5 x 5.8 = 2.0 base + 3.75 dovetail rib, neck 5.06 widening to 6.96 (about 19 deg flanks); jaw slot 5.38 at the face widening to 7.34, 3.9 deep: about 0.15-0.2 mm per side and 0.15 mm depth clearance; slides in from the end |  |
| Printables | [Robotic Claw Pads (SparkFun Claw MkII)](https://www.printables.com/model/127059-robotic-claw-pads) | CC-BY-SA | adapt OK, credit, share-alike | measured: 15 x 15 x 9.5 = 2 mm plate with two 2 mm half-round ears (r 7.5) each with a 3 x 3 square hole that pins onto the jaw; read: friction face is mouse-pad rubber on double-stick tape |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com gripper TPU finger pad`
- web search: `site:grabcad.com/library gripper TPU finger pad`
- web search: `gripper TPU finger pad STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/gripper-tpu-finger-pad/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new pad (TPU 95A, ribbed face, dovetail slid DOWN into the jaw onto a bottom stop) redrawn from the measured vise numbers (2.0 base, ~19° flanks, 0.15-0.2 mm per side): the vise is CC BY-NC-ND, so no geometry is copied, only the fit allowances; SparkFun's glued mouse-pad rubber (127059) was rejected because adhesive pads peel at the edges under shear.
