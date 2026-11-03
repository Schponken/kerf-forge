# hawk_wing: swing-wing FPV plane (outboard pivot on a fixed glove)

Spencer's brief (Kerf Studio, 2026-11-02): a ~1 m fixed-wing FPV drone whose wings sweep back in flight like a hawk's
(spread for slow efficient cruise, thermals and soft landings; half swept for speed; folded for a straight stable dive
and smooth pull-out; uneven sweep for roll), forgiving and predictable in every shape, wings spread on signal loss,
hand / bungee launch, 12+ min mixed flying, cheap parts break first, wings / tail swappable in the field with one
tool, wings off for a backpack case, printed in PETG on a Bambu A2L. He picked the quote's option 0: outboard-pivot
sweep on a fixed "shoulder" glove (F-14 style), conventional tail.

Every number below is a param in project.yaml, a value in parts/layout.py, a catalog value, or the result of the check
named next to it. Frame: X aft from the glove's leading edge at the centreline, Y right, Z up; root chord plane z = 0.

## Assumptions (decided, nobody to ask; Spencer can change them)

1. **Size held at 1.0 m.** With PETG, a 6S pack, FPV gear and two pivot drives it comes to ~1.65 kg on 20 dm2: about
   82 g/dm2 and a ~40 km/h stall. It flies and lands like a sport FPV plane, not a floater: floating in gentle thermals
   would need ~55-65 g/dm2 (1.3-1.4 m span or LW-PLA skins). The folding-wing-glider study Spencer asked for confirms
   this (REFERENCES.md: 2 m thermal models run 26-38 g/dm2; sink rate goes as the square root of loading, so this one
   sinks ~2x faster at best glide). "Spread" is sold as slow, stable cruise and soft landings, not thermalling.
2. **Power: 6S 1800 + iFlight 2806.5 1300 KV + HQ 7x4x3** (the quote's set, catalog-sourced), Skywalker 60A V2.
3. **Stress simulations are paused repo-wide** (PAUSED.json, Spencer 2026-11-02). Every `fea_static` here reports
   PAUSED: the strength of the glove corner, pods, caps and hubs is designed by the load path and the hand checks
   below but is UNPROVEN until FEA is resumed. Nothing here is called strong because a paused check shows no failure.
4. Flown in dry weather; no rain cover. Radio, goggles, charger not included.

## How it works (plain words)

The inner wing (the "glove", 300 mm wide) is fixed to the fuselage. Each outer panel (350 mm) turns about a vertical
steel pin at the glove's trailing-edge corner: the pin sits in a small nacelle (the "pod") under the glove, and the
panel's root fitting (the "hub") turns on it in two ball bearings 28 mm apart. A standard servo (MG996R) standing in
the pod turns the panel through a printed 13-tooth pinion and a 21-tooth sector gear on the hub: 105 deg of servo
travel = 65 deg of sweep. Spread (0 deg) it is a normal straight wing; half swept (32 deg) it is faster; folded
(65 deg) the panels lie back along the fuselage for a fast, straight dive. One side swept more than the other moves
that side's lift in and back: extra roll and yaw on top of the ailerons (which stay, because uneven sweep is weak at
low angle of attack: LisEagle, Wanner 2026, REFERENCES.md).

Because the glove's lift never moves, sweeping moves the wing's lift centre ~136 mm (strip model, sm_* details)
instead of ~300 mm for a root pivot (NASA: the outboard pivot is what made swing wings practical, Luckring 2016,
REFERENCES.md). The tail does the rest: the plane stays pitch-stable in every shape, and the flight controller holds
the trim (INAV angle / cruise mode; a mixer feed-forward per degree of sweep, "Flight controller setup" below).

A panel comes off in the field with one 2.5 mm hex key: two M3 screws hold the pivot cap; under it is the aileron
servo plug; unplug, lift the panel straight up off the pin (the sector gear slides out of the pinion). The tail boom
slides out of the fuselage after one more M3 (the boom clamp) and two servo plugs.

## Requirements

