# E6 pan_tilt (BLIND test of the tool)

Give a fresh subagent ONLY this brief and the instruction to use the `kerf` skill in this repo.

"I need a pan-tilt camera mount for a Raspberry Pi Camera Module 3 driven by two SG90-class micro servos, that
screws onto a standard 1/4-20 tripod thread. Pan at least ±80°, tilt from straight down-ish -30° to +60°."

## Grading contract
- Joints `pan` covering [-80, 80] and `tilt` covering [-30, 60], swept clear.
- Purchased servos from the catalog (SG90 or MG90S); a camera board proxy.
- Requirements (ids exactly): `torque_tilt` (static_torque on tilt, max_fraction <= 0.5).
- A tripod-thread interface on the base (a 1/4-20 nut trap or insert); add the 1/4-20 nut to the catalog with a source.
