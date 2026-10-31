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
| Strength | proximal takes 15 N at the pip pin, held at the mcp pin, SF 2 (load along the layers) | brief, ENGINEERING.md s3 |

Chosen: L1 = 44, L2 = 25, L3 = 21 mm (middle of each band, close to Aero Hand's measured 43 / 22), 15.4 mm wide,
15 mm deep at the knuckles (adult index ~16-18 mm wide; Aero 16.4 / 15.2 / 14.0 mm).

## 2. Architecture

| Option | For | Against |
|---|---|---|
| Fork/tongue (clevis) knuckles printed flat | symmetric double-shear pin | flat: knuckle undersides overhang; on the side: the upper fork cheek is a 15 mm unsupported bridge |
| Flexure / TPU hinges (Flexy-Hand) | no pins | no fixed axis, twists under side load (Yale lesson); brief asks for pin joints |
| **Two-layer lap knuckles, printed on the side (picked)** | pin axis vertical on the printer -> round pin holes; bending runs along the layers; every wall is vertical, so zero overhang | single-shear pin -> the joint can rock a little sideways (mitigated below) |

How a lap knuckle works (`parts/fingerlib.py`): each part is three Y layers — a bottom band (y side `b`, on the bed),
a 0.3 mm gap layer and a top band. At a joint the parent's round knuckle disc (R 7.5) sits in band `s` and the
child's in band `-s`; each disc turns inside a pocket of radius 7.9 (0.4 mm clearance) in the other part. Away from
the axis the child's knuckle band is full depth (it carries the segment's largest bending moment) and the parent's
other band is cut away where that band swings over the joint range (`fingerlib.swept`: the strip at 0, the strip at
full flexion and the wedge between). The child's other band keeps all material the rotation allows: dorsal ahead of
the axis, palmar where x sin(theta) + |z| cos(theta) >= 7.9 (clear of the parent's palmar face at full flexion
theta). Pockets are widened to |x| <= 5.1 so the pocket circle leaves no knife edge (>= 1.5 mm) at the faces. The
sweep checks prove all of it. The knuckle side alternates
(mcp -1, pip +1, dip -1) so every part has both of its knuckle discs in its bottom band: base and middle print with
-Y down, proximal and distal with +Y down. The gap layer and top band of a part are always a subset of its bottom
band's footprint, so nothing overhangs.

Axial hold and bearing: a lap joint has nothing that keeps the two bands together along the pin (a dowel pressed in
one band would let the other slide off its free end - found by the research pass), and a plain screw turning in a
printed hole wears on its thread crests (review round 1: the flexor puts ~220 N on each pivot). So each pivot is a
4 mm shoulder screw (`motion.shoulder_4_m3`, McMaster 97505A106: 4 x 8 mm shoulder, M3 x 4.5 thread, low head
7 x 1.8): head on the child's outer face, the ground 4 mm shoulder turning in the child's 4.35 mm hole, the shoulder end
bottomed on a heat-set M3 insert flush in the parent's band (pressed in from its gap face, open on the printer). The
finger is 15.4 mm wide so a knuckle band (7.55) plus the gap (0.3) is 7.85 under the 8 mm shoulder: the head never
clamps (0.15 mm play), tighten fully - `kerf/pins.py` proves the shoulder length, thread fit and engagement. The heads
stand 1.8 mm proud on alternating sides (proximal and distal +Y, middle -Y); leave that room to the neighbouring finger.

Hard stop at straight: two lines and three joints only define "straight" if each joint bottoms out at 0 deg (review
round 1: without it the extensor bends the finger backward ~60 deg). Every knuckle has a 2 mm dorsal lug on each part
(`fingerlib.LUG_H`): the parent's in its knuckle band, the child's in both bands, outside the pocket radius in the
band that faces the parent's knuckle. At 0 deg they are 0.3 mm apart; they touch at about -2 deg. The `stop_mcp`,
`stop_pip`, `stop_dip` requirements (`hard_stop`) prove the parts overlap at -5 deg; the sweeps prove 0-80 is clear.
The lugs make the knuckles 17 mm deep, like a real finger's knuckles.

