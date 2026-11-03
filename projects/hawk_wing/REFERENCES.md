# hawk_wing: references

Research for the ~1.0 m swing-wing FPV plane: fixed glove to |y| ~150 mm, outer panels (~350 mm) sweeping 0-65 deg about
a vertical 5 mm steel pin in two 625 bearings, MG996R in a nacelle driving a 13 T pinion / 21 T sector, tractor 2806.5
1300KV on 6S 1800, conventional tail on an 8x6 CF boom, camera in the nose. Everything below was opened on 2026-11-02.
Shared evidence is NOT repeated here: motor/prop/tail volume/wing area/airfoil numbers, the LisHawk, LisEagle, Wanner 2026,
Archer, DTFB/XFly F-14 rows and the sweep-schedule decisions are in `projects/drone_foldable_wings/REFERENCES.md` and
`references/INDEX.md` ("Variable-sweep and morphing wings" rows). "Read" = stated on the page; "derived" = my arithmetic.

## New references used by this project

| Source | Link | License | What it gives (numbers) |
|---|---|---|---|
| Luckring 2016 (NASA NTRS 20160010101), Polhamus outboard pivot | https://ntrs.nasa.gov/api/citations/20160010101/downloads/20160010101.pdf | NASA, public | Fixed centreline pivot: lift shifts aft faster than the CG, aircraft 'too stable' when swept; fixed outboard pivot on a gloved wing 'greatly reduced' the aerodynamic-centre shift (qualitative: no percentage and no pivot semispan fraction in the text; Figs 23-24 not extracted). Row added to references/INDEX.md. |
| ServoCity 5 mm stainless shafting | https://www.servocity.com/5mm-stainless-steel-precision-shafting/ | vendor page | 50-300 mm lengths, $2.39-4.79; no tolerance/hardness published. Catalog: rods.ss_rod_5. |
| SKF 7500625ZZ (Kramp) | https://kramp.com/shop-de/en/p/deep-groove-ball-bearing-5x16x5mm-skf--7500625ZZ | vendor datasheet page | 5 x 16 x 5; C0 = 380 N static, C = 1140 N dynamic radial. Catalog: bearings.625 (static_load_n / dynamic_load_n). NSK/Daiwa quote 670-675 / 1730 N. |
| 3DJake F625ZZ 8-pack | https://www.3djake.com/3djake/ball-bearing?sai=33706 | vendor page | $6.54 per 8 ($0.82 each), in stock. Catalog price bearings.625. |
| INAV docs: Failsafe.md, Mixer.md, Programming Framework.md, rx.c | https://github.com/iNavFlight/inav/blob/master/docs/Failsafe.md ; .../docs/Mixer.md ; .../docs/Programming%20Framework.md ; .../src/main/rx/rx.c | GPL-3.0 (docs read; no code copied) | Setting names in "INAV / ELRS setup facts" below. |
| ExpressLRS PWM receiver docs | https://www.expresslrs.org/hardware/pwm-receivers/ | docs | Receiver-side failsafe defaults (PWM receivers only): 1500 us on all outputs except Output 3 at 988 us, settable 988-2012 us in the PWM Output WebUI; failsafe when LQ drops to 0 or 1 s passes without a valid channels packet. |

## Existing designs (kerf find)

