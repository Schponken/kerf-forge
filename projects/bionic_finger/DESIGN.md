# Bionic index finger (E5) — design

One tendon-driven index finger for a bionic hand: a knuckle mount (`base`) and three phalanges (`proximal`,
`middle`, `distal`) on 4 mm shoulder-screw pivots (M3 thread into heat-set inserts) with a hard stop at straight. Pull the flexor line and it curls; pull the extensor and it straightens.
References and the evidence behind each choice: REFERENCES.md.

## 1. Requirements (numbers)

| Requirement | Value | Source |
|---|---|---|
| Segment lengths (axis-axis, axis-tip) | proximal 40-48, middle 22-28, distal 18-24 mm | brief; adult index bones 39.8 / 22.4 / 15.8 mm (Buryanov & Kotiuk), Aero Hand 43 / 22 / 26.8 |
| Joint ranges | mcp 0-80, pip 0-80, dip 0-70 deg, each and all together (curl) without jamming | brief |
| Tendon channels | flexor + extensor, >= 1.5 mm clear end to end at every pose | brief |
| Pins | real hardware (catalog pin or M3 screw), aligned through both parts | brief |
| Printing | no supports (`supports: avoid`: < 0.5 % of the surface may overhang > 45 deg) | brief |
| Strength | proximal takes 15 N at the pip pin, held at the mcp pin, SF 2 (load along the layers); every part also takes the 222 N rated line load (s8) | brief, ENGINEERING.md s3, s3b |
| Mass | <= 40 g printed (light finger, small actuator load) | `finger_mass` |

Chosen: L1 = 44, L2 = 25, L3 = 22 mm (inside each band, close to Aero Hand's measured 43 / 22 / 26.8), 15.6 mm wide,
18 mm deep (20 mm over the stop lugs at the knuckles; adult index ~16-18 mm wide; Aero 16.4 / 15.2 / 14.0 mm). The
depth was 15 mm until the 2026-10-31 audit: the single-shear pin moment (s8) and the 1.6 mm insert wall to the
tendon grooves (s7) need the extra 3 mm.

## 2. Architecture

| Option | For | Against |
|---|---|---|
| Fork/tongue (clevis) knuckles printed flat | symmetric double-shear pin | flat: knuckle undersides overhang; on the side: the upper fork cheek is a 15 mm unsupported bridge |
| Flexure / TPU hinges (Flexy-Hand) | no pins | no fixed axis, twists under side load (Yale lesson); brief asks for pin joints |
| **Two-layer lap knuckles, printed on the side (picked)** | pin axis vertical on the printer -> round pin holes; bending runs along the layers; every wall is vertical, so zero overhang | single-shear pin -> the joint can rock a little sideways (mitigated below) |

How a lap knuckle works (`parts/fingerlib.py`): each part is three Y layers — a bottom band (y side `b`, on the bed,
7.6 mm = 38 layers of 0.2), a 0.4 mm gap layer (2 layers; 0.2 mm per face, on the layer grid so it prints as drawn)
and a top band (7.6). At a joint the parent's round knuckle disc (R 9 = half the depth) sits in band `s` and the
child's in band `-s`; each disc turns inside a pocket of radius 9.4 (0.4 mm clearance) in the other part. Away from
the axis the child's knuckle band is full depth (it carries the segment's largest bending moment) and the parent's
other band is cut away where that band swings over the joint range (`fingerlib.swept`: the strip at 0, the strip at
full flexion and the wedge between). The child's other band keeps all material the rotation allows: dorsal ahead of
the axis, palmar where x sin(theta) + |z| cos(theta) >= 7.9 (clear of the parent's palmar face at full flexion
theta). Pockets are widened to |x| <= 5.67 so the pocket circle leaves no knife edge (>= 1.5 mm) at the faces. The
sweep checks prove all of it. The knuckle side alternates
(mcp -1, pip +1, dip -1) so every part has both of its knuckle discs in its bottom band: base and middle print with
-Y down, proximal and distal with +Y down. The gap layer and top band of a part are always a subset of its bottom
band's footprint, so nothing overhangs.