Side play: the two 7.55 mm lap faces bear on each other over the whole 15 mm disc. Axial play is the 0.3 mm gap plus
the 0.15 mm the 8 mm shoulder leaves under the head (0.45 mm), and the shoulder has 0.35 mm diametral clearance in a
single-shear joint: each joint can tilt ~1.7 deg sideways, a few mm of wobble at the fingertip under a side push
(review round 2). If that matters for the hand, print the free holes at 4.2 mm after a test pair, or shim with a 0.2 mm
PTFE washer under the head. The hyperextension stop meets in one band only (a 1.6 x 7.55 mm face, loaded along the
layers). The child's lug is cut by the pocket circle on its band-facing side: a small cosmetic point, not loaded.

## 3. Purchased parts

| Item | Catalog | Qty | Why |
|---|---|---|---|
| 4 x 8 mm shoulder screw, M3 x 4.5 thread, head 7 x 1.8 | `motion.shoulder_4_m3`, length from the pin check | 3 | joint pivots: the shoulder is the bearing, the head holds the lap joint together |
| M3 heat-set insert, 5.7 mm (CNC Kitchen standard) | `fdm_holes.M3` | 3 | thread in the parent's knuckle band |
| Braided PE line 0.5-0.8 mm, >= 100 lb (445 N) | bom_extra | 0.5 m | flexor + extensor; InMoov/Yale: braided line, >= 0.4 mm so it does not saw the plastic |
| CA glue | bom_extra | - | locks the fingertip knots |
| Crimp sleeve or bead, 2.5-2.9 mm OD | bom_extra | 2 | line stop in each 3 mm fingertip pocket (a knot alone can pull into the 2.2 mm channel) |
| 2 x M3 screw + nut | bom_extra | 2 | knuckle mount to the hand frame (15.4 mm through-holes along Y, 3.4 mm clearance from catalog) |

## 4. Parts

| Part | Job | Material | print_rot | Bed side | Envelope (mm) |
|---|---|---|---|---|---|
| base | knuckle mount, mcp insert, both tendons exit the back face | PETG 40 % | [90,0,0] | -Y | 37.5 x 15.4 x 17 |
| proximal | mcp free / pip insert | PETG 40 % | [-90,0,0] | +Y | 59 x 15.4 x 17 |
| middle | pip free / dip insert | PETG 40 % | [90,0,0] | -Y | 40 x 15.4 x 17 |
| distal | dip free, fingertip, two knot pockets | PETG 40 % | [-90,0,0] | +Y | 28.5 x 15.4 x 17 |

`load_axis: X` on every part: the segment bends in the XZ plane, which is in the layer plane when printed on the side.

## 5. Interfaces

| Joint | Parent (insert, band) | Child (free + head, band) | Group | Pivot |
|---|---|---|---|---|
| mcp | base, -Y | proximal, +Y | pin_mcp | 4 x 8 shoulder screw |
| pip | proximal, +Y | middle, -Y | pin_pip | 4 x 8 shoulder screw |
| dip | middle, -Y | distal, +Y | pin_dip | 4 x 8 shoulder screw |

Holes come from `iface.pin_hole` (heatset = 4.0 x 6.7 mm insert bore from the gap face, free = d + 0.35 from
`fdm_fits.pin`), vertical on the printer; `kerf/pins.py` proves them coaxial and picks the 14 mm length.

## 6. Joint tree

base (root) -mcp [0, 80]-> proximal -pip [0, 80]-> middle -dip [0, 70]-> distal; home 0 = straight. Each joint is
swept on its own (17 / 17 / 15 samples) and together as `curl` (0/0/0, 30/30/30, 60/60/60, 80/80/70).

## 7. Tendons

- Both lines run in the y = 0 plane. Flexor 4.0 mm palmar of the pin axes (exits 4.5 mm either side of each axis),
  extensor 4.98 mm dorsal, wrapping each knuckle over two crown points (95 deg on the parent, 85 deg on the child,
  radius 5).
- Where a line crosses a joint, each part cuts the union of the line's straight chord over the joint's whole range
  (every 10 deg) in its own frame (`fingerlib.crossing_cuts`; between two steps the line stays >= 0.05 mm inside the
  nearer 2.2 mm tube, so it never touches the ridges between them). The cut is a groove in the knuckle face (open toward the
  gap, so it prints) and the line therefore never touches plastic at any angle — `channel_clear` checks it at home,
  each joint alone at full flexion and three curl poses.
- Channels are 2.2 mm with a 55 deg pointed roof (no supports). Clear diameter across a joint = 0.3 gap + 2 x 0.95
  groove = 2.2 mm.