| Requirement | Target | Check id |
|---|---|---|
| All-up mass | <= 1800 g | `auw` |
| Wing loading | <= 95 g/dm2 (sport FPV, swing-wing class) | `wing_loading` |
| Stall speed spread | <= 45 km/h (belly landing on grass) | `stall_speed` |
| Pitch stability spread | static margin 8-20 % MAC | `sm_spread` |
| Pitch stability half / folded / uneven | >= 5 % MAC, and <= what full up elevator can trim ("Trim limits") | `sm_half`, `sm_folded`, `sm_asym` |
| Spars | 6 g, SF 1.5 | `spar_bending` |
| Sweep servo vs air load | <= 50 % of stall x 21/13 at the worst sweep angle: 4 g pull at 84 km/h, opening at 150 km/h | `fold_pull_*`, `fold_dive_*` |
| Sweep gears | Lewis bending at MG996R stall, SF 3 | `sweep_gears` |
| Real stops at both ends | spread and folded | `stop_spread_*`, `stop_fold_*` |
| Folded panel clear of the tail | >= 15 mm | `fold_tail_clear_*` |
| Folded panels never in the FPV view | >= 10 mm from the view cone | `view_clear_*` |
| Prop clear | 5 mm to everything at every sweep | `prop_clear` |
| Thrust / weight | >= 0.8 (hand launch) | `twr` |
| Flight time | >= 20 min level cruise = ~12 min mixed ("Flight time") | `flight_time` |
| Electrical | every wire, BEC, connector, pack C | `power` |
| Battery plug reachable | through the hatch | `xt60_plug` |
| Wings off: body in a backpack case | <= 500 x 330 x 220 mm | `case_fit` |
| Field repair | caps, boom clamp, nose off with a hex key on the finished plane | `story_field_repair` |

## Operating envelope

| Wing | Use | Speed |
|---|---|---|
| spread 0 deg | launch, cruise, landing | 40-80 km/h |
| half 25-40 deg | fast passes; uneven sweep adds roll | 65-110 km/h (elevator trims it down to ~49 km/h) |
| folded 55-65 deg | dive, motor low; pull out by opening to half, then spread below ~80 km/h | 75-150 km/h (elevator holds 1 g down to ~75 km/h folded) |

Rule for the pilot (also in ASSEMBLY): fold only above ~90 km/h; to pull out of a dive, open to half sweep first.

## Architecture and why

Options (the quote, evidence in REFERENCES.md):
1. **Outboard pivot on a fixed glove (F-14), conventional tail** - chosen by Spencer: the smallest lift-centre shift
   (Luckring 2016), so the most predictable trim through the sweep; one pin + two bearings + one gear per side.
