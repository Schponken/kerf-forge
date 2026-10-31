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
- Load the way the real part is loaded: `bearing_n` (cosine pressure on the half of a bore facing the load) for shaft
  and bearing seats, `torque_nmm` + `axis` for a servo/motor torque reaction, `pressure_mpa` for clamping or fluid
  pressure, `force_n` otherwise. Check `applied_force_n` / `applied_moment_nmm` in the report and look at
  `out/renders/fea_<id>.png`: the hot spot must sit where the load path says it should.
- Quick hand checks (`cantilever_stress`, beam formulas in DESIGN.md) are for sizing; FEA is the proof.
- If FEA fails, fix geometry (section depth, ribs, fillets, orientation) before reaching for a stronger material.
- Balance: `cg` gives the assembled CG (every item incl. purchased, plus a payload) against a reference line. Use it
  for a multirotor (CG within a few mm of the thrust centre, lateral) and for anything standing on a base (CG height
  `along`, worst over the arm's extreme poses). Printed parts act at their solid centroid, so keep ~1 mm margin.

## 4. Print orientation and layers
- Choose `print_rot` so the largest flat face is on the bed and the main bending load runs along layers, not across them.
  Arms and beams lie flat. Hooks and brackets are oriented so the bend is in the XY plane.
- Declare `load_axis` (part frame: `x`, `-y`, `[1, 0, 1]` or a list) on every structural part; `kerf check` warns when
  it runs more than 30° out of the bed plane in the print orientation and gives the cos² blended strength.
- Overhangs over 45° need support (check warns over 3% of the surface). Prefer 45° chamfers, teardrop horizontal holes,
  and bridges under 15 mm. Projects can set `supports: avoid` to make any overhang a failure (check).
- Horizontal holes (axis parallel to the bed) print oval: use teardrop or add +0.2 mm, or orient holes vertically.

## 5. Walls and features
- Wall thickness >= 1.2 mm anywhere (check fails < 0.8 mm), >= 1.6 mm on structural parts, >= 2.4 mm around heat-set
  inserts and screw bosses (use catalog `fdm_holes` min wall where given).
- Inside corners on any load path get a fillet r >= 1 mm (stress concentration). Outside edges: 0.5–1 mm chamfer or fillet.
- No feature thinner than 2 nozzle widths (0.8 mm) unless it is a deliberate flexure.
- Text/labels: embossed >= 0.6 mm, stroke >= 0.8 mm.
- Snap-fits and living hinges (`features.snap_hook`, `features.living_hinge`): bending strain <= 70% of yield strain
  (strength/modulus), x0.6 if taken apart often (Bayer snap-fit manual). Cantilever: eps = y h / (0.67 l^2), tapered to
  h/2: / (1.09 l^2). Living hinge: eps = t theta / (2 L). PETG/PLA hinges only bend ~20 deg; use TPU for 90 deg.
- Printed threads only >= M6 and pitch >= 1.0 (`features.threaded_rod/threaded_hole`, 0.4 mm diametral clearance);
  smaller threads go in heat-set inserts.

## 6. Fits (mm, on diameter, for a 0.4 mm nozzle; prefer catalog `fdm_holes` values when present)
| Fit | Printed hole vs. part |
|---|---|
| Press fit (bearing, pin) | +0.0 to +0.1 |
| Snug slip (shaft that must turn by hand, removable) | +0.2 |
| Free running clearance | +0.3 to +0.4 |
| Sliding printed-on-printed | 0.3–0.4 gap per side |
| Heat-set insert | catalog hole size exactly |
Clearances between moving printed parts: >= 0.5 mm everywhere over the full motion range.
These are textbook starting points. Spencer's real printer + material wins: `kerf calibrate` prints a fit coupon, `kerf feedback` stores measured offsets in `catalog/printers/`, and kerf/iface.py applies them to every screw hole, insert hole, bearing seat, servo window and pin hole it cuts (kerf/calibrate.py).

## 7. Fasteners
- Metric only, from the catalog. Prefer M3 (Spencer's workshop standard), M2/M2.5 for electronics, M4/M5 for big loads.
- Threads into plastic: heat-set inserts for anything assembled more than once or carrying load; self-tapping pilot
  holes only for light, rarely-removed parts. Nut traps where inserts don't fit.
- Edge distance: hole center >= 1.5 x screw diameter + wall from any edge. Boss outer diameter >= 2.2 x screw size.
- Every screw must be reachable by a hex key in the assembled order (check; write the order as `assembly.order`).
  Counterbore heads that would interfere.
  `kerf check` proves it (kerf/access.py): a straight hex key (ISO 2936 L-key reach, across-corners envelope) along
  each screw axis from the head must clear every item; a 25 deg ball-end path is a warning (put "ball-end key" in the
  build notes), no path at all is a failure. Parts that must slide into a pocket or window declare
  `insert: {direction, distance}` and the slide-in path is swept for collisions.
- Use the same group name on both sides; `kerf check` proves alignment and picks a standard length.

## 8. Moving joints
- Every joint declares its range; the sweep must be collision-free over the full range (check).
- Revolute joints carrying load use a bearing or a metal pin/screw shaft, not plastic-on-plastic with a printed pin.
  Pinned hinges use `iface.pin_hole` on every knuckle (`press` on the holding side, +0.05 mm; `free` on the turning
  side, +0.35 mm, catalog `fdm_fits.pin`); `kerf check` proves the holes coaxial, the pin axis = the joint axis, and
  picks a stocked pin length — make the knuckle span equal one (check).
- Servo output carries torque only: support side loads with a bearing or a second pivot on the opposite side
  (a "dual-support" bracket) whenever the link is longer than ~60 mm or carries more than ~100 g.
- Leave 0.5 mm axial clearance (washers or printed spacers) between rotating faces.
- Printed gears: `kerf.drives.spur_pair`; module >= 1.5 (>= 1.0 only on a tuned printer), >= 10 teeth, 0.3 mm total
  backlash at the standard centre distance (Sovol FDM gear guide: 0.2-0.4 mm). Couple the two joints in `sweeps:`
  (`follows`/`ratio`) so the sweep turns them together.
- GT2 belts: size the centre distance for a stock closed belt with `drives.center_for_belt`; keep >= 6 teeth in mesh
  on the small pulley (`drives.teeth_in_mesh`) and provide centre-distance adjustment (slotted mount or tensioner) for
  fitting the belt without forcing it over a flange (SDP-SI belt design guide,
  https://sdp-si.com/resources/beltdesignsuggestions.php). Tension snug, not preloaded.

## 9. Drones specifics
- Prop discs are keep-outs at the prop plane: >= 4 mm between neighbouring discs, >= 3 mm to any frame part, camera,
  stack or battery (check via prop_clearance / interference with keep-outs).
- Motor mount pattern and screw length from the catalog; screws must not reach the motor windings (use the catalog's
  max screw depth if listed).
- Stack mounted on soft-mount grommets when the catalog lists them; electronics boxed away from the prop wash debris.
- Arms: check root bending stress under max thrust x 2 (crash/aggressive) with SF from section 3.
- Battery: strap slots for a 20 mm strap, non-slip pad area, CG within 5 mm of the thrust center (X/Y) (`cg` check,
  `max_lateral_mm: 5` about the vertical line through the frame centre).

## 10. Robot arm specifics
- Static torque at every joint, worst pose (arm horizontal, full reach, payload), <= 50% of stall (check).
- Base yaw carries the arm's weight and moment on a bearing or turntable, never on the servo spline alone.
- Anything that stands on its own (arm base, landing legs) gets a `tip_over` requirement at its worst pose
  (arm stretched out with payload): >= 15 deg unless the brief says otherwise, or clamp/bolt it down.
- Cable path from base to wrist that survives the full motion range.
- Gripper: opening and grip force stated in DESIGN.md.

## 10b. Electrical (every project that moves or powers anything)
- Derive the whole electrical system, not only what the brief names: controller/FC, ESCs or drivers, receiver +
  antenna, VTX + antenna + camera for FPV, BEC/regulator for servos and logic, battery, strap + pad, power connector,
  switch/fuse where needed, sensors. Every one is a catalog item with a source (add it first).
- `power_budget` must pass: battery C rating at average and burst, every BEC/ESC output, connector and wire. Wire gauge
  from current: chassis ampacity (PowerStream table, catalog `wire.awg`) at the average current, and at the peak an
  adiabatic copper temperature rise over the burst (`burst_s`, default 5 s) of at most 60 K (40 C ambient to 100 C,
  half the 200 C rating of silicone insulation). Copper: 1.72e-8 ohm m and 0.00393 /K at 20 C (CRC via
  hyperphysics), 8.92 g/cm3 x 385 J/(kg K) (copper.org). A real, configured ESC/firmware current limit may cap the
  peak (`electrical.limits` with a why); never lower a rating.
- `flight_time` (drones, hover) or `run_time` (everything else) from 80 % of capacity (the LiPo 80 % rule, Flite
  Test). Hover power by momentum theory: P = sum(kappa x T^1.5 / sqrt(2 rho A)) / (FM x eta) with rho 1.225, figure
  of merit FM 0.5 (UIUC measured 0.38-0.61 on 2.5-5 in props, Deters & Selig 2008; 0.6 typical per Bauersfeld &
  Scaramuzza 2021, arXiv 2109.04741), motor efficiency eta 0.75 (same paper), kappa 1.281 for a coaxial pair at
  equal thrust (momentum theory, Simoes, IST). This is an estimate; measured motor tables beat it when catalogued.
- `connector_access`: the battery plug and the FC USB port are reachable with the device assembled.
- Every run declared in `wiring:` with gauge, colour and a cut length >= routed length + 15 %; route power runs
  through the frame's wire channels / keep-outs (`channel_clear` for enclosed channels).

## 11. Assembly sanity
- Tendon / wire channels are declared with `channel_clear` at the diameter of the tendon or wire plus clearance
  (bare wire or PTFE-sleeved tendon: add at least the free-running fit of section 6), at home and at the extreme poses.
- An assembly order exists and is written in DESIGN.md (step list). Nothing must be inserted through a closed part.
- Every printed part fits the A2L bed in its print orientation (check) and the plate file packs them.
- Mass budget in DESIGN.md matches report.json within 10%.
