# References — 5" freestyle FPV frame

Designs studied are in `references/INDEX.md` (rows marked fpv_5in); hardware numbers are catalog entries with sources.

| Reference | License | Why |
|---|---|---|
| OpenFrame-5F — https://github.com/OpenDrone-hw/OpenFrame-5F | CERN-OHL-S-2.0 | 226 mm wheelbase; separate arms clamped at the body; arm measured 6.0 mm thick, 16.0 → 12.4 mm wide; 30.5 stack on grommets |
| TBS Source One — https://github.com/tbs-trappy/source_one | not stated | 226 mm (V5), 6 mm arms; arms sold as spare packs → arms are the expected crash failure; TPU camera mount |
| ImpulseRC Apex 5" — https://www.getfpv.com/impulserc-apex-5-base-frame-kit.html | proprietary | 225 mm; stack mounted separately from the arm clamp |
| MFPV — https://github.com/mikeymascatu/MFPV | not stated | negative example: 3.5 mm printed arms "unflyable"; PLA softens near motors; ≥6 walls, >25% infill |
| Crab — https://makerworld.com/models/1284211 | not stated | crash data: PETG cracks, PETG-CF survived 10 m falls, PAHT-CF ~100 m |
| ModuFrame-5 / uavmodel blog — https://www.elecrow.com/sharepj/modular-5-inch-quadcopter-frame-1263.html ; https://blog.uavmodel.com/?p=4740 | CC BY-SA / not stated | printed arms 1.5-2× the carbon section, bolt-on arms, root fillets, heat-set or nuts not threads in plastic (unverified blog numbers: rules of thumb only) |
| iFlight XING2 2207 1855KV test report (catalog `drone.motors.2207_1855kv_6s`) | — | 16 mm bolt circle M3, ~3 mm thread depth, 31.6 g, 1685 g max thrust |
| Gemfan 51466 (catalog `drone.props.5_1in`) | — | 131.8 mm disc, 6.8 mm hub |
| SpeedyBee F405 V4 + BLS 55A (catalog `drone.stacks.fc_30_5`) | — | 30.5 mm M3, boards 41.6 / 45.6 mm, ~22 mm tall |
| RunCam Phoenix 2 (catalog `drone.cameras.micro_19mm`) | — | 19 mm cube, side M2 holes ~5.1 mm from the back face |
| CNHL 6S 1300 (catalog `drone.batteries.6S_1300`), Amass XT60 (catalog `drone.connectors.XT60`) | — | 82×40×36 mm 215 g; 21.3×8.1×16 mm |

## Decisions this supports
- Motor diagonal 226 mm (OpenFrame-5F, Source One V5): adjacent motors 159.8 mm apart → 28 mm between 131.8 mm discs.
- Bolt-on, replaceable arms (Source One spare-arm packs; blog: arms fail at the root) instead of a unibody.
- Arm section 20 × 11 mm = 220 mm² ≈ 2.3× the 96 mm² carbon root section (OpenFrame), in the 1.5-2×+ range the
  printed-frame reports call for; MFPV's 3.5 mm arms are the failure case to avoid.
- CF-PETG, not PLA/PETG (Crab, MFPV): prints on an open printer with a hardened nozzle, survives crashes far better.
- No threads in plastic for anything that is taken apart: nut traps for arms/stack, heat-set inserts in the posts
  (blog: nylon threads stripped in 2-3 motor swaps); motors use their own metal threads.
- Stack on M3 × 30 with the SpeedyBee grommets (OpenFrame soft-mounts its stack; MFPV's frame vibration reached the gyro).

## Open questions
- Camera side-hole position is scaled from a drawing (catalog note): check the tilt pivot on the real camera.
- Printed-frame stiffness under flight loads is not checked by FEA (only strength + static deflection); test-hover
  and watch the gyro noise in Blackbox before freestyle.
