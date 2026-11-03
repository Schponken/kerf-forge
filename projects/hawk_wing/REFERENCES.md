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