Axial hold and bearing: a lap joint has nothing that keeps the two bands together along the pin (a dowel pressed in
one band would let the other slide off its free end - found by the research pass), and a plain screw turning in a
printed hole wears on its thread crests (review round 1: the flexor puts ~220 N on each pivot). So each pivot is a
4 mm shoulder screw (`motion.shoulder_4_m3`, McMaster 97505A106: 4 x 8 mm shoulder, M3 x 4.5 thread, low head
7 x 1.8): head on the child's outer face, the ground 4 mm shoulder turning in the child's 4.35 mm hole, the shoulder end
bottomed on a heat-set M3 insert flush with a one-layer (0.2 mm, R 3.4) boss on the parent's gap face (pressed in from
that face, open on the printer). The boss is what makes the numbers work: the child's band (7.6) plus the gap left
at the boss (0.4 - 0.2) is 7.8 under the 8 mm shoulder, so the head never clamps (0.2 mm play, tighten fully), and
the insert gets 7.6 + 0.2 = 7.8 mm of material (catalog: 6.7 mm hole + 0.8 mm floor) - a 7.4 mm band would not hold
it. `kerf/pins.py` proves the shoulder length (8 mm), thread fit and engagement. The heads stand 1.8 mm proud on
alternating sides (proximal and distal +Y, middle -Y); leave that room to the neighbouring finger.

Hard stop at straight: two lines and three joints only define "straight" if each joint bottoms out at 0 deg (review
round 1: without it the extensor bends the finger backward ~60 deg). Every knuckle has a 2 mm dorsal lug on each part
(`fingerlib.LUG_H`): the parent's in its knuckle band, the child's in both bands, outside the pocket radius in the
band that faces the parent's knuckle. At 0 deg they are 0.3 mm apart; they touch at about -2 deg. The `stop_mcp`,
`stop_pip`, `stop_dip` requirements (`hard_stop`) prove the parts overlap at -5 deg; the sweeps prove 0-80 is clear.
The lugs make the knuckles 20 mm deep.

Side play: the child's band turns between the boss (0.2 mm away) and the screw head (0.2 mm away), so the axial play
is 0.4 mm over an 18 mm disc, and the shoulder has 0.35 mm diametral clearance in a single-shear joint: each joint can tilt ~1.3 deg
sideways, a few mm of wobble at the fingertip under a side push (review round 2). If that matters for the hand, print the free holes at 4.2 mm after a test pair, or shim with a 0.2 mm
PTFE washer under the head. The hyperextension stop meets in one band only (a 1.6 x 7.6 mm face, loaded along the
layers). The child's lug is cut by the pocket circle on its band-facing side: a small cosmetic point, not loaded.
Every outline edge on the bed face and the top face has a 0.5 mm chamfer (`features.bed_chamfer` for the first
layer's elephant's foot; the top one faces up and prints clean).

## 3. Purchased parts

| Item | Catalog | Qty | Why |
|---|---|---|---|
| 4 x 8 mm shoulder screw, M3 x 4.5 thread, head 7 x 1.8 | `motion.shoulder_4_m3`, length from the pin check | 3 | joint pivots: the shoulder is the bearing, the head holds the lap joint together |
| M3 heat-set insert, 5.7 mm (CNC Kitchen standard) | `fdm_holes.M3` | 3 | thread in the parent's knuckle band |
| Braided PE line 0.5-0.8 mm, >= 100 lb (445 N) | bom_extra | 0.5 m | flexor + extensor; InMoov/Yale: braided line, >= 0.4 mm so it does not saw the plastic |
| M2 flat washer, ISO 7089 (2.2 x 5.0 x 0.3) or DIN 433 (2.3 x 4.5 x 0.3) | bom_extra (`washer:M2` price) | 2 | line stop: spreads the line load over the 5.4 mm seat (s7, s8) |
| Bead 2.5-3 mm OD, hole <= 1.0 mm | bom_extra | 2 | sits on the washer, cannot pass its 2.2 mm hole; knotted behind |
| CA glue | bom_extra | - | stiffens line ends for threading, locks the fingertip knots |
| 2 x M3 screw + nut | bom_extra | 2 | knuckle mount to the hand frame (15.6 mm through-holes along Y, 3.5 mm clearance from catalog) |

