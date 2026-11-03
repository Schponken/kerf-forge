# Hawk electrical contract — not cleared for flight

The missing wiring graph is declared; this is not electrical or flight approval. The stock motor pigtails fail
the existing burst-heating rule, and the conservative cruise-duration calculation misses the existing target.
No current limit, wire upgrade, thermal threshold, endurance target or existing catalog rating was changed.

Power: 6S battery → XT60 → FC BAT/current sensor → FC ESC pads → Skywalker ESC → motor. Retain the supplied
12 AWG battery/input leads and 100 mm 14 AWG ESC phase leads plus 265 mm 18 AWG motor pigtails. The complete
phase path is conservatively modelled at the thinnest stock gauge, 18 AWG. Do not label the motor pigtails 14 AWG.

The ESC's separate 5 V / 7 A BEC feeds only the two MG996R sweep servos (5 A combined catalog stall). The FC Vx
BEC, bridged to 6 V, feeds the four X08 surface servos (3.6 A combined stall, 4.5 A continuous / 7 A peak supply).
FC 4V5/5 V powers receiver, GPS, TX800 and camera (1.1 A combined catalog peripheral draw). The existing FC
consumption override remains an unverified conservative bound; no assumed reduction was used to improve endurance.
Keep common ground; isolate the ESC BEC's positive wire from the FC rail. Verify actual rail voltage/polarity before
connecting electronics, particularly the 5 V-only receiver.

| FC output | Load |
|---|---|
| S1 | ESC throttle |
| S3 / S4 | Right / left sweep |
| S5 / S6 | Right / left aileron |
| S7 / S8 | Elevator / rudder |

[Matek's August 2025 manual](https://www.mateksys.com/downloads/Manual/F405-WMO_Manual.pdf) identifies S1/S2 as TIM8,
S3/S4 as TIM1 and S5–S8 as TIM2. Configure TIM1 and TIM2 for normal servo PWM in the INAV mixer/output settings;
retain normal PWM for the Skywalker. Do not leave S3/S4 assigned as additional motors or enable DShot on the servo
timer groups. This branch declares the signal mapping; it does not claim a flight controller has been configured.
GNSS uses UART4 plus I2C; CRSF uses UART2; TX800 control uses TX3 and video uses the FC Cam/VTx pads.

Routes use the existing glove, hub and rounded wing channels. Hub/panel waypoints move with their parts. Each
rounded wing channel arc is represented by eight chords. Tail leads leave through the flight lead's fuselage
side opening at x190,z−38, then follow the boom externally underneath; they never pass the transverse clamp screw.
The coordinate helper obtains electronics locations from the shared layout. Cut lengths and all-pose physical
clearance still require the lead's integrated CAD route check; no route-clearance pass is claimed here.

Retain factory servo female plugs. Each of six extension ends uses three [Pololu #1931 male crimp pins](https://www.pololu.com/product/1931)
in the existing #1902 1×3 housing: 18 pins and six housings in the explicit BOM. The manufacturer supports
22–28 AWG and 2.54 mm pitch; both extension gauges fit. Its page publishes no current rating or mass, so those
remain unknown. Mark polarity, insulate joints and secure plugs/strain relief. Pass each tail plug through the
service opening separately; thread wing connector pins before assembling their housing.

## Measured software evidence

At a **simulated 1800 g total mass**, the complete stock electrical graph estimates 4.760 A average, 51.214 A peak
and **18.15 minutes** against the unchanged **20-minute** requirement. At simulated 2155.1 g it estimates 15.92 min.
These masses are fixture inputs, not the final integrated aircraft mass. Declared wire mass is 109.72 g; full
servo-run lengths are conservatively counted in addition to the servo catalog masses because their stock lead
gauges/lengths are not all published. This is not a measured physical wire harness mass.

The stock phase run produces **227.054 K** calculated rise at 48.33 A over 10 s, versus the unchanged **60 K**
allowance. That is the sole hard rating failure in the current-only fixture; the power requirement remains FAIL.
The [iFlight test sheet](https://shop.iflight.com/image/catalog/TEST%20REPORT/XING-2806.5-1300KV.png) confirms the
18 AWG / 265 mm lead and 48.33 A peak figure. No unverified factory winding-termination modification is assumed.

Clean tested code: `b23e67c78750d017134e903caa4d70f123db68e0`. Six focused fixtures passed, covering feeds, separate
rails, unique outputs, parameter-aware/moving routes, connector quantities and honest failure reporting. Command:

```sh
PYTHONPATH="$PWD" .venv/bin/python -m pytest -q tests/test_hawk_wiring.py \
  --junitxml=.cache/hawk-wiring/results.xml
```

The current-only fixture replaces spatial queries with zeros and supplies a stated mass; it cannot establish
route clearance, final mass, strength, measured runtime or flight readiness. No actual project build, FEA,
installed-source write or full suite was run by the wiring worker. The flight lead owns the integrated gate.
