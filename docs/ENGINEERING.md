# Engineering rules for Kerf Forge designs

These are the rules the part-designer follows and the design-reviewer judges against. Numbers marked (check) are
enforced by `kerf check`; the rest are judged by the reviewer from the code and renders. When a rule must be broken,
DESIGN.md says why.

## 1. Requirements first
- Every project starts with DESIGN.md: what it must do, in numbers (payload, reach, thrust, size, motion range, mass budget).
- Every number that decides pass/fail becomes a `requirements:` entry in project.yaml, so it is re-checked on every build.
- Size purchased parts with math in DESIGN.md (torque, thrust, current, speed) before drawing anything.

## 2. Materials (printed, FDM)
- Use catalog `materials.*` values. Printed parts are weakest across layers: design strength assuming the Z (layer)
  direction has about 50% of the XY strength unless the catalog gives a measured Z value.
- Default material PETG. Use CF-PETG or PA6-CF for stiff structural arms and frames; TPU only for bumpers/grips.
- Allowable stress = material tensile strength (in the loaded direction) / safety factor.

## 3. Safety factors (minimums)
| Situation | SF |
|---|---|
| Static load, printed part, load in XY | 2.0 |
| Static load across layers (Z) | 3.0 |
| Impact / crash-exposed (drone arms, landing legs) | 3.0 on the 2x-thrust or drop case |
| Servo/motor holding torque | ask <= 50% of stall torque (static_torque max_fraction 0.5) |
| Thrust-to-weight, multirotor | >= 2.0 to fly; freestyle quad >= 6 |

## 3b. Strength verification
- Every structural part gets an `fea_static` requirement: fixed where it is bolted (fastener group region), loaded
  where the load enters (joint/seat region), the realistic worst case x the factor in section 3, strength in the
  loaded layer direction. Deflection limits where stiffness matters (arms: tip deflection < 1% of length).
- Quick hand checks (`cantilever_stress`, beam formulas in DESIGN.md) are for sizing; FEA is the proof.
- If FEA fails, fix geometry (section depth, ribs, fillets, orientation) before reaching for a stronger material.

## 4. Print orientation and layers
- Choose `print_rot` so the largest flat face is on the bed and the main bending load runs along layers, not across them.
  Arms and beams lie flat. Hooks and brackets are oriented so the bend is in the XY plane.
- Overhangs over 45° need support (check warns over 3% of the surface). Prefer 45° chamfers, teardrop horizontal holes,
  and bridges under 15 mm. Projects can set `supports: avoid` to make any overhang a failure (check).
- Horizontal holes (axis parallel to the bed) print oval: use teardrop or add +0.2 mm, or orient holes vertically.

## 5. Walls and features
- Wall thickness >= 1.2 mm anywhere (check fails < 0.8 mm), >= 1.6 mm on structural parts, >= 2.4 mm around heat-set
  inserts and screw bosses (use catalog `fdm_holes` min wall where given).
- Inside corners on any load path get a fillet r >= 1 mm (stress concentration). Outside edges: 0.5–1 mm chamfer or fillet.
- No feature thinner than 2 nozzle widths (0.8 mm) unless it is a deliberate flexure.
- Text/labels: embossed >= 0.6 mm, stroke >= 0.8 mm.

## 6. Fits (mm, on diameter, for a 0.4 mm nozzle; prefer catalog `fdm_holes` values when present)
| Fit | Printed hole vs. part |
|---|---|
| Press fit (bearing, pin) | +0.0 to +0.1 |
| Snug slip (shaft that must turn by hand, removable) | +0.2 |
| Free running clearance | +0.3 to +0.4 |
| Sliding printed-on-printed | 0.3–0.4 gap per side |
| Heat-set insert | catalog hole size exactly |
Clearances between moving printed parts: >= 0.5 mm everywhere over the full motion range.

## 7. Fasteners
- Metric only, from the catalog. Prefer M3 (Spencer's workshop standard), M2/M2.5 for electronics, M4/M5 for big loads.
- Threads into plastic: heat-set inserts for anything assembled more than once or carrying load; self-tapping pilot
  holes only for light, rarely-removed parts. Nut traps where inserts don't fit.
- Edge distance: hole center >= 1.5 x screw diameter + wall from any edge. Boss outer diameter >= 2.2 x screw size.
- Every screw must be reachable by a hex key in the assembled order. Counterbore heads that would interfere.
- Use the same group name on both sides; `kerf check` proves alignment and picks a standard length.

## 8. Moving joints
- Every joint declares its range; the sweep must be collision-free over the full range (check).
- Revolute joints carrying load use a bearing or a metal pin/screw shaft, not plastic-on-plastic with a printed pin.
- Servo output carries torque only: support side loads with a bearing or a second pivot on the opposite side
  (a "dual-support" bracket) whenever the link is longer than ~60 mm or carries more than ~100 g.
- Leave 0.5 mm axial clearance (washers or printed spacers) between rotating faces.

## 9. Drones specifics
- Prop discs are keep-outs at the prop plane: >= 4 mm between neighbouring discs, >= 3 mm to any frame part, camera,
  stack or battery (check via prop_clearance / interference with keep-outs).
- Motor mount pattern and screw length from the catalog; screws must not reach the motor windings (use the catalog's
  max screw depth if listed).
- Stack mounted on soft-mount grommets when the catalog lists them; electronics boxed away from the prop wash debris.
- Arms: check root bending stress under max thrust x 2 (crash/aggressive) with SF from section 3.
- Battery: strap slots for a 20 mm strap, non-slip pad area, CG within 5 mm of the thrust center (X/Y).

## 10. Robot arm specifics
- Static torque at every joint, worst pose (arm horizontal, full reach, payload), <= 50% of stall (check).
- Base yaw carries the arm's weight and moment on a bearing or turntable, never on the servo spline alone.
- Cable path from base to wrist that survives the full motion range.
- Gripper: opening and grip force stated in DESIGN.md.

## 11. Assembly sanity
- An assembly order exists and is written in DESIGN.md (step list). Nothing must be inserted through a closed part.
- Every printed part fits the A2L bed in its print orientation (check) and the plate file packs them.
- Mass budget in DESIGN.md matches report.json within 10%.
