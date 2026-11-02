# drone_foldable_wings: hawk-fold morphing-wing drone

Spencer's brief (Kerf Studio, 2026-11-01): "A drone that has foldable wings that allow it to fold out for long stable
UAV-like flight, and then on command it can fold the wings in like a hawk and allow it to do controlled dives. The
wings folding in and out should give it advanced control and air manoeuvrability. Mainly 3D printed parts."

Nobody was available to answer questions, so these were decided and are assumptions Spencer can change:
size class ~1.1 m span / ~1.1 kg (hand-launched, fits a car, prints on the A2L); 4S LiPo; the flight controller /
receiver / GPS family already used in this repo (F405-WMO + ELRS + M9N, INAV); no FPV camera (it is a UAV: GPS,
return-to-home, loiter); flown in dry weather.

Every number below is a param in project.yaml, a catalog value, or the result of the check named next to it.
Frame: X aft from the wing root leading edge at the centreline, Y right, Z up; wing root chord plane z = 0.

## How it works (plain words)

Each wing half is one rigid panel that pivots about a vertical steel pin at the corner where its root meets its
trailing edge. A servo inside the fuselage turns it through a printed 2:1 gear. Swept straight out (0 deg) the drone
is a normal efficient high-aspect-ratio plane for long, slow, stable flight. Swept back 70 deg the panels lie back
along the fuselage like a stooping hawk's wings: the span drops from 1.1 m to ~0.64 m, the lift slope drops ~75 %,
the aerodynamic centre moves far aft and the drone becomes a stable dart that dives fast and shrugs off gusts.
Pulling out is done the way a hawk does it: open the wings progressively as speed bleeds off. Sweeping one wing more
than the other moves that side's lift inboard and aft: roll and yaw on top of the ailerons, elevator and rudder.

## Requirements

| Requirement | Target | Check id |
|---|---|---|
| Span spread / folded | 1100 mm spread, <= 700 mm at full fold | `span`, (static_margin_tail_* report the span) |
| All-up mass | <= 1150 g | `auw` |
| Pitch stability, spread | static margin 8-20 % MAC (wing + tail NP) | `sm_spread` |
| Pitch stability, half sweep / folded / one side folded | stable (> 5 % MAC) everywhere; folded <= limit the elevator can still trim (below) | `sm_half`, `sm_folded`, `sm_asym` |
| Wing loading | <= 65 g/dm² (trainer / UAV class) | `wing_loading` |
| Stall speed (spread) | <= 40 km/h (hand launch) | `stall_speed` |
| Spar strength | 6 g pull-out, SF 1.5 on the low tube strength | `spar_bending` |
| Sweep servo vs air load | <= 50 % of stall x gear ratio, worst sweep angle, at the highest speed the wing must still move at | `fold_moment_r`, `fold_moment_l` |
| Sweep gears | Lewis bending at servo stall, SF 3 | `sweep_gears` |
| Mechanical stops | both sweep ends are real stops | `stop_spread_r/l`, `stop_fold_r/l` |
| Folded wing clear of tail and fuselage | >= 15 mm to the tail, no contact anywhere in the sweep | `fold_tail_clear_r/l` + motion sweeps |
| Thrust / weight | >= 0.7 (hand launch + climb) | `twr` |
| Flight time | >= 25 min level cruise at 50 km/h | `flight_time` |
| Electrical ratings | every wire, pad, BEC, connector, pack C | `power` |
| Structural parts | FEA at their real load cases | `hub_fea`, `spine_fea`, `deck_fea`, `mount_fea`, `tail_fea` |
| Battery plug reachable | through the hatch | `xt60_plug` |
| Prop clear | 5 mm to everything at every sweep | `prop_clear` |

## Operating envelope

| Wing | Use | Speed |
|---|---|---|
| spread 0 deg | launch, loiter, long-range cruise, landing | 40-80 km/h |
| 20-40 deg | fast cruise; pitch / roll trim by symmetric / asymmetric sweep | 70-100 km/h |
| 60-70 deg | dive (motor off or low); pull out by opening to ~35 deg, then spread below 80 km/h | up to ~140 km/h |

Hard rule (written into the INAV notes in ASSEMBLY): do not spread past ~35 deg above the manoeuvring speed
(~80 km/h, where the spread wing can already pull 6 g). The sweep servos are sized so the wing can still be opened
fully at that speed (`fold_moment_*`); above it they slow down and stall before the structure is at risk, which is
the safe direction.

