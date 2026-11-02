# drone_foldable_wings: references

Research for the hawk-fold morphing UAV (1.1 m span, conventional tail, tractor nose motor, each wing half one rigid
printed panel on carbon spars pivoting about a near-vertical axis at its root trailing-edge corner, 0 to ~65-75 deg
sweep, one MG90S-class servo per side through a ~2:1 printed gear). Everything was opened on 2026-11-01. Reuse from
projects/fpv_wing/REFERENCES.md: MH 45 / MH 60 polars (catalog/airfoils), MAC formulas (Scholz ch. 7), wing CLmax =
0.9 clmax cos(sweep) (Raymer eq. 12.15 via OpenConcept), 1.5 safety factor on limit load (14 CFR 25.303), 6 g load
case, thin-wall PLA/LW-PLA skins on pultruded carbon tubes, F405-WMO wing FC. Catalog numbers carry their own
`source` in catalog/hardware.json; this file is the design evidence. "Read" = stated on the page/file; "chart read" =
read off a published graph; "derived" = my arithmetic from cited inputs; "illustrative" = arithmetic on ASSUMED
geometry, to be redone with DESIGN.md numbers.

## Reference designs

| Design | What it shows (numbers) | Licence | Source |
|---|---|---|---|
| LisHawk, EPFL (Ajanic et al. 2020, Science Robotics 5:eabc2897) | 284 g, 10 min; span 1.05 m, chord 0.32 m; wing angle 45 deg tucked -> 130 deg extended, area 0.117 -> 0.165 m^2 (41 %); tail 0.014 -> 0.044 m^2; CG moves 18.6 mm with sweep; one **KST X08-Plus (9 g, 3.8 kg.cm @6 V) per side sweeps the wing**; 8 x 8 mm carbon square-tube backbone; min speed 7.6 m/s tucked, 4.0 m/s extended; tucked cut thrust 59 % at 12 m/s. **Extended wing + tucked tail is pitch-unstable at low angle of attack (not flown)**; the optimal schedule extends the wing below 6 m/s and tucks it above 8.5 m/s (Fig. 6D). Asymmetric sweep gives large roll moments at high angle of attack (Fig. 4F). | arXiv preprint, paper only | https://arxiv.org/abs/2002.02421 (pp. 3-11 read) |
| LisEagle morphing-wing MAV, EPFL (Di Luca et al. 2017, Interface Focus 7:20160092) | 330 g; span 0.84 / 0.395 m, area 0.131 / 0.077 m^2 (-41 %), AR 5.4 / 2; one HuiDa 1810MG per side through a tendon; **return spring 3 N = 1.5 x drag of the folded section at 20 m/s**; CDmin 0.033 open / 0.020 folded; CLmax 1.01-1.06; sim. min turn radius 3.9 m open / 6.6 m folded; Cl from 52 deg asymmetric fold 0.139 vs 0.104 from 20 deg aileron at CLmax. Asymmetric fold is weak at low CL (pilot pitched up before rolling). | open access (licence not checked) | https://pmc.ncbi.nlm.nih.gov/articles/PMC5206609/ |
| Wanner, Phan, Toumieh, Floreano 2026 (arXiv 2603.12059), EPFL | 130 g; span 0.67 / 0.45 m; **sweep -5 -> 75 deg in 0.10 s by one 4.5 g BMS-101DMG per side through a bar linkage**; conventional tail (elevator ~60 % of tailplane, rudder); CG moves +/-2 mm; lift slope falls when swept; roll by asymmetric sweep only was weak at low angle of attack (roll and altitude errors). | arXiv, paper only | https://arxiv.org/abs/2603.12059 |
| PigeonBot, Stanford (Chang et al. 2020, Science Robotics 5:eaay1246) | ~280 g, 40 feathers on elastic links, 42 DOF from 4 servo wrist/finger joints, conventional prop/fuselage/tail; asymmetric wrist/finger motion initiated turns. Paper 403; numbers from press, unverified. Low relevance (feathers, not a rigid pivot). | paywalled | https://www.science.org/doi/10.1126/scirobotics.aay1246 |
| Archer oblique-wing RC plane v2 (Printables 1232467) | **The flown printed swing wing**: 1500 mm, 29 dm^2, 1400 / 1700 g (58.6 g/dm^2), stall 10 m/s. Wing pivots on an **M6 x 55 bolt through two flanged nylon bushings 6 x 8 x 8 (top and bottom of the wing root)**, 30 % infill modifier around the bolt; **sweep 0-45 deg by a PowerHD LF-20MG (20 kg.cm standard servo)** via a 50 mm M3 ball-link rod on its own 5 V BEC; 12x10 main spar, **14x12x455 carbon tail boom cross-bolted with M3 through holes 25 / 27 mm from its ends**, 6x4 tail spars, 4 mm carbon-rod aileron hinge pins, M2 ball-link control rods, MG90S on the surfaces; LW-PLA 1 perimeter + 5 % infill (20 % at spars/hinges), fuselage 2 perimeters 10 %; ArduPlane FC 'to neutralise the trim as the wing rotates'; sweep on a 2-3 position switch. | Standard Digital File Licence: numbers only, no geometry | https://www.printables.com/model/1232467-archer-oblique-wing-rc-plane ; guide https://drive.google.com/file/d/1xMhwQXuymO50eh_G8XK65f9L1NIVUlB3/view ; BOM https://docs.google.com/spreadsheets/d/1VuVBQVcuFjI6-8O4fSAHmWHxGhbHCe5bLZm-qom-mFs |
| Flite Test DTFB F-14 swing wing | 36 / 26 in span, 488 g + battery; pivot = rivet sleeve on a 4-40 screw, 1/8 in ply bearing faces glued both sides of the foam; pushrod to a dowel; **a slow Turnigy TSS-9S could not sweep the wings in flight, a plain 9 g servo could**. | free plans, licence not stated | https://flitetest.com/articles/dtfb-f-14-with-swing-wings |
| XFly F-14 Twin 40 mm / Freewing F-14 Twin 80 mm (commercial) | XFly: 970 mm, 1150 g, 10 dm^2, 115 g/dm^2, 'high-torque servos' sweep the wings (2 x 13 g fitted; which servo sweeps is not stated), 4S. Freewing: 4160 g, 'rigid aluminium wing structure'. Same weight class as this project (XFly). | proprietary | https://www.skyraccoon.com/aircraft/XFLY-Model_F-14-Tomcat-Twin-40mm_XF122P ; https://lindinger.at/en/AIRPLANES/MODELS/Jets/FREEWING-F-14-TOMCAT-TWIN-80MM-EDF-JET-PNP/9775302 |
| NASA Langley variable sweep history (E. C. Polhamus) | Sweeping about one fixed pivot in the fuselage gave 'large unacceptable changes in stability and control'; the X-5 translated the whole wing (heavy); **'two fixed pivot points located outboard of the fuselage minimized adverse effects'** - used by the F-111, F-14, B-1. | NASA web page | https://www.nasa.gov/centers-and-facilities/langley/edward-c-polhamus |
| Bristol perched-landing variable-sweep UAV (Greatwood, Waldock, Richardson 2017, AST 71:510-520) | Up to 30 deg FORWARD sweep for pitch moments in the flare, stall 9 m/s, landing < 3 m/s; custom wing-box mechanism (full text blocked: abstract only). | AAM CC BY-NC-ND | https://research-information.bris.ac.uk/en/publications/perched-landing-manoeuvres-with-a-variable-sweep-wing-uav/ |
| Peregrine falcon dives (Ponitz et al. 2014, PLoS ONE 9(2):e86506) | Dives to 22.5 m/s at 50.75 deg path angle; wing phases from the literature: diamond up to ~190 km/h, tight tuck 190-240 km/h, wrapped >= 320 km/h; **wings opened for the pull-out** (peak 11.5 m/s^2). | CC BY | https://pmc.ncbi.nlm.nih.gov/articles/PMC3914994 |