2. Root-pivot whole-wing sweep (the repo's drone_foldable_wings): the most bird-like and the biggest span change, but
   its measured static margin goes 15 % -> 82 % -> 159 % (spread / half / folded): far more trim change.
3. Feathered / tendon fold (LisHawk, LisEagle, PigeonBot): dozens of thin parts, fragile, unprovable with a pin check.
Folding-wing gliders (Spencer's note): chordwise fold hinges and tape hinges give no sweep for a straight dive and were
rejected; their spring-to-spread idea was considered and NOT adopted (a spring would add ~ its own torque to the
servo's hold load at 65 deg, and an unpowered MG996R's gear train does not back-drive anyway, so the spring would not
open a dead-servo wing); the failsafe is the INAV logic condition below plus the real spread stop.

Pivot placement: the pin is pivot_back = 24 mm ahead of the trailing edge at the panel root (y = pivot_y = 150). On a
panel swept back about a point, everything ahead of the pin swings OUT and back and only what is behind it swings in.
Behind the pin the hub is a round "elbow" disc (r 24) centred on the pin, so it turns in place inside a matching
round notch in the glove's trailing-edge corner: nothing ever swings into the glove. The gears sit under the wing
in the pod; the pinion is straight ahead of the pin (same y), so the servo lies along X in a slim nacelle.

Airfoil MH 45 (catalog/airfoils, 9.85 %): near-zero Cm0 (-0.012), so trim changes only through the lift-centre and CG
shifts, which the tail handles; straight trailing edge (LE sweep 13.5 deg), 2.5 deg washout.

## Stability across the sweep (sm_* checks)

`static_margin_tail` moves the outer strips (|y| >= pivot_y) with the hubs, keeps the glove strips fixed, takes lift
slopes from Raymer eq. 12.6 for the projected wing, downwash 2a/(pi A), tail efficiency 0.9, and the CG of the whole
assembly at that pose (the panels' mass moves aft with them). On the stub masses (2409 g; finished numbers in
"Results"): spread 11.3 %, half 41.2 %, folded 94.1 %, uneven 40.1 % of the 206 mm MAC; NP x 138 -> 214 -> 338 mm,
wing AC x 105.5 -> 172 -> 241 mm, tail volume 0.47.

**Trim limits** (the `max` of sm_half / sm_folded / sm_asym): the most margin full up elevator can trim at a lift
coefficient CL is SM_max = eta_t V_h a_t tau d_max / CL = 0.9 x 0.47 x 3.23 /rad x 0.55 (35 % chord elevator) x
22 deg (0.384 rad) / CL = 0.289 / CL. Half / uneven: flown down to 70 km/h, CL = 16.2 N / (231.5 Pa x 0.2 m2) = 0.35
-> 0.82. Folded: flown above 90 km/h, CL = 16.2 / (382.8 x 0.2) = 0.21 -> 1.36. At the stub margins the elevator holds
1 g half swept down to 49 km/h and folded down to 75 km/h.

## Purchased parts and sizing

| Item | Catalog | Why / sizing |
|---|---|---|
| Motor | drone.motors.2806_5_1300kv_7in | iFlight test: 2319 g with the HQ 7x4x3 at 23.42 V; `twr` scales it to the pack voltage |
| Prop | drone.props.hq_7x4x3 | the prop the motor was tested with; a $1 break-first part (belly-landing strike is an accepted risk) |
| Battery | drone.batteries.6S_1800 | 302 g, 40 Wh; flight time below |
| ESC | drone.escs.skywalker_60a_v2 | 60 A / 80 A, 3-6S; its 5 V 7 A switch BEC feeds ONLY the two sweep servos (2 x 2.5 A stall) |
| FC | drone.fcs.f405_wmo | INAV plane FC: 90 A current sensor, Vx BEC 4.5 A (6 V jumper) for the 4 surface servos, 4V5 2 A for receiver, GPS, VTX, camera |
| Receiver / GPS / camera / VTX / antenna | elrs_nano / m9n_5883 / micro_19mm / tx800 / lollipop4p_mmcx_95 | FPV + return-to-home |
| Sweep servos | servos.MG996R x 2 + servo_horns.aluminum_25T | 9.4 kg cm stall at 4.8 V x 21/13 = 15.2 kg cm at the panel; 50 % = 7.6 kg cm vs 3.24 needed (fold_pull) |
| Surface servos | servos.KST_X08_Plus x 4 | ailerons (in the panels), elevator, rudder: 3.85 kg cm at 6 V, 8 mm thick |
| Pivot pin | rods.ss_rod_5, 50 mm stocked | pressed into the pod floor plate, slip fit in the cap (REFERENCES.md: soft stainless, measure the real rod) |
| Pivot bearings | bearings.625 x 4 | 5 x 16 x 5; C0 380 N (SKF, the lowest published) |
| Spars / boom | rods.cf_tube_8x6 (main, boom), rods.cf_tube_6x4 (rear) | `spar_bending`; boom: tail loads below |

**Pivot bearing load.** At 6 g (1.65 kg, elliptical lift) the outer panel carries 31 N at 145 mm outboard of the pin
and ~100 mm ahead of it: roll moment 4.5 N m, pitch moment 3.1 N m, resultant 5.5 N m, carried as a couple on the
two bearings 28 mm apart: 196 N each, against C0 380 N (static safety 1.9 at 6 g, 2.9 at 4 g). The lift itself (31 N
up) goes through the upper bearing's inner race into the cap.

**Sweep actuator sizing** (`fold_*`). The pin is normal to the chord plane, so lift makes no moment about it; the
servo holds the panel's chordwise force times its arm, integrated strip by strip over the real panel, worst over
0-65 deg: (a) a 4 g pull at the manoeuvring speed 84 km/h (= stall 42 x sqrt 4) at CL ~1.0: chordwise coefficient cd
cos a - cl sin a = 0.11 x 0.98 - 1.0 x 0.19 = -0.08 (forward); (b) opening the folded wing in a 150 km/h dive (about
the prop's pitch speed on 6S): CL 0.05, cd 0.015 (aft). Ball bearings + gear mesh: 20 N mm friction added to both.
Results on the real panel: 3.24 kg cm (pull) and 2.02 kg cm (dive) at the pin vs 7.59 allowed: the MG996R uses 43 %
and 27 % of half its stall. At full spread the forward pull presses the panel onto its spread stop; folded the drag
presses it onto the folded stop: only moving or holding in between loads the servo.

**Flight time** (`flight_time`, electrical.cruise): cruise power P = W V / (L/D) / eta at 55 km/h with L/D 8 and eta 0.45
(the sibling's values) = ~65 W + ~8 W electronics. The brief's 12+ min is MIXED flying: assumed 40 % cruise, 25 % half
swept at 2x cruise power, 15 % climbs at ~4x, 20 % dives / glides at idle: average = 0.4 + 0.5 + 0.6 + 0 = ~1.5x cruise
power, +10 % for sweep servos and turns = ~1.65x. So >= 20 min of level cruise on 80 % of the pack is ~12 min mixed.

## Electrical system

Power tree: battery (6S 1800, XT60) -> FC BAT pads (90 A current sensor) -> FC ESC pads -> ESC -> motor; ESC 5 V BEC ->
both sweep servos (its red wire off the FC's motor plug); FC Vx (6 V jumper) -> 4 KST surface servos; FC 4V5 ->
receiver, GPS, VTX, camera. Wire gauges from the peak currents (`power`, docs/ENGINEERING.md 10b). Each aileron lead
runs through its panel and hub to a plug under the pivot cap; the glove-side extension runs through the glove to
the FC. Sweep-servo leads leave each pod into the glove and fuselage. Tail servo leads run along the boom under
heat-shrink and plug in at the fuselage tail.

**Failsafe to spread** (REFERENCES.md, INAV docs): INAV holds the last RC values in failsafe, so a sweep servo on an
RC channel would stay where it was. A logic condition `Is Failsafe` (flight operand 24) drives `Override RC Channel`
(action 38) on the sweep channel to the spread value; `failsafe_procedure = RTH` (GPS home) with LAND as the fallback.
Bench-test it with the props off (the docs do not say the override applies during failsafe).

## Flight controller setup (INAV, starting values)

- Sweep: one RC channel (slider / 3-position switch) -> both sweep servos through the servo mixer (`smix`, RC channel
  input), the left one reversed; roll stick adds +-15 deg of uneven sweep (RC ROLL input, weight ~0.25) at half / folded.
- Pitch trim feed-forward: elevator += k x sweep with k ~ 0.16 deg of elevator per deg of sweep at 90 km/h (the margin
  change 0.30 MAC x CL 0.23 / (eta_t V_h a_t tau 0.75), DESIGN "Trim limits"); INAV's pitch loop holds the rest.
- Failsafe as above; angle limits stock.

## Load -> section

| Part | Loads in / out | Peak moment and where | Section chosen | Along the part |
|---|---|---|---|---|
| spar tubes | panel lift -> hub sockets | root moment at the hub face (y 195) | 8x6 + 6x4 CF sharing by EI | stock tube |
| hub (panel root) | tube moments + shear in at the sockets (x 100 / 171); out through the boss into two bearings | 5.5 N m at 6 g carried from the sockets aft to the boss (x 236) as torsion about X + bending | closed airfoil box over the sockets; aft of the rear spar a raised closed box (top up to the boss top z 6, flat underside z -2) so the section stays >= 8 mm deep to the boss; boss r 11, 33 tall | deepest at the sockets, raised box to the boss, fillets where it meets the boss |
| pin (5 mm steel) | bearing couple 196 N each end -> pod floor (bottom), cap (top) | - | stock rod | - |
| pod (nacelle) | pin's lower reaction 196 N + servo torque reaction -> glove (2 front M3 + 2 cap M3) | where the floor plate meets the pod walls | deep closed box round the servo; 8 mm floor plate under the boss tied to both side walls by ribs | deepest at the servo, sloping up to the trailing edge |
| cap | pin's upper reaction 196 N + 31 N lift -> 2 M3 through the glove into the pod | the bridge between the pin and the screws (31 mm) | 8 mm plate with a raised spine, hollow fairing round the plug | thick at the pin boss, tapering to the screw pads |
| glove | both panels' moments via pods + caps; lift; fuselage below | spanwise bending at the centreline (~6 N m at 6 g); local: the trailing-edge corner round the notch | closed airfoil box (3 walls), internal ribs at the fuselage sides and at each pod's screws; flat pads at each pod | constant section; ribs where loads enter |
| fuselage | glove (4 M3), battery 302 g, motor thrust + torque via the mount, tail via the boom | boom socket root; nose bulkhead | rounded box shell, 3 walls, floor + shelf as frames | tapers to the socket |
| motor mount | thrust 21 N, torque | flange at the bulkhead screws | stand-off tube + plate | - |
| tail mount | stab / fin air loads -> boom | socket front edge | sleeve on the boom + seat (sibling) | - |

Hand check (cantilever_stress once the parts exist): the cap bridge at the pin boss under 196 N, the pod floor
plate's root under 196 N.

## Part list and print orientation

| Part | Material | Print | Notes |
|---|---|---|---|
| fuselage | PETG 3 walls 15 % | standing on its tail end | bay, shelf, front bulkhead, saddle, boom socket |
| nose | PETG 2 walls 10 % | standing on its aft face | camera fairing round the motor stand-off; break-first |
| motor_mount | PETG 4 walls 40 % | standing | stand-off from the bulkhead to the motor plate |
| hatch | PETG 2 walls | upside down | battery hatch, front tongue + 1 M3 |
| boom_clamp | PETG 4 walls 50 % | flat | one M3 + a tongue over the boom socket |
| glove | PETG 3 walls 10 % | standing on its leading edge (span along the bed: spanwise bending in the layers) | centre wing, pivot notches, pod pads, GPS pocket |
| pod_r / pod_l | PETG 4 walls 40 % | upright | sweep servo nacelle, pin floor plate, stops |
| cap_r / cap_l | PETG 4 walls 50 % | upside down | pin top, plug fairing |
| hub_r / hub_l | PETG 4 walls 50 % | flat (boss vertical) | panel root, elbow disc, boss + bearings, sector, sockets |
| pinion_r / pinion_l | PETG 100 % | flat | 13 T on the alu horn (sibling part) |
| wing_r1/l1, r2/l2 | PETG 1 wall 3 % | standing on the root / joint face | thin-wall skins on the tubes (sibling) |
| ail_r / ail_l | PETG 1 wall 5 % | standing | tape hinge |
| skid_r / skid_l | PETG 2 walls 15 % | standing | wingtip skid, glued: break-first |
| tail_mount, hstab, elevator, fin, rudder | PETG | as the sibling | tail surfaces are break-first |

## Part contracts (for the part-designers)

All parts are modelled in the aircraft frame at their home placement. Shared numbers come from parts/layout.py (`L.*`)
and the layout values in ctx.p (pivot_x 236.0, pinion_x 202.0, gear_cd 34, main_*/rear_* tube ends, boom_len...). Do
not hard-code what layout gives. Right side numbers below; the left side is the mirror (y -> -y).

### Pivot system (pod.py, cap.py, hub.py; pinion.py exists) - one designer
- Pin axis vertical at (pivot_x 236, pivot_y 150). Stack: pod floor plate z -35.5..-27.5 (`L.POD_FLOOR_Z0/Z1`, pin
  pressed 8 mm: `iface.pin_hole(ctx, L.PIN, loc on the plate top z -27.5 +Z up, group "pivot_r", depth 8, fit "press",
  through=False)`), 0.5 gap, hub boss z -27..6 (`L.BOSS_Z0/Z1`, r `L.BOSS_R` 11), 0.5 gap, cap z 6.5..14.5
  (`L.CAP_Z0/Z1`, `pin_hole(..., loc on the cap's underside z 6.5 with +Z DOWN (out of the material), group "pivot_r",
  depth 8, fit "free", through=False)`). The pin (rod item pin_r, 50 mm) runs z -35.5..14.5.
- Bearings: two 625 pressed into the boss ends: `iface.bearing_seat(ctx, L.BEARING, loc, fit="press")` from the top
  face (z 6, +Z up) and from the bottom face (z -27, +Z down); the pin passes through (`through` clearance between).
  Hub joints `bear_top` = L.pin_loc(p, s, BOSS_Z1 - 5), `bear_bot` = L.pin_loc(p, s, BOSS_Z0) (already in the stub).
  Axial: a 0.5 mm ring (r 3.2..5) on the cap underside and on the pod floor plate touches only each bearing's INNER
  race (stationary on the pin), so lift and weight go through the races, never hub-on-plastic rubbing.
- Gears: `L.gears()` (pinion, sector) phased to mesh at home: pinion (pinion.py, exists) at (pinion_x, s*pivot_y,
  L.PINION_Z0 -16.5), 11 wide; sector gear centred on the pin at z `L.SECTOR_Z0` -16..-6, teeth over hub angles
  `L.sector_deg(p)` = 168..257 deg (right, CCW from +X seen from above; left mirrored), web back to the boss.
- Stops: kerf's hard_stop measures the fold joint's parent (pod) against its child (hub): two posts on the pod that the
  sector's radial end faces meet just past 0 deg (spread) and just past 65 deg (folded); `stop_spread_*` beyond -3,
  `stop_fold_*` beyond 68 must collide, and NOTHING may touch between -0.5 and 65.5 deg (keep >= 0.5 mm everywhere in
  the sweep: the sibling's review failed on zero-clearance rubs).
- **pod_r / pod_l** (nacelle under the glove's trailing-edge corner): MG996R standing output up, tabs frame
  `L.sweep_servo_loc(p, s)` (output on the pinion axis, output end aft; body x 171..212, y 140..160, z -59.7..-22.7,
  tabs x 164.6..218.6), `iface.servo_mount(ctx, "servos.MG996R", loc, group "sweep_servo_r", plate_t, kind
  "heatset" or "tap")`; servo goes in before the pod is bolted on. Roof top at z `L.POD_ROOF_Z` -3: bolted flat to the
  glove's underside pad (z -3) inboard of y 149.5; under the panel (outboard of y 150 and inside the notch) the roof is
  a free surface 1 mm below the hub's disc (hub disc underside z -2). Round roof opening r `L.POD_OPEN_R` 24.5 round
  the pin (the sector passes through when the panel is lifted off) and the roof must clear the pinion + horn (r 15 +
  1 round the pinion axis, z -17.5..-4.5) and the sector's swept band (r 23 + 1, z -16.5..-5.5). Fasteners: 2 M3
  heat-set inserts in the roof at `L.cap_screw_xy(p, s)` = (224, 119), (248, 119) for the cap screws (group "cap_r",
  screws from the cap's top through the glove), 2 M3 clearance holes from below at `L.pod_screw_xy(p, s)` = (162,
  130), (195, 126) into the glove's inserts (group "pod_r"). Joints (already in the stub): base, servo, pin
  (L.pin_loc at the plate bottom z -35.5), pivot (`ctx.revolute("pivot", L.pivot_axis(p, s), range=(0, p.fold_max))`).
  Shape: a nacelle, x ~158 to the trailing edge 260, deep (to z ~ -62) round the servo, sloping up to the floor
  plate (bottom ~ -38) at the pin; y from ~114 (cap-screw inserts) to ~176 (sector sweep r 23 + wall). Must stay
  above z -64 (fuselage belly -70) and clear the hub over the whole sweep.
- **cap_r / cap_l**: bridge from the 2 screw pads (cap screws, M3 counterbored from the top, length from the fastener
  check) over the hub to the pin's top (boss round the pin bore, underside z 6.5 where it is over the hub, following
  the glove's top surface where it sits on the glove). Hollow streamlined fairing on top (z up to ~16) holding the
  aileron plug: the hub's lead leaves the hub top at `L.LEAD_EXIT_D` (-14, +3) from the pin (r 14.3) and swings on an
  r 14.3 arc through 65 deg as the panel folds, so the cap's underside opening covers that arc (r 11..18, hub angles
  ~148..213 deg world); the glove-side lead comes up through the glove top at (pivot_x - 6, pivot_y - 20). Must clear
  the hub (>= 0.5 mm) over 0..65 deg.
- **hub_r / hub_l** (PETG 50 %): panel root block from y 150 (root face; the glove ends at 149.5) to hub_y1 195, same
  `L.planform` airfoil (the inner skin segment wing_x1 meets it flush at 195), closed box; spar sockets (blind bores
  tube OD + 0.2, epoxied) from spar_y0 156 outward along `L.tube_line`; aft of the rear spar a raised closed box up to
  z 6 with a flat underside at `L.HUB_DISC_Z0` -2; the elbow disc r `L.DISC_R` 24 round the pin (inboard half too:
  it fills the glove's notch r 25) with that flat underside; boss r 11 z -27..6; the sector below (z -16..-6) joined
  to the boss by a web. Aileron lead channel (4 mm) from `L.lead_root(p, s)` (190, 195, mid-thickness) to the exit at
  `L.LEAD_EXIT_D` on the hub top. Joints: as the stub (pivot, wing, main, rear, bear_top, bear_bot). Must clear the
  glove (>= 0.5 mm), pod and cap over 0..65 deg, and lift straight up off the pin with the cap removed.

### Glove (glove.py) - one designer
Centre wing |y| <= 149.5 (`aero.wing_solid(L.planform(p), -149.5, 149.5, stations=3)`), PETG 3 walls 10 %: closed
box with internal ribs at |y| ~34 (fuselage sides) and round each pod's screws; notch r `L.NOTCH_R` 25 round each pin
(full height); flat pad on the underside at z `L.POD_PAD_Z` -3 over each pod footprint (x 156..260, |y| 112..149.5),
with 2 M3 heat-set inserts per side at `L.pod_screw_xy` (from below) and 2 clearance holes per side at
`L.cap_screw_xy` (cap screws pass through); 4 counterbored M3 clearance holes from the top at `L.GLOVE_SCREWS` (group
"glove") into the fuselage's inserts; saddle: the underside where it sits on the fuselage stays the airfoil (the
fuselage is cut to it); GPS pocket under the top skin at `L.gps_loc` (32 x 32 x 10 + 0.5), open from below; VTX antenna
hole (14 mm) at (L.VTX_X 205, 0) top to bottom; aileron-lead channel (5 mm) from (pivot_x - 6, +-(pivot_y - 20)) at the
top skin inboard to the fuselage (exits the underside at |y| < 25, x ~200); sweep-servo lead hole from each pod pad
(x ~165, |y| ~ 125) inboard to the fuselage. Joints as the stub. Print standing on its leading edge (layers carry the
spanwise bending). Must clear the hubs (>= 0.5 mm) over 0..65 deg.

### Body (fuselage.py, nose.py, motor_mount.py, hatch.py, boom_clamp.py) - one designer
Fuselage from the front bulkhead at nose_x1 -120 to fuse_x1 300 through `L.fuse_stations` (rounded rectangles),
3 walls: battery bay floor at `L.BAY_FLOOR_Z` -66 with 2 strap slots at bat_x +- 20 (pack 87 x 58 x 34 on its pad),
shelf at `L.SHELF_TOP` -25 (2 mm, x -110..0) for ESC / FC / receiver (`L.item_locs`), hatch opening on top x -112..-8,
|y| < 27 with ledges; front bulkhead at -120 with 4 M3 heat-set inserts for the motor mount (group "motor_mount") and
a wire hole; saddle under the glove (cut by the glove solid + 0.3), with 4 heat-set inserts at `L.GLOVE_SCREWS`; boom
socket from boom_x0 215 to fuse_x1 300 (bore 8.2, dry slip fit) with an open top slot the boom clamp closes; VTX on
the floor at `L.item_locs` vtx; wire holes to the glove (aileron and sweep leads) and out of the tail end (tail leads).
Joints as the stub. Nose cap (break-first): fairing nose_x0 -175..nose_x1 -120 round the motor stand-off, camera
(RunCam 19 mm, 2 x M2 side screws) at `L.camera_locs` looking forward tilted up 10 deg; joints base, camera, lens;
held by 2 M3 (group "nose", field repair). Motor mount: stand-off from the bulkhead (4 M3) to a plate at nose_x0 - 6
carrying the 2806.5 (`iface.motor_mount`, motor screwed on first on the bench), joint "motor" (+Z forward); thrust 21
N, torque. Hatch: tongue at the front + 1 M3 at the back (group "hatch"). Boom clamp: saddle over the boom in the
socket slot, tongue under a lip at one end, 1 M3 (group "boom_clamp") at the other: one screw to take the tail off.

### Wings (wing.py, aileron.py exist from the sibling; skid.py) - one designer
wing.py builds (lead now aft of the rear spar to L.lead_root 190); fix aileron.py (mesh not watertight) and the thin
walls; skid_r/l: a wingtip skid on the underside of the rounded tip (glued, 2 walls), joint "skid" on wing_x2.
Lead channel ends at L.lead_root on the inner segment's root face (the hub takes it on).

### Tail (tail_mount.py, hstab.py, elevator.py, fin.py, rudder.py exist from the sibling) - one designer
Boom rods.cf_tube_8x6 from boom_x0 215 to boom_x1 790 at z boom_z -25; hstab chord plane htail_z0 -37 under the boom (2.5 mm wall under the boom bore at the 120 mm root chord)
(the sibling's offset); adapt tail_mount (BLOCK_TOP and every hard-coded z to the new boom height), PETG, keep the
two-M3 stab seat and servo pockets.

## Interfaces

| Between | How | Group |
|---|---|---|
| fuselage - glove | 4 M3 from the glove top into heat-set inserts in the fuselage saddle | glove |
| glove - pod | 2 M3 from below into heat-set inserts in the glove pad | pod_r / pod_l |
| cap - glove - pod | 2 M3 from the cap top through the glove into heat-set inserts in the pod roof (field) | cap_r / cap_l |
| pod / cap - hub | 5 mm pin pressed in the pod floor, slip in the cap; two 625 in the hub boss | pivot_r / pivot_l |
| pod - sweep servo | MG996R tabs, 4 screws | sweep_servo_r / _l |
| horn - pinion | 4 M3 through the pinion into the aluminium 25T horn | pinion_r / pinion_l |
| hub - spar tubes, hub - wing_x1 - wing_x2 | epoxy | - |
| wing_x2 - aileron | bottom tape hinge, pushrod | ail_r / ail_l |
| fuselage - motor_mount | 4 M3 into the bulkhead inserts | motor_mount |
| motor_mount - motor | 4 M3, on the bench first | motor |
| fuselage - nose | 2 M3 (field) | nose |
| fuselage - hatch | tongue + 1 M3 | hatch |
| fuselage - boom_clamp - boom | tongue + 1 M3 (field) | boom_clamp |
| boom - tail_mount | epoxy | - |
| tail_mount - hstab | 2 M3 into inserts | hstab |

## Joint tree

fuselage (root) -> nose (-> camera, camera_view), motor_mount -> motor -> prop, hatch, boom, boom_clamp, tail_mount
(-> hstab -> elevator, fin -> rudder, elev_servo, rud_servo), glove (-> gps, pod_r/l, cap_r/l), items;
pod_r/l -> pin, sweep servo -> horn -> pinion, **fold_r / fold_l** (0..65 deg) -> hub -> bearings, tubes, wing_x1 ->
wing_x2 -> aileron (+-20), aileron servo, skid. Couplings: sweep_srv_r = +1.6154 x fold_r, sweep_srv_l = -1.6154 x
fold_l (21:13; 65 deg of sweep = 105 deg of the MG996R).

## What breaks on these aircraft and what this design does about it

From Spencer's note (REFERENCES.md "What breaks on these aircraft"; ranked there, sources per row). No flown 1 m
swing-wing publishes a failure log, so several rows rest on one report (DTFB F-14) or own engineering, marked there.

| Failure seen elsewhere | What hawk_wing does |
|---|---|
| Sweep servo too weak / slow to move the wing in flight (DTFB F-14) | MG996R through 21:13 sized against the real panel's air load at 84 and 150 km/h (`fold_*`: 43 % / 27 % of half its stall); 105 deg of its ~120 deg travel, so it never sits on its own end stop; bench test with the props off: time 0 -> 65 deg with a 1 kg weight hung at mid-panel (ASSEMBLY) |
| Wing stuck swept after a failure | real spread stop (`stop_spread_*`) that the high-lift pull drives the panel onto; INAV `Is Failsafe` -> `Override RC Channel` to spread; RTH. A spring to spread was rejected (it adds its torque to the servo's hold load at 65 deg, and a dead MG996R's gear train does not back-drive, so it would not open a dead-servo wing) |
| One sweep drive fails -> uneven sweep | pitch stays stable uneven (`sm_asym`); roll is countered by the ailerons + the other panel on the sweep switch; it is the plane's worst single failure (Risks) |
| Gear backlash -> tip play, flutter | pinion on the clamped aluminium horn (not a plastic spline), 100 % infill, module 2; backlash 0.8 deg ~ 5 mm at the tip (measure; INAV sweep channel held still in flight) |
| Pivot slop / wear | two 625 ball bearings 28 mm apart on a steel pin instead of plastic on a bolt; races clamped axially by rings on the inner races only |
| Servo lead fatigue at the pivot | the lead crosses the pivot 14 mm from the pin (65 deg = 16 mm of arc), in a service loop under the cap; plug there |
| Brown-outs from servo stall current | the sweep servos have the ESC's 7 A BEC to themselves (2 x 2.5 A stall); a 1000 uF capacitor on that rail (BOM) |
| PETG glue joints let go (3DLabPrint: PETG "not recommended for parts that require to be glued") | the structural joints are bolted (pod, cap, glove, boom); the glued ones (tubes in the hub sockets and skins, skins to hub) are roughened + 2-part epoxy and proof-loaded: sandbag each panel to 1.5 x its 4 g load before the first flight (ASSEMBLY) |
| Aileron flutter from linkage slop | horn holes 1.3 mm for the 1.2 mm wire, Z-bends, hinge taped both sides |
| Tail boom slipping / rotating in a one-screw clamp | positive location: the clamp's one M3 passes through a cross hole in the boom (Archer's method) or a keyed collar; the tail comes back at the same incidence after a field swap |
| Nose / prop / tips take the crash | nose cap, prop, wingtip skids and tail surfaces are the cheap break-first parts (use story); the pivots sit inside the wing aft of the nose |
| Sun creep (dark PLA warped at ~60 C) | PETG everywhere (HDT ~70 C; `story_heat` 45 C); light filament colour recommended |

## Assembly order

(filled from ASSEMBLY.md after the build)

## Results

(filled after the build)

## Risks / measure first

(filled after the build)