## Architecture and why

Options considered (evidence in REFERENCES.md):
1. **Rigid panels on a root pivot (variable sweep), tailed airframe** - chosen. One joint per side, a pin in two
   plates, a gear and a servo: printable, inspectable, every load path provable. The EPFL LisHawk / LisEagle work shows
   sweep morphing extends the speed range and gives roll authority; a tail keeps the drone stable while the wing's
   aerodynamic centre moves.
2. Feathered / telescoping wing (LisHawk feathers, PigeonBot): closer to a bird, but dozens of thin overlapping
   printed parts that flutter, wear and cannot be proven with a pin-and-plate check. Rejected for a first build.
3. Tailless (flying wing) that sweeps: its neutral point IS the wing, so sweeping it back makes it massively
   nose-heavy with nothing to trim it. Rejected.

Pivot placement: on a panel swept back about a point, everything ahead of the pivot moves out and everything behind
it moves in. A pivot near the root leading edge would swing the root trailing edges into each other after ~20 deg.
So the pivot sits 10 mm ahead of the root trailing-edge corner (`pivot_back`): the whole panel swings out and back,
the two panels never meet, and only a 10 mm sliver behind the pin moves inboard (8 mm at full fold).

Airfoil MH 45 (catalog/airfoils, 9.85 %): its pitching moment is near zero (Cm0 -0.012), so sweeping the wing changes
the trim only through the aerodynamic-centre and CG shifts, which the tail handles; straight trailing edge (LE sweep
9.3 deg), 2 deg washout.

## Stability across the sweep