Abstract-only leads (full text blocked, numbers not used): Gao et al. 2023, Drones 7(9):552 (tandem-wing MAV, sweep for
pitch and roll, no ailerons); 'Employing wing morphing to cooperate aileron deflection improves the rolling agility of
drones', Advanced Intelligent Systems 2023 (asymmetric sweep + aileron, outdoor flights); Drones 8(9):474 (2024),
tube-launched UAV with worm-gear continuous sweep.

## Engineering formulas for the checks (with sources)

1. **Swept-wing lift-curve slope** (Helmbold / DATCOM, Raymer sect. 12.4.1):
   CL_alpha = 2 pi A / (2 + sqrt(4 + (A beta / eta)^2 (1 + tan^2 Lambda_t / beta^2))), beta^2 = 1 - M^2, eta = cl_alpha /
   (2 pi) - 'Raymer, Sect. 12.4.1; citing DATCOM' in AeroSandbox `CL_over_Cl`
   (https://github.com/peterdsharpe/AeroSandbox/blob/master/aerosandbox/library/aerodynamics/inviscid.py, MIT). Raymer
   uses the max-thickness-line sweep, SUAVE `datcom.py` the half-chord sweep. Equation number 12.6 is the brief's; the
   book was not opened. Cross-check: NACA TR 711 Fig. 7 (unswept, conventional sections) AR 4 ~3.55, AR 5 ~4.0,
   AR 6 ~4.25 /rad (chart read). MH 45 section slope 0.1129 /deg at Re 200 k (catalog/airfoils) -> eta = 1.03.
2. **Downwash gradient** d(eps)/d(alpha) = 2 CL_alpha,w / (pi A): MIT OCW 16.333 `navion_1.m` line 56 ('Adapted from
   Nelson, page 57'). Limits: elliptic-loading far-wake value, independent of tail position; NACA TR 711 Figs. 4-6
   give 0.3-0.9 depending on tail height/distance, taper and AR, so treat 2CLa/(pi A) as a mid-range estimate and check
   sensitivity. When the panels sweep back their trailing edges and tip vortices move toward the tail (inference).
3. **Neutral point, wing + tail** (stick fixed): CL_alpha,T = CL_alpha,w + eta_t (S_t/S) CL_alpha,t (1 - d eps/d alpha);
   h_np = (h_ac,w + (gamma - 1) h_t) / gamma, gamma = CL_alpha,T / CL_alpha,w (h in MAC fractions from the MAC leading
   edge): `navion_1.m` lines 79-81. **eta_t = q_t/q_0 = 0.9**: NACA TR 711 p. 139 symbol list; eCalc gives 0.9-0.6
   for a normal tail (0.3 in the wing wake), SUAVE's test uses 0.95. Check at 0.9 and 0.7.
4. **Fuselage destabilising term**: Cm_alpha,fus = K_f w_f^2 L_f / (S c) per radian (TR 711 eq. 1: it sits beside
   S_w d dCL/dalpha), which moves the NP forward by Delta h_np = Cm_alpha,fus / CL_alpha,T. **K_f (TR 711 Fig. 8, chart
   read off the 300 dpi scan, +/-0.05) vs wing-root quarter-chord position in % of body length from the nose: 30 % 0.58,
   35 % 0.78, 40 % 1.0, 45 % 1.3, 50 % 1.6, 60 % 2.9.** Raymer's per-degree K_fus chart is this /57.3 (book not opened).
   SUAVE `taw_cmalpha.py` uses Kf = 1.5012 p^2 + 0.538 p + 0.0331 (no source), about half of TR 711 - use TR 711
   (conservative).
5. **Tail volume coefficients** (Scholz 2021, INCAS Bulletin 13(3), Table 2): C_H = S_H l_H / (S_W c_MAC), C_V =
   S_V l_V / (S_W b); sailplane 0.500 / 0.0190, homebuilt 0.484 / 0.0380, GA single 0.672 / 0.0443. LisHawk's tail is
   12-27 % of its wing area (derived from Table 1). Reference them to the SPREAD wing (largest S, c and b).
6. **Static margin**: eCalc cgCalc recommends 12.5-5 % MAC with the fuselage effect included, 17.5-10 % if it is
   neglected (+5-8 % more with a fat fuselage ahead of the wing). fpv_wing used 10 % for the first flight.
7. **Induced drag / Oswald factor**: CD_i = CL^2 / (pi e A); e from Nita & Scholz 2012 (eq. 36-37) as implemented in
   AeroSandbox `oswalds_efficiency` (formula in references/INDEX.md). **Profile drag** from the MH 45 XFOIL polar at
   Re 200 k (airfoiltools xf-mh45-il-200000, Ncrit 9): cd 0.0093-0.0115 for cl 0-0.67, 0.0175 at cl 0.96, 0.039-0.043 at
   cl 1.18 (clmax). XFOIL is for a smooth surface; a printed skin will be draggier (no source for a factor; apply the
   LisEagle 1.5 margin).
8. **Hinge moment about the sweep pivot** (derived). With the pivot axis normal to the panel's chord plane, lift makes
   no moment about it; what remains: M = F_X a_f + n_x m_p g a_m + L_p y_cp sin(delta) + mu (R_up + R_low) r_pin +
   mu_t N r_face, where
   - F_X = q S_p (C_D cos(alpha) - C_L sin(alpha)): the panel force along the aircraft axis (aft positive; it turns
     FORWARD at high CL, leading-edge suction);
   - a_f = y_cp cos(Lambda) + x_f sin(Lambda): its lateral arm after sweeping by Lambda, with y_cp the spanwise and x_f the
     forward (ahead-of-pivot, ~0.75 c at the quarter chord) distance of the centre of pressure from the pivot at 0 deg;
     a_m the same for the panel's centre of mass; n_x the fore-aft load factor (thrust, braking, landing);
   - delta = tilt of the pivot axis from the panel normal in the chordwise plane (e.g. the wing incidence if the axis is
     fuselage-vertical): 3 deg at 4 g on the illustrative panel is ~0.24 N.m - so build the incidence into the pivot
     block (delta = 0) or keep the term in the check; a spanwise (dihedral) tilt adds no lift moment;
   - R_up = R_low = M_root / h with M_root = n (W/2) y_cp, the root bending moment carried as a couple over the support
     spacing h (brief: 40 mm); mu = 0.24-0.29 PETG on steel, dry (Stoimenov 2024, references/INDEX.md; nylon on steel 0.4,
     Engineering ToolBox); the spanwise in-plane force of a swept panel is neglected (no source).
   Size the actuator to 1.5 x the worst case (LisEagle's rule) and keep it under ~50 % of stall.
   **Illustrative** (assumed: S_p 0.09 m^2, y_cp = y_cg 0.22 m, x_f 0.13 m, m_p 80 g, h 40 mm, M5 shank r 2.5 mm,
   mu 0.25, A 6.4, e 0.8, W 10.3 N, delta 0): spread 4.3 g turn at 20 m/s, CL 1.0 -> |F_X| ~1.9 N -> 0.42 N.m aero +
   0.15 N.m friction; 35 deg sweep at 25 m/s, CL 0.2 -> 0.11 + 0.04 N.m; 70 deg dive at 30 m/s, CL 0.1 -> 0.10 + 0.04
   N.m; 1 g fore-aft acceleration of a spread panel -> 0.17 N.m; a 4 g belly-landing deceleration -> 0.69 N.m.
   **MG90S through 2:1 = 0.35 N.m (1.8 kg.cm @4.8 V) to 0.43 N.m (2.2 kg.cm @6.6 V) at the panel at STALL.** Sweeping at
   moderate CL is easy; holding the spread wing at high CL and landing loads are not, unless hard stops take them
   (Decision 6).
9. **Neutral-point shift from the root trailing-edge pivot** (derived geometry): a panel whose quarter-chord sits
   0.75 c_r ahead of the pivot and y_ac outboard moves its aerodynamic centre aft by y_ac sin(Lambda) + 0.75 c (1 -
   cos(Lambda)) (+0.29 m at 70 deg for y_ac 0.22 m, c 0.17 m: ~1.7 MAC, illustrative) while the panels' own mass moves
   the CG aft by only (2 m_p / m)(the same shift) (~30 mm illustrative; LisHawk measured 18.6 mm). This is the 'single
   fuselage pivot' problem NASA solved with outboard pivots on a fixed glove (Polhamus).

## Purchased parts (catalog/hardware.json)

| Item | Choice | Key numbers (sourced in the catalog) |
|---|---|---|
| Sweep servo | servos.MG90S (researched; **replaced by servos.MG996R in DESIGN.md**, see below) | 13.4 g, 21T spline, 1.8 kg.cm @4.8 V, 2.2 kg.cm @6.6 V, 0.7 A stall, 0.12-0.25 A running, 4.8-6 V, 1000-2000 us = 180 +/-15 deg (ProtoSupplies) - keys torque_6v_kgcm, voltage_min/max, pulse_us, pulse_travel_deg added |
| Not adopted | TowerPro MG92B | 13.8 g, 3.1 kg.cm @5 V / 3.5 @6 V, 5.0-6.6 V, but 22.8 x 12 x **31** mm with dimension A **35** (MG90S 28.4 / 32.5: not the same footprint), spline **20T** (Adafruit) or **25T** (ServoDatabase) - not the 21T horn; discontinued at Botland and Rotorama. https://www.towerpro.com.tw/product/mg92b/ ; https://www.adafruit.com/products/2307 ; https://servodatabase.com/servo/towerpro/mg92b |
| Stronger fallback | servos.KST_X08_Plus (already in the catalog) | LisHawk's sweep servo: 9 g, 3.85 kg.cm @6 V (1.75 x MG90S), but 15T spline (needs its own horn) and 1000-2000 us = +/-60 deg only |
| ESC | **drone.escs.skywalker_40a_v2** (added) | 40 / 60 A, **3-4S only**, 5 V 5 A BEC, 60 x 25 x 8 mm, 36 g (60A V2: 3-6S, 73 x 30 x 12, 68 g). On 6S no Skywalker V2 is lighter than 68 g (the 50A-6S is the 60A's size and weight). |
| Motor / prop | drone.motors.2806_5_1300kv_7in + drone.props.hq_7x4x3 (kept) | iFlight test report is at 23.4 V only. On 4S (14.8-16.8 V = 62-70 % of 23.9 V) the report's 60-70 % throttle rows are the nearest published points (derived, duty-cycle approximation): HQ 7x4x3 1147-1438 g at 13.9-19.2 A, Gemfan 7040 856-1159 g at 9.5-13.8 A -> T/W 1.1-1.4 (HQ) at 1.05 kg. https://shop.iflight.com/image/catalog/TEST%20REPORT/XING-2806.5-1300KV.png |
| Folding prop | **none sourced** | No motor + folding-prop thrust table was found for any 2212-2216 or 2806 motor (searched T-Motor AT, Dualsky XM-EG, Hacker A20, AXI, generic 2212). The only folding-prop data found are UIUC static CT/CP for Aero-naut CAM 9x4-16x8 (no size below 9 in, no motor). Aero-naut CAM blades have 8 mm roots and need a matching yoke + spinner (Mozzie build notes, https://mapping-mozzie.readthedocs.io/en/latest/parts/planeprop/). Keep the fixed 7 in prop and document the belly-landing prop strike. |

## Decisions this supports

1. **Sweep range 0-70 deg is flown precedent**: Wanner 2026 75 deg with a servo per side, F-14 20-68 deg, Archer 45 deg;
   the falcon progressively folds with speed and **opens the wings for the pull-out** (Ponitz 2014).
2. **Schedule sweep with airspeed, not only a switch**: LisHawk's optimum keeps the wing extended below 6 m/s and tucked
   above 8.5 m/s; with the root-TE pivot the swept wing's aerodynamic centre moves ~1.7 MAC aft (formula 9,
   illustrative) and the tail must carry that trim, which is only possible at high dynamic pressure. Limit max sweep
   by airspeed in the FC and mix elevator trim with sweep (Archer uses the FC to null the trim change).
3. **CG and static margin set for the SPREAD wing** (most forward neutral point): 5-12.5 % MAC with the fuselage term
   included (eCalc), K_f from TR 711 (0.78-1.3 for a wing root quarter chord at 35-45 % of the body), eta_t 0.9
   (TR 711) checked at 0.7; the swept state only becomes more stable. LisHawk: spread wing + small tail = unstable.
4. **Tail volumes referenced to the spread wing: C_H >= 0.5, C_V >= 0.038** (Scholz Table 2 sailplane / homebuilt;
   sailplane C_V 0.019 is too small for a rudder-and-sweep yaw case - inference). Tail arm and boom: Archer flies
   1.7 kg on a 14x12 carbon boom cross-bolted with M3; size ours by its bending/torsion load (catalog has up to 8x6).
5. **Keep ailerons** for roll at low angle of attack; asymmetric sweep adds roll mainly at high angle of attack
   (LisEagle, Wanner, LisHawk Fig. 4F). Command asymmetric sweep as a small differential on top of the symmetric
   setting (inference from LisHawk: symmetric in 3 steps, asymmetric continuous).
6. **Hard stops at 0 deg and at max sweep in the pivot block**, servo endpoints just inside them: the spread-wing high-CL
   forward pull (~0.4-0.6 N.m illustrative, formula 8) and the 4 g landing deceleration (~0.7 N.m) then go into the stop, not the
   MG90S (0.35-0.43 N.m stall at the panel through 2:1). **Land with the wings spread on the stop.** If high-g holding at
   intermediate sweep is wanted, use the KST X08 Plus (LisHawk's choice) or a self-locking worm (Drones 8(9):474).
7. **Pivot: steel bolt through bushing faces top and bottom** (Archer M6 in 6x8x8 flanged nylon bushings with 30 %
   infill around the bolt; DTFB ply faces), friction counted in the servo budget (formula 8). Precedent supports
   the brief's two-support couple. NASA history: a single pivot at the fuselage gives large stability changes; an
   outboard pivot on a short fixed glove reduces them (evidence for a short fixed root stub, not a decision).
8. **Gear drive**: printed pinion screwed to the 21T aluminium disc horn (servo_horns.aluminum_micro_21T), never pressed
   on the bare spline (grippers lesson, references/INDEX.md); module >= 1.5 for a 0.4 mm nozzle and 0.1-0.2 mm flank
   clearance (Sovol, in INDEX); Lewis check with Y from gearpy. 2:1 needs ~140-150 deg of servo travel: MG90S travel per
   microsecond varies (ProtoSupplies 180 deg per 1000 us vs Mistral ~78 deg per 1000 us measured).
9. **Printed construction**: LW-PLA 1 perimeter + 5 % infill skins with 20-30 % infill modifiers at spars, hinges and the
   pivot (Archer), PLA 2 perimeters 20 % for small hard parts; 4 mm carbon-rod hinge pins (Archer) or CA hinges
   (3DLabPrint FanBlade guide: 815 mm, 15.4 dm^2, 616 g printed, <= 8 mm carbon tube,
   https://3dlabprint.com/wp-content/uploads/2021/08/FanBlade-Guide-3D-LabGang-ver1.pdf); M2 ball-link pushrods (Archer).
   Calibrate LW-PLA wall thickness on spar and boom bores first (Archer guide sect. 2.1). Printed mass per wing area
   (derived): RazorBlade 520 g / 15.4 dm^2 = 34 g/dm^2 and FanBlade 616 g / 15.4 dm^2 = 40 g/dm^2 for the whole
   printed airframe (PLA, single-layer skins); LW-PLA at ~67 % density saves ~30 % (CNC Kitchen, fpv_wing refs).
10. **Wing loading <= ~60 g/dm^2** (Archer 58.6 g/dm^2 stalls at 10 m/s; AR Wing Classic 59 in fpv_wing): ~17.5 dm^2
    spread for 1.05 kg; stall ~9.5 m/s with CLmax = 0.9 x 1.185 (derived).
11. **Power**: 4S 1500 with the 1300 KV 2806.5 + HQ 7x4x3 gives T/W ~1.1-1.4 (derived from the 6S table at 60-70 %
    throttle); Skywalker 40A V2 (36 g, 3-4S) covers the ~14-19 A; a separate BEC for the sweep servos (Archer).

### Sweep servo decision (orchestrator, after formula 8 with this project's geometry)

Formula 8 with the real panel (S_half 0.0856 m², spanwise arm ~0.24 m, pivot 10 mm ahead of the root trailing edge)
gives a FORWARD chordwise moment of ~0.5-0.6 N m in a 4 g pull at the manoeuvring speed (83 km/h, CL 0.74,
c_a = cd cos(a) - cl sin(a) ~ -0.07) plus ~0.12 N m pivot friction. At full spread the 0 deg stop takes it, but at any
partial sweep the servo must: the MG90S through 2:1 (0.35 N m at STALL at the panel) would be back-driven and the wing
would unsweep under g. Chosen instead: **servos.MG996R** (already in the catalog: 9.4 kg cm at 4.8 V, 2.5 A stall,
55 g, 120 deg standard travel, 25T spline with the catalog servo_horns.aluminum_25T) through a 15:24 module-2 gear
(1.6:1: 70 deg of fold = 112 deg of servo travel) = 15 kg cm = 1.47 N m at the panel at stall, 0.74 N m at the 50 %
rule. Cost: +83 g for the pair. Power: the Skywalker 40A V2's 5 V 5 A BEC feeds only the two sweep servos (2 x 2.5 A
stall = 5 A), the FC's Vx BEC the four surface servos. Checked by `fold_moment_*` and `sweep_gears` in project.yaml.

## Open questions

- Folding prop: no published motor + folding-prop thrust figure exists for our class; the belly-landing prop strike stays
  a documented risk (or a test-stand measurement of a CAM 8-9 in folder on the 2806.5 becomes a build step).
- MG90S real travel and torque: measure degrees per microsecond at 500-2500 us (ProtoSupplies vs Mistral disagree by
  2x) and choose the gear ratio so the needed servo travel stays <= ~140 deg.
- The illustrative hinge moments use assumed panel geometry: recompute formula 8 with DESIGN.md numbers, including the
  inertial and landing cases, before committing to the MG90S.
- Tail authority in the swept state: formula 9 with the real geometry decides the max sweep allowed per airspeed and
  whether a short fixed root stub (outboard pivot) is worth adding.
- Downwash at the tail when the panels are swept (trailing edges closer to the tail) has no small-UAV data; TR 711
  charts cover unswept wings only.
- No source gives the drag penalty of a printed (rough) skin over the XFOIL polar.
- MG92B spline: Adafruit says 20T, ServoDatabase 25T, TowerPro says nothing - irrelevant unless the servo is revisited.

## Existing designs (kerf find)

### `kerf find "variable sweep RC plane"` (2026-11-01)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Archer - Oblique Wing RC Plane (flown printed swing wing)](https://www.printables.com/model/1232467-archer-oblique-wing-rc-plane) | Standard Digital File | print as-is only (no remix) | read (User Guide v1.0.0 + BOM sheet): span 1500 mm, 29 dm2, 1400 g empty / 1700 g MTOW, stall 10 m/s; pivot M6x55 bolt in 2 flanged nylon bushings 6x8x8; sweep 0-45 deg by PowerHD LF-20MG (20 kg.cm) via 50 mm M3 ball-link rod; 12x10 spar, 14x12x455 boom; LW-PLA 1 wall 5 % infill |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com variable sweep RC plane`
- web search: `site:grabcad.com/library variable sweep RC plane`
- web search: `variable sweep RC plane STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/variable-sweep-rc-plane/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Archer (Printables 1232467, the only printed swing-wing that flies) is used as evidence only (sweep range, bolt-in-bushings pivot, FC trim compensation): its Standard Digital File licence allows numbers, not geometry; no hit fits a root trailing-edge pivot with a gear drive.

### `kerf find "morphing wing drone"` (2026-11-01)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| — | nothing found | | | | |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com morphing wing drone`
- web search: `site:grabcad.com/library morphing wing drone`
- web search: `morphing wing drone STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/morphing-wing-drone/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Nothing printable exists; LisHawk / LisEagle / Wanner 2026 are research airframes whose numbers (sweep range, schedule with airspeed, keep ailerons) are used, not their geometry.

### `kerf find "folding wing RC glider"` (2026-11-01)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [RC Glider Plane Wing With High Efficiency Aerofoil](https://www.printables.com/model/720339-rc-glider-plane-wing-with-high-efficiency-aerofoil) | CC-BY-ND | print as-is only (no remix) | Hex Ribs - Hex Ribs.stl: 107.5 x 13.6 x 3 mm; Rib closest to fuselage.stl: 108 x 13.3 x 5 mm; Wing Tip - Wing Tip.stl: 108 x 17 x 13.3 mm | 32 likes, 434 downloads |
| Printables | [Servo Wing Cover for Dragon RC Glider from Valenta](https://www.printables.com/model/125854-servo-wing-cover-for-dragon-rc-glider-from-valenta) | CC-BY | adapt OK, credit | Dragon_Servoabdeckung_2.stl: 82.8 x 52 x 14.8 mm | 3 likes, 59 downloads |
| Printables | [Rc Glider Plane Motorglider 1.7m wingspan](https://www.printables.com/model/1555895-rc-glider-plane-motorglider-17m-wingspan) | CC-BY-NC | adapt OK, credit, non-commercial | no STL files | 42 likes, 295 downloads |
| Printables | [Blanik L-13 (Free sample) 2400mm wingspan RC glider](https://www.printables.com/model/1705459-blanik-l-13-free-sample-2400mm-wingspan-rc-glider) | Standard Digital File | print as-is only (no remix) | F_3.stl: 58.9 x 50.2 x 46.2 mm; F_1.stl: 69 x 44.1 x 27.3 mm; F_4.stl: 115 x 78.4 x 58.5 mm | 7 likes, 102 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com folding wing RC glider`
- web search: `site:grabcad.com/library folding wing RC glider`
- web search: `folding wing RC glider STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/folding-wing-rc-glider/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. The hits are fixed-wing parts or (MakerWorld 385029) a non-RC slingshot toy; none folds a powered wing in flight.

### `kerf find "3D printed RC plane wing pivot"` (2026-11-01)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [3D Printed RC SkidSteer V3.0](https://www.printables.com/model/721244-3d-printed-rc-skidsteer-v30) | CC-BY-NC | adapt OK, credit, non-commercial | Main Color PLA.stl: 205.3 x 159.3 x 75.2 mm; Secondary Color PLA.stl: 151.8 x 54.6 x 51.6 mm; TPU.stl: 154 x 136.3 x 23.9 mm | 3132 likes, 14031 downloads |
| Printables | [3D Printed RC car Tarmo5](https://www.printables.com/model/348623-3d-printed-rc-car-tarmo5) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | END CHASSIS - B06.stl: 58.7 x 58 x 33.7 mm; Bumper - B07-T.stl: 155 x 45 x 14 mm; FRONT A PLATE - B10-T.stl: 85 x 55 x 8 mm | 1609 likes, 8926 downloads |
| Printables | [3D Printed RC Forklift - DIY](https://www.printables.com/model/1058749-3d-printed-rc-forklift-diy) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | 1.) Main Color.stl: 129.8 x 125.5 x 61.7 mm; 2.) Secondary Color.stl: 180.8 x 175.6 x 169.9 mm; 3.) Third Color (Highlights).stl: 88.9 x 86.1 x 36 mm | 1787 likes, 8433 downloads |
| Printables | [V2.0 3D Printed RC Skidsteer](https://www.printables.com/model/544937-v20-3d-printed-rc-skidsteer) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | 6.) Wheel.STL: 30 x 30 x 16 mm; 4.) Left Arm.STL: 106.1 x 65.4 x 13.4 mm; 21.) Claw.STL: 79.4 x 45.6 x 44.6 mm | 2334 likes, 4965 downloads |
| Printables | [3D printed RC Jet boat OLD DESIGN](https://www.printables.com/model/51680-3d-printed-rc-jet-boat-old-design) | CC-BY-NC | adapt OK, credit, non-commercial | — | 454 likes, 3018 downloads |
| Printables | [STREET BASHER 3D PRINTED RC CAR 1/7](https://www.printables.com/model/700706-street-basher-3d-printed-rc-car-17) | CC-BY-NC | adapt OK, credit, non-commercial | — | 528 likes, 2378 downloads |
| Printables | [V2.0 3D Printed RC DumpTruck](https://www.printables.com/model/649741-v20-3d-printed-rc-dumptruck) | CC-BY-NC | adapt OK, credit, non-commercial | — | 527 likes, 1980 downloads |
| Printables | [3D Printed RC LogTruck - DIY](https://www.printables.com/model/1391190-3d-printed-rc-logtruck-diy) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | — | 565 likes, 2047 downloads |
| Printables | [Archer - Oblique Wing RC Plane (flown printed swing wing)](https://www.printables.com/model/1232467-archer-oblique-wing-rc-plane) | Standard Digital File | print as-is only (no remix) | read (User Guide v1.0.0 + BOM sheet): span 1500 mm, 29 dm2, 1400 g empty / 1700 g MTOW, stall 10 m/s; pivot M6x55 bolt in 2 flanged nylon bushings 6x8x8; sweep 0-45 deg by PowerHD LF-20MG (20 kg.cm) via 50 mm M3 ball-link rod; 12x10 spar, 14x12x455 boom; LW-PLA 1 wall 5 % infill |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com 3D printed RC plane wing pivot`
- web search: `site:grabcad.com/library 3D printed RC plane wing pivot`
- web search: `3D printed RC plane wing pivot STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/3d-printed-rc-plane-wing-pivot/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new, borrowing only Archer's arrangement (a steel pin through bushing faces top and bottom, infill raised round it); the Printables hits are RC-car parts.

### `kerf find "RC plane tail boom mount"` (2026-11-01)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [RC Plane Tail Wheel Assemblies and Tail Skids](https://www.printables.com/model/201589-rc-plane-tail-wheel-assemblies-and-tail-skids) | CC-BY | adapt OK, credit | Fixed_Tail_Wheel.stl: 62.5 x 27 x 15 mm; Tail_Skid_1.stl: 62.5 x 15 x 15 mm; Steerable_Tail_Wheel_2.stl: 34 x 15 x 11.8 mm | 26 likes, 181 downloads |
| Printables | [RC Plane Tail Steering Wheel](https://www.printables.com/model/235636-rc-plane-tail-steering-wheel) | CC0 | adapt OK, credit | Fuselage Plate.stl: 60.2 x 26.4 x 17.3 mm; Rudder Plate.stl: 30 x 16 x 2.1 mm; Rudder Guide.stl: 18.9 x 15 x 9 mm | 37 likes, 232 downloads |
| Printables | [RC Plane Tail Wheel Hanger](https://www.printables.com/model/70215-rc-plane-tail-wheel-hanger) | CC-BY-NC | adapt OK, credit, non-commercial | RC Wall Hanger ( 1 Slot ).stl: 90 x 41.5 x 25 mm; RC Wall Hanger ( 3 Slot ).stl: 90 x 41.5 x 25 mm; RC Wall Hanger - Extra Long Single.stl: 94.5 x 90 x 25 mm | 11 likes, 71 downloads |
| Printables | [RC Plane tail wire rod](https://www.printables.com/model/754770-rc-plane-tail-wire-rod) | CC-BY-NC | adapt OK, credit, non-commercial | no STL files | 3 likes, 16 downloads |
| Printables | [180mm wall hook for RC planes tails.](https://www.printables.com/model/1044515-180mm-wall-hook-for-rc-planes-tails) | CC-BY-NC | adapt OK, credit, non-commercial | — | 12 likes, 87 downloads |
| Printables | [Tail Bracket for RC Plane](https://www.printables.com/model/577937-tail-bracket-for-rc-plane) | CC0 | adapt OK, credit | — | 15 likes, 67 downloads |
| Printables | [Tail Protector for RC 3D Foamy Plane](https://www.printables.com/model/1260681-tail-protector-for-rc-3d-foamy-plane) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | — | 1 likes, 10 downloads |
| Printables | [Rc plane back gear-wheels taildragger](https://www.printables.com/model/777621-rc-plane-back-gear-wheels-taildragger) | CC-BY-NC-ND | print as-is only (no remix) | — | 12 likes, 126 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com RC plane tail boom mount`
- web search: `site:grabcad.com/library RC plane tail boom mount`
- web search: `RC plane tail boom mount STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/rc-plane-tail-boom-mount/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new: a printed sleeve epoxied on the boom end (Archer cross-bolts its tube; our 8x6 tube is not drilled). The hits are tail wheels, wall hangers and a helicopter antenna mount.

### `kerf find "oblique wing RC plane"` (2026-11-01)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [21700 4s2p battery pack (for fix wing RC plane)](https://www.printables.com/model/367683-21700-4s2p-battery-pack-for-fix-wing-rc-plane) | CC-BY | adapt OK, credit | no STL files | 15 likes, 157 downloads |
| Printables | [Cowling and Spinner for Tower Hobbies Phoenix Model Sonic Mk2 Low-Wing RC Plane](https://www.printables.com/model/1704264-cowling-and-spinner-for-tower-hobbies-phoenix-mode) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | soniccowlingr3v3.stl: 102.2 x 89.6 x 77.1 mm; sonic_spinner_base_55mm.stl: 55 x 51.4 x 11.8 mm; sonic_spinner_55mm.stl: 57.8 x 55 x 48 mm | 0 likes, 29 downloads |
| Printables | [RC Glider Plane Wing With High Efficiency Aerofoil](https://www.printables.com/model/720339-rc-glider-plane-wing-with-high-efficiency-aerofoil) | CC-BY-ND | print as-is only (no remix) | Hex Ribs - Hex Ribs.stl: 107.5 x 13.6 x 3 mm; Rib closest to fuselage.stl: 108 x 13.3 x 5 mm; Wing Tip - Wing Tip.stl: 108 x 17 x 13.3 mm | 32 likes, 434 downloads |
| Printables | [Wing  for rc plane](https://www.printables.com/model/426728-wing-for-rc-plane) | CC0 | adapt OK, credit | no STL files | 58 likes, 770 downloads |
| Printables | [LW-PLA RC Plane - Version D Wing](https://www.printables.com/model/392053-lw-pla-rc-plane-version-d-wing) | CC-BY-NC | adapt OK, credit, non-commercial | — | 55 likes, 558 downloads |
| Printables | [RC Plane (Ardupilot Flying Plank / Flying Wing)](https://www.printables.com/model/577694-rc-plane-ardupilot-flying-plank-flying-wing) | CC-BY | adapt OK, credit | — | 52 likes, 489 downloads |
| Printables | [Version A Wing - LW-PLA RC PLANE](https://www.printables.com/model/1402225-version-a-wing-lw-pla-rc-plane) | CC-BY-NC | adapt OK, credit, non-commercial | — | 16 likes, 131 downloads |
| Printables | [wing tip skid for Multiplex Easyglider or any RC plane](https://www.printables.com/model/462655-wing-tip-skid-for-multiplex-easyglider-or-any-rc-p) | CC-BY | adapt OK, credit | — | 11 likes, 95 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com oblique wing RC plane`
- web search: `site:grabcad.com/library oblique wing RC plane`
- web search: `oblique wing RC plane STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/oblique-wing-rc-plane/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Archer did not show up in this search; the other hits do not pivot the wing.
