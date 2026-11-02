# Diary: drone_foldable_wings

25 problems recorded (21 open). Found at: before parts 0, rough 0, detail 1, final review 24.
Estimated active fix time 134 min; parts redrawn: hub. Costs are estimates from git (commit times, edited part files).

## Review rounds

| Commit | Date | Verdict | Findings |
|---|---|---|---|
| 9aca1069 | 2026-11-02 | FAIL | 19 |
| 76851c6a | 2026-11-02 | FAIL | 21 |

## Problems

| Id | Sev | Part | Stage | Status | ~min | Redrawn | What |
|---|---|---|---|---|---|---|---|
| 1 | major | hub_r | final review | resolved | 23 | 1: hub | root fairing: the new nose touches the spine ridge before the real spread stop does (hub_l |
| 2 | minor | hub_r | final review | resolved | 23 | 1: hub | root fairing: structurally the cap is neutral, and the 25.8 -> 24.2 MPa hub_fea drop is no |
| 3 | minor | hub_r | final review | resolved | 23 | 1: hub | root fairing: print and mass. (a) As printed (boss on the bed, airfoil floating above it o |
| 4 | minor | hub_r | final review | open |  |  | root fairing: what still faces the flow after the change. I re-measured the designer's own |
| 5 | blocker | hub_r | final review | open |  |  | hub_fea fails: p99.9 von Mises 24.2 MPa against 17.5 allowed (CF-PETG / SF 2), and 8.2 mm  |
| 6 | blocker | hub_l | final review | open |  |  | hub_l is the mirror image of hub_r: same section, same 6 g load, same thin root trailing e |
| 7 | blocker | spine | final review | open |  |  | spine_fea fails: 53.6 MPa against 16 allowed (3.4 times over), and 2.1 mm deflection again |
| 8 | blocker | aft_fuse | final review | open |  |  | deck_fea did not run ('PLC Error: A segment and a facet intersect'), so the lower pivot pl |
| 9 | major | aft_fuse | final review | open |  |  | 103 sharp inside corners (1281 mm of edge) are neither filleted nor declared, e.g. [226.4, |
| 10 | major | ail_r | final review | open |  |  | The aileron servo leads are too short: ail_r_pwr/sig and ail_l_pwr/sig are declared at 620 |
| 11 | major | fwd_fuse | final review | open |  |  | About 45 wiring routes pass through solid parts instead of holes or channels. The main lea |
| 12 | minor | spine | final review | open |  |  | Aerodynamics at full spread: the ridge's front is a vertical face about 28 mm wide and 17  |
| 13 | minor | fwd_fuse | final review | open |  |  | Overbuilt parts in a mass-limited aircraft. fwd_fuse is 183.5 g of PLA working at 6 % of a |
| 14 | minor | pinion_r | final review | open |  |  | The 4 M3 horn-screw holes leave only 71 % of the ring material near the tooth roots (pinio |
| 15 | minor | aft_fuse | final review | open |  |  | The 4 sweep-servo screws on each side need a ball-end 2.5 mm key (a straight key hits the  |
| 16 | minor | elevator | final review | open |  |  | Thin walls below 1.2 mm: elevator 0.93, rudder 0.86, ail_r/l 1.02-1.03, hatch 1.01, tail_m |
| 17 | minor | hub_r | final review | open |  |  | Pre-existing print setup: the hub is printed boss-down, so the whole airfoil block floats  |
| 18 | minor | fwd_fuse | final review | open |  |  | DESIGN.md is out of date. Its requirements table still says AUW <= 1150 g, wing loading <= |
| 19 | minor | aft_fuse | final review | open |  |  | Environment and export: the circuit check did not run (KiCad symbol libraries not found),  |
| 20 | minor | hub_r | final review | open |  |  | Root fairing (this change): nothing guards the new over-travel clearance. The nose-to-ridg |
| 21 | minor | hub_r | final review | open |  |  | Root fairing (this change): the nose has a wave in plan view (top render). I measured its  |
| 22 | major | hub_r | final review | open |  |  | Infill (pre-existing geometry; the engine check is new, kerf/infill.py). hub_r prints at 1 |
| 23 | major | spine | final review | open |  |  | Zero running clearance to each hub boss (pre-existing geometry, found now; this change did |
| 24 | major | spine | final review | open |  |  | Infill (pre-existing geometry; the engine check is new). The spine prints at 15 % infill,  |
| 25 | commit |  | detail | resolved | 65 |  | drone_foldable_wings: sweep servos get their real travel (0..113.1 / -113.1..0: the full s |