The M2 washer comes from the catalog (`screws.M2` washer_d1 2.2 / washer_d2 5.0 / washer_h 0.3, ISO 7089, sourced):
the seat is washer_d2 + `stop_pocket_clear` 0.4 = 5.4 mm, the line hole `stop_hole_d` 1.2.

## 4. Parts

| Part | Job | Material | print_rot | Bed side | Envelope (mm) |
|---|---|---|---|---|---|
| base | knuckle mount, mcp insert, both tendons exit the back face | PETG 40 %, 4 walls | [90,0,0] | -Y | 39 x 15.6 x 20 |
| proximal | mcp free / pip insert | PETG 40 %, 4 walls | [-90,0,0] | +Y | 62 x 15.6 x 20 |
| middle | pip free / dip insert | PETG 40 %, 4 walls | [90,0,0] | -Y | 43 x 15.6 x 20 |
| distal | dip free, fingertip, two washer line stops | PETG 40 %, 4 walls | [-90,0,0] | +Y | 31 x 15.6 x 20 |

`load_axis: X` on every part: the segment bends in the XZ plane, which is in the layer plane when printed on the side.

## 5. Interfaces

| Joint | Parent (insert, band) | Child (free + head, band) | Group | Pivot |
|---|---|---|---|---|
| mcp | base, -Y | proximal, +Y | pin_mcp | 4 x 8 shoulder screw |
| pip | proximal, +Y | middle, -Y | pin_pip | 4 x 8 shoulder screw |
| dip | middle, -Y | distal, +Y | pin_dip | 4 x 8 shoulder screw |

Holes come from `iface.pin_hole` (heatset = 4.0 x 6.7 mm insert bore from the boss face, free = d + 0.35 from
`fdm_fits.pin`), vertical on the printer; `kerf/pins.py` proves them coaxial and picks the 8 mm shoulder.

## 6. Joint tree

base (root) -mcp [0, 80]-> proximal -pip [0, 80]-> middle -dip [0, 70]-> distal; home 0 = straight. Each joint is
swept on its own (17 / 17 / 15 samples) and together as `curl` (0/0/0, 30/30/30, 60/60/60, 80/80/70).

## 7. Tendons

- Both lines run in the y = 0 plane. Flexor 4.7 mm palmar of the pin axes (exits 4.5 mm either side of each axis),
  extensor 6.15 mm dorsal, crossing each knuckle over two crown points straight above the axis (radius 6.15, one on
  the parent, one on the child; at 0 deg they coincide and the line runs straight).
- Insert wall (audit C-6): every swept groove stays >= 1.6 mm (catalog `heatset_min_wall`) from the 4.0 mm insert
  bore. The flexor chord is closest to the axis at 0 deg (4.7 mm); the extensor chord at full flexion (80 deg) passes
  6.15 x cos 40 = 4.71 mm from the axis. 4.7 - 1.1 (groove radius) - 2.0 (bore radius) = 1.6 mm.
- Where a line crosses a joint, each part cuts the union of the line's straight chord over the joint's whole range
  (every 10 deg) in its own frame (`fingerlib.crossing_cuts`). The cut is a groove in the knuckle face (open toward
  the gap, so it prints) and the line never touches plastic at any angle — `channel_clear` checks it at home, each
  joint alone at full flexion and three curl poses.
- Channels are 2.2 mm with a 55 deg pointed roof toward the top of the print (no supports); the roof triangle sits on
  the tangent chord (audit C-5), so the cutter is exactly 2.2 mm wide across the line (it was 2.69 before).
  Clear diameter across a joint = 0.4 gap + 2 x 0.9 groove = 2.2 mm.