`static_margin_tail` (kerf/req_aero.py) puts the wing halves where the fold joints put them, measures the projected
wing (area, span, sweep), takes lift slopes from Raymer eq. 12.6, the tail's downwash 2a/(pi A), tail efficiency 0.9,
and the CG of the whole assembly at that pose (the wings' own mass moves aft with them).
Numbers: see "Results" (filled from out/report.json).

Trim through the sweep: sweeping back moves the neutral point aft faster than the CG, so the drone pitches nose
down as the wing folds. INAV gets a mixer rule elevator += k x sweep so the transition is trimmed automatically
(k measured on the first flights; start at the value in "Results"). The elevator's authority sets the upper limit on
the folded margin: with full up elevator (22 deg, tau 0.55 for a 34 % chord elevator) the folded drone must still
reach CL 0.15 (1 g at ~95 km/h) - that limit is the `max` of `sm_folded`.

## Purchased parts and sizing

(filled after research: see REFERENCES.md)

## Electrical system

(filled after research)

## Load -> section

| Part | Loads in / out | Peak moment and where | Section chosen | Along the part |
|---|---|---|---|---|
| spar tubes | lift along the panel -> hub sockets | root moment at the hub face (y 90) | 8x6 + 6x4 CF tubes sharing by EI | constant (stock tube) |
| hub (root fitting) | tube moments + shear in at the sockets; out through the boss into the pin (bearing couple between deck and spine arm) | lift moment ~7 N m about X + ~4 N m about Y at 6 g, carried as torsion + bending from the sockets (x 63 / 128) aft to the boss (x 200) | closed airfoil-shaped box (CF-PETG, 4 walls) with a solid web along the root rib, boss 20 mm OD x 37 mm tall | deepest at the sockets (airfoil 14-20 mm), boss column at the aft end, fillets r 3 where the web meets the boss |
| pin (4 mm stainless) | boss bearing pressure -> plates | radial ~ M / 43 mm per plate | 4 mm rod, double supported | - |
| spine (upper plate) | pin radial + lift up-force at the arm -> ridge -> 4 M3 into the aft fuselage | arm root where it leaves the ridge | 6 mm arm plate (in-plane load) on a 28 mm box ridge | arm wide at the ridge, tapering to the pin boss |
| aft fuselage deck (lower plate) | pin radial -> deck -> side walls + floor | deck root at the side walls | 6 mm plate with ribs down to the floor | ribs under the pins |
| aft fuselage | wing loads from deck + spine, tail loads from the boom socket | boom socket root | rounded box shell, 4 walls PETG | tapers to the socket |
| tail mount | stabiliser and fin loads -> boom | socket front edge | sleeve on the boom + plate | - |
| motor mount | thrust (tension) and torque | plate at the 4 bolts | 6 mm plate | - |

## Part list and print orientation

| Part | Material | Print | Notes |
|---|---|---|---|
| fwd_fuse | PLA 4 walls 15 % | standing on its aft face | nose face for the motor mount, battery bay + shelf, hatch opening and ledges |
| aft_fuse | PETG 4 walls 25 % | standing on its front face | pivot deck, sweep servo seats, open top closed by the spine, boom socket |
| spine | PETG 4 walls 30 % | upside down (flat top on the bed) | cover over the aft fuselage, ridge between the wing roots, arms over both pivots, stops, GPS pad |
| hatch | PLA 2 walls | upside down | lid over the forward bay |
| motor_mount | PETG 4 walls | flat (standing on its aft face) | 2806.5 pattern, 4 M3 to the fuselage nose |
| hub_r / hub_l | CF-PETG 4 walls 40 % | flat on its lower side (boss vertical) | root block + boss + gear sector + spar sockets + stop lug |
| pinion_r / pinion_l | PETG 100 % | flat | 14 T m1.5 gear on the aluminium micro horn |
| wing_r1/l1, wing_r2/l2 | PLA 1 wall 3 % | standing on the root / joint face | thin-wall skins on the tubes (as fpv_wing) |
| ail_r / ail_l | PLA 1 wall 5 % | standing on the inner end | tape hinge, horn |
| tail_mount | PETG 4 walls | standing on its front face | boom sleeve, servo pockets, stab and fin seats |
| hstab, elevator, fin, rudder | PLA 1 wall 5 % | flat / standing | NACA 0009, tape hinges |

## Part contracts (for the part-designers)

All parts are modelled in the aircraft frame at their home placement; shared numbers come from parts/layout.py
(`L.*` and the layout values in ctx.p: pivot_x, deck_z0/z1, boss_z0/z1, spine_arm_z0, gear_cd, pinion_x, sector_ro,
main_*/rear_* tube ends, boom_len ...). Do not hard-code what layout gives.

### Pivot system (aft_fuse, spine, hub_r/l, pinion_r/l) - one designer

- Pivot axis per side: `L.pivot_axis(p, s)` at (pivot_x 200, s*pivot_y 28), vertical. Stack along it: deck z -30.5..-24.5,
  0.5 gap, hub boss z -24..13, 0.5 gap, spine arm z 13.5..19.5 = 50 mm = the stocked 4 mm stainless rod
  (`rods.ss_rod_4`). `iface.pin_hole(ctx, "rods.ss_rod_4", loc, group="pivot_r"/"pivot_l", depth, fit)`: deck
  `press` (loc on the deck top, +Z up), hub boss `free` (loc on the boss top, +Z up, depth = boss height), spine arm
  `press` (loc on the arm top face z 19.5, +Z up, depth 6).
- Gears: `L.gears()` returns (pinion, sector gear) already phased: pinion at (pinion_x, s*pivot_y, L.PINION_Z0 = -24),
  10 mm wide; sector gear centred on the pivot axis at z L.SECTOR_Z0 = -23, 8 mm wide. Keep the sector's teeth over the
  arc the pinion meets during the sweep (right hub: angles 160..270 deg measured from +X counter-clockwise seen from
  above at home; left hub: mirror) plus the web back to the boss; cut the rest away. The pinion is bolted to the
  aluminium micro horn: `iface.horn_mount(ctx, "servo_horns.aluminum_micro_21T", loc, group="pinion_r"/"pinion_l",
  plate_t)` with loc on the pinion's top face (z -14) +Z up; child joint `horn` at the horn face (z -24) on the
  pinion axis. The coupling is in project.yaml sweeps (right ratio +2, left -2): checked tooth-clear at 0/10/23/35/70.
- Sweep servos (MG90S, output up, output end aft): `L.sweep_servo_loc(p, s)` is the servo's `tabs` frame; the
  aft_fuse declares rigid joints `sweep_servo_r/l` there and cuts `iface.servo_mount(ctx, "servos.MG90S", loc,
  group="sweep_servo_r"/"..._l", plate_t, kind="heatset" or "tap")` (servo drops in from above, tabs on a shelf).
- aft_fuse: outer skin lofted through `L.fuse_stations(p)` from x = fuse_joint_x to fuse_x1 (section at the joint =
  `L.section_face(p, fuse_joint_x)`, shared with fwd_fuse), 4 perimeters; top open between ~x 100 and 218 for the
  spine (rim with heat-set M3 inserts, group `spine`); front bulkhead at x 60 with 4 heat-set M3 at `L.JOINT_BOLTS`
  (group `fuse_joint`, screws come from inside fwd_fuse) and a wire pass-through; pivot deck = lower plate tied by
  ribs to the side walls and floor, kept out of: the boss (r 10 + 0.5) above z -24.5, the sector's sweep (r 22.5 + 1,
  z -23..-15), the pinion + horn (r 12 + 1 round the pinion axis, z -25.2..-14), the servos; boom socket bore
  (boom OD + 0.2, epoxied) from boom_x0 to fuse_x1 on the boom axis; joints: fwd, spine, tail (Location()), boom
  (`L.boom_loc`), pivot_r/l (`ctx.revolute(..., L.pivot_axis(p, s), range=(0, p.fold_max))`), sweep_servo_r/l.
