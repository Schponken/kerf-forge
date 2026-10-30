# E5 bionic_finger

"One finger for my bionic hand: three segments like a real index finger, adult size, pin joints, and internal
channels for a flexor and an extensor line so it curls and straightens when the lines are pulled. It has to print
without supports and the joints must bend all the way without the segments jamming."

## Grading contract
- Printed `base` (the knuckle mount), `proximal`, `middle`, `distal`. Project-level `supports: avoid`.
- Joints `mcp`, `pip`, `dip` (revolute) covering [0, 80], [0, 80], [0, 70]; each swept clear; coupled pose sweep
  `curl` with all three joints together at 0/30/60/80 (dip capped at 70), clear.
- Joint pins are real hardware: catalog pins or M3 screws, aligned through both parts (fastener/pin check).
- Requirements (ids exactly): `len_proximal` (distance mcp→pip axis 40–48 mm), `len_middle` (pip→dip 22–28 mm),
  `len_distal` (dip axis → `distal.tip` 18–24 mm), `flexor_open` and `extensor_open` (channel_clear, diameter >= 1.5 mm,
  through every segment), `proximal_fea` (fea_static on the proximal segment: 15 N at the pip joint, fixed at the
  mcp pin, SF per docs/ENGINEERING.md).
