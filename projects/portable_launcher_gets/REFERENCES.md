# References

## Existing designs (kerf find)

### `kerf find "bungee launcher rc plane"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [mig 21 missle pod launcher rc plane  1/6 model can be scale down](https://www.printables.com/model/1804053-mig-21-missle-pod-launcher-rc-plane-16-model-can-b) | CC-BY-NC-ND | print as-is only (no remix) | no STL files | 3 likes, 3 downloads |
| Printables | [RC Plane Launcher Parts](https://www.printables.com/model/1704290-rc-plane-launcher-parts) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | pulleyspindle_v1.stl: 70 x 70 x 50 mm; efx_wing_support_v5.stl: 109.2 x 70 x 22.9 mm; 50_metal_conduit_internal_coupler_r1_4w_100pct_w_hole.stl: 65 x 18 x 15.8 mm | 2 likes, 6 downloads |
| Printables | [RC Car RC plane Launch System](https://www.printables.com/model/525457-rc-car-rc-plane-launch-system) | CC-BY | adapt OK, credit | top.stl: 86.1 x 30.2 x 10 mm; Wing_Support.stl: 161.1 x 55 x 20 mm; bottom.stl: 80 x 50 x 12.9 mm | 20 likes, 46 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com bungee launcher rc plane`
- web search: `site:grabcad.com/library bungee launcher rc plane`
- web search: `bungee launcher rc plane STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/bungee-launcher-rc-plane/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: DESIGN NEW (architecture fixed). Nothing found is a rail + V-wheel sled + latex-over-pulley launcher. Only the cradle idea is borrowed: the CC-BY RC Car RC plane Launch System (Wing_Support 161.1 x 55 x 20 mm, top 86.1 x 30.2 x 10, bottom 80 x 50 x 12.9) shows a plain wing-support block under the wing; credit it if its proportions are reused. RC Plane Launcher Parts is CC-BY-NC-SA: ideas only (pulley spindle 70 x 70 x 50 mm, wing support 109.2 x 70 x 22.9). The real references are the published launchers in the table below.

### `kerf find "v-slot wheel carriage sled"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| — | nothing found | | | | |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com v-slot wheel carriage sled`
- web search: `site:grabcad.com/library v-slot wheel carriage sled`
- web search: `v-slot wheel carriage sled STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/v-slot-wheel-carriage-sled/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: DESIGN NEW. No open sled for a 2040 rail exists. Rail section from bd_warehouse.open_builds.VSlotLinearRailProfile('20x40') (Apache-2.0, already in the venv; verified against vendor numbers, see catalog motion.vslot_2040) and wheel stack from catalog motion.vwheel_delrin_solid: axle 10.0 mm off the rail face, 40.0 mm centre to centre across the 20 mm width, 7.12 mm eccentric hole in one wheel per side for preload.

### `kerf find "rope pulley bearing"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Pulley block (soft mount) for 7-8mm OD rope and 608 bearings](https://www.printables.com/model/919046-pulley-block-soft-mount-for-7-8mm-od-rope-and-608) | CC-BY-SA | adapt OK, credit, share-alike | bearing_rope_trace_8mm.STL: 28.7 x 28.7 x 10 mm; Pulley_Block.STL: 50 x 30.5 x 30 mm | 15 likes, 74 downloads |
| Printables | [Basic Pulley (2x 608 bearing, 2x M4x30mm, 12mm rope)](https://www.printables.com/model/161642-basic-pulley-2x-608-bearing-2x-m4x30mm-12mm-rope) | CC-BY | adapt OK, credit | Pulley-stator.stl: 77.5 x 50 x 15 mm; Pulley-rotor.stl: 50 x 50 x 20 mm | 7 likes, 52 downloads |
| Printables | [Strong Single and Double Pulley for rope (608 bearings)](https://www.printables.com/model/440677-strong-single-and-double-pulley-for-rope-608-beari) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | Wheel.stl: 45.9 x 45.9 x 15.9 mm; FrameDual.stl: 143.1 x 44 x 35.7 mm; FrameSingle.stl: 143.1 x 35.7 x 26 mm | 37 likes, 219 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com rope pulley bearing`
- web search: `site:grabcad.com/library rope pulley bearing`
- web search: `rope pulley bearing STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/rope-pulley-bearing/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: ADAPT concept, DESIGN NEW part. Printed rope pulleys on 608 bearings exist (CC-BY Basic Pulley: rotor 50 x 50 x 20 mm, stator 77.5 x 50 x 15; CC-BY-SA Pulley Block soft mount 50 x 30.5 x 30; CC-BY-NC-SA Strong Single/Double Pulley wheel 45.9 x 15.9). All are for 7-12 mm rope and 608 bearings; ours carries 1-4 latex strands (8 mm OD each, 32 mm total width flat) and sits at the nose where the sled stops, so design a wide sheave on catalog 625 bearings (or 608) with the groove sized for the strand bundle, sheave diameter >= 40 mm (Basic Pulley 50 mm class) to keep the latex bend gentle. Share-alike and NC licences mean no geometry copied, only the proportions.

### `kerf find "release latch trigger"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| — | nothing found | | | | |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com release latch trigger`
- web search: `site:grabcad.com/library release latch trigger`
- web search: `release latch trigger STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/release-latch-trigger/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: DESIGN NEW. Nothing on Printables for a launcher trigger. Mechanism references are patent/commercial: NASA US6851647 uses a self-actuating trigger (contact with the carrier springs a latch) plus a safety pin removed before launch; Ukrspecsystems SCL-2 uses a safety pin and a remote release; the diydrones Talon catapult releases by pulling a 5 m trigger line off a ground hook. Ours (safety pin + foot pedal) matches that practice: keep the pedal line long enough to stand clear of the prop, and test the release empty first (Unmanned Tech Shop).

### `kerf find "2040 extrusion hinge"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [2020 Extrusion Hinge for Voron Fridge Door mod](https://www.printables.com/model/249299-2020-extrusion-hinge-for-voron-fridge-door-mod) | CC-BY | adapt OK, credit | hinge_door_side.stl: 60 x 25 x 10 mm; hinge_door_side_no_holes.stl: 60 x 25 x 10 mm; hinge_frame_side.stl: 60 x 18 x 10 mm | 57 likes, 254 downloads |
| Printables | [2020 Extrusion Pivot/Hinge](https://www.printables.com/model/506305-2020-extrusion-pivothinge) | GPL 3.0 | adapt OK, credit, share-alike | PivotBall.stl: 21.1 x 21.1 x 13.5 mm; HingeBody_BHCS.stl: 60 x 31 x 31 mm; HingeBody_HeatSet.stl: 60 x 31 x 31 mm | 140 likes, 474 downloads |
| Printables | [2020 Extrusion Pivot/Hinge - 90deg](https://www.printables.com/model/506313-2020-extrusion-pivothinge-90deg) | GPL 3.0 | adapt OK, credit, share-alike | PivotBall.stl: 21.1 x 21.1 x 13.5 mm; HingeBody_90_thru.stl: 60 x 46 x 31 mm; HingeBody_inline-long_heatset.stl: 80 x 31 x 31 mm | 108 likes, 381 downloads |
| Printables | [2020 Extrusion - Pivot/Hinge - Midspan](https://www.printables.com/model/513523-2020-extrusion-pivothinge-midspan) | GPL 3.0 | adapt OK, credit, share-alike | PivotBall.stl: 21.1 x 21.1 x 13.5 mm; HingeBody_BHCS.stl: 60 x 31 x 31 mm; HingeBody_Midspan.stl: 60 x 60 x 31 mm | 67 likes, 326 downloads |
| Printables | [Print In Place Trapped Hinge for 2020 Extrusions](https://www.printables.com/model/705960-print-in-place-trapped-hinge-for-2020-extrusions) | CC-BY-SA | adapt OK, credit, share-alike | — | 17 likes, 128 downloads |
| Printables | [Removable door hinges for voron or any 2020 extrusions](https://www.printables.com/model/426447-removable-door-hinges-for-voron-or-any-2020-extrus) | CC-BY | adapt OK, credit | — | 24 likes, 154 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com 2040 extrusion hinge`
- web search: `site:grabcad.com/library 2040 extrusion hinge`
- web search: `2040 extrusion hinge STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/2040-extrusion-hinge/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: DESIGN NEW hinge blocks, borrow ideas only. The 2020 Pivot/Hinge family (GPL-3.0: PivotBall 21.1 x 21.1 x 13.5 mm, HingeBody 60 x 31 x 31 mm) is GPL so no geometry copied; Voron door hinge (CC-BY, 60 x 25 x 10 mm) is a door hinge for 20 mm extrusion, not a rail splice. Rail joint practice: NASA US6851647 hinges the track centrally and locks the extended track with a lever and locking pin or a sliding locking plate. Our joint must also keep the wheel running surface continuous across the gap: no source found for the wheel bump at a joint, see Open questions.

### `kerf find "rc plane launcher cradle"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [RC Plane Launcher Parts](https://www.printables.com/model/1704290-rc-plane-launcher-parts) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | pulleyspindle_v1.stl: 70 x 70 x 50 mm; efx_wing_support_v5.stl: 109.2 x 70 x 22.9 mm; 50_metal_conduit_internal_coupler_r1_4w_100pct_w_hole.stl: 65 x 18 x 15.8 mm | 2 likes, 6 downloads |
| Printables | [mig 21 missle pod launcher rc plane  1/6 model can be scale down](https://www.printables.com/model/1804053-mig-21-missle-pod-launcher-rc-plane-16-model-can-b) | CC-BY-NC-ND | print as-is only (no remix) | no STL files | 3 likes, 3 downloads |
| Printables | [RC Car RC plane Launch System](https://www.printables.com/model/525457-rc-car-rc-plane-launch-system) | CC-BY | adapt OK, credit | top.stl: 86.1 x 30.2 x 10 mm; Wing_Support.stl: 161.1 x 55 x 20 mm; bottom.stl: 80 x 50 x 12.9 mm | 20 likes, 46 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com rc plane launcher cradle`
- web search: `site:grabcad.com/library rc plane launcher cradle`
- web search: `rc plane launcher cradle STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/rc-plane-launcher-cradle/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: ADAPT proportions, DESIGN NEW. RC Car RC plane Launch System is CC-BY (credit): Wing_Support 161.1 x 55 x 20 mm shows the scale of a foam-wing support pad. Hook placement from diydrones: the hook sits at or just forward of the CG, mounted on a rigid (ply or aluminium) base, never on foam alone; too far forward and the plane flips, too far back it stalls. A swappable cradle must bring the hook point and wing-support points to the plane's CG line for each of pusher/tractor and high/low wing.

### `kerf find "tripod bipod head tube clamp"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Front Reflector Clamp for a Bicycle Head Tube](https://www.printables.com/model/1737699-front-reflector-clamp-for-a-bicycle-head-tube) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | Bike Front Reflector Clamp.stl: 99 x 75.1 x 35.5 mm | 0 likes, 12 downloads |
| Printables | [10° 2-axis up to 29.6mm tube lamps, for 90mm lamp head](https://www.printables.com/model/164001-10deg-2-axis-up-to-296mm-tube-lamps-for-90mm-lamp-) | CC0 | adapt OK, credit | 4.stl: 10 x 10 x 4.4 mm; 3.stl: 82.2 x 41 x 15.3 mm; 1.stl: 2.9 x 2.5 x 1.2 mm | 0 likes, 16 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com tripod bipod head tube clamp`
- web search: `site:grabcad.com/library tripod bipod head tube clamp`
- web search: `tripod bipod head tube clamp STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/tripod-bipod-head-tube-clamp/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: DESIGN NEW. No usable open design. Legs are 20 x 1.5 mm aluminium tube (catalog rods.alu_tube_20x1_5): a printed head clamps two tubes and the rail. NASA US6851647 uses a bi-pod stand with a weighted cross cord and a weight tied to the track; Unmanned Tech Shop: base pegs in grass or soft ground. Elevation 7-20 degrees (Novakovic 2014) / 15-25 degrees (Unmanned Tech Shop, Talon example) / under 30 degrees (diydrones).

### `kerf find "foot pedal release"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Kenmore 116 Series Vacuum Foot Release Pedal](https://www.printables.com/model/1633004-kenmore-116-series-vacuum-foot-release-pedal) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | Kenmore 116 Series Vacuum Foot Release Pedal_Pedal.stl: 58.5 x 40 x 27 mm | 0 likes, 7 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com foot pedal release`
- web search: `site:grabcad.com/library foot pedal release`
- web search: `foot pedal release STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/foot-pedal-release/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: DESIGN NEW. Only a vacuum-cleaner pedal (CC-BY-NC-SA, 58.5 x 40 x 27 mm) turned up. Needs a lever pivoting on the rear foot or rail with a cord to the trigger and a safety-pin interlock (SCL-2 style).

## References studied

| Reference | Link | License | Why relevant (numbers READ unless marked) |
|---|---|---|---|
| BRIN/LAPAN LSU-02 bungee launcher (paper) | https://ejournal.brin.go.id/MIPI/article/view/1353 | not stated | 2.7 m effective rail, 15.2 m/s target, 7 kg cradle + 14.4 kg UAV, 0.27 s and 2.5 m measured in test (0.28 s / 2.55 m simulated); about 7.6 g at rail start (search snippet of the paper, not the full text). Bungee chosen over pneumatic for simplicity and weight. |
| Novakovic et al. 2014, "Increasing launch capability of a UAV bungee catapult" | https://scindeks-clanci.ceon.rs/data/pdf/1820-0206/2014/1820-02061404017N.pdf | not stated | Launch speed >= 15 % above stall; acceleration < 10 g; rail elevation 7-20 degrees; assumed catapult efficiency 0.7; cords used 0-110 % elongation with a hysteresis loop (loading curve above unloading curve); jerk at the start is the main weakness; friction brake engages when the trolley opens to release the UAV and an extended ramp is needed; elastic + non-elastic cord with small pulleys keeps rolling inertia low. |
| NASA portable catapult launcher US 6,851,647 | https://patents.google.com/patent/US6851647 | public patent document, reference only | Hinged two-track rail (lever + locking pin or sliding plate), latex surgical tubes (0.625 in OD, five in one embodiment, 750 % break elongation), speed set by moving the tube anchor along the track (same idea as our notches), self-actuating trigger + safety pin, polyurethane/foam end barrier between rigid plates, four roller bearings on the carrier, bipod with weighted cross cord. |
| Ukrspecsystems SCL-2 bungee catapult | https://uascomponents.com/launch-and-landing-systems/scl2 | commercial page | 15 kg at 18 m/s, 25 g max, band tension up to 420 kgf, 3.17 x 1.2 x 1.07 m deployed, 15 min set-up by two people, safety pin and remote launch. |
| Unmanned Tech Shop, folding catapult guide | https://www.unmannedtechshop.co.uk/blogs/knowledge-base/why-hand-launching-fixed-wing-drones-fails-catapult-launcher | commercial page | 2.5 m rail folding to 1.1 m, 1.5-4.5 kg MTOW, 15-25 degrees, about 5 min set-up, pegs in grass; "below about 1.5 kg the bungee tension overpowers the airframe": our 0.3 kg end needs a gentle (1 strand, low notch) setting. |
| Embention C200R folding catapult | https://avpay.aero/company/embention/product/c200r-drone-catapult/ | commercial page | Folding man-portable, up to 5 kg, speed set by calibrating the elastic tension, under 4 min set-up. |
| diydrones: catapult launch of an XUAV Talon | https://diydrones.com/profiles/blogs/how-to-catapult-launch-and-arduplane-xuav-talon | blog post | Pull about 5 x the plane weight (hand scale to set it), stroke 5 m or more, hook on rigid base at/just forward of CG, trigger line off a ground hook; comments: latex cord from spearfishing suppliers. |
| arXiv 1604.00049, physics of slingshots | https://arxiv.org/pdf/1604.00049 | arXiv (author copyright, CC terms not stated) | MEASURED force vs stretch factor of latex tubes (2040: 4 x 2 mm, 9.2 g/m), reverse-draw hysteresis, force decay with log hold time, force proportional to absolute temperature. Source of the premium latex curve. |
| Latex-Tubing.com force table | https://www.latex-tubing.com/Exercise.html | vendor page | Force in lbf at 50/100/150/200 % stretch for 20 sizes (vendor-calculated from 100 % and 300 % tests); caps stretch at 200 % for exercise. |
| RCSE thread "High Start tubing" (T. Engel) | https://groups.google.com/g/rcse/c/JtUN_Ya_kpU | forum post | lbf at 300 % for five extruded surgical tubing sizes (175 psi = 1.21 MPa at 300 %), mandrel-dipped tubing stretches to 500 %, Theraband about 250 %. |
| bd_warehouse open_builds | https://github.com/gumyr/bd_warehouse | Apache-2.0 | Parametric OpenBuilds profile, eccentric spacer, T-nut and Xtreme V wheel; source of 2040 section and wheel-groove numbers. |
| RC Car RC plane Launch System | https://www.printables.com/model/525457-rc-car-rc-plane-launch-system | CC-BY | Wing-support block proportions. |
| RC Plane Launcher Parts | https://www.printables.com/model/1704290-rc-plane-launcher-parts | CC-BY-NC-SA | Pulley spindle and wing support, ideas only. |
| 2020 Extrusion Pivot/Hinge | https://www.printables.com/model/506305-2020-extrusion-pivothinge | GPL 3.0 | Ball-pivot hinge for 2020, ideas only. |
| Voron 2020 extrusion hinge | https://www.printables.com/model/249299-2020-extrusion-hinge-for-voron-fridge-door-mod | CC-BY | 60 x 25 x 10 mm printed hinge on 20 mm extrusion. |
| Basic Pulley (2 x 608) | https://www.printables.com/model/161642-basic-pulley-2x-608-bearing-2x-m4x30mm-12mm-rope | CC-BY | Sheave proportions, 50 mm rotor. |

Purchased-part datasheets and vendor pages are cited in catalog/hardware.json (motion.vslot_2040, vwheel_delrin_solid, tnut_m5_vslot, qr_pin_6mm, latex_tubing, shock_cord_6mm, braid_100lb, tent_stake_steel; rods.alu_tube_20x1_5). No vendor STEP was freely downloadable (openbuilds.com not reachable from the research machine, Kipp/McMaster need a browser); bd_warehouse gives parametric Apache-2.0 geometry instead.

## Decisions this supports

1. Rail section: 2040, area 292.7 mm2, 0.79-0.80 kg/m, Ix 46935 mm4 (vertical bending, 40 mm depth), Iy 12132 mm4 (sideways) - computed from bd_warehouse's OpenBuilds profile, cross-checked against the Systeal sheet (4.75 / 1.21 cm4, 0.799 kg/m, snippet). Rail beam check: 3 m of 4 sections, E about 69 GPa.
2. 750 mm sections are not stocked anywhere found (stock lengths 250/280/500/1000/1437/1500/2400): buy 3 x 1000 mm and cut four 750 mm pieces, or 2 x 1500 mm and halve them.
3. Wheel geometry: axle 10.0 mm off the rail face (staff rule: centre to centre = depth + 20), so 40.0 mm between the two wheel rows on a 20 mm face; V engagement 1.95 mm vs 1.455 mm groove chamfer; upper slot of each 40 mm face is centred 10 mm below the top face. Eccentric: 0.79 mm offset, 7.12 mm hole, 6 mm cam. Wheel is 23.9 OD x 10.23 wide, 2 x 625-2RS (380 N static each, catalog), no published wheel load rating.
4. Latex force per strand (3/16 x 1/16 in, 31.7 mm2) at 100/200/300/400 % stretch: commodity 16.9 / 29.4 / 38.2 / 46.9 N (400 % derived), premium 40 / 60 / 79 / 97 N. Stress 0.53 / 0.93 / 1.21 / 1.49 MPa (commodity), 1.27 / 1.89 / 2.50 / 3.07 MPa (premium). Scale other tubing sizes by cross-section. Energy per strand per metre of unstretched length (forward draw, before hysteresis): 8.4 / 31.6 / 65.4 / 107.9 J at 100/200/300/400 %. Use 300 % as the normal maximum, 400 % absolute.
5. Setting repeatability is limited by rubber behaviour, not notch geometry: hysteresis, force falling with log hold time, and F proportional to Kelvin (about 7 % per 20 degrees C). Print a scale but also a calibration check with a hand scale (diydrones does this).
6. Efficiency 0.7 (assumed, Novakovic) and launch speed >= 1.15 x stall (Novakovic) to 1.2 x stall (UAV practice, US patent 7992827 via search snippet); acceleration limit 10 g in the paper; BRIN design 7.6 g, SCL-2 25 g (heavy UAV, not foam).
7. Ground reaction: while the sled accelerates the stake and foot see the strand tension, 150 N (4 commodity strands, 300 %) to about 390 N (4 premium at 400 %); one tent stake holds about 60-100 N (Far Out Guides 14-32 lbf, 6 in aluminium/titanium stakes, soil unspecified), so plan several stakes plus weight, not one.
8. Brake: sled kinetic energy 0.5 m v^2, for example 0.4 kg at 15 m/s = 45 J; 225 N average over a 0.2 m stop, comparable with the working-load figure of one 6.35 mm shock cord (60 lbf, 150 lbf break): use two or more cords or a longer stop. NASA uses a polyurethane/foam barrier plate, Novakovic a friction brake that engages when the sled opens.
9. Hinge pins: 6 mm ball-lock pin, double shear 17.8 kN (Carr Lane at SF 2), hole 6.0-6.1 mm, pull-out 230 lbf; the printed lug (not the pin) is the weak link, so bush the lugs with aluminium or steel sleeves.

## Open questions

- Force-vs-elongation of the 6 mm shock cord: no source found; measure on the real cord.
- Latex tubing price per foot and which size to specify (3/16 x 1/16 assumed); the premium/commodity spread (2.1x) must be settled by a hand-scale test of the purchased tubing.
- Wheel behaviour crossing a joint gap in a spliced 2040 rail (bump, wobble): no source found; design the hinge block face flush and test a gap of 0.5 mm, 0.2 mm.
- The 2040 centre-hole diameter (4.2 vs 4.6 mm) and the real T-nut dimensions (10 x 5.9 x 4 from a model, not a drawing): measure one piece.
- 6 mm ball-lock pin price (about 35 USD each for Kipp, 3-6 USD unverified imports) and the available grip lengths (15/25/30/40/50 mm).
- Foam-plane acceleration limits: no source states a g limit for foam airframes; only 10 g (Novakovic), 7.6 g (BRIN), 25 g (SCL-2). Check the hook mount and wing-support loads per drone.
- Braid: the 100 lb line (0.55 mm) is a search snippet; only needed if a pull line is used.
- Several price entries are search snippets (OpenBuilds kit 5.19 USD, tee nuts, Kipp pin, Speedy Metals tube): re-check before ordering.