- spine: cover plate over the aft-fuselage opening (top face flush with fuse_top - the wing roots pass 3+ mm above
  it; MH 45 lower surface is at z -6.7 at 20 % chord), with a 13 mm radius hole round each boss (the boss and the
  aileron lead pass); a ridge |y| <= 14 between the wing roots from x ~100 to ~225 up to z 19.5 (flat top: GPS pad,
  joint `gps` on it at x ~150); arms at z 13.5..19.5 from the ridge over each pin (pin bosses r ~8 round the pin). The
  arms must stay within ~20 mm of the pivot axis and above z 13.5: the hub's upper surface rises to z 15 further out.
  Bolted to the aft fuselage rim with >= 4 M3 (group `spine`).
- Stops (`hard_stop` both ends): the hub carries a stop lug; spread stop: no forward sweep past 0 deg; fold stop at
  fold_max (70). Suggested: a lug on the boss's aft side (pointing +X at home, z 0..13) hitting faces on the ridge /
  arm at -1 deg and at 71 deg; place it where the folded wing's air load (pushes aft) presses it onto the stop.
- hub_r / hub_l (CF-PETG): the panel's root block from y = pivot_y to hub_y1 (the `L.planform` airfoil, built with
  `aero.wing_solid`, same section as wing_*1 at y = hub_y1 so the skins meet flush) made into a strong closed box,
  plus the boss column (r 10, z boss_z0..boss_z1) on the pivot axis, the sector below the wing, spar sockets
  (blind bores tube OD + 0.2 from spar_y0 outward along `L.tube_line`, epoxied; >= 54 mm engagement) and the aileron
  lead channel from `L.lead_root(p, s)` on the outer face to `L.lead_exit(p, s)` on the underside beside the boss.
  Joints: `pivot` = `L.pivot_axis(p, s).location` (rigid, child side of fold_r/l), `wing` Location(), `main` /
  `rear` = `L.tube_loc(p, which, s)`. Must clear the spine (arms, ridge) and fuselage top (z -10) over 0..70 deg.
- Loads for FEA (DESIGN "Strength"): 6 g half-wing lift ~31 N at its centre of lift + the root moment; the hub is
  fixed at its boss bore; the deck and spine arm see the pin's bearing couple.

### Wings (wing.py x4, aileron.py x2) - one designer

Adapt projects/fpv_wing/parts/wing.py + elevon.py (same thin-wall approach, same aero helpers): inner segment
y hub_y1..seg_split_y, outer seg_split_y..semi (both sides). Spar bores OD + 0.3 along `L.tube_line` (main to
spar_main_y1, rear to spar_rear_y1). Aileron on the outer segment from ail_y0 to ail_y1, hinge at ail_hinge_frac
(`aero.elevon_split`), revolute joint `aileron` on wing_x2, `hinge` on ail_x; aileron servo (KST X08, lying flat,
output inboard) in a pocket of the outer segment between the spars just inboard of the aileron, joint `servo`
(its tabs frame), arm + 1.2 mm pushrod to a horn on the aileron. Lead channel from the pocket through the outer and
inner segment to `L.lead_root(p, s)` on the inner segment's root face. Inner segment joint `root` = Location(),
outer `joint` = Location(). Rounded wingtip on the outer segment. Segments glue to each other and to the hub.

### Tail (tail_mount, hstab, elevator, fin, rudder) - one designer

