# References — servo test rig

| Reference | License | Why |
|---|---|---|
| TowerPro MG996R datasheet (catalog `servos.MG996R`, source in catalog) | — | body/tab/spline dimensions, stall torque |
| DS3218 drawing via catalog (same size class) | — | tab hole spacing/diameter marked UNVERIFIED for MG996R in the catalog note |
| CNC Kitchen heat-set insert table (catalog `fdm_holes.M3`) | — | 4.0 mm hole, 5.7 mm insert, 6.7 mm depth |
| Aluminium 25T disc horn listings (catalog `servo_horns.aluminum_25T`) | — | 20 mm disc, 14 mm bolt circle, 4× M3 |

## Decisions this supports
- Servo window = body 40.7 × 20.0 mm + 0.6 mm clearance; tab screws on a 49.5 × 10 mm pattern.
- 8 mm wall so the 6.7 mm insert hole keeps a 0.8 mm floor (it is a through window anyway).

## Open questions
- MG996R tab hole spacing/diameter come from the DS3218 drawing (catalog note: UNVERIFIED). Measure a real servo
  before printing the final bracket.