- Moment arms at home: flexor 4.0 mm, growing as the joint bends (the chord moves away from the axis); extensor ~5 mm.
  With the finger straight the flexor must balance the tip force about the mcp: T = F x 90 / 4 = 22.5 F (dip 5.3 F,
  pip 11.5 F). A >= 100 lb (445 N) braid at SF 2 therefore rates ~10 N at a straight fingertip, more as the finger
  curls (the arms grow). Do not use the common 30 kg line (~1x at 12 N).
- Travel: full curl takes up ~16 mm of flexor (4 mm x 4.0 rad) but pays out ~20 mm of extensor (5 mm wrap). One servo
  wheel driving both lines would go slack or bind: use two take-ups, or a spring/elastic on the extensor.
- Termination: both lines end in 3 mm pockets in the distal, open to the top face — thread a 2.5-2.9 mm crimp sleeve
  or bead onto the line end, crimp/knot it, pull it into the pocket, wick CA in. The sleeve cannot enter the 2.2 mm
  channel, so the line holds without relying on the glue. Lines leave the base through its back face toward the actuator.

## 8. Strength

- Proximal hand check: 15 N at 44 mm -> M = 660 N mm; section 15.4 x 15 minus two channels ~ Z 550 mm3 -> 1.2 MPa,
  pin bearing 15 / (3 x 7.85) = 0.64 MPa. PETG XY strength / SF 2 is an order of magnitude above. FEA
  (`proximal_fea`) is the proof; result in the report.
- FEA model (as the brief specifies): fixed on the mcp pin bore, 15 N bearing load on the pip bore. Clamping the whole
  660 N mm moment on one 3 mm bore is harsher than the real finger (the flexor carries most of it) and most of the
  deflection is the segment rotating about that bore. The first layout kept only the dorsal half of the child's
  knuckle band for 8 mm ahead of the axis; that neck let the pip end move 0.72 mm. Now the child's knuckle band is
  full depth and the parent's other band is cut where it swings (`fingerlib.swept`), which meets the 1 %-of-length
  limit of ENGINEERING.md (0.44 mm).
- Line load (`proximal_fea_line`): the flexor at its rated 222 N (100 lb braid / SF 2) presses the segment between
  the pivots, plus 10 N at the tip: FEA p99.9 ~10.5 MPa vs 24 allowed. Pivot bearing on the 4 mm shoulder:
  222 / (4 x 7.55) = 7.4 MPa nominal on a smooth ground shoulder (PETG yield ~48 MPa); insert pull-out not loaded.

## 9. Assembly order

1. Heat-set an M3 insert into the gap face of the base, proximal and middle knuckle bands (soldering iron at
   ~230 C for PETG), then press it flush to slightly below the face with a flat plate while it cools, and shave off
   any plastic lip (the face must stay flat): with 0.15 mm under the head, an insert left proud clamps the joint.
2. Put the proximal's knuckle over the base's, push a 4 x 8 shoulder screw through the proximal's outer face into the
   base's insert and tighten until the shoulder bottoms on the insert - gently (~0.5 N m, two-finger torque on the
   driver; the insert's wall to the extensor groove is thin) - then check the joint swings freely.
3. Same for proximal -> middle and middle -> distal.
4. Tendons last, with the finger slightly curled (opens the paths through the knuckle gaps): stiffen ~20 mm of each
   line end with thin CA (or use a fine wire leader) and feed it; pliers or a crimper for the sleeves.
   Thread the flexor from the base's back face through the palmar channel to the distal pocket; sleeve, pull in, CA.
   Same for the extensor along the dorsal channel.
5. Bolt the base to the hand frame with two M3 screws and nuts through its 15.4 mm holes.

## 10. Risks / measure first

- Pivot fit: print one knuckle pair first. If the free hole binds on the shoulder, run a 4.4 mm drill through it.
- Insert mouth: the swept extensor groove passes ~0.5 mm from the insert hole (~0.2 mm from the knurls) in the top 0.95 mm; the
  insert seats below that, but heat it gently and trim any lip.
- Thin spots: the tendon grooves (0.95 mm deep, only at the knuckle faces) graze the knuckle rims; the wall check
  reports p2 >= 1.1 mm on every part.
- Single-shear joints rock slightly sideways under a hard side load (see section 2).