Boom: catalog rods.cf_tube_8x6 from boom_x0 to boom_x1 at z boom_z (-40). tail_mount: sleeve on the boom's last
~60 mm (bore OD + 0.2, epoxied), seat for the hstab underneath (hstab chord plane htail_z0 -50, `L.tail_planform`)
bolted by 2 M3 from below into heat-set inserts (group `hstab`), fin on top (fin root on the mount, 2 M3 or a glued
tab), elevator and rudder servos (KST X08) in pockets, short 1.2 mm pushrods. Joints on tail_mount: base, hstab, fin
(Location()), elev_servo, rud_servo (servo tabs frames). hstab: NACA 0009 planform from `L.tail_planform`, elevator
split at elev_hinge_frac with `aero.elevon_split` (one-piece elevator, full span; revolute `elevator`, child `hinge`).
fin: NACA 0009, fin_h / fin_root / fin_tip / fin_sweep_deg, TE at the boom end, rudder at rud_hinge_frac (revolute
`rudder` on fin, `hinge` on rudder). The folded wing tips pass at y >= 200 and z >= -10: keep the tail below z -30
outboard of |y| 150 (it is).

### Front (fwd_fuse, hatch, motor_mount) - one designer

fwd_fuse: lofted through `L.fuse_stations` from fuse_x0 to fuse_joint_x, 4 perimeters PLA; nose face at fuse_x0 with 4
M3 heat-set inserts (group `motor_mount`); aft bulkhead at fuse_joint_x with 4 M3 clearance holes at `L.JOINT_BOLTS`
(heads inside, group `fuse_joint`) + a wire pass-through; battery bay on the floor (4S 1500, 80 x 39 x 28) centred at
bat_x with a strap slot pair; shelf above it carrying ESC, FC, receiver; hatch opening on top (x ~-180..40, |y| < 24)
with ledges, hatch held by a front tongue + 2 M3 (group `hatch`). Joints: aft, hatch, motor_mount (Location()),
battery, xt60, esc, fc, rx (each box proxy's `bottom`). motor_mount: 6 mm PETG plate with `iface.motor_mount` for
the 2806.5 (screws from its aft face, motor screwed on first), 4 M3 into the nose inserts; joint `motor` = the motor
base frame (+Z forward, -X world).

## Interfaces

| Between | How | Group |
|---|---|---|
| aft_fuse - fwd_fuse | 4 M3 from inside fwd_fuse into heat-set inserts in aft_fuse's front bulkhead | fuse_joint |
| aft_fuse - spine | >= 4 M3 into heat-set inserts in the aft fuselage rim | spine |
| aft_fuse / spine - hub | 4 mm stainless pin pressed in deck + spine arm, free in the boss | pivot_r / pivot_l |
| aft_fuse - sweep servo | MG90S tabs, 2 M2 | sweep_servo_r / sweep_servo_l |
| horn - pinion | 4 M2 through the pinion into the aluminium micro horn | pinion_r / pinion_l |
| hub - spar tubes | blind sockets, epoxy | - |
| hub - wing_x1 - wing_x2 | glued faces + tubes | - |
| wing_x2 - aileron | bottom tape hinge, pushrod | joint ail_r / ail_l |
| fwd_fuse - motor_mount | 4 M3 into nose inserts | motor_mount |
| motor_mount - motor | 4 M3 from the mount's aft face, on the bench first | motor |
| fwd_fuse - hatch | front tongue + 2 M3 | hatch |
| aft_fuse - boom - tail_mount | sockets, epoxy | - |
| tail_mount - hstab | 2 M3 from below into inserts | hstab |
| tail_mount - fin | 2 M3 / glued tab | fin |

## Joint tree

aft_fuse (root) -> fwd_fuse (-> hatch, motor_mount -> motor -> prop, battery, xt60, esc, fc, receiver), spine (-> gps),
boom, tail_mount (-> hstab -> elevator, fin -> rudder, elev_servo, rud_servo), sweep servos -> horns -> pinions,
**fold_r / fold_l** (0..70 deg) -> hub -> wing_x1 -> wing_x2 -> aileron (+-20), aileron servo, spar tubes.
Couplings: sweep_srv_r = +2 x fold_r, sweep_srv_l = -2 x fold_l (the 2:1 gear).

## Assembly order

(filled from ASSEMBLY.md after the build)

## Risks / measure first

(filled after the build)