- Moment arms at home: flexor 4.7 mm, growing as the joint bends (the chord moves away from the axis); extensor
  6.15 mm. With the finger straight the flexor must balance the tip force about the mcp: T = F x 91 / 4.7 = 19.4 F
  (pip 10 F, dip 4.7 F). A >= 100 lb (445 N) braid at SF 2 (222 N) therefore rates ~11 N at a straight fingertip,
  more as the finger curls. Do not use the common 30 kg line.
- Travel (chord geometry, mcp 80 / pip 80 / dip 70): the flexor takes up 8.2 + 8.2 + 7.0 = 23.3 mm, the extensor
  pays out 7.9 + 7.9 + 7.1 = 22.9 mm, but not in step (at 30/30/30: 8.2 vs 9.6 mm). One servo wheel driving both lines
  would go slack or bind: use two take-ups, or a spring/elastic on the extensor.
- Termination (audit C-1): each line ends on a washer stop in the distal. The 2.2 mm channel stops at a 1.5 mm flat
  step at x = 11.5 with a 1.2 mm line hole; beyond it a U-slot (5.4 mm wide, 4.5 mm long, round bottom on the bed
  side, open to the top face) holds an M2 flat washer flat on the step, then a 2.5-3 mm bead and a knot. The line
  load bears on the washer's whole face: 222 N / (pi/4 x (5.0^2 - 1.2^2)) = 222 / 18.5 = 12.0 MPa nominal (DIN 433
  4.5 mm washer: 15.0 MPa) vs 24 MPa allowed, and the bead cannot pass the washer's 2.2 mm hole. The plug of step
  over the channel end shears on pi x 2.2 x 1.5 = 10.4 mm2 under the ~32 N the washer puts on it: 3 MPa. FEA
  (`distal_fea_flexor`, `distal_fea_extensor`) is the proof. The flexor stop is at z = -3.8, the extensor's at
  z = +4.0 (slots 2.4 mm apart, about 1.8-2.0 mm skin to the palmar/dorsal faces); each line keeps its joint height until
  it is clear of the middle's knuckle pocket (r > 9.4 mm from the dip axis) and only then turns to its stop, inside
  the distal where the line no longer slides. Lines leave the base through its back face toward the actuator.

## 8. Strength

Load cases (all `fea_static`, PETG along the layers, 48 MPa / SF 2 = 24 MPa allowed; `load_axis: X` lies in the
bed plane for every part). The 222 N line case is the rated line tension (100 lb braid / SF 2); it compresses every
segment between its pivots. Each pivot is single shear: the engine adds the pin moment (222 N x 7.1 mm = 1578 N mm,
the distance along the pin from the loaded band to the band that pushes on it) to every pin-bore bearing load.

| Requirement | Part | Held at | Load | p99.9 (MPa) | Limit |
|---|---|---|---|---|---|
| proximal_fea | proximal | mcp bore | 15 N on the pip insert bore (+ 106 N mm pin moment) | 4.8 (defl 0.22 mm vs 0.44) | 24 |
| proximal_fea_line | proximal | mcp bore | [-222, 0, 10] N on the pip insert bore + 1578 N mm | 20.5 | 24 |
| base_fea_line | base | both M3 frame-screw holes | [-222, 0, 10] N on the mcp insert bore + 1578 N mm | 19.6 | 24 |
| middle_fea_line | middle | pip bore | [-222, 0, 10] N on the dip insert bore + 1578 N mm | 20.2 | 24 |
| distal_fea_flexor | distal | dip bore | 222 N on the flexor washer seat + 10 N on the fingertip pad | 18.5 | 24 |
| distal_fea_extensor | distal | dip bore | 222 N on the extensor washer seat | 20.0 | 24 |

- Where it peaks: the pin moment bends each knuckle band (7.6 mm thick, the only layer at the joint) about Z,
  hardest at the step where the other band's pocket ends (~5.7 mm from the axis) and at the groove lips there. Hand
  check: 1578 N mm / (18 x 7.6^2 / 6) = 9.1 MPa bending + 222 / (18 x 7.6) = 1.6 MPa compression = 10.7 MPa nominal;
  the FEA's 20 MPa is that times the notch factor of the step and grooves. With the old 15 mm depth and 7.55 mm band
  the same case gave 26.5 MPa (audit C-2); the 18 mm depth, the true 2.2 mm channel width and the grooves moved off
  the dorsal skin brought it under the limit.
