# fpv_wing: references

Everything below was opened on 2026-11-01 unless noted. Catalog numbers carry their own `source` in
catalog/hardware.json; this file is the design evidence and the decisions taken from it.

## Reference designs (specs only; no geometry copied)

| Design | What it shows | Source |
|---|---|---|
| Darkwing-1 (MakerWorld 3396838) | The brief's target class: 1000 mm span, 577 mm long, max 1400 g, 6S 2500 mAh (~380 g), thrust/weight 3:1, stall 50 km/h, cruise 70 km/h, PLA+ and TPU, 1 wall, 3 % infill. The page itself refused automated reading; the numbers are the brief's. Licence: no redistribution, so none of its files are used. | https://makerworld.com/en/models/3396838 |
| SonicModell AR Wing Pro 1000 | 1 m FPV wing: 450 mm long, PNP 500 g, max take-off 1425 g, 2216 1400 KV on 8x5, 40 A ESC, 2 x 9 g servos, 4S 3200-3500 mAh; minimum speed 31 km/h, **cruise 75-80 km/h at 5.5 A (4S, ~81 W)**, 130 km/h max, carbon spar | https://fpv24.com/en/sonic/sonicmodel-ar-wing-pro-1000mm-fpv-flying-wing-pnp ; https://www.racer.lt/article/1631/sonicmodell-ar-wing-pro-1000mm-wingspan-world-first-dji-hd-fpv-wing.html |
| SonicModell AR Wing Classic 900 | wing loading 59 g/dm², 10-80+ km/h, CG bump under the wing, battery slot for CG | https://www.skyraccoon.com/aircraft/SonicModell_AR-Wing-Classic_AW900CLSSC |
| 3DLabPrint RazorBlade (Tangent Labs) | a printed flying wing: 815 mm span, 15.4 dm², **72.7 g/dm²**, print 520 g, 1120 g with 3S 2200; single-layer printing with internal webbing, an 8 mm carbon tube spar, reflexed airfoil (elevons neutral = flush), throws 12-16 mm at the tip, CG marked under the wing | https://3dlabprint.com/wp-content/uploads/2020/03/RazorBlade-Guide-3D-LabGang-Ver-1.pdf |
| Sine qua non II (Printables 436776) | printed wing: LW-PLA / PETG, 22 exchangeable parts with self-locking plugs (replaceable sections) | https://www.printables.com/model/436776-rc-flying-wing-sine-qua-non-ii |

## Aerodynamics

- **Airfoil MH 45** (Martin Hepperle, 9.85 % thick, reflexed, made for flying wings): coordinates from the UIUC
  Airfoil Coordinates Database, catalog/airfoils/mh45.dat; clmax by Reynolds number in catalog/airfoils/airfoils.json
  (1.185 at Re 200 000, XFOIL polars from airfoiltools.com). Sources: catalog/airfoils/SOURCES.md.
  MH 60 (10.08 %) is the alternative on file.
