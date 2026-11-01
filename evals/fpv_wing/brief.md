# E7 fpv_wing — a 1 m 6S FPV flying wing (class of MakerWorld's Darkwing-1)

"Design a 3D-printed FPV flying wing like the Darkwing-1 on MakerWorld: about 1000 mm span, one pusher motor on 6S,
elevons, a fast and efficient wing for FPV and long range. Printable on my Bambu A2L with thin-wall wing sections,
TPU where it lands, and bolted sections I can replace after a crash. Include every component it needs to fly."

Reference (specs only; its files are under a no-redistribution licence, so nothing is copied):
https://makerworld.com/en/models/3396838 — 1000 mm span, 577 mm long, max 1400 g, 6S 2500 mAh (~380 g), thrust/weight
3:1, stall 50 km/h, cruise 70 km/h, PLA+ and TPU, 0.2 mm layers, 1 wall, 3 % infill.

## Grading contract
- Span 950-1050 mm (`span` requirement, size along Y), all-up mass <= 1400 g (`auw`).
- An airfoil from catalog/airfoils (sourced) on every wing panel; wing panels printed in segments that fit the A2L.
- Elevon joints `elevon_l` / `elevon_r` covering at least [-20, 20] deg, swept clear of the prop disc.
- Requirements (ids exactly): `static_margin` (5-15 % MAC), `wing_loading`, `stall_speed` (<= 55 km/h),
  `spar_bending` (load factor >= 6 g), `twr` (thrust_to_weight >= 1.5), `flight_time`, `prop_clear` (prop_clearance).
- Every purchased part from the catalog with a source: motor, prop, ESC/FC, servos, battery, camera, VTX, receiver,
  GPS, carbon spar tubes.