- Proximal 15 N hand check: 15 N at 44 mm -> M = 660 N mm; section 15.6 x 18 minus two channels, Z ~ 800 mm3 ->
  0.8 MPa; pin bearing 15 / (4 x 7.6) = 0.5 MPa. Deflection 1 %-of-length limit (0.44 mm) met: 0.22 mm.
- Pivot bearing on the 4 mm shoulder: 222 / (4 x 7.6) = 7.3 MPa nominal on a smooth ground shoulder (PETG yield ~48
  MPa); the line load is across the pin, so the insert sees pull-out only from the screw preload: keep the
  tightening torque at 0.2-0.3 N m (assembly step 2).
- The FEA peaks (not p99.9) are single-element spikes at sharp re-entrant edges where a groove meets the pocket step;
  they are in the gap face of a band, which a 4-wall print lays down as solid perimeter.

## 8b. Mass budget

| Part | Estimate (4 walls, 40 % infill) |
|---|---|
| base | 7.2 g |
| proximal | 10.2 g |
| middle | 6.2 g |
| distal | 5.2 g |
| Printed total | 28.9 g (report `finger_mass`; cap 40 g) |
| 3 shoulder screws, 3 inserts, 2 washers, 2 beads, line | ~3 g (not modelled as proxies) |

## 9. Assembly order

1. Heat-set an M3 insert into the boss on the gap face of the base, proximal and middle knuckle bands (soldering iron
   at ~230 C for PETG), then press it flush with the boss face with a flat plate while it cools, and shave off any
   plastic lip (the boss face must stay flat): the shoulder bottoms on the insert, so an insert left proud of the
   boss only adds play, while one sunk below the boss face lets the head pull down onto the child band and clamp
   the joint (flush is the target).
2. Put the proximal's knuckle over the base's, push a 4 x 8 shoulder screw through the proximal's outer face into the
   base's insert and tighten until the shoulder just bottoms on the insert (flat-blade screwdriver, 0.2-0.3 N m; a
   drop of medium threadlocker on the screw's thread tip only, never on the plastic), then check the joint swings
   freely. More torque only pulls the insert back out toward the face it was pressed in from.
3. Same for proximal -> middle and middle -> distal.
4. Tendons last, with the finger slightly curled (opens the paths through the knuckle gaps): stiffen ~20 mm of each
   line end with thin CA (or use a fine wire leader) and feed it. Thread the flexor from the base's back face through
   the palmar channel until it comes out of the 1.2 mm hole into the distal's palmar stop slot; there thread an M2
   washer and a bead onto it, tie a double overhand knot against the bead, pull the washer flat onto the step and
   wick CA onto the knot. Same for the extensor along the dorsal channel into the dorsal slot.
5. Bolt the base to the hand frame with two M3 screws and nuts through its 15.6 mm holes.

## 10. Risks / measure first

- Pivot fit: print one knuckle pair first. If the free hole binds on the shoulder, run a 4.4 mm drill through it.
- Insert boss: the boss is one 0.2 mm layer; check it printed (without it the insert sits 0.2 mm shallower; the play is the same). The swept
  grooves pass 1.6 mm from the insert bore, so heat-setting no longer bulges into them.
- Thin spots: the wall check reports p2 >= 1.27 mm (middle; the grooves at its short top band), >= 1.6 elsewhere.
- Single-shear joints rock slightly sideways under a hard side load (see section 2).
- The swept grooves are cut every 10 deg: between two steps a 0.5 mm line stays inside the groove, a 0.8 mm line may
  just touch the ridges between steps at the knuckle rims (9.4 mm from the axis) in mid-step poses. Prefer 0.5-0.6 mm
  braid.
- The line stop seat is sized for an ISO 7089 M2 washer (5.0 OD); the common retail DIN 433 (4.5 OD) also fits and
  still passes the bearing check (15 MPa).