- **MAC, its station and the neutral point** of a straight-tapered wing: MAC = 2/3 c_r (1 + l + l²)/(1 + l),
  y_MAC/(b/2) = (1 + 2l)/(3(1 + l)) (Scholz, Aircraft Design lecture notes ch. 7, eq. 7.10-7.12,
  https://www.fzt.haw-hamburg.de/pers/Scholz/HOOU/AircraftDesign_7_Wing.pdf; the same MAC formula on
  https://www.airfieldmodels.com/information_source/math_and_science_of_model_aircraft/formulas/mean_aerodynamic_chord.htm).
  A tailless wing's neutral point = its aerodynamic centre ~ 25 % MAC (Hepperle, https://www.mh-aerotools.de/airfoils/flywing1.htm).
- **Static margin**: Hepperle gives 2-5 % for flying-wing models (10 % as the graphs' reference); eCalc's CG calculator
  recommends 5-12.5 % (https://www.ecalc.ch/cgcalc.php). Brief: 5-15 %. Aim: 10 % for the first flight, then move the
  pack back in small steps.
- **Wing CLmax** = 0.9 x airfoil clmax x cos(quarter-chord sweep): Raymer, Aircraft Design (1992) eq. 12.15, as coded in
  OpenConcept's CleanCLmax (MIT; https://mdolab-openconcept.readthedocs-hosted.com/en/latest/_srcdocs/packages/aerodynamics/CL_max_estimation.html, code: aerodynamics/CL_max_estimation.py); Scholz eq.
  7.37 gives the cos(sweep) factor.
- **Washout**: Scholz ch. 7 recommends -3 deg for preliminary design (aft-swept wings need negative twist against tip
  stall); -2.5 deg is used with the reflexed MH 45.
- **Elevons**: control-surface chord 20-40 % of the wing chord, typically 30 %; ailerons over 65-95 % of the semi-span
  (Scholz ch. 7.4). Here 24 % chord (hinge at 76 %), 32-92 % of the semi-span.

## Structure

- **Spar tubes**: pultruded carbon tubes 8 x 6 and 6 x 4 mm. Easy Composites lists these exact sizes at 400-500 MPa
  tensile, 28-40 GPa modulus (low ends used; https://www.easycomposites.co.uk/8mm-pultruded-carbon-fibre-tube and
  .../6mm-pultruded-carbon-fibre-tube); Rock West T700 pultrusions list 1.72 GPa (https://www.rockwestcomposites.com/47317-2.html).
- **Safety factor 1.5 on limit load**: 14 CFR 25.303 (https://www.law.cornell.edu/cfr/text/14/25.303), on the low strength figure.
- **Load factor 6 g**: hand launches and FPV pull-outs (ENGINEERING.md 9b).
- **LW-PLA** (alternative for the wing skins): CNC Kitchen measured 49 MPa unfoamed, 24 MPa at 67 % density, 12 MPa at
  44 %; stiffness falls faster than density (https://cnckitchen.com/blog/colorfabb-lw-pla-testing-foaming-pla). Plain PLA
  with 1 wall and 3 % infill is used (the Darkwing's settings); LW-PLA at ~67 % density would save ~30 % of the wing mass.

## Purchased parts (catalog/hardware.json; prices in catalog/prices.json)

| Item | Choice | Key numbers |
|---|---|---|
| Motor | iFlight XING 2806.5 1300 KV (already in the catalog) | 2319 g max thrust at 23.42 V, 48.3 A peak, 54.3 g, 19 mm M3 circle |
| Prop | Gemfan Flash 7040 tri-blade (pusher-direction one of the pair) | 178 mm, 7.9 g |
| ESC | Hobbywing Skywalker 60A V2 | 60 / 80 A, 3-6S, 5 V 7 A BEC (unused), 73 x 30 x 12 mm, 68 g |
| FC | Matek F405-WMO | 90 A PDB/current sensor, 5 V 2 A + Vx 4.5 A servo BEC, 10 PWM, 32 x 22 x 12.7 mm, 9 g |
| Servos | KST X08 Plus V6.0 | 8 mm thick, 3.85 kgf.cm at 6 V, 9 g, metal gears, 2BB |
| Battery | CNHL Black 6S 2200 mAh 40C | 108 x 55 x 35 mm, 372 g |
| GPS | Matek M9N-5883 | 32 x 32 x 10 mm, 14.5 g, 50 mA |
| Camera / VTX / RX / antenna | RunCam Phoenix 2, SpeedyBee TX800, RadioMaster RP1, Foxeer Lollipop 4 Plus 95 mm (already in the catalog) | |
| Spars | 8 x 6 and 6 x 4 mm pultruded carbon, 1 m (ReadyMadeRC) | one tube of each size gives both halves |

Other motors looked at: T-Motor AT2814 (108 g, 3-4S only), T-Motor Velox V2812 925 KV (78.6 g, 2477 g on HQ 8x4.5x3 at
25 V, 41.4 A; mount pattern not published) - the XING 2806.5 is lighter, 6S-rated and already sourced with its pattern.

## Decisions

1. 1000 mm span, 250 / 120 mm chords, 28 deg leading-edge sweep, -2.5 deg washout, MH 45: 18.5 dm², aspect ratio 5.4.
2. Static margin target 10 % MAC, set by the battery's position (`bat_x`), not by changing the number.
3. All-up mass target <= 1300 g (brief max 1400): wing loading <= 75 g/dm² (RazorBlade 72.7), stall <= 45 km/h.
4. Two carbon spars per side (8 x 6 at 28 % chord, 6 x 4 at 60 %), separate left/right tubes ending 8 mm off the
   centreline in pod sleeves: the pod box carries the moment across the middle.
5. Wing in 4 printed segments + pod (each fits the A2L standing on its end), 1 wall + 3 % infill PLA; TPU nose and fins
   (the parts that land); PETG motor mount (motor heat).
6. 6S, one pusher 2806.5 on a 7 in tri-blade; elevons on KST X08 servos in pockets in the inner segments.
7. Wing FC with its own PDB and servo BEC (F405-WMO), a separate 60 A wing ESC, GPS on the shelf under plain PLA.