### `kerf find "swing wing rc plane"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [RC Glider Plane Wing With High Efficiency Aerofoil](https://www.printables.com/model/720339-rc-glider-plane-wing-with-high-efficiency-aerofoil) | CC-BY-ND | print as-is only (no remix) | Hex Ribs - Hex Ribs.stl: 107.5 x 13.6 x 3 mm; Rib closest to fuselage.stl: 108 x 13.3 x 5 mm; Wing Tip - Wing Tip.stl: 108 x 17 x 13.3 mm | 32 likes, 435 downloads |
| Printables | [Wing  for rc plane](https://www.printables.com/model/426728-wing-for-rc-plane) | CC0 | adapt OK, credit | no STL files | 58 likes, 770 downloads |
| Printables | [LW-PLA RC Plane - Version D Wing](https://www.printables.com/model/392053-lw-pla-rc-plane-version-d-wing) | CC-BY-NC | adapt OK, credit, non-commercial | Wing - 4 - 2 (B).stl: 42.9 x 42.5 x 8.1 mm; Wing - 4 - 1 (B).stl: 112 x 44.4 x 25.2 mm; Wing - 4 - 2.stl: 42.9 x 42.5 x 8.1 mm | 56 likes, 559 downloads |
| Printables | [RC Plane (Ardupilot Flying Plank / Flying Wing)](https://www.printables.com/model/577694-rc-plane-ardupilot-flying-plank-flying-wing) | CC-BY | adapt OK, credit | no STL files | 52 likes, 489 downloads |
| Printables | [Version A Wing - LW-PLA RC PLANE](https://www.printables.com/model/1402225-version-a-wing-lw-pla-rc-plane) | CC-BY-NC | adapt OK, credit, non-commercial | — | 16 likes, 131 downloads |
| Printables | [wing tip skid for Multiplex Easyglider or any RC plane](https://www.printables.com/model/462655-wing-tip-skid-for-multiplex-easyglider-or-any-rc-p) | CC-BY | adapt OK, credit | — | 11 likes, 95 downloads |
| Printables | [21700 4s2p battery pack (for fix wing RC plane)](https://www.printables.com/model/367683-21700-4s2p-battery-pack-for-fix-wing-rc-plane) | CC-BY | adapt OK, credit | — | 15 likes, 157 downloads |
| Printables | [Version C Wing - LW-PLA RC PLANE](https://www.printables.com/model/1402224-version-c-wing-lw-pla-rc-plane) | CC-BY | adapt OK, credit | — | 12 likes, 87 downloads |
| Printables | [Archer - Oblique Wing RC Plane v2](https://www.printables.com/model/1232467-archer-oblique-wing-rc-plane) | Standard Digital File Licence (numbers only) | print as-is only (no remix) | span 1500 mm, pivot M6 bolt in 2 bushings, LF-20MG servo + M3 rod, sweep 0-45 deg (see references/INDEX.md) |  |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com swing wing rc plane`
- web search: `site:grabcad.com/library swing wing rc plane`
- web search: `swing wing rc plane STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/swing-wing-rc-plane/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Archer (Printables 1232467, the only flown printed swing wing) is evidence only: Standard Digital File Licence allows numbers, not geometry, and it is a 1.5 m oblique wing on an M6 bolt, not an outboard-pivot glove. MakerWorld swing-wing hits (F-14, MiG-23, Tu-22M) are scale/display models with hand-swept wings (search snippets only, pages not opened); none is RC-flyable with a servo drive. The Printables wing hits (CC0 / CC-BY 426728, 577694, 1402224) are fixed-wing skins and not used.

### `kerf find "wing pivot servo gear"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| — | nothing found | | | | |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com wing pivot servo gear`
- web search: `site:grabcad.com/library wing pivot servo gear`
- web search: `wing pivot servo gear STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/wing-pivot-servo-gear/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. No printed sector-gear wing drive exists; the gear module (2), 13 T pinion / 21 T sector, and the 25T aluminium horn come from the catalog and the sibling projects/drone_foldable_wings/REFERENCES.md (Archer drives with a pushrod; LisHawk/Wanner use X08-class servos on linkages).

### `kerf find "rc plane glove centre section"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| — | nothing found | | | | |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com rc plane glove centre section`
- web search: `site:grabcad.com/library rc plane glove centre section`
- web search: `rc plane glove centre section STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/rc-plane-glove-centre-section/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Nothing found; the glove concept itself is Polhamus' outboard pivot (references/INDEX.md, Luckring 2016) and the pivot hub is Archer-like (steel pin in bearings, locally dense infill) with 625 bearings instead of bushings.

### `kerf find "fpv plane nose camera mount"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [FPV nose for RC plane](https://www.printables.com/model/1466014-fpv-nose-for-rc-plane) | CC0 | adapt OK, credit | FPV RC plane nose.stl: 121 x 116.5 x 92.9 mm | 3 likes, 12 downloads |
| Printables | [M42 Lens to 1.25" adapter for cameras planetary cameras with 12.5mm back focus. With vixen-plate and tripod mount and 3D-pritnable nosepiece](https://www.printables.com/model/355354-m42-lens-to-125-adapter-for-cameras-planetary-came) | CC-BY | adapt OK, credit | M42-ASI.stl: 75.8 x 70 x 50.8 mm; NosePiece_T2-1p25_v1.stl: 44 x 44 x 24 mm | 16 likes, 111 downloads |
| Printables | [Mini Drak Nose Camera Mount](https://www.printables.com/model/356645-mini-drak-nose-camera-mount) | CC-BY | adapt OK, credit | drak_split_1177_singleCam_base.stl: 90.6 x 41.3 x 11.4 mm; cover_only_revB_18p4mm_lens_hole.stl: 89.7 x 39.8 x 29.8 mm; minidraknose_1177_only_1pc.stl: 90.6 x 45.5 x 41.5 mm | 0 likes, 16 downloads |
| Printables | [Rite Wing Super Spec Caddx Tarsier v2 Nose Camera Mount](https://www.printables.com/model/278808-rite-wing-super-spec-caddx-tarsier-v2-nose-camera-) | CC-BY | adapt OK, credit | RiteSpuerSpecTarsierV2.stl: 57.5 x 51.5 x 31.4 mm; RiteSpuerSpecTarsierV2_v2.stl: 57.5 x 51.5 x 31.4 mm; RiteSpuerSpecTarsierV2_no_lead_v1.stl: 57.5 x 51.5 x 31.5 mm | 0 likes, 11 downloads |
| Printables | [Prusa Mini HeatBreak Fan Noise Reducer compatible with Raspberry Pi Camera V2.1 mount](https://www.printables.com/model/152426-prusa-mini-heatbreak-fan-noise-reducer-compatible-) | CC0 | adapt OK, credit | — | 9 likes, 51 downloads |
| Printables | [AtomRC Dolphin Thumb Pro nose with 19mm camera mount](https://www.printables.com/model/694390-atomrc-dolphin-thumb-pro-nose-with-19mm-camera-mou) | CC-BY | adapt OK, credit | — | 5 likes, 55 downloads |
| Printables | [Heewing T1 Vented Nose VTX and Camera Mount](https://www.printables.com/model/1034694-heewing-t1-vented-nose-vtx-and-camera-mount) | CC-BY-NC | adapt OK, credit, non-commercial | — | 0 likes, 62 downloads |
| Printables | [ZOHD Talon GT Rebel nose cone integrated micro camera mount and naca duct](https://www.printables.com/model/1486257-zohd-talon-gt-rebel-nose-cone-integrated-micro-cam) | CC-BY-NC | adapt OK, credit, non-commercial | — | 1 likes, 14 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com fpv plane nose camera mount`
- web search: `site:grabcad.com/library fpv plane nose camera mount`
- web search: `fpv plane nose camera mount STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/fpv-plane-nose-camera-mount/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: adapt as an idea only (no geometry copied). Closest fits: Rite Wing nose camera mount (Printables 278808, CC-BY) and AtomRC Dolphin Thumb Pro 19mm camera nose (694390, CC-BY): a printed nose with a camera cradle and a removable cap; the catalog camera drone.cameras.micro_19mm sets the pocket, so the cradle is drawn from the catalog dimensions. CC-BY-NC hits (Heewing, ZOHD) are numbers-only for a non-commercial use and not used.

### `kerf find "tail boom clamp 8mm"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| Printables | [Thunder tiger Raptor 30/50/SE Tail boom clamp](https://www.printables.com/model/657373-thunder-tiger-raptor-3050se-tail-boom-clamp) | CC-BY | adapt OK, credit | Tail Boom Clamp.STL: 31.5 x 26 x 10 mm | 1 likes, 39 downloads |
| Printables | [MULTI-TOOL ___ Barrel Clamp Picatinny Rail Mod + Frontgrip (Boom Grip)](https://www.printables.com/model/1230632-multi-tool-___-barrel-clamp-picatinny-rail-mod-fro) | CC-BY-NC-SA | adapt OK, credit, non-commercial, share-alike | Barrel_Clamp_Picatinny_Rail_(front).stl: 47.9 x 43.9 x 26.2 mm; Barrel_Clamp_Picatinny_Rail_(rear).stl: 47.9 x 43.9 x 12 mm; Front_Grip_Multi-Tool_(short).stl: 95.6 x 62 x 38.6 mm | 4 likes, 32 downloads |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com tail boom clamp 8mm`
- web search: `site:grabcad.com/library tail boom clamp 8mm`
- web search: `tail boom clamp 8mm STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/tail-boom-clamp-8mm/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Thunder Tiger Raptor boom clamp (Printables 657373, CC-BY) is a 31.5 x 26 x 10 mm helicopter clamp, which only confirms the split-clamp-plus-one-screw approach; our socket is sized to the catalog cf_tube_8x6 (8 mm OD) with a clamp coupon. Archer holds a 14x12 boom with M3 screws through cross holes 25-27 mm from the ends (INDEX).

### `kerf find "wingtip skid"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| — | nothing found | | | | |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com wingtip skid`
- web search: `site:grabcad.com/library wingtip skid`
- web search: `wingtip skid STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/wingtip-skid/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Printables 462655 (CC-BY, Multiplex Easyglider skid) is the same idea (replaceable printed tip skid) but geometry-free here: ours must fit the tip rib of the swept panel and be the cheap, first-to-break part; adapt only the idea.

### `kerf find "servo pod nacelle"` (2026-11-02)

| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |
|---|---|---|---|---|---|
| — | nothing found | | | | |

Not searched by script (run these, add fits with `kerf find --add`):
- Thingiverse: set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) to search Thingiverse; its website blocks scripted access
- web search: `site:makerworld.com servo pod nacelle`
- web search: `site:grabcad.com/library servo pod nacelle`
- web search: `servo pod nacelle STEP model site:mcmaster.com`
- McMaster-Carr (purchased hardware): https://www.mcmaster.com/products/servo-pod-nacelle/ — download the part's STEP by hand into catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)

Decision: design new. Nothing found; the nacelle holds an upright MG996R (dimensions from the catalog) and carries the glove lower plate loads, so it is sized from the catalog servo and the gear centre distance, not from a model.

## INAV / ExpressLRS setup facts (for the setup notes)

The ELRS Nano receiver talks CRSF to the F405-WMO, so the sweep servos are driven by the FC, not by the receiver; the
receiver-side PWM failsafe values do not apply (they only exist on PWM receivers). INAV's own failsafe decides.

(a) Fixed value on failsafe. INAV rx.c (read): while the receiver is in failsafe the "last good input values are
retained", so a servo mixer fed by an RC channel HOLDS the last sweep angle in failsafe (the wings would stay swept).
Failsafe.md: failsafe starts when a flight channel sends no pulses, a channel leaves `rx_min_usec`..`rx_max_usec`, or
the FAILSAFE aux mode is on. Programming Framework.md lists the condition operand FLIGHT `Is Failsafe` (id 24, boolean)
and the action `Override RC Channel` (id 38, "operand A should normally be set as a Value, NOT as Get RC Channel").
So: logic condition `Is Failsafe` -> `Override RC Channel` <sweep channel> = spread value (UNVERIFIED on hardware:
the docs do not say the override is applied while failsafe is active; test with the props off).
`rxfail` is Betaflight, NOT in INAV docs (grep of Cli.md, Settings.md, Rx.md, Failsafe.md: no hit). The ELRS PWM-receiver
failsafe default is 1500 us, which is mid-sweep, if a PWM receiver were ever used.

(b) Elevator from an RC channel. Mixer.md servo mixer inputs (verbatim): `RC ROLL` 4, `RC PITCH` 5, `RC YAW` 6,
`RC THROTTLE` 7, `RC channel 5` 8 ... `RC channel 8` 11, `RC channel 9` 15 ... `RC channel 16` 22 (raw channels),
`Stabilised ROLL/PITCH/YAW/THROTTLE` 0-3, `FIXED-VALUE (MAX)` 29 ("fixed percentage of total range"). Command:
`smix <n> <servo_index> <input_id> <weight> <speed> <logic_condition_id>`; weight range [-1000, 1000], 0 disables the
rule; per-servo `servo <n> <min> <max> <mid> <rate>` with rate [-125, 125]. Elevator trim vs sweep: add a second `smix`
rule on the elevator servo with input = the sweep RC channel (e.g. `RC channel 6`, id 9) and a weight that is the
trim change per unit sweep (to be measured; sign and size UNVERIFIED).

(c) Failsafe procedure (Failsafe.md): `failsafe_procedure` = `DROP` (kill motor and disarm), `LAND` (replaces
`SET-THR` from INAV 4.0; emergency landing, fixed-wing spirals down using `failsafe_fw_roll_angle` -200 (deci-deg),
`failsafe_fw_pitch_angle` 100, `failsafe_fw_yaw_rate` -45 deg/s), `RTH` (needs GPS; the F405 + M9N GPS is in the BOM),
`NONE`. Also `failsafe_delay` (0.1 s units, guard time before activating), `failsafe_recovery_delay`,
`failsafe_throttle` (default 1000), `failsafe_throttle_low_delay`. Recommended for this plane: `failsafe_procedure =
RTH`, with a landing fallback; the wing must be spread before RTH (the plane glides/lands at the spread stall speed).

## Decisions this supports

1. **Pivot = fixed outboard pivot on a glove** (Luckring 2016 / Polhamus: all production variable-sweep aircraft in
   the NASA chart used it; the root pivot shifts lift aft faster than the CG). The 80 mm vs 300 mm lift-shift numbers
   in the option quote are Kerf's estimate, not NASA's: UNVERIFIED.
2. **Bearing = two 625 (5x16x5) on a 5 mm steel pin** (Archer proves steel pin in plastic bushings top and bottom).
   Use C0 = 380 N (SKF, lowest published) for the couple check; shielded miniature bearings are not moment bearings, so
   keep the bearing spacing (the glove depth, ~26 mm) as large as possible and treat the pin as soft stainless (no
   hardness published for ss_rod_5). Pin length: 50-300 mm stocked; ServoCity sells it cut, so pick the next length up
   (e.g. 50 mm) and trim.
3. **Sweep actuator sizing rule** (LisEagle, INDEX): hold the folded section against 1.5 x its drag at top speed, and
   check the stall torque against the spread-wing aerodynamic hinge moment with hard stops at 0 and max sweep (sibling
   decision 6: land on the stop). MG996R through 13/21 gives torque x 21/13 = 1.6 at the panel (derived).
4. **Failsafe-to-spread** needs an INAV logic condition (Is Failsafe -> Override RC Channel), because INAV holds the
   last RC values in failsafe.
5. **Roll by asymmetric sweep is weak at low angle of attack** (LisEagle, Wanner 2026): ailerons stay.
6. **Tail volume must cover the SPREAD wing** (sibling decision 4: C_H >= 0.5, C_V >= 0.038 referenced to the spread
   wing; LisHawk's spread wing + small tail was unstable). The glove being fixed keeps the shift small (decision 1) but does not remove it.
7. **Tail boom** is the catalog 8x6 CF tube (tensile 400 MPa low end, 28 GPa) in a split socket with one M3 clamp.

## Open questions / UNVERIFIED (Spencer to measure)

- Real diameter of the ServoCity 5 mm pin (no tolerance published) and the press fit to the 625 bore: measure with
  calipers; print a bore coupon.
- The aerodynamic-centre shift with this glove (80 vs 300 mm): not in Luckring 2016; needs a vortex-lattice run or a
  flown CG test.
- MG996R holding torque at the panel versus the hinge moment at high CL, and whether the 13/21 pair survives the shock
  of a landing on the sweep stop.
- Whether `Override RC Channel` takes effect during INAV failsafe (docs silent); bench-test with props off.
- Elevator trim weight per degree of sweep: tune in flight.
- 625 load figures differ by maker (380 vs 675 N static); which bearing you actually receive is unknown.

## Folding-wing gliders (Spencer's note, 2026-11-02)

Spencer asked to look at folding-wing gliders and to take inspiration from real-world folding-wing jets and drones.
About 10 pages opened. Honest finding: no open RC folding-wing glider with published pivot dimensions, mass and span
turned up; what exists is patents, one paper, and printable toys. Search snippets are marked "(snippet)".

| Source | URL | Licence | What it establishes |
|---|---|---|---|
| US 9,975,622 B2, Snook / Blue Bear, 'Morphing foil or wing' | https://patents.google.com/patent/US9975622 | Active patent (to 2034, Google's assumption); ideas only | Servo-driven sweep with a main pivot on upper and lower race bearings (acetal shells). The servo arm is spring-biased toward both end positions; an elastic element pulls the tip toward extended (more tension when tucked); nylon-cord limiters stop over-extension. No separate latch. No dimensions or mass (ratios only). |
| US 4,836,817 'Folding wing toy glider' (expired) and Sling Wing (MakerWorld 385029, printable, built on it) | https://patents.google.com/patent/US4836817 , https://makerworld.com/models/385029 | Patent expired; model licence not read (page blocked, 403 on Printables mirror) | Chordwise tape hinge on the centreline; a rubber band pulls the wings open to 12-40 deg sweep (12-18 preferred), 1-3 deg dihedral per panel; launched folded, the band opens them when speed drops. Elastic-to-spread works at toy scale. |
| ICAS 2010-423, MiMo-UAV variable-sweep mini-UAV | https://icas.org/ICAS_ARCHIVE/ICAS2010/PAPERS/423.PDF | Paper, (c) authors; reference only | 3.67 kg, 1.6 m, AR 6, 8-10 kg/m2, two outboard pivots, servo, up to 40 deg sweep. Datcom at 40 deg: Cm_alpha doubles (-0.0177 -> -0.0333), Cl_beta jumps about 23x, lift falls and drag rises. Pivot load concentration and left/right sync named as the hard parts. |
| Model Aviation / outerzone / UC 'Intro to R/C gliders' (thermal reference points) | https://library.modelaviation.com/article/zephyr , https://outerzone.co.uk/plan_details.asp?ID=6020 , https://www.mat.uc.pt/~pedro/ncientificos/artigos/intro_rc_glider.html | Articles; numbers only | (snippet) a hand-launch glider built to 4 oz/ft2 (= 12 g/dm2) at 10 oz; Stylus 40 in span, 344 in2 (AR 4.6, derived); Alcyone 2M 8.5 oz/ft2 (= 26 g/dm2), Thermal Modi 12.4 oz/ft2 (= 38 g/dm2) (snippet); hand-launch class up to 1.5 m span (read). The UC page gives no numeric loading or AR. |
| XB-70 drooping wingtips (VT presentation via search; Cranfield 'in-flight folding wingtip system') | https://dspace.lib.cranfield.ac.uk/handle/1826/13881 | Paper; ideas only | (snippet) Outer panels hinged down 25 deg in flight (hydraulic) for subsonic flight: more vertical area and less aft wing area to offset the aft lift shift. Chordwise fold hinge, a different axis from our vertical pivot. |
| Prior in this file: LisEagle / LisHawk, Luckring 2016 (outboard pivot on a glove), Archer pin and bushings | see sections above | see INDEX.md | Already cover the actuator rule (1.5 x folded drag) and pivot layout. |

### Ideas and decisions for hawk_wing

1. **Adopt: a spring that biases both panels toward SPREAD** (Snook patent spring-biased arm; US4836817 elastic open;
   MiMo needs a servo to hold the sweep). Sized so the spring beats pivot friction plus the panel's aerodynamic hinge
   moment at dive speed, but the servo (MG996R, stalls against it) still holds the swept position. This turns
   "spread on signal loss" from an INAV logic-condition trick (decision 4 above) into hardware that also works on a
   dead servo or brown-out. Spring torque is a number to calculate; none is published.
2. **Adopt: hard stops at 0 and 65 deg plus nylon-cord or printed travel limiters**, so the servo does not carry the
   end-of-travel shock (Snook limiters; consistent with decision 3). Keep the upper-and-lower bearing pair (Snook,
   Archer).
3. **Reject: chordwise fold hinge** (US4836817, Sling Wing, XB-70 tips): it folds the panel up or down, which does not
   give sweep for a straight dive and puts the hinge bending on one printed knuckle. Also reject a tape hinge.
   Keep the vertical pivot.
4. **Context, derived:** hawk_wing at 85 g/dm2 (8.5 kg/m2) matches MiMo-UAV (8-10 kg/m2) but is 2.2-3.3x the 26-38 g/dm2 of
   2 m thermal models and 7x a 12 g/dm2 hand-launch floater. Sink rate scales with the square root of loading, so it
   will sink about 1.8x (vs 26 g/dm2) to 2.6x (vs 12 g/dm2) faster at its best glide speed: it is a motor-assisted
   cruiser that can glide, not a thermal soarer. Sell the spread mode as slow, stable and soft landing, not thermalling,
   or move the target loading down (a lower-mass or bigger-area redesign).
5. **Plan the spread CG:** MiMo Datcom shows sweeping adds pitch stability and a big dihedral effect (Cl_beta x23),
   so a plane trimmed for the swept case may be roll-sluggish and the spread case is the critical one for CG and tail
   volume (matches decision 6). Expect aileron-roll authority to fall as sweep rises.
6. **Real-world inspiration kept:** F-14 and the other variable-sweep jets use the outboard fixed pivot on a glove
   (Luckring); XB-70 shows the tips-down fold as a stability aid (not for us); tube-launched drones use a spring to
   open the wings fast (spring housing + torque tube, from the patents list seen in search) - the same spring-to-spread
   idea as bullet 1.

### Open questions

- Spring torque and rate needed at the pivot: needs the hinge moment at CL max and dive q (not in any source read).
- Does a spring that opens the wings fight the MG996R hold (current, heat) at 65 deg? Over-centre detent instead?
- Sling Wing's actual licence and fold geometry (page blocked) - read it in a browser.
- No source gives a published flown pivot size (pin diameter, bearing spacing) for a ~1 m sweep model: our 5 mm pin and
  2x 625 stay Kerf's calculation, not a proven design.
- Real thermal-capable 1 m span loading: sources read give only 2 m-class numbers; check a 1 m F5J or hand-launch kit spec.

## What breaks on these aircraft and how builders fixed it (Spencer's note, 2026-11-02)

Honest scope: about 14 pages opened. No published failure log exists for a ~1 m printed swing-wing with a servo-and-gear
sweep drive. What exists is (a) one RC swing-wing build report (DTFB F-14), (b) full-scale swing-wing history, (c) printed
FPV/sport plane write-ups, (d) general gear, servo, flutter and boom guidance. Rows say which. Searches for Freewing/XFly
F-14 sweep-servo failures, EPFL LisHawk lessons-learned and RC tail-boom-clamp slip returned nothing usable (see Open questions).
"Opened" = fetched and read; "snippet" = seen only in a search result, not opened.

| failure | where reported (URL) | fix builders used | what hawk_wing should do |
|---|---|---|---|
| Sweep servo too slow/weak to move the wings in flight (RC swing wing) | DTFB F-14, FliteTest (opened): https://flitetest.com/articles/dtfb-f-14-with-swing-wings ("didn't have enough torque to move the wings during flight") | Swapped the slow Turnigy TSS-9S for a standard 9 g servo; popsicle-stick arm with several drilled holes to tune leverage | Size sweep torque for air load at dive speed, not static; MG996R + 21/13 gear is 1.6x torque but 0.62x speed, so time the full 65 deg sweep on the bench under a load |
| Wing rubbing on the fuselage / foam wear at the pivot (same build) | same page | Plywood glued where the wing rubs; opened-up rivet sleeve so the screw turns freely | Keep the panel root off the glove with a PTFE or printed-PETG thrust washer and a set gap (suggest 0.5 mm) at the root rib; no PETG-on-PETG rubbing face |
| Control-linkage jam by sliding rod in a slit (same build; maiden crash) | same page | Slit in foam for the stick gave clearance, kept the rod from moving in and out | Route the aileron pushrod/servo lead through the pivot axis with clearance for the full 0-65 deg turn; sweep the check in `kerf check` with the rod in place |
| Sweep mechanism jams and wing cannot unsweep (full-scale XF10F) | Wikipedia Variable-sweep wing (search result, XF10F designers "assumed the wing would unsweep itself"); article body opened gives X-5/XF10F positions, not the jam | Not documented in the opened text; the lesson is fail-to-safe | Spring-to-spread bias (decision 1 above) so a dead or jammed servo leaves the panels spread; hard stops at 0 and 65 deg |
| One wing swept, one not (asymmetric failure) | Wikipedia Variable-sweep wing (opened): F-14 caption names one wing at min and one at max sweep as an in-flight failure case; full-scale F-14 links the two sides by a crossover shaft (search snippet only) | Mechanical cross-link between the two sides | If the two panels have separate servos or gear trains, tie them to one shaft or one driven gear; else add a differential-position INAV check (not available: use a single driven gear train with a common bar) |
| Pitch trim shift with sweep | Wikipedia Variable-sweep wing (opened): sweeping moves the centre of lift; fixes were sliding root, bigger tailplane, or canard; outboard pivots reduce the change but also reduce span variation | Outboard pivot on a glove (F-14 style); retained conventional stabiliser | hawk_wing already uses a glove pivot; still program a sweep-linked elevator trim (a servo-mixer or INAV mixer on the sweep channel) and measure it on first flight; start with the wings spread |
| Sweep-servo travel buzzing/stalling at the end stops; MG996R heat | Supplier guides (opened via search only, vendor text): https://zbotic.in/mg996r-servo-motor-high-torque-projects-control-guide/ ; https://www.kpower.com/insight_servo/1096.html . Claim: usable travel nearer 120 deg; pulses past it make the servo buzz and draw stall current | Stay inside the travel, bulk 470-1000 uF capacitor at the servo, common ground | Panel 65 deg x 21/13 = 105 deg at the servo: inside ~120 deg but only 15 deg spare; put the hard stops on the panel (gear sector or pin), set endpoints so the servo never reaches its own end stop, and add the capacitor near the plug |
| Plastic-gear "MG996R" sold as metal; stripped gears | Vendor pages (search result): https://besomi.com/product/mg996r-servo-motor ; stall 1.3-2.5 A varies by source. The catalog already stores 2.5 A at 6 V (Cornell datasheet) | Buy metal-gear, inspect, treat a plastic gear as the fuse | Buy by metal-gear listing, open one servo and read its gear train before flying; BEC rated above stall of every servo that can stall together |
| Printed gear teeth shear along the layer lines under shock; binding when backlash too small | Sovol gear guide (opened, already in the index): backlash 0.2-0.4 mm total, 4-6 walls, PETG ductile (Tg ~75-80 C), "should not be used in safety-critical or high-torque systems" | Root fillets 0.3-0.5 m, 25 deg pressure angle for a wider root, D-shaft or heat-set plus setscrew rather than press-fit on a plain bore | Print the 13 T / 21 T flat, 6 walls, 25 deg or fillet checked; bench-test torque to 2x the dive hinge moment; clamp the pinion on a metal horn plus grub screw, not a printed horn (see next row) |
| Printed servo horn wears and slips | MakerWorld "Customizable Servo Horn" listing (search snippet, not opened): "printed horns are for prototyping/small loads"; Sovol: avoid press-fit on plain printed bores | Metal horn, keyed or D hub, setscrew into insert | Use a metal servo horn bolted through the 13 T pinion (the catalog horn), thread-lock; do not rely on the 25T spline in PETG |
| Backlash makes the swept wing wobble | Sovol (opened), derived here | The tooth gap itself is needed for printing | Derived, not reported: 0.3 mm gap on a 21 mm pitch radius is 0.8 deg, about 5 mm at a 350 mm panel tip. Keep the spring that spreads the wing preloading the teeth on one flank so the gap never shows in flight |
| Control-surface flutter from linkage slop, loose horn holes, tight-bend pushrod play | Model Aviation Control Surface Flutter (opened): https://library.modelaviation.com/article/control-surface-flutter ; "Slop in linkages or bending structure allows some movement"; ailerons to the tip flutter most | Eliminate slop, static mass balance with solder-weighted 1/16 in (1.6 mm) wire ahead of hinge, seal hinge gaps, epoxy solder joints; if it starts, cut throttle | Hinge line sealed with the tape; drill horn holes to wire diameter + 0.1 mm only; use an L-bend with a keeper or Z-bend with a tight hole; no mass balance is possible on a tape hinge, so check aileron static balance and keep the pushrod rigid. Test: wiggle the aileron at the surface, slop under about 0.5 mm at the trailing edge (a number to set, not from a source) |
| Dark PLA parts warp in sun; PLA softens near 60 C | 3DLabPrint Zivko Edge, a year of flying (opened): https://3dlabprint.com/?p=34931 ; materials page (opened): https://3dlabprint.com/?p=1415291 | Keep dark planes in shade; PETG for motor mounts and springs | PETG (Tg ~75-80 C) is the right choice for the nacelle and gears; keep the white or light colour on the glove/panel skins; park in shade |
| PETG: lower stiffness/strength, weak glue joints | 3DLabPrint materials page (opened): PETG "not recommended for parts that require to be glued to hold together", "more prone to fail mid-flight due to higher G forces" | PLA for whole planes, PETG only for motor mounts, wheels, springs | hawk_wing is PETG throughout, so avoid glue-only joints: bolt the pivot hub and servo nacelle, use epoxy on roughened surfaces plus a mechanical lock (pin or screw) for carbon tubes |
| Spar-socket cracking, root tube buckling, layer delamination | uavmodel blog (opened; no CAD, rules of thumb, UNVERIFIED): https://blog.uavmodel.com/the-case-for-3d-printed-wing-structures/ | Printed bushing oriented vertically (layers along the spar) at the spar penetration; chamfer 0.4-0.6 mm at tube entry; hole 0.2-0.3 mm under tube OD interference, or 0.5 mm oversize filled with thickened epoxy; ribs 2-4 mm; rib spacing 40-50 mm; load-test to 100 % then 150 % design load | Do this at the 8x6 and 6x4 sockets in the glove and panel hub; fit-test on a printed coupon; wet-lay epoxy sleeve at the root; proof-load the wing (with the panel spread) to 150 % of the launch load before flying |
| Crash breaks the tail or small tabs; repair in the field | 3DLabPrint Zivko Edge (opened): "glue joints are probably the strongest parts of the plane" | Cut along the glue line, glue back in 5 min; masking tape + CA for missing bits; reprint in 3 days; extra perimeters and two 1 mm wires per landing-gear leg; larger wheels for grass; EPP foam in the handled fuselage section | Design every part to be re-glued: electronics removable, tail boom and nacelle separable. Belly landing on grass: add a skid or rib under the nacelle and fuselage (a number to set, no source) |
| Boom slips or turns in a one-screw clamp; socket cracks | No RC source found. Analogues (search results only): RC helicopter column on a carbon tail rod separating from its socket (fix: setscrew + epoxy); windsurf boom slip from oversized holes (fix: tight pin fit, carbon wrap) | Pinned or bonded joint instead of friction; tighter hole | Engineering judgement, not sourced: keep the unpluggable clamp but add an anti-rotation flat or a dimple the grub screw seats into, roughen the carbon, and a 0.2 mm interference sleeve; proof-turn test by hand with 1 N.m at the tail before flight |
| Flight-controller loses attitude if autolevel set wrong (loss of the Zivko Edge) | 3DLabPrint Zivko Edge (opened): "turning autolevel feature with wrong set attitude too low" | Retired the plane | Confirm angle mode and the sweep-spread failsafe in the bench, props off, before every first flight of a new sweep state |

### Design actions for hawk_wing (ranked)

1. **Fail to spread, mechanically.** A jammed or dead sweep mechanism has to leave the plane flyable (XF10F designers assumed unsweep; DTFB F-14 flew into a jam). Spring on the spread side (decision 1), hard stops on the panel at 0 and 65 deg, panel-side not servo-side. Sources: Wikipedia Variable-sweep wing, FliteTest DTFB.
2. **Size and test the sweep drive under load, not static.** Torque x ratio (1.6) and speed x 0.62; bench-test the whole 65 deg sweep under a load equal to the dive-speed hinge moment and time it. Source: DTFB servo failure. Inside the servo travel: 65 x 21/13 = 105 deg (< about 120 deg usable, supplier guide).
3. **Use the spring to remove backlash and keep tip play under about 5 mm.** The printed 13/21 gear needs 0.2-0.4 mm of clearance (Sovol); the spring keeps the flank loaded. Derived tip play 0.8 deg x 350 mm = 5 mm.
4. **Verify the servo is metal-gear, add the capacitor and size the BEC for stall.** Sources: vendor listings, Cornell datasheet in the catalog.
5. **Mechanical, not glued, PETG joints.** Bolt the hub and nacelle; epoxy with a mechanical lock for tubes; spar sockets with a vertical bushing, chamfer 0.4-0.6 mm, interference 0.2-0.3 mm; proof-load to 150 %. Sources: 3DLabPrint materials page, uavmodel blog (rules of thumb).
6. **Eliminate linkage slop and seal the hinge line** before the first fast pass. Source: Model Aviation flutter article.
7. **Metal horn plus grub screw on the pinion; 6 walls, root fillets, print the gear flat.** Sources: Sovol, MakerWorld horn note.
8. **Trim for sweep:** sweep-linked elevator trim, first flights spread. Source: Wikipedia Variable-sweep wing.
9. **Pivot wire:** service loop, strain relief, connector under the cap, no wire in the bearing path (no source found; own engineering, check by turning the panel 500 times).
10. **Build repair into the design.** Separable electronics and tail, glue lines as the repair line. Source: Zivko Edge report.

### Open questions

- No published report found of a Freewing/XFly F-14 sweep-servo or gear failure, of servo leads chafing at a model pivot, or of RC tail-boom-clamp slip: search RCGroups threads in a browser (the shell blocks it) before relying on rows labelled "own engineering".
- LisHawk and LisEagle papers (arXiv 2002.02421, 2403.08598) were found by search but not opened for lessons; the 2024 paper states stable flight with failed actuators.
- Is hawk_wing one servo driving both panels or one each? Asymmetric sweep depends on it.
- Needed numbers: hinge moment at dive speed and the spring torque; the proof-load for the sockets; the actual MG996R gear material in the stock we buy.
