# E3 robot_arm

"A 4-axis desktop robot arm — base rotation, shoulder, elbow and wrist pitch — run by hobby servos, with a simple
two-finger gripper on a fifth servo. About 250 mm reach, able to lift a 150 g object at full reach, and it should
clamp or bolt to a desk. I want it to actually work, not just look like an arm."

## Grading contract
- Joints named `base_yaw`, `shoulder`, `elbow`, `wrist`, `grip` (all revolute). Ranges must cover at least:
  base_yaw [-90, 90], shoulder [-60, 60], elbow [-60, 60], wrist [-75, 75], grip any opening range. All sweeps clear.
- A rigid joint label `tcp` on the gripper item marks the grip point.
- Purchased servos from the catalog, plus at least one catalog bearing carrying the base yaw load.
- Requirements (ids exactly): `torque_shoulder`, `torque_elbow`, `torque_wrist` (static_torque, payload_g >= 150 at
  the tcp, max_fraction <= 0.5, worst pose with the arm stretched out horizontally included in poses);
  `reach` (distance from the shoulder axis to the tcp at the stretched-out pose, between 230 and 300 mm);
  `grip_open` (distance between the two finger tips with the gripper open, >= 40 mm);
  `upper_arm_fea` (fea_static on the shoulder-to-elbow link: fixed at the shoulder, 2x the worst static load at the
  elbow incl. payload, SF per docs/ENGINEERING.md, tip deflection <= 1% of the link length).
