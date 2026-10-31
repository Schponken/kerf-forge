# Bionic index finger (E5) — design

One tendon-driven index finger for a bionic hand: a knuckle mount (`base`) and three phalanges (`proximal`,
`middle`, `distal`) on 3 mm steel dowel pins. Pull the flexor line and it curls; pull the extensor and it straightens.
References and the evidence behind each choice: REFERENCES.md.

## 1. Requirements (numbers)

| Requirement | Value | Source |
|---|---|---|
| Segment lengths (axis-axis, axis-tip) | proximal 40-48, middle 22-28, distal 18-24 mm | brief; adult index bones 39.8 / 22.4 / 15.8 mm (Buryanov & Kotiuk), Aero Hand 43 / 22 / 26.8 |
| Joint ranges | mcp 0-80, pip 0-80, dip 0-70 deg, each and all together (curl) without jamming | brief |
| Tendon channels | flexor + extensor, >= 1.5 mm clear end to end at every pose | brief |
| Pins | real hardware (catalog dowel or M3), aligned through both parts | brief |
| Printing | no supports (`supports: avoid`: < 0.5 % of the surface may overhang > 45 deg) | brief |
| Strength | proximal takes 15 N at the pip pin, held at the mcp pin, SF 2 (load along the layers) | brief, ENGINEERING.md s3 |

Chosen: L1 = 44, L2 = 25, L3 = 21 mm (middle of each band, close to Aero Hand's measured 43 / 22), 16 mm wide,
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
the axis the child keeps palmar material only beyond x = 8.5 mm and dorsal material anywhere ahead of the axis, which
is exactly what stays clear of the parent at 80 deg (the sweep check proves it). The knuckle side alternates
(mcp -1, pip +1, dip -1) so every part has both of its knuckle discs in its bottom band: base and middle print with
-Y down, proximal and distal with +Y down. The gap layer and top band of a part are always a subset of its bottom
band's footprint, so nothing overhangs.

Side play: the two 7.85 mm lap faces bear on each other over the whole 15 mm disc, the pin is a hardened m6 dowel
pressed into the parent for its full 7.85 mm, and the 0.3 mm gap is the only axial play. Expect a slight sideways
rock under a hard side push; a thin PTFE/nylon washer is not needed at 0.3 mm (the open designs run 0.15-0.25 mm
per side, REFERENCES.md).

## 3. Purchased parts

| Item | Catalog | Qty | Why |
|---|---|---|---|
| 3 x 16 mm hardened dowel (ISO 8734 m6) | `motion.pin_3mm`, length 16 | 3 | stocked length = finger width = pin span; InMoov / Raptor use 3 mm pins |
| Braided PE line 0.5-0.8 mm, >= 30 kg | bom_extra | 0.5 m | flexor + extensor; InMoov/Yale: braided line, >= 0.4 mm so it does not saw the plastic |
| CA glue | bom_extra | - | locks the fingertip knots |
| 2 x M3 screw + nut | bom_extra | 2 | knuckle mount to the hand frame (16 mm through-holes along Y, 3.4 mm clearance from catalog) |

## 4. Parts

| Part | Job | Material | print_rot | Bed side | Envelope (mm) |
|---|---|---|---|---|---|
| base | knuckle mount, mcp pin pressed, both tendons exit the back face | PETG 40 % | [90,0,0] | -Y | 37.5 x 16 x 15 |
| proximal | mcp free / pip pressed | PETG 40 % | [-90,0,0] | +Y | 59 x 16 x 15 |
| middle | pip free / dip pressed | PETG 40 % | [90,0,0] | -Y | 40 x 16 x 15 |
| distal | dip free, fingertip, two knot pockets | PETG 40 % | [-90,0,0] | +Y | 28.5 x 16 x 15 |

`load_axis: X` on every part: the segment bends in the XZ plane, which is in the layer plane when printed on the side.

## 5. Interfaces

| Joint | Parent (press, band) | Child (free, band) | Group | Pin |
|---|---|---|---|---|
| mcp | base, -Y | proximal, +Y | pin_mcp | 3 x 16 dowel |
| pip | proximal, +Y | middle, -Y | pin_pip | 3 x 16 dowel |
| dip | middle, -Y | distal, +Y | pin_dip | 3 x 16 dowel |

Holes come from `iface.pin_hole` (press = d + 0.05, free = d + 0.35 from `fdm_fits.pin`), vertical on the printer.

## 6. Joint tree

base (root) -mcp [0, 80]-> proximal -pip [0, 80]-> middle -dip [0, 70]-> distal; home 0 = straight. Each joint is
swept on its own (17 / 17 / 15 samples) and together as `curl` (0/0/0, 30/30/30, 60/60/60, 80/80/70).

## 7. Tendons

- Both lines run in the y = 0 plane. Flexor 4.0 mm palmar of the pin axes (exits 4.5 mm either side of each axis),
  extensor 4.98 mm dorsal, wrapping each knuckle over two crown points (95 deg on the parent, 85 deg on the child,
  radius 5).
- Where a line crosses a joint, each part cuts the union of the line's straight chord over the joint's whole range
  (every 10 deg) in its own frame (`fingerlib.crossing_cuts`). The cut is a groove in the knuckle face (open toward the
  gap, so it prints) and the line therefore never touches plastic at any angle — `channel_clear` checks it at home,
  each joint alone at full flexion and three curl poses.
- Channels are 2.2 mm with a 55 deg pointed roof (no supports). Clear diameter across a joint = 0.3 gap + 2 x 0.95
  groove = 2.2 mm.
- Moment arms at home: flexor 4.0 mm, growing as the joint bends (the chord moves away from the axis); extensor ~5 mm.
  Holding a 15 N tip force at full reach (60 mm from mcp, 21 from dip) needs roughly 15 x 21 / 4 ~ 80 N flexor
  tension at the dip alone — braided line >= 30 kg (~295 N) gives > 3x.
- Termination: both lines end in 3 mm knot pockets in the distal, open to the top face — tie a stopper knot, pull it
  into the pocket, wick CA in. Lines leave the base through its back face toward the actuator.

## 8. Strength

- Proximal hand check: 15 N at 44 mm -> M = 660 N mm; section 16 x 15 minus two channels ~ Z 550 mm3 -> 1.2 MPa,
  pin bearing 15 / (3 x 7.85) = 0.64 MPa. PETG XY strength / SF 2 is an order of magnitude above. FEA
  (`proximal_fea`) is the proof; result in the report.
- Pin: 3 mm steel in single shear, 15 N -> 2 MPa; irrelevant.

## 9. Assembly order

1. Press a dowel into the base knuckle (vise or a gentle tap; the hole is d + 0.05) until flush with the outer face.
2. Slide the proximal's knuckle onto the protruding pin end; check it swings freely.
3. Same for proximal -> middle and middle -> distal.
4. Thread the flexor from the base's back face through the palmar channel to the distal pocket; knot, pull in, CA.
   Same for the extensor along the dorsal channel.
5. Bolt the base to the hand frame with two M3 screws and nuts through its 16 mm holes.

## 10. Risks / measure first

- Pin fits: print one knuckle pair first. If the dowel will not press in, ream the parent hole with a 3.0 mm drill;
  if the free hole binds, run a 3.2 mm drill through it.
- Thin spots: the extensor's swept groove passes 0.8-0.9 mm from the pin hole on the knuckle faces only (0.95 mm
  deep); the rest of the 7.85 mm hole is full bearing. Watch for wear there.
- Single-shear joints rock slightly sideways under a hard side load (see section 2).
